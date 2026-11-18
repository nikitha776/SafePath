"""Prototype mapped-condition indicators. These are not calibrated personal-safety probabilities."""
import json
import math
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_engine
from app.activity import IST, BUSINESSES, schedule_state
from app.places import route_distance, route_lines


def load_route_evidence(geometry):
    try:
        with get_engine().connect() as connection:
            rows = connection.execute(text('''SELECT evidence_kind, ST_AsGeoJSON(geometry) AS geometry,
                tags, fetched_at, source_url FROM osm_evidence
                WHERE ST_DWithin(geometry::geography, ST_SetSRID(ST_GeomFromGeoJSON(:route),4326)::geography,150)
                ORDER BY osm_type, osm_id, evidence_kind LIMIT 2001'''), {'route': json.dumps(geometry)}).mappings().all()
        return {'available': True, 'truncated': len(rows)>2000, 'features': [
            {'type':'Feature', 'geometry':json.loads(row['geometry']), 'properties':{'kind':row['evidence_kind'],
             **row['tags'], 'fetched_at':row['fetched_at'].isoformat(), 'source_url':row['source_url']}} for row in rows[:2000]]}
    except (SQLAlchemyError, RuntimeError):
        return {'available': False, 'truncated': False, 'features': []}


def length(a, b):
    return math.hypot((b[0]-a[0])*math.cos(math.radians((a[1]+b[1])/2)), b[1]-a[1])*111195.08


def split_route(geometry, size=100):
    """At most 100 m per section; preserve vertices and separate geometry legs."""
    sections, offset = [], 0.0
    for line in route_lines(geometry):
        points, traveled = [], 0.0
        for a, b in zip(line, line[1:]):
            remaining = length(a, b)
            if remaining <= 1e-6:
                continue
            cursor = list(a)
            if not points:
                points = [cursor]
            while remaining > 1e-6:
                take = min(size-traveled, remaining)
                ratio = take/remaining
                end = [cursor[0]+(b[0]-cursor[0])*ratio, cursor[1]+(b[1]-cursor[1])*ratio]
                points.append(end); traveled += take; remaining -= take; cursor = end
                if traveled >= size-1e-6:
                    sections.append({'coordinates': points, 'length': traveled, 'offset': offset})
                    offset += traveled; points = [cursor]; traveled = 0.0
        if traveled > 1e-6:
            sections.append({'coordinates': points, 'length': traveled, 'offset': offset})
            offset += traveled
    return sections, offset


def point_at(points, distance):
    for a, b in zip(points, points[1:]):
        span = length(a,b)
        if span >= distance and span:
            t = distance/span
            return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t]
        distance -= span
    return points[-1]


def nearby_distance(point, geometry):
    return route_distance(point, geometry)


