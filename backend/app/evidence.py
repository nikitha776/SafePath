"""Read cached, sourced infrastructure evidence; never infer current light operation."""
import json
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.config import get_settings
from app.city import WEST, SOUTH, EAST, NORTH, EVIDENCE_WEST, EVIDENCE_SOUTH, EVIDENCE_EAST, EVIDENCE_NORTH
from app.database import get_engine

router = APIRouter(prefix='/api')

@router.get('/database/health')
def database_health():
    if not get_settings().database_url:
        raise HTTPException(503, 'PostgreSQL is not configured.')
    try:
        with get_engine().connect() as connection:
            version = connection.execute(text('SELECT PostGIS_Version()')).scalar_one()
            counts = connection.execute(text('SELECT evidence_kind, count(*) FROM osm_evidence GROUP BY evidence_kind')).all()
        return {'status': 'ok', 'database': 'postgresql', 'postgis_version': version, 'evidence_counts': dict(counts)}
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, 'Database unavailable or migration not applied.') from None

@router.get('/evidence')
def evidence(
    west: Annotated[float, Query(ge=WEST, le=EAST)] = EVIDENCE_WEST,
    south: Annotated[float, Query(ge=SOUTH, le=NORTH)] = EVIDENCE_SOUTH,
    east: Annotated[float, Query(ge=WEST, le=EAST)] = EVIDENCE_EAST,
    north: Annotated[float, Query(ge=SOUTH, le=NORTH)] = EVIDENCE_NORTH,
):
    if west >= east or south >= north or east-west > .1 or north-south > .1:
        raise HTTPException(422, 'Choose a valid pilot-area bounding box no wider than 0.1 degrees.')
    if not get_settings().database_url:
        raise HTTPException(503, 'PostgreSQL is not configured.')
    try:
        with get_engine().connect() as connection:
            rows = connection.execute(text('''SELECT osm_type, osm_id, evidence_kind,
                ST_AsGeoJSON(geometry) AS geometry, tags, source_url, fetched_at, source_updated_at
                FROM osm_evidence
                WHERE ST_Intersects(geometry,ST_MakeEnvelope(:west,:south,:east,:north,4326))
                ORDER BY osm_type,osm_id,evidence_kind LIMIT 1001'''), {'west': west, 'south': south, 'east': east, 'north': north}).mappings().all()
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, 'Cached evidence is unavailable. Check the database and migration.') from None
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': json.loads(row['geometry']), 'properties': {
            'osm_type': row['osm_type'], 'osm_id': row['osm_id'], 'kind': row['evidence_kind'],
            'lit': row['tags'].get('lit', 'unknown'), 'highway': row['tags'].get('highway'),
            'source_url': row['source_url'], 'fetched_at': row['fetched_at'].isoformat(),
            'source_updated_at': row['source_updated_at'].isoformat() if row['source_updated_at'] else None,
        }} for row in rows[:1000]], 'truncated': len(rows)>1000,
        'notice': 'Cached OSM infrastructure only. Missing tags mean unknown; lamp operation is unverified.',
        'attribution': '© OpenStreetMap contributors, ODbL'}
