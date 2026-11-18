"""Small, bounded Geoapify/OSM feasibility audit. Never log request URLs or keys."""
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'work/pilot-data'
CACHE.mkdir(parents=True, exist_ok=True)


def load_key():
    key = os.environ.get('GEOAPIFY_API_KEY', '')
    if not key:
        for line in (ROOT / '.env').read_text().splitlines():
            if line.strip().startswith('GEOAPIFY_API_KEY='):
                key = line.split('=', 1)[1].strip().strip('\"\'')
    if not key or key == 'your_key_here':
        raise RuntimeError('Missing API key in .env.')
    return key


def request_json(path, params, label):
    url = 'https://api.geoapify.com/' + path + '?' + urllib.parse.urlencode({**params, 'apiKey': KEY})
    req = urllib.request.Request(url, headers={'User-Agent': 'SafePath-Pilot-Audit/0.1'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{label}: HTTP {e.code}. Check API access, restrictions, or quota.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError(f'{label}: network connection failed or timed out.') from None
    # Only retain useful result fields, excluding any echoed request URL or parameters.
    clean = {'type': data.get('type'), 'features': data.get('features', [])}
    (CACHE / (label + '.json')).write_text(json.dumps(clean, indent=2))
    print(f'{label}: received {len(clean["features"])} result(s).', flush=True)
    return clean['features']


def properties_hours(p):
    return p.get('opening_hours') or (p.get('datasource', {}).get('raw', {}) or {}).get('opening_hours')


def run():
    summary = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'geocoding': [], 'routes': [], 'limitations': []}
    landmarks = ['Indiranagar Metro Station, Bengaluru, India', 'Domlur Flyover, Bengaluru, India', 'Chinmaya Mission Hospital, Indiranagar, Bengaluru, India']
    points = []
    for i, text in enumerate(landmarks):
        found = request_json('v1/geocode/search', {'text': text, 'filter': 'countrycode:in', 'limit': 1}, f'geocode_{i}')
        if not found:
            raise RuntimeError('A pilot landmark was not found; choose a more precise location.')
        p = found[0]['properties']
        lat, lon = p['lat'], p['lon']
        if p.get('rank', {}).get('confidence', 0) < 0.7 or p.get('result_type') in ('city', 'state', 'country'):
            raise RuntimeError('A landmark resolved too broadly or with low confidence; refine the query.')
        if not (12.90 < lat < 13.10 and 77.50 < lon < 77.75):
            raise RuntimeError('A landmark resolved outside the Bengaluru pilot vicinity.')
        points.append((lat, lon))
        summary['geocoding'].append({'query': text, 'resolved': p.get('formatted'), 'lat': lat, 'lon': lon, 'confidence': p.get('rank', {}).get('confidence')})
    for end_i in (1, 2):
        seen = set()
        for kind in ('balanced', 'short'):
            features = request_json('v1/routing', {'waypoints': '|'.join(f'{lat},{lon}' for lat, lon in (points[0], points[end_i])), 'mode': 'walk', 'type': kind, 'details': 'route_details', 'format': 'geojson'}, f'route_{end_i}_{kind}')
            for f in features:
                p = f['properties']
                signature = json.dumps(f.get('geometry'), sort_keys=True)
                summary['routes'].append({'destination': landmarks[end_i], 'optimization': kind, 'distance_m': p.get('distance'), 'duration_seconds': p.get('time'), 'duplicates_previous_geometry': signature in seen, 'steps': sum(len(leg.get('steps', [])) for leg in p.get('legs', []))})
                seen.add(signature)
    lat, lon = points[0]
    base = {'filter': f'circle:{lon},{lat},1500', 'bias': f'proximity:{lon},{lat}', 'limit': 100}
    business = []
    category_counts = {}
    for category in ('commercial', 'catering', 'healthcare.pharmacy'):
        found = request_json('v2/places', {**base, 'categories': category}, 'businesses_' + category.replace('.', '_'))
        business.extend(found)
        category_counts[category] = len(found)
    unique = {}
    for f in business:
        p = f['properties']
        identity = p.get('place_id') or json.dumps(f.get('geometry'), sort_keys=True) + p.get('name', '')
        unique[identity] = f
    hours = sum(bool(properties_hours(f['properties'])) for f in unique.values())
    summary['businesses'] = {'radius_m': 1500, 'returned': len(business), 'category_counts': category_counts, 'unique': len(unique), 'with_hours_in_search': hours, 'result_limit': 100, 'possibly_truncated': any(n >= 100 for n in category_counts.values()), 'scope': 'Area sample around Indiranagar Metro, not a route corridor census.'}
    detail_results = []
    for i, f in enumerate(list(unique.values())[:10]):
        p = f['properties']
        if not p.get('place_id'):
            continue
        details = request_json('v2/place-details', {'id': p['place_id'], 'features': 'details'}, f'business_detail_{i}')
        schedule = next((properties_hours(d['properties']) for d in details if properties_hours(d['properties'])), None)
        detail_results.append({'name': p.get('name', 'Unnamed'), 'opening_hours': schedule})
    summary['business_details_sample'] = {'selection': 'First ten unique search results in category order, proximity-biased within each category; not a random sample.', 'checked': len(detail_results), 'with_hours': sum(bool(x['opening_hours']) for x in detail_results), 'records': detail_results}
    assistance = request_json('v2/places', {**base, 'categories': 'healthcare.hospital,service.police'}, 'assistance')
    summary['assistance'] = {'returned': len(assistance), 'radius_m': 1500, 'names': [f['properties'].get('name', 'Unnamed') for f in assistance], 'availability': 'Mapped listings only; accessibility and current operation unverified.'}
    summary['limitations'] += ['Each category search is capped at 100 and is not exhaustive; opening hours are schedules, not live confirmation.', 'Balanced and short requests do not guarantee distinct alternatives; no undocumented alternatives parameter is used.', 'No arrival-time evaluation, safety score, crime audit, or real-world route validation performed in this feasibility check.']
    (CACHE / 'summary.json').write_text(json.dumps(summary, indent=2))
    print('Geoapify audit complete. Summary saved without credentials.', flush=True)

if __name__ == '__main__':
    try:
        KEY = load_key()
        run()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
