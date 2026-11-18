"""Direct OSM feasibility audit via bounded, sequential public Overpass requests.
No Geoapify credential is read or required. Uses curl for enforced network deadlines.
"""
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'work/pilot-data'
CACHE.mkdir(parents=True, exist_ok=True)
ENDPOINTS = ['https://overpass.private.coffee/api/interpreter', 'https://overpass-api.de/api/interpreter']
CENTER = (12.9782941, 77.6386519)
BBOX = '12.968,77.630,12.985,77.647'
BUSINESS_AMENITIES = {'restaurant', 'cafe', 'fast_food', 'bar', 'pub', 'ice_cream', 'food_court', 'pharmacy'}
ASSISTANCE_AMENITIES = {'hospital', 'police'}
query = f'''[out:json][timeout:15];
(
 nwr(around:1500,{CENTER[0]},{CENTER[1]})[shop];
 nwr(around:1500,{CENTER[0]},{CENTER[1]})[amenity~"^(restaurant|cafe|fast_food|bar|pub|ice_cream|food_court|pharmacy|hospital|police)$"];
 way[highway]({BBOX});
 node[highway=street_lamp]({BBOX});
);
out tags center;'''


def osm_key(element):
    return f"{element['type']}/{element['id']}"


def summarize(data, endpoint):
    elements = {osm_key(e): e for e in data['elements']}
    business = [e for e in elements.values() if (e.get('tags', {}).get('shop') not in (None, 'no', 'vacant') or e.get('tags', {}).get('amenity') in BUSINESS_AMENITIES)]
    assistance = [e for e in elements.values() if e.get('tags', {}).get('amenity') in ASSISTANCE_AMENITIES]
    roads = [e for e in elements.values() if e['type'] == 'way' and 'highway' in e.get('tags', {})]
    lamps = [e for e in elements.values() if e['type'] == 'node' and e.get('tags', {}).get('highway') == 'street_lamp']
    lit = dict(Counter(e['tags'].get('lit', 'unknown') for e in roads))
    hours = [e for e in business if e['tags'].get('opening_hours')]
    geo_records = {}
    for name in ('businesses_commercial', 'businesses_catering', 'businesses_healthcare_pharmacy'):
        file = CACHE / (name + '.json')
        if not file.exists():
            continue
        for f in json.loads(file.read_text()).get('features', []):
            p = f['properties']
            raw = p.get('datasource', {}).get('raw', {}) or {}
            typ = {'n': 'node', 'w': 'way', 'r': 'relation', 'node': 'node', 'way': 'way', 'relation': 'relation'}.get(raw.get('osm_type'))
            if typ and raw.get('osm_id'):
                geo_records[f"{typ}/{raw['osm_id']}"] = p
    shared = [e for e in business if osm_key(e) in geo_records]
    newly_available_hours = []
    for e in shared:
        p = geo_records[osm_key(e)]
        old = p.get('opening_hours') or (p.get('datasource', {}).get('raw', {}) or {}).get('opening_hours')
        if e['tags'].get('opening_hours') and not old:
            newly_available_hours.append(osm_key(e))
    return {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'endpoint': endpoint,
        'osm_base_timestamp': data.get('osm3s', {}).get('timestamp_osm_base'),
        'business_scope': {'center_lat_lon': CENTER, 'radius_m': 1500, 'definition': 'shop except no/vacant, or selected food/drink/pharmacy amenities; not identical to Geoapify category definitions.'},
        'businesses': {'osm_records': len(business), 'with_opening_hours': len(hours), 'coverage_percent': round(100*len(hours)/len(business), 2) if business else None, 'examples': [{'osm_id': osm_key(e), 'name': e['tags'].get('name', 'Unnamed'), 'opening_hours': e['tags']['opening_hours']} for e in hours[:10]]},
        'lighting': {'bbox_south_west_north_east': BBOX, 'highway_ways': len(roads), 'lit_tag_values': lit, 'street_lamp_nodes': len(lamps), 'interpretation': 'Way counts, not road-length coverage; includes non-walkable ways. Missing tags are unknown; mapped tags/lamps do not verify operation.'},
        'assistance': {'osm_records': len(assistance), 'types': dict(Counter(e['tags']['amenity'] for e in assistance)), 'interpretation': 'OSM element counts, not necessarily distinct facilities or verified emergency assistance.'},
        'geoapify_comparison': {'cached_records_with_osm_identity': len(geo_records), 'matching_business_osm_ids': len(shared), 'matching_records_with_hours_absent_in_cached_geoapify_search': len(newly_available_hours), 'interpretation': 'Matched by exact OSM element type/id. Different samples, categories, result limits and update timestamps prevent a complete coverage comparison. Different elements can refer to the same business.'},
        'attribution': '© OpenStreetMap contributors, ODbL https://www.openstreetmap.org/copyright',
    }


def main():
    attempts = []
    (CACHE / 'osm_pilot_query.overpassql').write_text(query)
    for endpoint in ENDPOINTS:
        print(f'Testing {endpoint} (25-second request limit)...', flush=True)
        try:
            result = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--connect-timeout', '8', '--max-time', '25', '--user-agent', 'SafePath-Pilot-Audit/0.1', '--get', '--data-urlencode', 'data=' + query, endpoint], capture_output=True, text=True, timeout=30)
            if result.returncode:
                attempts.append({'endpoint': endpoint, 'status': 'failed', 'curl_exit_code': result.returncode, 'error': result.stderr.strip()[:300]})
                print(f'Endpoint unavailable (request exit {result.returncode}); checking fallback.', flush=True)
                continue
            data = json.loads(result.stdout)
            if data.get('remark') or not isinstance(data.get('elements'), list):
                attempts.append({'endpoint': endpoint, 'status': 'incomplete_response'})
                continue
            summary = summarize(data, endpoint)
            attempts.append({'endpoint': endpoint, 'status': 'success'})
            (CACHE / 'osm_direct.json').write_text(json.dumps(data, indent=2))
            (CACHE / 'osm_direct_summary.json').write_text(json.dumps(summary, indent=2))
            (CACHE / 'osm_attempts.json').write_text(json.dumps(attempts, indent=2))
            print(json.dumps(summary, indent=2), flush=True)
            return
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            attempts.append({'endpoint': endpoint, 'status': 'deadline_or_invalid_json'})
    (CACHE / 'osm_attempts.json').write_text(json.dumps(attempts, indent=2))
    print('Direct OSM check could not complete. No coverage claims can be made.', flush=True)
    raise SystemExit(1)

if __name__ == '__main__':
    main()
