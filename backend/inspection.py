"""Inspection protocol + local report export. Geometry stays in shared JS."""
import base64
import copy
import html
import json
import math
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.agent_service import _client, _model_name, _usage, AgentProviderError

router = APIRouter(prefix='/inspection')
DATA = Path(__file__).resolve().parents[1] / 'public/data/buildings/nyc-local.json'
REPORTS = Path(__file__).resolve().parents[5] / '2026-09-28/geoscene-130-6-7-python-http/outputs/inspection-reports'

def dataset():
    return json.loads(DATA.read_text(encoding='utf-8'))

def tool_definitions():
    return [dict(type='function', function=dict(name=name, description=description, parameters=dict(
        type='object', properties={**{'target_ids':dict(type='array', items=dict(type='string'), minItems=1, maxItems=100)},
                                  **({'scheme_id':dict(type='string', enum=['A','B'])} if name=='analyze_batch' else {})},
        required=['target_ids']+(['scheme_id'] if name=='analyze_batch' else []), additionalProperties=False)))
        for name,description in [('analyze_batch','对指定方案执行真实批量目标点可见性计算'),
                                 ('compare_observers','对A和B方案使用相同目标执行真实几何比较')]]

def validate_arguments(name, args, data):
    if name not in ('analyze_batch','compare_observers') or not isinstance(args,dict):
        raise ValueError('不支持的工具或参数')
    ids=args.get('target_ids')
    if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(not isinstance(i,str) for i in ids):
        raise ValueError('缺少有效目标列表')
    if len(set(ids))!=len(ids) or not set(ids)<=set(t['id'] for t in data['targets']):
        raise ValueError('重复或无效目标ID')
    if name=='analyze_batch' and args.get('scheme_id') not in ('A','B'):
        raise ValueError('缺少有效方案ID')
    if set(args)-({'target_ids','scheme_id'} if name=='analyze_batch' else {'target_ids'}):
        raise ValueError('未知参数')

def plan(instruction, client=None):
    data=dataset()
    response=(client or _client()).chat.completions.create(model=_model_name(), temperature=0,
        extra_body={'thinking': {'type': 'disabled'}},
        messages=[dict(role='system',content='只能通过工具计算。真实目标ID：'+','.join(t['id'] for t in data['targets'])+
                       '。方案为A和B。所有目标指该列表。'
                       '用户只说分析某目标但未指定方案时，必须用文字询问选择A还是B，不调用任何工具。'
                       '只有用户明确要求比较、两组方案或A和B时，才能调用compare_observers；不得用比较两组来代替缺参数追问。'
                       '用户指定不存在的目标时，明确说明目标不存在并请求有效ID，禁止换成其他目标或全部目标。'
                       '禁止编造结果。'),
                  dict(role='user',content=instruction)], tools=tool_definitions(), tool_choice='auto')
    msg=response.choices[0].message
    if not msg.tool_calls: return dict(kind='message',message=msg.content,usage=_usage(response))
    call=msg.tool_calls[0]
    try:
        args=json.loads(call.function.arguments)
        validate_arguments(call.function.name,args,data)
    except (ValueError,TypeError) as exc:
        return dict(kind='message',status='rejected',message='工具参数被拒绝：'+str(exc),usage=_usage(response))
    return dict(kind='tool_call',tool_name=call.function.name,arguments=args,tool_call_id=call.id,usage=_usage(response))

