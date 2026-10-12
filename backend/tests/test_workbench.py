import copy
import json
import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import workbench as w, inspection

client=TestClient(app)

def rectangle(**kwargs):
    return dict(dict(id='manual-test',name='人工遮挡测试',source='manual',height_source='user_input',method='rectangle',height=10,x=-75,z=-125,length=8,width=8,rotation=0),**kwargs)

def request(manual=None):
    data=w.dataset()
    return dict(schema='geoscene-manual-project-v1',data_version=data['version'],coordinate_system='local_xz_metres',manual_buildings=manual or [],tool_name='compare_observers',arguments=dict(target_ids=['inspect-02']),schemes=data['schemes'],critical_target_ids=['inspect-02'])

def test_actual_shared_geometry_changes_and_restores():
    baseline=w.evaluate(request())
    blocked=w.evaluate(request([rectangle()]))
    low=w.evaluate(request([rectangle(height=.5)]))
    moved=w.evaluate(request([rectangle(x=200,z=200)]))
    assert baseline['plans'][0]['results'][0]['visible']
    assert not blocked['plans'][0]['results'][0]['visible']
    assert blocked['plans'][0]['results'][0]['blocker_id']=='manual-test'
    assert low['plans'][0]['results'][0]['visible'] and moved['plans'][0]['results'][0]['visible']
    assert blocked['building_count']==55 and blocked['official_building_count']==54
    assert blocked['rules']['assessments'][0]['missing_critical']==['inspect-02']
    assert blocked['rules']['recommended_scheme'] is None
    assert baseline['rules']['status']=='待确认'

@pytest.mark.parametrize('patch',[dict(height=-1),dict(height=True),dict(height='10'),dict(height=float('inf')),dict(length=0),dict(width=-1),dict(name='  '),dict(source='official'),dict(height_source='measured'),dict(id='inspect-02'),dict(x=None)])
def test_invalid_rectangle(patch):
    with pytest.raises(ValueError): w.manual_buildings([rectangle(**patch)])

def test_polygon_roundtrip_and_actual_obstruction():
    polygon=rectangle(method='polygon',points=[[-79,-129],[-71,-129],[-71,-121],[-79,-121]])
    project=w.validate_project(request([polygon]))
    assert w.validate_project(json.loads(json.dumps(project)))==project
    result=w.evaluate(dict(request(),manual_buildings=project['manual_buildings']))
    assert result['plans'][0]['results'][0]['blocker_id']=='manual-test'
    assert project['manual_buildings'][0]['position']['x']==-75

@pytest.mark.parametrize('points',[[[0,0],[1,1]],[[0,0],[4,4],[0,4],[4,0]],[[0,0],[0,0],[1,1]],[[0,0],[1,1],[2,2]],[[0,0],['x',1],[2,3]]])
def test_invalid_polygon(points):
    with pytest.raises(ValueError):w.manual_buildings([rectangle(method='polygon',points=points)])

def test_duplicates_coordinate_system_and_versions():
    with pytest.raises(ValueError):w.manual_buildings([rectangle(),rectangle()])
    for key,value in [('coordinate_system','EPSG:4326'),('data_version','old')]:
        req=request();req[key]=value
        assert client.post('/inspection/workbench/project',json=req).status_code==400

def test_reports_issued_snapshot_only_and_json_download(tmp_path,monkeypatch):
    monkeypatch.setattr(inspection,'REPORTS',tmp_path)
    assert client.post('/inspection/workbench/report',json={}).status_code==400
    result=w.evaluate(request([rectangle()]))
    snap=dict(result=result,run_id=result['server_run_id'],created_at=result['generated_at'],execution_mode='离线测试',screenshot='data:image/png;base64,iVBORw0KGgo=')
    response=client.post('/inspection/workbench/report',json=snap)
    assert response.status_code==200
    report=response.json()
    html=client.get(report['url']).text
    saved=client.get(report['json_url'])
    assert saved.json()==snap
    assert 'attachment' in saved.headers['content-disposition']
    assert 'manual-test' in html and w.RULE_VERSION in html and '待确认' in html
    forged=copy.deepcopy(snap);forged['result']['plans'][0]['results'][0]['visible']=True
    assert client.post('/inspection/workbench/report',json=forged).status_code==400
    forged=copy.deepcopy(snap);del forged['result']['server_run_id']
    assert client.post('/inspection/workbench/report',json=forged).status_code==400
    w._runs[result['server_run_id']]=(time.monotonic()-3601,result)
    assert client.post('/inspection/workbench/report',json=snap).status_code==400

def test_invalid_targets_schemes_and_failure(monkeypatch):
    req=request();req['arguments']['target_ids']=['missing']
    assert client.post('/inspection/workbench/evaluate',json=req).status_code==400
    req=request();req['schemes'][0]['direction']={a:0 for a in 'xyz'}
    assert client.post('/inspection/workbench/evaluate',json=req).status_code==400
    req=request();req['critical_target_ids']=['missing']
    assert client.post('/inspection/workbench/evaluate',json=req).status_code==400
    monkeypatch.setattr(w.shutil,'which',lambda _:None)
    assert client.post('/inspection/workbench/evaluate',json=request()).status_code==503

def test_policy_omitted_critical_and_ranking():
    r=w.evaluate(request())
    policy=w.rules(r,['inspect-01'],[])
    assert all(not a['eligible'] for a in policy['assessments'])
    assert policy['provisional_candidate'] is None
    synthetic=copy.deepcopy(r)
    synthetic['quality']['assumed_height_count']=0
    synthetic['plans'][1]['results']=copy.deepcopy(synthetic['plans'][0]['results'])
    synthetic['plans'][1]['results'][0]['distance']=1
    assert w.rules(synthetic,[],[])['recommended_scheme']=='B'

def test_offline_agent_workflow_and_missing_parameters(tmp_path,monkeypatch):
    calls=[]
    def stub(instruction):
        calls.append(instruction)
        return dict(kind='tool_call',tool_name='compare_observers',arguments=dict(target_ids=['inspect-02']),tool_call_id='offline-stub',usage={'total_tokens':0})
    monkeypatch.setattr(inspection,'plan',stub)
    req=dict(request(),instruction='比较A和B，关键设备优先，并生成报告')
    missing=dict(req,critical_target_ids=[])
    assert client.post('/inspection/workbench/agent-plan',json=missing).json()['kind']=='message'
    assert not calls
    plan=client.post('/inspection/workbench/agent-plan',json=req).json()
    assert plan['generate_report'] and calls
    result=client.post('/inspection/workbench/evaluate',json=dict(req,tool_name=plan['tool_name'],arguments=plan['arguments'])).json()
    monkeypatch.setattr(inspection,'REPORTS',tmp_path)
    snapshot=dict(result=result,run_id=result['server_run_id'],created_at=result['generated_at'],execution_mode='协议替身，不是真实模型联调',screenshot='data:image/png;base64,iVBORw0KGgo=')
    assert client.post('/inspection/workbench/report',json=snapshot).status_code==200

def test_project_file_export_preserves_manual_source(tmp_path,monkeypatch):
    monkeypatch.setattr(inspection,'REPORTS',tmp_path)
    response=client.post('/inspection/workbench/project/export',json=request([rectangle()]))
    assert response.status_code==200
    saved=client.get(response.json()['url']).json()
    assert w.validate_project(saved)==saved
    assert saved['manual_buildings'][0]['source']=='manual'
    assert len(list(tmp_path.glob('*.json')))==1

def test_zero_visible_never_a_candidate():
    result=w.evaluate(request([rectangle()]))
    policy=w.rules(result,[],[])
    assert policy['provisional_candidate'] is None
