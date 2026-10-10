"""NYC-only bounded WGS84 -> UTM18N -> local east/up/south, in metres."""
import hashlib
import json
import math
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.ops import transform, unary_union

ORIGIN = (-74.00875, 40.7075)
PROJECT = Transformer.from_crs('EPSG:4326', 'EPSG:32618', always_xy=True)
E0, N0 = PROJECT.transform(*ORIGIN)
LIMITATIONS = [
    '全部建筑高度假设为10米；原始HEIGHT_ROOF保留但单位未充分核实，不作实测高度使用。',
    '地面统一为0米：无DEM，不使用未核实单位的GROUND_ELEVATION；未模拟地形遮挡。',
    '建筑为闭合轮廓垂直拉伸体，保留孔洞/多部件；无屋顶细节、立面开口、树木或临时设施。',
    '仅分析查询范围内建筑；范围外障碍物未知；观察点和巡检目标为模拟点。',
    '可见性仅代表目标点的距离、视角与单射线检测，不是建筑可见面积比例。',
    '仅供模型假设下方案比较，不作为安全、测绘或工程决策认证。',
]

def local_point(lon, lat):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lon, lat)):
        raise ValueError('Coordinates must be finite numeric longitude/latitude')
    if not (-74.1 < lon < -73.9 and 40.6 < lat < 40.8):
        raise ValueError('Coordinates outside supported NYC study area or axes swapped')
    east, north = PROJECT.transform(lon, lat)
    return [east - E0, -(north - N0)]

def convert_buildings(data, source):
    if data.get('type') != 'FeatureCollection' or not 1 <= len(data.get('features', [])) <= 150:
        raise ValueError('Expected 1..150 GeoJSON features')
    buildings, skipped, ids = [], [], set()
    for feature in data['features']:
        props = feature.get('properties', {})
        oid = props.get('OBJECTID')
        if oid is None or oid in ids:
            raise ValueError('Missing or duplicate OBJECTID')
        ids.add(oid)
        geometry = feature.get('geometry') or {}
        if geometry.get('type') not in ('Polygon', 'MultiPolygon'):
            skipped.append({'id': oid, 'reason': 'unsupported geometry'})
            continue
        original = shape(geometry)
        if original.is_empty or not original.is_valid:
            skipped.append({'id': oid, 'reason': 'invalid topology; not auto-repaired'})
            continue
        polys = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        local_polys = []
        for rings in polys:
            converted = []
            for ring in rings:
                if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                    raise ValueError('Unclosed polygon ring')
                converted.append([local_point(*p[:2]) for p in ring])
            local_polys.append(converted)
        buildings.append(dict(id=f'nyc-{oid}', name=props.get('NAME') or f'NYC {oid}',
                              polygons=local_polys, height=10, base=0, height_source='assumed_10m',
                              original_geometry=geometry, original_properties=props))
    if not buildings:
        raise ValueError('No valid buildings')
    geometries = [shape({'type': 'MultiPolygon', 'coordinates': b['polygons']}) for b in buildings]
    union = unary_union(geometries)
    # A reproducible, explicitly simulated grid in open space, not new building records.
    points = []
    for z in range(-140, 161, 30):
        for x in range(-120, 141, 30):
            if not union.buffer(2).covers(Point(x, z)):
                points.append((x, z))
    if len(points) < 12:
        raise ValueError('Insufficient open space for simulated targets')
    chosen = points[::max(1, len(points)//12)][:12]
    targets = [dict(id=f'inspect-{i+1:02}', name=f'模拟巡检点 {i+1:02}', simulated=True,
                    position=dict(x=x, y=1.5, z=z)) for i, (x,z) in enumerate(chosen)]
    candidates = []
    for index, p in enumerate((points[0], points[-1])):
        x, z = p
        candidates.append(dict(id='A' if index == 0 else 'B', simulated=True,
                               position=dict(x=x, y=2, z=z), direction=dict(x=-x, y=0, z=-z),
                               maxDistance=500, fov=120))
    canonical = json.dumps(data, sort_keys=True).encode()
    return dict(version='nyc-block-v1-' + hashlib.sha256(canonical).hexdigest()[:12],
                source=source, conversion=dict(source_crs='EPSG:4326', projected_crs='EPSG:32618',
                origin_lon_lat=ORIGIN, origin_easting=E0, origin_northing=N0, unit='metre',
                axes='x=E-E0; y=assumed height above flat ground; z=-(N-N0)', always_xy=True),
                buildings=buildings, targets=targets, schemes=candidates, skipped=skipped,
                quality=dict(assumed_height_count=len(buildings), terrain='unknown_flat_assumption',
                             original_count=len(data['features']), valid_count=len(buildings)),
                limitations=LIMITATIONS)

if __name__ == '__main__':
    folder = Path(__file__).resolve().parents[1] / 'public/data/buildings'
    source = json.loads((folder/'source.json').read_text())
    for input_name, output_name in [('nyc-sample.geojson','sample-local.json'), ('nyc-raw.geojson','nyc-local.json')]:
        result = convert_buildings(json.loads((folder/input_name).read_text()), source)
        (folder/output_name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(output_name, len(result['buildings']), 'buildings;', len(result['skipped']), 'skipped')