def verified_result(result):
    if not isinstance(result,dict): raise ValueError('工具结果必须是对象')
    data=dataset()
    if result.get('source')!='geoscene_inspection_tool' or result.get('data_version')!=data['version']:
        raise ValueError('数据版本或工具来源不匹配')
    validate_arguments(result.get('tool_name'),result.get('parameters'),data)
    if result.get('limitations')!=data['limitations'] or result.get('conversion')!=data['conversion'] or result.get('quality')!=data['quality']:
        raise ValueError('限制、数据质量或坐标参数被改写')
    if result.get('building_count')!=len(data['buildings']): raise ValueError('建筑数量不一致')
    plans=result.get('plans',[])
    expected=['A','B'] if result['tool_name']=='compare_observers' else [result['parameters']['scheme_id']]
    if not isinstance(plans,list) or any(not isinstance(p,dict) or not isinstance(p.get('scheme'),dict) for p in plans): raise ValueError('方案格式无效')
    if [p.get('scheme',{}).get('id') for p in plans]!=expected: raise ValueError('方案不一致')
    ids=result['parameters']['target_ids']
    lookup={t['id']:t['position'] for t in data['targets']}
    finite=lambda v: isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)
    for p in plans:
        s=p['scheme']
        for key in ('position','direction'):
            if not isinstance(s.get(key),dict) or set(s[key])!={'x','y','z'} or not all(finite(v) for v in s[key].values()): raise ValueError('无效观察参数')
        if sum(v*v for v in s['direction'].values())<1e-16: raise ValueError('零方向')
        if not finite(s.get('fov')) or not 0<s['fov']<=180 or not finite(s.get('maxDistance')) or not 0<s['maxDistance']<=2000: raise ValueError('无效范围')
        rows=p.get('results',[])
        if [r.get('target_id') for r in rows]!=ids or p.get('total')!=len(ids): raise ValueError('结果目标不一致')
        for r in rows:
            if r.get('position')!=lookup[r['target_id']] or type(r.get('visible')) is not bool: raise ValueError('结果字段无效')
            distance=math.dist(tuple(s['position'][a] for a in ('x','y','z')),tuple(r['position'][a] for a in ('x','y','z')))
            if not finite(r.get('distance')) or abs(r['distance']-distance)>1e-6: raise ValueError('距离与参数不一致')
            if not isinstance(r.get('reason'),str): raise ValueError('原因无效')
        if p.get('visible_count')!=sum(r['visible'] for r in rows): raise ValueError('统计不一致')
    if len(plans)==2:
        expected_comparison=dict(visible_delta_B_minus_A=plans[1]['visible_count']-plans[0]['visible_count'],
            changed_target_ids=[a['target_id'] for a,b in zip(plans[0]['results'],plans[1]['results']) if a['visible']!=b['visible']])
        if result.get('comparison')!=expected_comparison: raise ValueError('方案比较不一致')
    elif result.get('comparison') is not None: raise ValueError('单方案不应包含比较')
    return copy.deepcopy(result)

def complete(request, client=None):
    result=verified_result(request['tool_result'])
    response=(client or _client()).chat.completions.create(model=_model_name(),temperature=0,
        extra_body={'thinking': {'type': 'disabled'}},
        messages=[dict(role='system',content='只能确认工具完成，不得改写确定性结果或省略限制。'),
                  dict(role='user',content=request['instruction']),
                  dict(role='assistant',content=None,tool_calls=[dict(id=request['tool_call_id'],type='function',function=dict(name=result['tool_name'],arguments=json.dumps(result['parameters'])))]),
                  dict(role='tool',tool_call_id=request['tool_call_id'],content=json.dumps(result,ensure_ascii=False))])
    return dict(tool_result=result,message='；'.join(f"方案{p['scheme']['id']}：{p['visible_count']}/{p['total']}个目标点可见" for p in result['plans'])+'。假设高度与地形限制见结果。',usage=_usage(response))

@router.post('/agent/plan')
def plan_endpoint(request: dict):
    try:
        instruction=request.get('instruction')
        if not isinstance(instruction,str) or not 1<=len(instruction.strip())<=500: raise ValueError('无效指令')
        return plan(instruction)
    except ValueError as e: raise HTTPException(400,str(e))
    except Exception: raise HTTPException(502,'模型服务不可用')

