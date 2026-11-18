"""Idempotently import the active city's cached OSM XML into PostGIS.
Reads original fetch time from the cached file mtime, not import time.
"""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text
from app.database import get_engine
from app.city import CONFIG, CITY

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://api.openstreetmap.org/api/0.6/map?bbox=' + ','.join(map(str, CITY['evidenceBounds']))

def main():
    file = ROOT / 'work/pilot-data' / (CONFIG['activeCity'] + '_osm_sample.xml')
    if not file.exists() and CONFIG['activeCity'] == 'bengaluru':
        file = ROOT / 'work/pilot-data/osm_small_sample.xml'
    tree = ET.parse(file).getroot()
    fetched_at = datetime.fromtimestamp(file.stat().st_mtime, timezone.utc)
    nodes = {n.attrib['id']: [float(n.attrib['lon']),float(n.attrib['lat'])] for n in tree.findall('node')}
    rows, skipped = [], 0
    for element in tree:
        tags = {t.attrib['k']:t.attrib['v'] for t in element.findall('tag')}
        if element.tag == 'node' and tags.get('highway') == 'street_lamp':
            kind, geometry = 'street_lamp', {'type':'Point','coordinates':nodes[element.attrib['id']]}
        elif element.tag == 'way' and 'highway' in tags:
            refs = [n.attrib['ref'] for n in element.findall('nd')]
            if len(refs)<2 or any(ref not in nodes for ref in refs):
                skipped += 1
                continue
            kind, geometry = 'road', {'type':'LineString','coordinates':[nodes[ref] for ref in refs]}
        else:
            continue
        rows.append({'osm_type':element.tag,'osm_id':int(element.attrib['id']),'kind':kind,'geometry':json.dumps(geometry),'tags':json.dumps(tags),'source':SOURCE_URL,'fetched':fetched_at,'updated':element.attrib.get('timestamp')})
    statement = text('''INSERT INTO osm_evidence(osm_type,osm_id,evidence_kind,geometry,tags,source_url,fetched_at,source_updated_at)
        VALUES(:osm_type,:osm_id,:kind,ST_SetSRID(ST_GeomFromGeoJSON(:geometry),4326),CAST(:tags AS jsonb),:source,:fetched,CAST(:updated AS timestamptz))
        ON CONFLICT(osm_type,osm_id,evidence_kind) DO UPDATE SET geometry=EXCLUDED.geometry,tags=EXCLUDED.tags,
        source_url=EXCLUDED.source_url,fetched_at=EXCLUDED.fetched_at,source_updated_at=EXCLUDED.source_updated_at
        WHERE osm_evidence.fetched_at<=EXCLUDED.fetched_at''')
    with get_engine().begin() as connection:
        if rows:
            connection.execute(statement,rows)
        counts = dict(connection.execute(text('SELECT evidence_kind,count(*) FROM osm_evidence GROUP BY evidence_kind')).all())
    print('OSM import complete:',json.dumps({'input_records':len(rows),'skipped_incomplete_ways':skipped,'database_counts':counts}))
    print('Source: cached OpenStreetMap sample. Current streetlight operation is unverified.')

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(f'OSM import failed ({type(exc).__name__}). Connection details were not logged.',file=sys.stderr)
        sys.exit(1)
