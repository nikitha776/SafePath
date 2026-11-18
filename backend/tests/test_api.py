import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings
from app.city import CITY, CONFIG

@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value

def install_transport(client, handler):
    async def apply():
        await app.state.http.aclose()
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.portal.call(apply)

def test_invalid_location_never_calls_provider(client):
    response = client.post('/api/routes', json={'start': {'lat': 0, 'lon': 0}, 'end': {'lat': 13, 'lon': (CITY['center'][0] + -0.03865)}})
    assert response.status_code == 422

def test_deduplicates_routes_and_does_not_echo_credentials(client, monkeypatch):
    monkeypatch.setattr(get_settings(), 'geoapify_api_key', 'private-test-key')
    def handle(request):
        return httpx.Response(200, json={'properties': {'apiKey': 'private-test-key'}, 'features': [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[(CITY['center'][0] + -0.00865),(CITY['center'][1] + -0.00829)],[(CITY['center'][0] + 0.00135),(CITY['center'][1] + 0.00171)]]}, 'properties': {'distance': 1000, 'time': 900}}]})
    install_transport(client, handle)
    response = client.post('/api/routes', json={'start': {'lat':(CITY['center'][1] + -0.00829),'lon':(CITY['center'][0] + -0.00865)},'end':{'lat':(CITY['center'][1] + 0.00171),'lon':(CITY['center'][0] + 0.00135)}})
    assert response.status_code == 200
    assert len(response.json()['features']) == 1
    assert 'private-test-key' not in response.text
    assert response.json()['partial'] is False

def test_partial_failure_keeps_available_route(client, monkeypatch):
    monkeypatch.setattr(get_settings(), 'geoapify_api_key', 'private-test-key')
    def handle(request):
        if request.url.params.get('type') == 'short':
            return httpx.Response(429)
        return httpx.Response(200, json={'features':[{'type':'Feature','geometry':{'type':'LineString','coordinates':[[(CITY['center'][0] + -0.00865),(CITY['center'][1] + -0.00829)],[(CITY['center'][0] + 0.00135),(CITY['center'][1] + 0.00171)]]},'properties':{'distance':1000,'time':900}}]})
    install_transport(client, handle)
    response = client.post('/api/routes', json={'start':{'lat':(CITY['center'][1] + -0.00829),'lon':(CITY['center'][0] + -0.00865)},'end':{'lat':(CITY['center'][1] + 0.00171),'lon':(CITY['center'][0] + 0.00135)}})
    assert response.status_code == 200
    assert response.json()['partial'] is True

def test_search_rejects_broad_matches(client, monkeypatch):
    monkeypatch.setattr(get_settings(), 'geoapify_api_key', 'private-test-key')
    install_transport(client, lambda _: httpx.Response(200,json={'features':[{'properties':{'result_type':'city','lat':(CITY['center'][1] + -0.00829),'lon':(CITY['center'][0] + -0.03865),'rank':{'confidence':1}}}]}))
    assert client.get('/api/search', params={'q':'Vijayawada'}).json()['results'] == []

def test_database_missing_configuration_is_explicit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), 'database_url', '')
    response = client.get('/api/database/health')
    assert response.status_code == 503
    assert response.json()['detail'] == 'PostgreSQL is not configured.'

def test_evidence_bounds_rejected_before_query(client):
    response = client.get('/api/evidence?west=80.7&east=80.6')
    assert response.status_code == 422

