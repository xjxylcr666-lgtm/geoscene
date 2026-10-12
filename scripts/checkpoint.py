"""Create reproducible source-only checkpoint, never traverse secrets or dependencies."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'outputs/checkpoints'
files=[]
for folder in ['src','backend','public','tests','scripts','docs']:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.suffix!='.pyc' and not p.name.startswith('.env'))
files.extend(ROOT/p for p in ['index.html','inspection.html','package.json','package-lock.json','requirements-dev.txt','README.md','vite.config.js','.gitignore'])
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
archive=OUTPUT/f'GeoScene-source-{stamp}.zip'
OUTPUT.mkdir(parents=True,exist_ok=True)
manifest={}
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
    for path in files:
        relative=path.relative_to(ROOT).as_posix()
        manifest[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
        bundle.write(path,relative)
    bundle.writestr('SOURCE-MANIFEST.json',json.dumps(manifest,indent=2))
    # Package versions only, not environment variables or configuration values.
    import sys
    versions=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True,encoding='utf-8')
    bundle.writestr('requirements-snapshot.txt',versions)
print(archive)
print(f'{len(files)} source/data files; {archive.stat().st_size} bytes; no secrets/dependencies')
