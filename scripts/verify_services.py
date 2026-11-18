"""End-to-end checks through the running Next.js server, not directly against the API."""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import quote
CONFIG=json.loads((Path(__file__).resolve().parents[1]/'frontend/src/config/cities.json').read_text())
CITY=CONFIG['cities'][CONFIG['activeCity']]
BASE = 'http://127.0.0.1:3000'

def read(path):
    with urllib.request.urlopen(BASE+path,timeout=40) as response:
        assert response.status==200
        return json.load(response)

def main():
    health=read('/api/database/health')
    assert health['status']=='ok' and health['postgis_version']
    print('Next.js → FastAPI → Neon health: HTTP 200')
    evidence=read('/api/evidence')
    kinds={kind:sum(f['properties']['kind']==kind for f in evidence['features']) for kind in ('road','street_lamp')}
    assert kinds['road']>0  # Missing lamp tags are legitimate unknown coverage.
    assert all(f['properties']['source_url'] and f['properties']['fetched_at'] for f in evidence['features'])
    print('Next.js → FastAPI → PostGIS evidence: HTTP 200',json.dumps(kinds))
    print('Source attribution and fetch timestamps: PASS')
    results=read('/api/search?q='+quote(CITY['origin']['label']))['results']
    assert results
    print('Geoapify location search: HTTP 200')
    payload={key:{axis:CITY[place][axis] for axis in ('lat','lon')} for key,place in [('start','origin'),('end','destination')]}
    request=urllib.request.Request(BASE+'/api/routes',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=45) as response:
        routes=json.load(response)['features']
        assert routes and all(f['properties']['distance']>0 for f in routes)
        print('Geoapify walking routes: HTTP 200,',len(routes),'candidate(s)')

if __name__=='__main__':
    try:
        main()
    except (AssertionError,urllib.error.URLError,TimeoutError,KeyError):
        print('End-to-end service check FAILED. Inspect the local app; credentials were not logged.',file=sys.stderr)
        sys.exit(1)