def test_places_filter_corridor_classify_and_deduplicate(client, monkeypatch):
    from app.places import CACHE
    CACHE.clear()
    monkeypatch.setattr(get_settings(), 'geoapify_api_key', 'private-test-key')
    def feature(identity, coordinates, categories):
        return {'type':'Feature','geometry':{'type':'Point','coordinates':coordinates},'properties':{'name':'Test place','place_id':identity,'categories':categories,'datasource':{'raw':{'osm_type':'n','osm_id':identity,'opening_hours':'24/7'}},'apiKey':'private-test-key'}}
    def handle(request):
        import json
        payload=json.loads(request.content)
        assert payload['filter']['type']=='polyline'
        assert payload['filter']['buffer']==100
        category=payload['categories'][0]
        features=[]
        if category=='commercial':
            features=[feature(1,[(CITY['center'][0] + 0.00335),(CITY['center'][1] + -0.00029)],['commercial','healthcare.pharmacy']),feature(2,[(CITY['center'][0] + 0.00135),(CITY['center'][1] + 0.00971)],['commercial'])]
        if category=='healthcare.pharmacy':
            features=[feature(1,[(CITY['center'][0] + 0.00335),(CITY['center'][1] + -0.00029)],['healthcare.pharmacy'])]
        return httpx.Response(200,json={'features':features})
    install_transport(client,handle)
    response=client.post('/api/route-places',json={'geometry':{'type':'LineString','coordinates':[[(CITY['center'][0] + 0.0),(CITY['center'][1] + 0.0)],[(CITY['center'][0] + 0.00754),(CITY['center'][1] + -0.00039)]]}})
    assert response.status_code==200
    data=response.json()
    assert len(data['features'])==1
    assert data['features'][0]['properties']['kind']=='pharmacy'
    assert data['features'][0]['properties']['opening_hours']=='24/7'
    assert data['features'][0]['properties']['availability']=='unverified'
    assert 'private-test-key' not in response.text
    CACHE.clear()

def test_places_partial_category_failure_is_explicit(client,monkeypatch):
    from app.places import CACHE
    import json
    CACHE.clear()
    monkeypatch.setattr(get_settings(),'geoapify_api_key','private-test-key')
    def handle(request):
        category=json.loads(request.content)['categories'][0]
        return httpx.Response(429) if category=='service.police' else httpx.Response(200,json={'features':[]})
    install_transport(client,handle)
    response=client.post('/api/route-places',json={'geometry':{'type':'LineString','coordinates':[[(CITY['center'][0] + 0.0),(CITY['center'][1] + 0.0)],[(CITY['center'][0] + 0.00754),(CITY['center'][1] + -0.00039)]]}})
    assert response.status_code==200
    assert response.json()['unavailable_categories']==['police']
    assert not CACHE

def test_places_do_not_join_disconnected_route_legs():
    from app.places import route_distance
    geometry={'type':'MultiLineString','coordinates':[[[(CITY['center'][0] + -0.03865),(CITY['center'][1] + -0.00829)],[(CITY['center'][0] + -0.02865),(CITY['center'][1] + -0.00829)]],[[(CITY['center'][0] + 0.01135),(CITY['center'][1] + -0.00829)],[(CITY['center'][0] + 0.02135),(CITY['center'][1] + -0.00829)]]]}
    assert route_distance([(CITY['center'][0] + -0.00865),(CITY['center'][1] + -0.00829)],geometry)>1000

def test_places_reject_unsupported_geometry_and_large_buffer(client):
    assert client.post('/api/route-places',json={'geometry':{'type':'Polygon','coordinates':[]}}).status_code==422
    assert client.post('/api/route-places',json={'geometry':{'type':'LineString','coordinates':[[(CITY['center'][0] + -0.00865),(CITY['center'][1] + -0.00829)],[(CITY['center'][0] + 0.00135),(CITY['center'][1] + 0.00171)]]},'buffer_m':5000}).status_code==422


def test_search_uses_active_city_bounds(client, monkeypatch):
    from app.city import WEST, SOUTH, EAST, NORTH
    monkeypatch.setattr(get_settings(), 'geoapify_api_key', 'private-test-key')
    def handle(request):
        assert request.url.params['filter'] == f'rect:{WEST},{SOUTH},{EAST},{NORTH}'
        return httpx.Response(200, json={'features': []})
    install_transport(client, handle)
    assert client.get('/api/search', params={'q': 'Vijayawada Junction'}).status_code == 200


def test_inactive_city_rejected_for_routes_and_places(client):
    city = CONFIG['cities']['vijayawada' if CONFIG['activeCity'] == 'bengaluru' else 'bengaluru']
    origin, destination = city['origin'], city['destination']
    assert client.post('/api/routes', json={'start': origin, 'end': destination}).status_code == 422
    assert client.post('/api/route-places', json={'geometry': {'type': 'LineString', 'coordinates': [[origin['lon'], origin['lat']], [destination['lon'], destination['lat']]]}}).status_code == 422
