"""Read-only heuristic scan of reachable history and index; no matched values."""
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

patterns={
    'api_key':rb'sk-[A-Za-z0-9_-]{20,}',
    'github_token':rb'(?:ghp_|github_pat_)[A-Za-z0-9_]{25,}',
    'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'credential_url':rb'https?://[^\s/:]+:[^\s/@]+@',
}
findings=[]
blobs={}
for commit in git('rev-list','--all').decode().splitlines():
    for entry in git('ls-tree','-r','-z',commit).split(b'\0'):
        if not entry: continue
        meta,path=entry.split(b'\t',1)
        _,kind,oid=meta.split()
        name=path.decode('utf-8','replace')
        if kind==b'blob': blobs.setdefault(oid.decode(),set()).add(name)
        if Path(name).name.startswith('.env') and not name.endswith('.example'):
            findings.append({'path':name,'kind':'environment_file_in_history'})
        if any(part in name.split('/') for part in ['node_modules','.venv','__pycache__']):
            findings.append({'path':name,'kind':'generated_directory_in_history'})
for entry in git('ls-files','--stage','-z').split(b'\0'):
    if not entry: continue
    meta,path=entry.split(b'\t',1)
    _,oid,stage=meta.split()
    name=path.decode('utf-8','replace')
    blobs.setdefault(oid.decode(),set()).add(name)
    if Path(name).name.startswith('.env') and not name.endswith('.example'):
        findings.append({'path':name,'kind':'environment_file_in_index'})
    if any(part in name.split('/') for part in ['node_modules','.venv','__pycache__']):
        findings.append({'path':name,'kind':'generated_directory_in_index'})
for oid,paths in blobs.items():
    content=git('cat-file','blob',oid)
    for kind,pattern in patterns.items():
        if re.search(pattern,content): findings.append({'paths':sorted(paths),'kind':kind})
print(json.dumps({'commits':len(git('rev-list','--all').splitlines()),'unique_blobs':len(blobs),'findings':findings},ensure_ascii=False,indent=2))
raise SystemExit(bool(findings))