def assess_route(body, activity, evidence, now=None):
    sections, total = split_route(body.geometry.model_dump())
    now = now or datetime.now(timezone.utc)
    roads = [f for f in evidence['features'] if f['properties'].get('kind')=='road' and f['geometry']['type'] in ('LineString','MultiLineString')]
    lamps = [f for f in evidence['features'] if f['properties'].get('kind')=='street_lamp' and f['geometry']['type']=='Point']
    features, weighted_confidence, lit_length, road_length, adverse_length = [], 0.0, 0.0, 0.0, 0.0
    longest_gap = gap = 0.0
    weighted_score, scored_length = 0.0, 0.0
    source_dates, freshness = [], 1.0
    for f in evidence['features']:
        stamp = f['properties'].get('fetched_at')
        try:
            age = (now-datetime.fromisoformat(stamp)).total_seconds()/86400
            source_dates.append(stamp)
            if age>180: freshness=min(freshness,.5)
        except (TypeError,ValueError): freshness=min(freshness,.5)
    partial = bool(activity.get('truncated_categories') or activity.get('unavailable_categories') or evidence.get('truncated'))
    businesses = [f for f in activity['features'] if f['properties']['kind'] in BUSINESSES]
    assistance = [f for f in activity['features'] if f['properties']['kind'] in ('police','hospital')]
    for index, section in enumerate(sections):
        geometry = {'type':'LineString','coordinates':section['coordinates']}
        arrival = body.departure_time.astimezone(IST)+timedelta(seconds=body.duration_seconds*(section['offset']+section['length']/2)/total)
        # Fixed pilot window, not a computed sunset/sunrise or live visibility observation.
        nighttime = arrival.hour>=18 or arrival.hour<6
        counts = {'expected_open':0,'expected_closed':0,'hours_unknown':0}
        for place in businesses:
            if nearby_distance(place['geometry']['coordinates'],geometry)<=100:
                status,_=schedule_state(place['properties'].get('opening_hours'),arrival)
                counts[status]+=1
        nearby_assistance=sum(nearby_distance(p['geometry']['coordinates'],geometry)<=200 for p in assistance)
        samples = max(2, math.ceil(section['length']/20)+1)
        lighting_known = mapped_unlit = road_known = access_known = restricted = 0
        for sample in range(samples):
            point = point_at(section['coordinates'], section['length']*sample/(samples-1))
            nearest = None; distance = 15.0
            for road in roads:
                d = nearby_distance(point,road['geometry'])
                if d<distance: nearest=road;distance=d
            tags = nearest['properties'] if nearest else {}
            if nearest: road_known+=1
            if tags.get('lit')=='no': lighting_known+=1;mapped_unlit+=1
            elif tags.get('lit')=='yes' or any(length(point,lamp['geometry']['coordinates'])<=20 for lamp in lamps): lighting_known+=1
            access = tags.get('foot') or tags.get('access')
            if access in ('no','private','yes','designated','permissive','destination'):
                access_known+=1
                if access in ('no','private'): restricted+=1
        lighting_fraction=lighting_known/samples
        road_fraction=road_known/samples
        listed=sum(counts.values()); known=counts['expected_open']+counts['expected_closed']
        schedule_fraction=known/listed if listed else 0
        confidence=(.45*schedule_fraction+.4*lighting_fraction+.15*road_fraction)*100*freshness
        if partial: confidence*=.6
        if not evidence.get('available'): confidence=min(confidence,35)
        observed=[]
        if listed and schedule_fraction>=.6: observed.append((counts['expected_closed']/known,.45))
        if nighttime and lighting_known: observed.append((mapped_unlit/lighting_known,.35))
        if access_known: observed.append((restricted/access_known,.2))
        score=sum(value*weight for value,weight in observed)/sum(weight for _,weight in observed)*100 if observed else None
        if restricted or (nighttime and mapped_unlit): concern='more_concerns'
        elif confidence>=60 and score is not None: concern='more_concerns' if score>=60 else 'mixed' if score>=30 else 'fewer_concerns'
        else: concern='unknown'
        reasons=[]
        if counts['expected_open']: reasons.append(f"{counts['expected_open']} businesses scheduled open nearby at this section's estimated arrival.")
        if counts['hours_unknown']: reasons.append(f"{counts['hours_unknown']} nearby business schedules unknown.")
        if nighttime and mapped_unlit: reasons.append('Nearby road records include lit=no; actual lighting is unverified.')
        elif lighting_known: reasons.append('Mapped lamps or lit=yes road tags cover part of this section; lamp operation is unverified.')
        else: reasons.append('Lighting evidence missing; illumination is unknown.')
        if restricted: reasons.append('Nearby road records indicate foot/access restrictions; entrance and current access require checking.')
        if nearby_assistance: reasons.append(f'{nearby_assistance} hospital/police listings within 200 m straight-line; access and assistance unconfirmed.')
        if not counts['expected_open'] and not nearby_assistance:
            gap+=section['length'];longest_gap=max(longest_gap,gap)
        else: gap=0
        # A new geometry leg cannot extend a continuous support gap.
        if index+1<len(sections) and length(section['coordinates'][-1],sections[index+1]['coordinates'][0])>1:
            gap=0
        lit_length+=lighting_fraction*section['length'];road_length+=road_fraction*section['length']
        if concern=='more_concerns': adverse_length+=section['length']
        weighted_confidence+=confidence*section['length']
        if score is not None and confidence>=60:
            weighted_score+=score*section['length'];scored_length+=section['length']
        features.append({'type':'Feature','geometry':geometry,'properties':{
            'index':index+1,'distance_from_start_m':round(section['offset']),'length_m':round(section['length'],1),
            'estimated_arrival':arrival.isoformat(),'nighttime_window':nighttime,'concern':concern,
            'concern_score':round(score) if score is not None and confidence>=60 else None,
            'confidence_percent':round(confidence),'businesses':counts,'assistance_listings':nearby_assistance,
            'lighting_coverage_percent':round(lighting_fraction*100),'reasons':reasons}})
    confidence=weighted_confidence/total if total else 0
    schedule_coverage=activity['summary']['schedule_coverage_percent'] or 0
    lighting_coverage=100*lit_length/total if total else 0
    scored_coverage=scored_length/total if total else 0
    rankable=bool(total and confidence>=60 and schedule_coverage>=60 and lighting_coverage>=60 and scored_coverage>=.8 and not partial and evidence.get('available') and freshness==1)
    concern_score=round(weighted_score/scored_length) if rankable else None
    reasons=[]
    if schedule_coverage<60: reasons.append(f'Only {schedule_coverage}% of listed businesses have usable schedules.')
    if lighting_coverage<60: reasons.append(f'Mapped lighting evidence covers approximately {round(lighting_coverage)}% of the route.')
    if partial: reasons.append('Place listings or cached infrastructure are incomplete/truncated.')
    if not evidence.get('available'): reasons.append('Cached infrastructure is currently unavailable.')
    if freshness<1: reasons.append('Some infrastructure fetch dates are missing or older than 180 days.')
    reasons.append('Crime, observed footfall and verified current illumination are not available in this assessment.')
    return {'version':'mapped-conditions-v1','segments':{'type':'FeatureCollection','features':features},
            'rankable':rankable,'concern_score':concern_score,'concern_label':'Insufficient evidence' if not rankable else 'More concerns' if concern_score>=60 else 'Mixed conditions' if concern_score>=30 else 'Fewer concerns',
            'confidence_percent':round(confidence),'confidence_label':'Limited' if confidence<40 else 'Partial' if confidence<70 else 'Stronger',
            'lighting_coverage_percent':round(lighting_coverage),'road_coverage_percent':round(100*road_length/total) if total else 0,
            'mapped_concern_length_m':round(adverse_length),'longest_mapped_support_gap_m':round(longest_gap),
            'reasons':reasons,'evidence_available':evidence.get('available',False),'oldest_infrastructure_fetch':min(source_dates) if source_dates else None,
            'method':'Prototype coverage index: schedules 45%, mapped lighting 40%, road evidence 15%. Partial listings reduce the index; unknown evidence is not an adverse condition. Concern uses only evaluable indicators. Ranking requires >=60% schedule/lighting coverage and confidence, >=80% scored length and complete/fresh sources. These provisional thresholds are not empirically calibrated.',
            'notice':'Mapped-condition indicators, not a probability of harm or a guarantee of safety. A mapped-support gap means no listed scheduled-open business within 100 m and no hospital/police listing within 200 m; it does not establish an isolated or deserted road.'}


def assess_with_cached_evidence(body, activity):
    return {**activity, 'assessment':assess_route(body, activity, load_route_evidence(body.geometry.model_dump()))}
