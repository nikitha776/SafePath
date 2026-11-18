"""Check mapped road lighting in a bounded Indiranagar box, not live light status."""
import json
import signal
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
out = root / 'work/pilot-data'
# south, west, north, east: fixed pilot box, not all Bengaluru.
bbox = '12.968,77.630,12.985,77.647'
query = f'[out:json][timeout:25];way[highway]({bbox});out tags geom;'
request = urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data': query}).encode(), headers={'User-Agent': 'SafePath-Pilot-Audit/0.1'})
def timeout_handler(signum, frame):
    raise TimeoutError('Overall lighting request deadline exceeded.')

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(50)

try:
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.load(response)
    if data.get('remark'):
        raise RuntimeError('Overpass reported incomplete results; no coverage percentage calculated.')
    ways = data.get('elements', [])
    counts = {}
    for way in ways:
        value = way.get('tags', {}).get('lit', 'unknown')
        counts[value] = counts.get(value, 0) + 1
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'bbox_south_west_north_east': bbox, 'road_way_count': len(ways), 'lit_values': counts, 'scope': 'OSM highway ways in fixed Indiranagar box; counts are not length-weighted and do not measure route coverage.', 'interpretation': 'Missing lit tags mean unknown, not unlit. Tags describe mapped infrastructure, not verified current operation.', 'attribution': '© OpenStreetMap contributors, ODbL https://www.openstreetmap.org/copyright'}
    (out / 'osm_lighting.json').write_text(json.dumps(data, indent=2))
    (out / 'lighting_summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
except (urllib.error.URLError, TimeoutError, OSError, RuntimeError):
    print('Lighting check unavailable or incomplete; lighting coverage remains unverified.')
    raise SystemExit(1)
