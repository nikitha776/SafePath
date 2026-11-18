"""Schedule estimates at route arrival, never a claim of live availability."""
import math
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from opening_hours import OpeningHours, ParserError, State
from pydantic import AwareDatetime, Field, field_validator
from app.places import PlacesRequest, route_lines

IST = ZoneInfo('Asia/Kolkata')
BUSINESSES = {'shop', 'fuel', 'pharmacy'}

class ActivityRequest(PlacesRequest):
    departure_time: AwareDatetime
    duration_seconds: float = Field(gt=0, le=86400, allow_inf_nan=False)

    @field_validator('departure_time')
    @classmethod
    def supported_date(cls, value):
        if not 2020 <= value.year <= 2100:
            raise ValueError('Choose a departure year between 2020 and 2100.')
        return value


def schedule_state(hours, arrival):
    if not isinstance(hours, str) or not hours.strip():
        return 'hours_unknown', 'No published opening hours.'
    if not re.sub(r'"[^"]*"', '', hours).strip() or re.search(r'appointment|on request|on call', hours, re.I):
        return 'hours_unknown', 'Opening is conditional or by appointment.'
    if len(hours) > 1000:
        return 'hours_unknown', 'Schedule is too complex to evaluate.'
    # No validated regional holiday/school calendar or solar context in this pilot.
    if re.search(r'\b(PH|SH|sunrise|sunset|dawn|dusk|easter)\b', hours, re.I):
        return 'hours_unknown', 'Holiday or solar rules need additional local data.'
    # The parser treats whitespace after weekday-list commas as separate rules.
    # Normalize only comma-separated weekday tokens so their hours stay attached.
    normalized = re.sub(r'\b(Mo|Tu|We|Th|Fr|Sa|Su)\s*,\s*(?=(?:Mo|Tu|We|Th|Fr|Sa|Su)\b)', r'\1,', hours)
    try:
        state, comment = OpeningHours(normalized, timezone=IST).state(arrival.astimezone(IST))
    except (ParserError, ValueError, TypeError, OverflowError):
        return 'hours_unknown', 'Published schedule could not be interpreted.'
    if state == State.OPEN:
        return 'expected_open', 'Published schedule predicts open; live availability is unconfirmed.'
    if state == State.CLOSED:
        return 'expected_closed', 'Published schedule predicts closed; live availability is unconfirmed.'
    return 'hours_unknown', comment or 'Published schedule leaves availability uncertain.'


def route_segments(geometry):
    """Flatten legs in travel order, excluding artificial connectors across gaps."""
    result, total = [], 0.0
    for line in route_lines(geometry):
        for a, b in zip(line, line[1:]):
            lat = math.radians((a[1] + b[1]) / 2)
            length = math.hypot(math.radians(b[0] - a[0]) * math.cos(lat), math.radians(b[1] - a[1])) * 6371008.8
            if length:
                result.append((a, b, total, length))
                total += length
    return result, total


def progress_at(point, segments):
    """Nearest point along the route; ties choose the earliest encounter."""
    lon, lat = point
    xscale = math.cos(math.radians(lat))
    closest, progress = math.inf, 0.0
    for a, b, offset, length in segments:
        ax, ay = (a[0] - lon) * xscale, a[1] - lat
        dx, dy = (b[0] - a[0]) * xscale, b[1] - a[1]
        t = max(0, min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
        distance = math.hypot(ax + t * dx, ay + t * dy)
        if distance < closest - 1e-12:
            closest, progress = distance, offset + t * length
    return progress


def analyze_activity(body, places):
    geometry = body.geometry.model_dump()
    segments, total = route_segments(geometry)
    departure = body.departure_time.astimezone(IST)
    counts = dict(expected_open=0, expected_closed=0, hours_unknown=0)
    businesses = dict(counts)
    features = []
    for feature in places['features']:
        along = progress_at(feature['geometry']['coordinates'], segments)
        seconds = body.duration_seconds * along / total if total else 0
        arrival = departure + timedelta(seconds=seconds)
        properties = {**feature['properties']}
        state, reason = schedule_state(properties.get('opening_hours'), arrival)
        properties.update(schedule_status=state, schedule_reason=reason, estimated_arrival=arrival.isoformat(),
                          arrival_offset_seconds=round(seconds), route_progress_m=round(along))
        counts[state] += 1
        if properties['kind'] in BUSINESSES:
            businesses[state] += 1
        features.append({**feature, 'properties': properties})
    total_businesses = sum(businesses.values())
    return {**places, 'features': features, 'departure_time': departure.isoformat(),
            'estimated_route_arrival': (departure + timedelta(seconds=body.duration_seconds)).isoformat(),
            'summary': {**counts, 'total': len(features), 'businesses': {**businesses, 'total': total_businesses},
                        'schedule_coverage_percent': round(100 * (total_businesses - businesses['hours_unknown']) / total_businesses) if total_businesses else None},
            'arrival_method': 'Average walking pace from route duration, projected onto the nearest route segment. No stops or access detours are included; repeated locations use the first closest encounter.',
            'timezone': 'Asia/Kolkata', 'notice': 'Schedule estimates at arrival, not confirmed real-time opening, street activity or assistance. Missing or unsupported hours remain unknown. Listings may be incomplete.'}
