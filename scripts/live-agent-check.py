"""Explicitly opt-in paid smoke tests; never run by pytest or npm test."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.inspection import plan

parser=argparse.ArgumentParser()
parser.add_argument('--allow-paid',action='store_true')
args=parser.parse_args()
if not args.allow_paid: parser.error('This calls the configured paid provider. Pass --allow-paid only with authorization.')
results=[]
for instruction in ['分析inspect-02的可见性','用方案A分析missing-target']:
    try:
        result=plan(instruction)
        results.append(dict(instruction=instruction,response=result,passed=result.get('kind')=='message'))
    except Exception as error:
        results.append(dict(instruction=instruction,passed=False,error_type=type(error).__name__,usage='unknown'))
output=Path(__file__).resolve().parents[1]/'outputs/live-agent-check-20261012.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
