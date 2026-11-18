from datetime import datetime
import copy
import httpx
import pytest
from app.activity import ActivityRequest, analyze_activity, schedule_state, route_segments, progress_at, IST
from app.city import CITY
from app.main import app
from app.places import CACHE
from app.config import get_settings
from fastapi.testclient import TestClient


def at(value):
    return datetime.fromisoformat(value).astimezone(IST)


@pytest.mark.parametrize('hours,time,status', [
    ('Mo, Tu, Th, Fr 11:00-19:00; Sa 12:00-19:00', '2026-10-22T23:10:00+05:30', 'expected_closed'),
    ('Mo, Tu, Th, Fr 11:00-19:00; Sa 12:00-19:00', '2026-10-22T12:00:00+05:30', 'expected_open'),
    ('09:00-12:00, 14:00-18:00', '2026-10-22T13:00:00+05:30', 'expected_closed'),
    ('09:00-12:00, 14:00-18:00', '2026-10-22T23:00:00+05:30', 'expected_closed'),
    ('24/7', '2026-10-22T23:15:00+05:30', 'expected_open'),
    ('Mo-Su 09:00-23:00', '2026-10-22T22:59:00+05:30', 'expected_open'),
    ('Mo-Su 09:00-23:00', '2026-10-22T23:00:00+05:30', 'expected_closed'),
    ('Fr 20:00-02:00', '2026-10-24T01:30:00+05:30', 'expected_open'),
    ('Fr 20:00-02:00', '2026-10-24T02:00:00+05:30', 'expected_closed'),
    ('Mo-Fr 09:00-18:00', '2026-10-25T12:00:00+05:30', 'expected_closed'),
    ('09:00-12:00,14:00-18:00', '2026-10-22T13:00:00+05:30', 'expected_closed'),
    ('09:00-12:00,14:00-18:00', '2026-10-22T15:00:00+05:30', 'expected_open'),
    ('09:00-18:00', '2026-10-22T04:00:00+00:00', 'expected_open'),
    ('Mo-Su 00:00-24:00', '2026-10-23T00:00:00+05:30', 'expected_open'),
    (None, '2026-10-22T22:00:00+05:30', 'hours_unknown'),
    ('nonsense hours', '2026-10-22T22:00:00+05:30', 'hours_unknown'),
    ('"by appointment"', '2026-10-22T22:00:00+05:30', 'hours_unknown'),
    ('09:00-18:00; PH off', '2026-10-22T12:00:00+05:30', 'hours_unknown'),
    ('sunrise-sunset', '2026-10-22T12:00:00+05:30', 'hours_unknown'),
])
def test_schedule_boundaries_and_unknowns(hours, time, status):
    assert schedule_state(hours, at(time))[0] == status


def inputs():
    lon, lat = CITY['center']
    geometry = {'type': 'LineString', 'coordinates': [[lon, lat], [lon + .01, lat]]}
    places = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon + .005, lat]},
         'properties': {'id': 'shop', 'kind': 'shop', 'opening_hours': '09:00-23:00'}},
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon + .01, lat]},
         'properties': {'id': 'police', 'kind': 'police', 'opening_hours': '24/7'}},
    ]}
    return geometry, places


def test_arrival_after_closing_and_cache_is_immutable():
    geometry, places = inputs()
    original = copy.deepcopy(places)
    body = ActivityRequest(geometry=geometry, departure_time='2026-10-22T22:45:00+05:30', duration_seconds=3600)
    late = analyze_activity(body, places)
    assert late['features'][0]['properties']['estimated_arrival'].startswith('2026-10-22T23:15:00')
    assert late['features'][0]['properties']['schedule_status'] == 'expected_closed'
    assert late['summary']['businesses']['total'] == 1  # Police listing is not commercial activity.
    assert late['summary']['businesses']['expected_closed'] == 1
    early = analyze_activity(body.model_copy(update={'departure_time': at('2026-10-22T21:00:00+05:30')}), places)
    assert early['features'][0]['properties']['schedule_status'] == 'expected_open'
    assert places == original


def test_midnight_rollover_and_empty_coverage():
    geometry, _ = inputs()
    body = ActivityRequest(geometry=geometry, departure_time='2026-10-22T23:55:00+05:30', duration_seconds=1200)
    result = analyze_activity(body, {'features': []})
    assert result['estimated_route_arrival'].startswith('2026-10-23T00:15:00')
    assert result['summary']['schedule_coverage_percent'] is None


def test_projection_does_not_create_connector_between_legs():
    segments, total = route_segments({'type': 'MultiLineString', 'coordinates': [[[0, 0], [.001, 0]], [[.01, 0], [.011, 0]]]})
    assert 220 < total < 225
    assert progress_at([.0105, 0], segments) == pytest.approx(total * .75)


def test_activity_endpoint_validation_and_schedule_cache(monkeypatch):
    geometry, places = inputs()
    CACHE.clear()
    monkeypatch.setattr('app.assessment.load_route_evidence', lambda _: {'available': False, 'truncated': False, 'features': []})
    monkeypatch.setattr(get_settings(), 'geoapify_api_key', 'private-test-key')
    calls = []
    def handler(request):
        calls.append(request)
        # Return just one actual shop in its requested category.
        import json
        data = json.loads(request.content)
        feature = copy.deepcopy(places['features'][0]); feature['properties'].update(place_id='sample', name='Example shop', categories=['commercial'])
        return httpx.Response(200, json={'features': [feature] if data['categories'] == ['commercial'] else []})
    with TestClient(app) as client:
        client.portal.call(app.state.http.aclose)
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        payload = {'geometry': geometry, 'departure_time': '2026-10-22T22:45:00+05:30', 'duration_seconds': 3600}
        assert client.post('/api/route-activity', json={**payload, 'departure_time': '2026-10-22T22:45'}).status_code == 422
        assert client.post('/api/route-activity', json={**payload, 'duration_seconds': 0}).status_code == 422
        late = client.post('/api/route-activity', json=payload)
        assert late.status_code == 200
        assert late.json()['summary']['expected_closed'] == 1
        assert late.json()['assessment']['evidence_available'] is False
        assert late.json()['assessment']['rankable'] is False
        assert 'private-test-key' not in late.text
        early = client.post('/api/route-activity', json={**payload, 'departure_time': '2026-10-22T21:00:00+05:30'})
        assert early.json()['summary']['expected_open'] == 1
        assert len(calls) == 5  # Departure changes reuse only raw POIs, then reevaluate schedules.
    CACHE.clear()
