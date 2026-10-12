"""Authoritative local modelling, shared-JS execution, bounded issued snapshots."""
import copy
import hashlib
import json
import math
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from shapely.geometry import Polygon
from backend.inspection import dataset, validate_arguments, PROJECT_ROOT

router = APIRouter(prefix='/inspection/workbench')
RULE_VERSION = 'precheck-rules-1'
_runs = {}
_lock = threading.Lock()
_workers = threading.BoundedSemaphore(2)

def number(value, label, low=-5000, high=5000):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label}须为{low}至{high}之间的有限数值')
    return value

def manual_buildings(items):
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError('人工建筑必须为列表，最多100栋')
    result, ids = [], set()
    for item in items:
        if not isinstance(item, dict): raise ValueError('建筑必须为对象')
        id_ = item.get('id', '')
        if not isinstance(id_, str) or not re.fullmatch(r'manual-[a-zA-Z0-9-]{1,64}', id_) or id_ in ids:
            raise ValueError('人工建筑ID须唯一且以manual-开头')
        ids.add(id_)
        name = item.get('name')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80: raise ValueError('建筑名称须为1至80个非空字符')
        if item.get('source') != 'manual' or item.get('height_source') != 'user_input':
            raise ValueError('人工建筑来源必须是manual，高度来源必须是user_input')
        height = number(item.get('height'), '高度', .1, 500)
        method = item.get('method')
        record = dict(id=id_, name=name.strip(), source='manual', height_source='user_input', method=method, height=height, base=0)
        if method == 'rectangle':
            x, z = number(item.get('x'), 'X'), number(item.get('z'), 'Z')
            length, width = number(item.get('length'), '长度', .1, 1000), number(item.get('width'), '宽度', .1, 1000)
            rotation = number(item.get('rotation'), '旋转角', -360, 360)
            a = math.radians(rotation)
            ring = [[x+u*math.cos(a)-v*math.sin(a), z+u*math.sin(a)+v*math.cos(a)] for u,v in [(-length/2,-width/2),(length/2,-width/2),(length/2,width/2),(-length/2,width/2)]]
            record.update(x=x,z=z,length=length,width=width,rotation=rotation)
        elif method == 'polygon':
            ring = item.get('points')
            if not isinstance(ring, list) or not 3 <= len(ring) <= 100: raise ValueError('多边形需要3至100个边界点')
            for point in ring:
                if not isinstance(point, list) or len(point) != 2: raise ValueError('每个点必须是[X,Z]')
                for value in point: number(value, '边界坐标')
            if ring[0] == ring[-1]: ring = ring[:-1]
            record['points'] = copy.deepcopy(ring)
        else: raise ValueError('创建方式须为rectangle或polygon')
        polygon = Polygon(ring)
        if len(ring) < 3 or not polygon.is_valid or polygon.area < .01 or len(set(map(tuple,ring))) != len(ring):
            raise ValueError('边界不可自相交、重复或退化；至少3个不同点')
        record.update(position=dict(x=polygon.centroid.x,y=0,z=polygon.centroid.y),polygons=[[ring+[ring[0]]]])
        result.append(record)
    return result

def validate_project(body):
    data = dataset()
    if body.get('schema') != 'geoscene-manual-project-v1' or body.get('data_version') != data['version']:
        raise ValueError('项目格式或官方数据版本不匹配')
    if body.get('coordinate_system') != 'local_xz_metres': raise ValueError('只接受本地场景X/Z米制坐标，不接受经纬度')
    return dict(schema=body['schema'],data_version=data['version'],coordinate_system='local_xz_metres',manual_buildings=manual_buildings(body.get('manual_buildings')))

def rules(result, critical, manual):
    assessments = []
    for p in result['plans']:
        visible = {r['target_id'] for r in p['results'] if r['visible']}
        missing = sorted(set(critical)-visible)
        distances = [r['distance'] for r in p['results'] if r['visible'] and r['target_id'] not in critical]
        assessments.append(dict(scheme_id=p['scheme']['id'],missing_critical=missing,eligible=not missing and bool(visible),
            ordinary_visible=len(visible-set(critical)),mean_visible_ordinary_distance=sum(distances)/len(distances) if distances else None))
    eligible = [p for p in assessments if p['eligible']]
    eligible.sort(key=lambda p:(-p['ordinary_visible'], p['mean_visible_ordinary_distance'] if p['mean_visible_ordinary_distance'] is not None else float('inf'),p['scheme_id']))
    pending = bool(result['quality'].get('assumed_height_count'))
    return dict(version=RULE_VERSION,critical_target_ids=critical,assessments=assessments,
        status='待确认' if pending else ('条件预检' if eligible else '不推荐'),
        recommended_scheme=None if pending or not eligible else eligible[0]['scheme_id'],
        provisional_candidate=eligible[0]['scheme_id'] if eligible else None,
        conclusion=('建筑高度未实测确认，不出正式推荐。' if pending else '') + ('条件候选方案'+eligible[0]['scheme_id'] if eligible else '没有方案覆盖全部关键目标，不得推荐。'),
        basis='至少有一个可见目标，且先全部覆盖指定关键目标；再普通可见目标数降序、可见普通目标平均直线距离升序；完全相同按方案ID作展示排序，不表示质量更好。',
        risks=['54栋官方轮廓采用假设10米高度；地形为平地；目标为模拟点；非建筑整体可见率或导航。']+(['人工建筑均为用户输入假设，非实测。'] if manual else [])+([] if critical else ['未指定关键目标，不能据此认定关键设备验收通过。']))

