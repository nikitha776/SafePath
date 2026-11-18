import asyncio
import json
from contextlib import asynccontextmanager
from typing import Annotated, Literal
import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field
from app.config import get_settings
from app.city import CITY, WEST, SOUTH, EAST, NORTH
from app.evidence import router as evidence_router
from app.places import PlacesRequest, route_places
from app.activity import ActivityRequest, analyze_activity
from app.assessment import assess_with_cached_evidence
from starlette.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
        app.state.http = client
        yield

app = FastAPI(title='SafePath API', version='0.1.0', lifespan=lifespan)
app.include_router(evidence_router)

class Point(BaseModel):
    lat: float = Field(ge=SOUTH, le=NORTH)
    lon: float = Field(ge=WEST, le=EAST)

class RouteRequest(BaseModel):
    start: Point
    end: Point

async def provider(path: str, params: dict, *, payload: dict | None = None):
    key = get_settings().geoapify_api_key
    if not key:
        raise HTTPException(503, 'Geoapify key is not configured on the backend.')
    try:
        response = await app.state.http.request('POST' if payload is not None else 'GET', 'https://api.geoapify.com/' + path, params={**params, 'apiKey': key}, **({'json': payload} if payload is not None else {}))
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        message = 'Mapping service rate limit reached. Please try later.' if status == 429 else 'Mapping provider could not complete this request.'
        raise HTTPException(502, message) from None
    except httpx.RequestError:
        raise HTTPException(502, 'Mapping service is unavailable. Please retry.') from None

@app.get('/api/health')
def health():
    settings = get_settings()
    return {'status': 'ok', 'geoapify_configured': bool(settings.geoapify_api_key), 'database_configured': bool(settings.database_url), 'assessment_available': True, 'assessment_method': 'prototype_mapped_conditions'}

@app.get('/api/search')
async def search(q: Annotated[str, Query(min_length=3, max_length=200)]):
    response = await provider('v1/geocode/search', {'text': q, 'filter': f'rect:{WEST},{SOUTH},{EAST},{NORTH}', 'bias': f"proximity:{CITY['center'][0]},{CITY['center'][1]}", 'limit': 5, 'format': 'geojson'})
    items = []
    for feature in response.json().get('features', []):
        p = feature.get('properties', {})
        if p.get('result_type') in ('city', 'state', 'country', 'county') or p.get('rank', {}).get('confidence', 0) < 0.7:
            continue
        if p.get('lat') is not None and p.get('lon') is not None:
            items.append({'id': p.get('place_id'), 'label': p.get('formatted', p.get('name', q)), 'lat': p['lat'], 'lon': p['lon']})
    return {'results': items}

@app.post('/api/routes')
async def routes(body: RouteRequest):
    if body.start == body.end:
        raise HTTPException(422, 'Choose different start and destination locations.')
    waypoints = f'{body.start.lat},{body.start.lon}|{body.end.lat},{body.end.lon}'
    async def fetch(kind):
        response = await provider('v1/routing', {'waypoints': waypoints, 'mode': 'walk', 'type': kind, 'details': 'route_details', 'format': 'geojson'})
        return kind, response.json().get('features', [])
    # Partial provider failures must not hide a successfully retrieved route.
    responses = await asyncio.gather(fetch('balanced'), fetch('short'), return_exceptions=True)
    results, seen = [], set()
    for item in responses:
        if isinstance(item, BaseException):
            continue
        kind, features = item
        for f in features:
            geometry = f.get('geometry')
            signature = json.dumps(geometry, sort_keys=True)
            if not geometry or signature in seen:
                continue
            seen.add(signature)
            p = f.get('properties', {})
            results.append({'type': 'Feature', 'geometry': geometry, 'properties': {'preference': kind, 'distance': p.get('distance'), 'time': p.get('time')}})
    if not results:
        if all(isinstance(x, BaseException) for x in responses):
            raise HTTPException(502, 'Route provider unavailable. Please try again.')
        raise HTTPException(404, 'No walking route was found between these locations.')
    return {'type': 'FeatureCollection', 'features': results, 'partial': any(isinstance(x, BaseException) for x in responses), 'assessment': 'Not yet assessed. Routes are distance/time candidates, not safety recommendations.'}

@app.get('/api/map/tiles/{z}/{x}/{y}.png')
async def tile(z: int, x: int, y: int, style: Literal['osm-carto', 'dark-matter'] = 'dark-matter'):
    if not (0 <= z <= 20 and 0 <= x < 2**z and 0 <= y < 2**z):
        raise HTTPException(422, 'Invalid tile coordinates.')
    response = await provider(f'v1/tile/{style}/{z}/{x}/{y}.png', {})
    return Response(content=response.content, media_type='image/png', headers={'Cache-Control': 'public, max-age=3600'})


@app.post('/api/route-places')
async def places(body: PlacesRequest):
    return await route_places(body, provider)


@app.post('/api/route-activity')
async def activity(body: ActivityRequest):
    places = await route_places(body, provider)
    analysis = await run_in_threadpool(analyze_activity, body, places)
    return await run_in_threadpool(assess_with_cached_evidence, body, analysis)
