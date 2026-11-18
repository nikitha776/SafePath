"""Bounded route-corridor POIs. Coordinates are mapped locations, not access guarantees."""
import asyncio
import hashlib
import json
import math
import time
from collections import OrderedDict
from typing import Annotated, Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

from app.city import WEST, SOUTH, EAST, NORTH

Lon = Annotated[float, Field(ge=WEST, le=EAST)]
Lat = Annotated[float, Field(ge=SOUTH, le=NORTH)]
Position = tuple[Lon, Lat]
Line = Annotated[list[Position], Field(min_length=2, max_length=2000)]

class LineGeometry(BaseModel):
    type: Literal['LineString']
    coordinates: Line

class MultiGeometry(BaseModel):
    type: Literal['MultiLineString']
    coordinates: Annotated[list[Line], Field(min_length=1, max_length=20)]

class PlacesRequest(BaseModel):
    geometry: LineGeometry | MultiGeometry
    buffer_m: int = Field(default=100, ge=50, le=300)

    @model_validator(mode='after')
    def bounded_geometry(self):
        lines = route_lines(self.geometry.model_dump())
        if sum(map(len,lines))>2000:
            raise ValueError('Route geometry may contain at most 2000 positions.')
        if sum(math.hypot((b[0]-a[0])*108000,(b[1]-a[1])*111200) for line in lines for a,b in zip(line,line[1:]))>50000:
            raise ValueError('The pilot supports routes up to 50 kilometers.')
        return self

CATEGORIES = {
    'shop': 'commercial',
    'fuel': 'service.vehicle.fuel',
    'pharmacy': 'healthcare.pharmacy',
    'hospital': 'healthcare.hospital',
    'police': 'service.police',
}
CACHE = OrderedDict()
CACHE_TTL = 300


def route_lines(geometry):
    return [geometry['coordinates']] if geometry['type']=='LineString' else geometry['coordinates']


def route_distance(point, geometry):
    """Approximate shortest ground distance in meters, with no joins between route legs."""
    radius=6371008.8
    lon,lat=point
    scale=math.cos(math.radians(lat))
    def project(p):
        return math.radians(p[0]-lon)*radius*scale, math.radians(p[1]-lat)*radius
    best=math.inf
    for line in route_lines(geometry):
        for start,end in zip(line,line[1:]):
            ax,ay=project(start)
            bx,by=project(end)
            dx,dy=bx-ax,by-ay
            fraction=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))) if dx or dy else 0
            best=min(best,math.hypot(ax+fraction*dx,ay+fraction*dy))
    return best


def category_for(properties, fallback):
    categories=properties.get('categories',[])
    # More specific facilities take priority over the broad commercial category.
    for kind in ('police','hospital','pharmacy','fuel'):
        if any(c==CATEGORIES[kind] or c.startswith(CATEGORIES[kind]+'.') for c in categories):
            return kind
    return fallback


def clean_place(feature, kind, geometry, buffer_m):
    p=feature.get('properties',{})
    geom=feature.get('geometry',{})
    if geom.get('type')!='Point' or len(geom.get('coordinates',[]))<2:
        return None
    coords=geom['coordinates'][:2]
    try:
        if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in coords):
            return None
        distance=route_distance(coords,geometry)
    except (TypeError,ValueError):
        return None
    if distance>buffer_m:
        return None
    raw=p.get('datasource',{}).get('raw',{}) or {}
    identity=f"osm:{raw['osm_type']}:{raw['osm_id']}" if raw.get('osm_type') and raw.get('osm_id') else p.get('place_id')
    if not identity:
        identity=f"{p.get('name','')}:{coords[0]:.6f}:{coords[1]:.6f}"
    return {'type':'Feature','geometry':{'type':'Point','coordinates':coords},'properties':{
        'id':identity,'kind':category_for(p,kind),'name':p.get('name') or 'Unnamed location',
        'address':p.get('formatted') or p.get('address_line2') or '',
        'opening_hours':hours if isinstance(hours := p.get('opening_hours') or raw.get('opening_hours'), str) else None,
        'distance_from_route_m':round(distance),'availability':'unverified',
    }}


async def route_places(body, provider):
    geometry=body.geometry.model_dump()
    key=hashlib.sha256(json.dumps([geometry,body.buffer_m],sort_keys=True).encode()).hexdigest()
    cached=CACHE.get(key)
    if cached and cached[0]>time.monotonic():
        CACHE.move_to_end(key)
        return cached[1]
    semaphore=asyncio.Semaphore(3)
    async def fetch(kind,category):
        async with semaphore:
            response=await provider('v2/places',{},payload={'categories':[category],
                'filter':{'type':'polyline','geometry':geometry,'buffer':body.buffer_m},'limit':100})
            return kind,response.json().get('features',[])
    responses=await asyncio.gather(*(fetch(k,v) for k,v in CATEGORIES.items()),return_exceptions=True)
    places,failed,truncated={},[],[]
    for requested_kind,result in zip(CATEGORIES,responses):
        if isinstance(result,BaseException):
            failed.append(requested_kind)
            continue
        kind,features=result
        if len(features)>=100:
            truncated.append(kind)
        for feature in features:
            cleaned=clean_place(feature,kind,geometry,body.buffer_m)
            if cleaned:
                places[cleaned['properties']['id']]=cleaned
    if len(failed)==len(CATEGORIES):
        raise HTTPException(502,'Places are temporarily unavailable. Your walking route is still available.')
    result={'type':'FeatureCollection','features':sorted(places.values(),key=lambda f:(f['properties']['distance_from_route_m'],f['properties']['id'])),
        'buffer_m':body.buffer_m,'unavailable_categories':failed,'truncated_categories':truncated,
        'notice':'Mapped places within the route corridor. Schedules and access are unverified; distance is not walking access distance.',
        'attribution':'Geoapify · © OpenStreetMap contributors'}
    # Avoid caching transient failures. Cache only normalized, credential-free results.
    if not failed:
        CACHE[key]=(time.monotonic()+CACHE_TTL,result)
        CACHE.move_to_end(key)
        while len(CACHE)>32:
            CACHE.popitem(last=False)
    return result
