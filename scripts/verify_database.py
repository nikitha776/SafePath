"""Prove pooled PostgreSQL read/write + PostGIS support, rolling probe writes back."""
import json
import sys
from sqlalchemy import text
from app.database import get_engine

def main():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text('CREATE TEMP TABLE safepath_connection_probe (id integer PRIMARY KEY, point geometry(Point,4326)) ON COMMIT DROP'))
            connection.execute(text('INSERT INTO safepath_connection_probe VALUES (1, ST_SetSRID(ST_Point(77.6386519,12.9782941),4326))'))
            assert connection.execute(text('SELECT count(*) FROM safepath_connection_probe WHERE ST_DWithin(point::geography,ST_SetSRID(ST_Point(77.6386519,12.9782941),4326)::geography,1)')).scalar_one() == 1
            print('PostgreSQL read/write + PostGIS geography query: PASS')
        finally:
            transaction.rollback()
        assert connection.execute(text("SELECT to_regclass('pg_temp.safepath_connection_probe') IS NULL")).scalar_one()
        print('Probe cleanup (rollback): PASS')
        version = connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
        counts = dict(connection.execute(text('SELECT evidence_kind,count(*) FROM osm_evidence GROUP BY evidence_kind')).all())
        invalid = connection.execute(text('SELECT count(*) FROM osm_evidence WHERE NOT ST_IsValid(geometry) OR ST_SRID(geometry)<>4326')).scalar_one()
        assert version == '0001_osm_evidence' and invalid == 0
        print('Applied migration:', version)
        print('Persistent cached OSM evidence:',json.dumps(counts))
        print('Geometry validity and SRID: PASS')

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(f'Database verification FAILED ({type(exc).__name__}); credentials were not logged.',file=sys.stderr)
        sys.exit(1)