@router.post('/agent/complete')
def complete_endpoint(request: dict):
    try: return complete(request)
    except (ValueError,KeyError,TypeError) as e: raise HTTPException(400,str(e))
    except Exception: raise HTTPException(502,'模型服务不可用')

def report_html(snapshot):
    r=verified_result(snapshot['result'])
    esc=lambda v:html.escape(str(v))
    screenshot=snapshot.get('screenshot','')
    if not screenshot.startswith('data:image/png;base64,') or len(screenshot)>4_000_000: raise ValueError('截图必须是小于3MB的PNG')
    raw=base64.b64decode(screenshot.split(',',1)[1],validate=True)
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('PNG签名无效')
    rows=''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in (p['scheme']['id'],row['target_id'],row['visible'],f"{row['distance']:.3f}",row.get('angle'),row['reason'],row.get('blocker_id','')) )+'</tr>' for p in r['plans'] for row in p['results'])
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>GeoScene 巡检方案报告</title>
    <style>body{{font:15px/1.6 sans-serif;max-width:1100px;margin:35px auto;color:#21343d}}img{{max-width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd7dc;padding:6px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}.warning{{background:#fff1d4;padding:16px}}</style>
    <h1>真实建筑轮廓 · 模拟巡检方案比较</h1><p>运行ID：{esc(snapshot['run_id'])} ｜ 时间：{esc(snapshot['created_at'])}</p>
    <p>数据版本：{esc(r['data_version'])}；建筑数：{r['building_count']}；坐标单位：米。</p>
    <p>执行方式：{esc(snapshot['execution_mode'])}。模型未参与确定性计算。</p>
    <div class="warning">{'<br>'.join(esc(w) for w in r['limitations'])}</div>
    <h2>同次分析截图</h2><p>青色=A，橙色=B；绿色/红色目标分别代表方案{esc(r['plans'][0]['scheme']['id'])}的可见/不可见；视线颜色对应方案，不代表通行路线。</p><img src="{screenshot}">
    <h2>输入参数</h2><pre>{esc(json.dumps([p['scheme'] for p in r['plans']],ensure_ascii=False,indent=2))}</pre>
    <h2>结果清单</h2><table><tr><th>方案</th><th>目标</th><th>可见</th><th>米</th><th>角度</th><th>原因</th><th>遮挡ID</th></tr>{rows}</table>
    <h2>统计和运行条件</h2><pre>{esc(json.dumps(dict(summary=[dict(scheme=p['scheme']['id'],visible=p['visible_count'],total=p['total'],analysis_ms=p['analysis_ms']) for p in r['plans']],comparison=r['comparison'],conditions=snapshot.get('conditions')),ensure_ascii=False,indent=2))}</pre>
    <h2>来源与转换</h2><p>NYC OTI Building Footprints / NYC Open Data，信息用途，无准确性保证。</p><a href="https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje">使用条款</a>
    <pre>{esc(json.dumps(dict(source=dataset()['source'],conversion=r['conversion'],quality=r['quality']),ensure_ascii=False,indent=2))}</pre></html>'''

@router.post('/reports')
def save_report(snapshot: dict):
    try: rendered=report_html(snapshot)
    except (ValueError,KeyError,TypeError) as e: raise HTTPException(400,str(e))
    REPORTS.mkdir(parents=True,exist_ok=True)
    name='inspection-'+uuid4().hex
    (REPORTS/(name+'.html')).write_text(rendered,encoding='utf-8')
    (REPORTS/(name+'.json')).write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    return dict(url='/inspection/reports/'+name+'.html',filename=name+'.html')

@router.get('/reports/{filename}')
def get_report(filename: str):
    if not filename.startswith('inspection-') or not filename.endswith('.html') or len(filename)!=48 or not all(c in '0123456789abcdef' for c in filename[11:-5]): raise HTTPException(404)
    path=REPORTS/filename
    if not path.is_file(): raise HTTPException(404)
    return FileResponse(path,media_type='text/html')
