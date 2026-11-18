"""Validate migrations on an explicitly selected temporary Neon branch without logging URLs."""
import os
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2 or sys.argv[1] in ('production', 'br-rough-brook-a1d4gbys'):
    raise SystemExit('Supply a temporary branch name or ID, not production.')
result = subprocess.run(['npx', '--offline', '--yes', 'neon@latest', 'connection-string', sys.argv[1]], capture_output=True, text=True, timeout=60, cwd=ROOT)
if result.returncode:
    raise SystemExit('Could not retrieve temporary branch connection; credentials were not logged.')
url = result.stdout.strip()
if not url.startswith(('postgresql://', 'postgres://')):
    raise SystemExit('Temporary branch connection returned an unexpected format.')
env = {**os.environ, 'DATABASE_URL': url, 'DATABASE_URL_UNPOOLED': url}
result = subprocess.run([str(ROOT/'backend/.venv/bin/alembic'), '-c', 'backend/alembic.ini', 'upgrade', 'head'], env=env, cwd=ROOT, capture_output=True, text=True, timeout=90)
if result.returncode:
    # ORM errors can contain host/user data; do not print the raw traceback.
    raise SystemExit('Temporary branch migration FAILED; no production migration attempted.')
print('Temporary branch migration: PASS (upgrade head).')
result = subprocess.run([str(ROOT/'backend/.venv/bin/python'), '-c', "from app.database import get_engine; from sqlalchemy import text; c=get_engine().connect(); print('PostGIS:',c.execute(text('SELECT PostGIS_Version()')).scalar_one()); assert c.execute(text(\"SELECT to_regclass('public.osm_evidence') IS NOT NULL\")).scalar_one(); print('Evidence table and migration: PASS'); c.close()"], env={**env,'PYTHONPATH':str(ROOT/'backend')}, cwd=ROOT, capture_output=True, text=True, timeout=45)
if result.returncode:
    raise SystemExit('Temporary branch schema verification FAILED; no production migration attempted.')
print(result.stdout.strip())