def evaluate(body):
    data = dataset()
    project = validate_project(body)
    manual = project['manual_buildings']
    name, args = body.get('tool_name'), body.get('arguments')
    validate_arguments(name,args,data)
    critical = body.get('critical_target_ids', [])
    if not isinstance(critical,list) or any(not isinstance(i,str) for i in critical) or len(set(critical)) != len(critical) or not set(critical)<=set(t['id'] for t in data['targets']):
        raise ValueError('关键目标须为真实列表中不重复的ID')
    schemes = body.get('schemes')
    if not isinstance(schemes,list) or len(schemes)!=2 or any(not isinstance(s,dict) for s in schemes) or [s.get('id') for s in schemes]!=['A','B']: raise ValueError('必须提供A、B两组方案')
    for s in schemes:
        for key in ('position','direction'):
            if not isinstance(s.get(key),dict) or set(s[key])!={'x','y','z'}: raise ValueError('坐标和方向需要x/y/z')
            for v in s[key].values(): number(v,key)
        if math.hypot(*s['direction'].values())<1e-8: raise ValueError('方向不能为零')
        number(s.get('fov'),'视场角',.01,180)
        number(s.get('maxDistance'),'最大距离',.01,2000)
    data['buildings'] += manual
    node = shutil.which('node')
    if not node: raise RuntimeError('未找到Node.js，无法执行共享几何核心')
    if not _workers.acquire(blocking=False): raise RuntimeError('分析服务忙，请稍后重试')
    try:
        process = subprocess.run([node,str(PROJECT_ROOT/'scripts/evaluate-workbench.mjs')],input=json.dumps(dict(data=data,name=name,args=args,schemes=schemes)),text=True,encoding='utf-8',capture_output=True,timeout=30,cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired: raise RuntimeError('几何计算超过30秒，未生成成功结果')
    finally: _workers.release()
    if process.returncode: raise RuntimeError('共享几何执行失败，未生成结果')
    result = json.loads(process.stdout)
    result['limitations'] = [line.replace('全部建筑高度','官方建筑高度') for line in result['limitations']]
    if manual: result['limitations'].append('人工建筑高度来自用户输入，非实测；具体值见manual_buildings，不统一采用10米。')
    result.update(manual_buildings=manual,official_building_count=len(data['buildings'])-len(manual),manual_building_count=len(manual),project_version='workbench-v1',rules=rules(result,critical,manual))
    result['scene_version'] = hashlib.sha256(json.dumps(project,sort_keys=True).encode()).hexdigest()[:16]
    result['server_run_id'] = uuid4().hex
    result['generated_at'] = datetime.now(timezone.utc).isoformat()
    with _lock:
        now=time.monotonic()
        for key in list(_runs):
            if now-_runs[key][0]>3600: del _runs[key]
        while len(_runs)>=64: del _runs[next(iter(_runs))]
        _runs[result['server_run_id']] = (now,copy.deepcopy(result))
    return result

def issued_result(result):
    with _lock:
        saved = _runs.get(result.get('server_run_id'))
        if not saved or time.monotonic()-saved[0]>3600: raise ValueError('服务器分析快照已过期或服务已重启，请重新分析')
        if result != saved[1]: raise ValueError('分析结果与服务器快照不一致，禁止生成报告')
        return copy.deepcopy(saved[1])

@router.post('/project')
def project_endpoint(body:dict):
    try: return validate_project(body)
    except (ValueError,TypeError,KeyError) as e: raise HTTPException(400,str(e))

@router.post('/evaluate')
def evaluate_endpoint(body:dict):
    try: return evaluate(body)
    except (ValueError,TypeError,KeyError) as e: raise HTTPException(400,str(e))
    except RuntimeError as e: raise HTTPException(503,str(e))

@router.post('/project/export')
def export_project_endpoint(body:dict):
    from backend.inspection import REPORTS
    try:
        project=validate_project(body)
        name='inspection-'+uuid4().hex+'.json'
        REPORTS.mkdir(parents=True,exist_ok=True)
        (REPORTS/name).write_text(json.dumps(project,ensure_ascii=False,indent=2),encoding='utf-8')
        return dict(url='/inspection/reports/'+name,filename=name)
    except (ValueError,TypeError,KeyError) as e: raise HTTPException(400,str(e))
    except OSError: raise HTTPException(503,'项目输出目录不可写')

@router.post('/report')
def report_endpoint(snapshot:dict):
    from backend.inspection import save_report
    try:
        issued_result(snapshot.get('result', {}))
    except (ValueError,TypeError,AttributeError) as e: raise HTTPException(400,str(e))
    return save_report(snapshot)

@router.post('/agent-plan')
def agent_plan_endpoint(body:dict):
    # Validate context BEFORE any provider request; the model cannot choose critical IDs.
    from backend.inspection import plan
    try:
        validate_project(body)
        instruction=body.get('instruction')
        if not isinstance(instruction,str) or not 1<=len(instruction.strip())<=500: raise ValueError('指令须为1至500字符')
        critical=body.get('critical_target_ids',[])
        if not isinstance(critical,list) or any(not isinstance(i,str) for i in critical) or len(set(critical))!=len(critical) or not set(critical)<=set(t['id'] for t in dataset()['targets']): raise ValueError('关键目标ID无效')
        if '关键' in instruction and not critical:
            return dict(kind='message',message='请先指定必须验收的关键目标ID；不会由模型猜测。',usage=None)
        response=plan(instruction)
        response['generate_report']='报告' in instruction
        return response
    except (ValueError,TypeError,KeyError) as e: raise HTTPException(400,str(e))
    except Exception: raise HTTPException(502,'模型规划不可用；手动分析和报告仍可使用')
