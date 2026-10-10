import copy
import json
import math
from pathlib import Path
import pytest
from pyproj import Geod, Transformer
from backend.building_adapter import local_point, convert_buildings, ORIGIN, E0, N0

FOLDER=Path(__file__).resolve().parents[2]/'public/data/buildings'
RAW=json.loads((FOLDER/'nyc-raw.geojson').read_text())
SOURCE=json.loads((FOLDER/'source.json').read_text())

def test_origin_axis_roundtrip_and_independent_geodesic_scale():
    assert local_point(*ORIGIN)==[0,0]
    east=local_point(ORIGIN[0]+.001,ORIGIN[1]);north=local_point(ORIGIN[0],ORIGIN[1]+.001)
    assert east[0]>0 and north[1]<0
    for lon,lat in [(ORIGIN[0]+.001,ORIGIN[1]),(ORIGIN[0],ORIGIN[1]+.001)]:
        x,z=local_point(lon,lat)
        distance=Geod(ellps='WGS84').inv(*ORIGIN,lon,lat)[2]
        assert abs(math.hypot(x,z)/distance-1)<.001
        result=Transformer.from_crs(32618,4326,always_xy=True).transform(E0+x,N0-z)
        assert result==pytest.approx((lon,lat),abs=1e-8)

@pytest.mark.parametrize('p',[(40.7,-74),(float('nan'),40.7),(True,40.7),('a',40.7)])
def test_invalid_coordinates(p):
    with pytest.raises(ValueError):local_point(*p)

def test_real_unique_records_preserved_and_all_assumptions_explicit():
    result=convert_buildings(RAW,SOURCE)
    assert len(result['buildings'])==54
    assert len({b['id'] for b in result['buildings']})==54
    assert result['quality']['assumed_height_count']==54
    assert all(b['original_geometry'] and b['original_properties'] for b in result['buildings'])
    assert all(t['simulated'] for t in result['targets'])
    assert len(result['schemes'])==2

def test_duplicate_and_invalid_topology():
    bad=copy.deepcopy(RAW);bad['features'][1]=bad['features'][0]
    with pytest.raises(ValueError):convert_buildings(bad,SOURCE)
    bad=copy.deepcopy(RAW);bad['features'][0]['geometry']={'type':'Polygon','coordinates':[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}
    result=convert_buildings(bad,SOURCE)
    assert len(result['skipped'])==1
