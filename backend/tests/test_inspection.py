"""Offline protocol substitutes only: these tests never call a model provider."""
import base64
import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend import inspection
from backend.main import app

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def result():
    # Compute with the real shared JS tool, no fixture containing invented geometry.
    code="import fs from 'node:fs';import {buildingMeshes,executeInspectionTool} from './src/inspection-core.js';const d=JSON.parse(fs.readFileSync('public/data/buildings/nyc-local.json'));console.log(JSON.stringify(executeInspectionTool('compare_observers',{target_ids:d.targets.map(t=>t.id)},d,buildingMeshes(d),d.schemes)))"
    return json.loads(subprocess.check_output(['node','--input-type=module','-e',code],cwd=ROOT,text=True,encoding='utf-8'))

class StubClient:
    def __init__(self, message):
        self.chat=SimpleNamespace(completions=self)
        self.message=message
    def create(self,**kwargs):
        assert kwargs['extra_body']=={'thinking':{'type':'disabled'}}
        return SimpleNamespace(choices=[SimpleNamespace(message=self.message)])

def test_plan_real_target_parameters_via_explicit_stub():
    ids=[t['id'] for t in inspection.dataset()['targets']]
    msg=SimpleNamespace(tool_calls=[SimpleNamespace(id='offline-stub',function=SimpleNamespace(name='compare_observers',arguments=json.dumps(dict(target_ids=ids))))])
    result=inspection.plan('比较方案',StubClient(msg))
    assert result['tool_name']=='compare_observers'
    assert result['arguments']['target_ids']==ids

def test_rejected_model_arguments_preserve_usage():
    msg=SimpleNamespace(tool_calls=[SimpleNamespace(id='offline',function=SimpleNamespace(name='analyze_batch',arguments=json.dumps({'target_ids':['missing-target'],'scheme_id':'A'})))])
    response=SimpleNamespace(choices=[SimpleNamespace(message=msg)],usage=SimpleNamespace(prompt_tokens=10,completion_tokens=5,total_tokens=15))
    with patch.object(StubClient,'create',return_value=response):
        result=inspection.plan('无效对象',StubClient(msg))
    assert result['kind']=='message' and result['status']=='rejected'
    assert result['usage']['total_tokens']==15

def test_clarification_does_not_execute_tool():
    msg=SimpleNamespace(tool_calls=None,content='请选择A还是B')
    result=inspection.plan('分析inspect-02',StubClient(msg))
    assert result['kind']=='message' and 'tool_name' not in result

@pytest.mark.parametrize('name,args',[('bad',{}),('analyze_batch',{}),('compare_observers',{'target_ids':['fake']}),('analyze_batch',{'target_ids':['inspect-01'],'scheme_id':'C'})])
def test_reject_invalid_tool_parameters(name,args):
    with pytest.raises(ValueError):inspection.validate_arguments(name,args,inspection.dataset())

def test_model_cannot_overwrite_results_or_limitations(result):
    response=inspection.complete(dict(instruction='比较方案',tool_call_id='offline-stub',tool_result=result),StubClient(SimpleNamespace(content='全部可见，没有任何限制')))
    assert response['tool_result']==result
    assert '全部可见' not in response['message']
    assert '假设' in response['message']

def test_real_block_rays_cross_checked_with_independent_shapely(result):
    # All default rays lie between 1.5 and 2 m; prisms span 0..10 m.
    # Thus an independent XY polygon intersection is a valid reference here.
    from shapely.geometry import shape, LineString
    polygons=[shape({'type':'MultiPolygon','coordinates':b['polygons']}) for b in inspection.dataset()['buildings']]
    for plan in result['plans']:
        start=plan['scheme']['position']
        for row in plan['results']:
            if row['angle']>plan['scheme']['fov']/2: continue
            end=row['position']
            line=LineString([(start['x'],start['z']),(end['x'],end['z'])])
            blocked=any(p.intersects(line) for p in polygons)
            assert row['visible'] is (not blocked)

@pytest.mark.parametrize('field,value',[('data_version','fake'),('building_count',999),('limitations',[]),('comparison',{})])
def test_tampered_snapshot_rejected(result,field,value):
    changed=copy.deepcopy(result);changed[field]=value
    with pytest.raises(ValueError):inspection.verified_result(changed)

def test_provider_failure_endpoint_is_not_success():
    with patch('backend.inspection.plan',side_effect=RuntimeError('offline failure')):
        response=TestClient(app).post('/inspection/agent/plan',json={'instruction':'比较方案'})
    assert response.status_code==502

def test_report_export_uses_actual_snapshot_and_escapes_text(result,tmp_path):
    png='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
    snapshot=dict(run_id='<script>bad</script>',created_at='test',execution_mode='offline protocol test',result=result,screenshot=png)
    with patch.object(inspection,'REPORTS',tmp_path):
        client=TestClient(app);response=client.post('/inspection/reports',json=snapshot)
        assert response.status_code==200
        report=client.get(response.json()['url'])
        assert report.status_code==200
        assert '<script>bad</script>' not in report.text
        assert '&lt;script&gt;' in report.text
        assert result['data_version'] in report.text
        assert len(list(tmp_path.glob('*.json')))==1

def test_invalid_report_rejected(result):
    snapshot=dict(run_id='bad',created_at='test',execution_mode='test',result=result,screenshot='javascript:alert(1)')
    assert TestClient(app).post('/inspection/reports',json=snapshot).status_code==400
