"""Small OSM main-API fallback audit. Reuses the local XML unless --refresh is set.
This is a one-off feasibility sample, not a production tile/POI download service.
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'work/pilot-data'
FILE = CACHE / 'osm_small_sample.xml'
URL = 'https://api.openstreetmap.org/api/0.6/map?bbox=77.636,12.976,77.640,12.980'


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    if not FILE.exists() or '--refresh' in sys.argv:
        response = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--connect-timeout', '8', '--max-time', '20', '--user-agent', 'SafePath-Pilot-Audit/0.1', URL], capture_output=True, timeout=25)
        if response.returncode:
            raise RuntimeError('OSM main API request failed; no coverage inferred.')
        # Validate before replacing any prior successful download.
        ET.fromstring(response.stdout)
        FILE.write_bytes(response.stdout)
    tree = ET.parse(FILE).getroot()
    elements = []
    for e in tree:
        if e.tag not in ('node', 'way', 'relation'):
            continue
        elements.append({'type': e.tag, 'id': e.attrib['id'], 'tags': {x.attrib['k']: x.attrib['v'] for x in e.findall('tag')}, 'lat': e.attrib.get('lat'), 'lon': e.attrib.get('lon')})
    business_types = {'restaurant', 'cafe', 'fast_food', 'bar', 'pub', 'ice_cream', 'food_court', 'pharmacy'}
    business = [e for e in elements if e['tags'].get('shop') not in (None, 'no', 'vacant') or e['tags'].get('amenity') in business_types]
    roads = [e for e in elements if e['type'] == 'way' and 'highway' in e['tags']]
    lamps = [e for e in elements if e['type'] == 'node' and e['tags'].get('highway') == 'street_lamp']
    inside_lamps = [e for e in lamps if 77.636 <= float(e['lon']) <= 77.640 and 12.976 <= float(e['lat']) <= 12.980]
    assistance = [e for e in elements if e['tags'].get('amenity') in {'hospital', 'police'}]
    result = {
        'analyzed_at_utc': datetime.now(timezone.utc).isoformat(), 'source': URL,
        'bbox_west_south_east_north': [77.636, 12.976, 77.640, 12.980],
        'scope': 'Approximately 430 by 440 meters around Indiranagar Metro. Map API output includes intersecting ways and referenced elements beyond the box. Unless explicitly stated, counts describe returned records, not a strictly clipped census. Different area and category definitions from Geoapify sample.',
        'element_count': len(elements), 'returned_business_records': len(business),
        'returned_business_records_with_hours': sum(bool(e['tags'].get('opening_hours')) for e in business),
        'returned_highway_ways': len(roads), 'returned_highway_lit_values': dict(Counter(e['tags'].get('lit', 'unknown') for e in roads)),
        'returned_street_lamp_nodes': len(lamps), 'street_lamp_nodes_strictly_inside_box': len(inside_lamps),
        'returned_assistance_records': len(assistance),
        'hours_examples': [{'name': e['tags'].get('name', 'Unnamed'), 'opening_hours': e['tags']['opening_hours']} for e in business if e['tags'].get('opening_hours')],
        'limitations': ['Separate OSM elements may represent the same establishment.', 'No schedule parsing or current availability verification.', 'Missing lighting tags mean unknown. Way counts are not length-weighted coverage, and lamp locations do not prove working lights or continuous illumination.', 'A main-API sample verifies access, not Overpass availability. Public APIs are not a dependable production backend.'],
        'attribution': '© OpenStreetMap contributors, ODbL https://www.openstreetmap.org/copyright',
    }
    (CACHE / 'osm_small_summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, ET.ParseError):
        print('Small OSM sample unavailable or invalid; no coverage inferred.', file=sys.stderr)
        sys.exit(1)
