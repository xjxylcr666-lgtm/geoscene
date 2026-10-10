"""Bounded official NYC sample download. No credentials or external accounts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/BUILDING_view/FeatureServer/0'
BBOX = [-74.0105, 40.7060, -74.0070, 40.7090]
MAX_BYTES = 2_000_000

def get(params):
    url = SERVICE + '/query?' + urlencode(params)
    with urlopen(url, timeout=30) as response:
        length = response.headers.get('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError('Download exceeds 2 MB budget')
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Stream exceeds 2 MB budget')
    data = json.loads(raw)
    if 'error' in data:
        raise ValueError(data['error'])
    return url, raw, data

if __name__ == '__main__':
    params = dict(f='json', where='1=1', geometry=','.join(map(str, BBOX)),
                  geometryType='esriGeometryEnvelope', inSR=4326,
                  spatialRel='esriSpatialRelIntersects')
    _, _, count = get({**params, 'returnCountOnly': 'true'})
    if not 1 <= count['count'] <= 150:
        raise ValueError(f'Unexpected count: {count}')
    # Estimate from a 3-feature sample before requesting the whole bounded block.
    query = {**params, 'f': 'geojson', 'outSR': 4326, 'outFields': '*',
             'orderByFields': 'OBJECTID', 'returnGeometry': 'true', 'resultRecordCount': 3}
    _, sample_raw, sample = get(query)
    estimate = len(sample_raw) / len(sample['features']) * count['count']
    if estimate > MAX_BYTES:
        raise ValueError('Estimated block exceeds download budget')
    url, raw, data = get({**query, 'resultRecordCount': 150})
    assert len(data['features']) == count['count'], 'Incomplete query response'
    assert len({f['properties']['OBJECTID'] for f in data['features']}) == count['count']
    folder = ROOT / 'public/data/buildings'
    folder.mkdir(parents=True, exist_ok=True)
    for filename, body in [('nyc-raw.geojson', raw), ('nyc-sample.geojson', sample_raw)]:
        path = folder / filename
        if path.exists():
            raise ValueError(f'Refusing to overwrite existing snapshot: {path}')
        path.write_bytes(body)
    manifest = dict(source=SERVICE, query=url, downloaded_at=datetime.now(timezone.utc).isoformat(),
                    bbox=BBOX, count=count['count'], sample_count=3, sample_bytes=len(sample_raw),
                    estimated_bytes=round(estimate), actual_bytes=len(raw), maximum_bytes=MAX_BYTES,
                    sha256=hashlib.sha256(raw).hexdigest(), source_service_crs='EPSG:3857',
                    delivered_crs='EPSG:4326 longitude,latitude; degrees',
                    license='NYC Open Data Terms of Use; informational use, no accuracy warranty',
                    license_url='https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje',
                    metadata_url='https://raw.githubusercontent.com/CityOfNewYork/nyc-geo-metadata/master/Metadata/Metadata_BuildingFootprints.md')
    (folder / 'source.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
