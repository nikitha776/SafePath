"""Public pilot configuration shared with the frontend; no credentials."""
import json
from pathlib import Path
CONFIG = json.loads((Path(__file__).resolve().parents[2] / 'frontend/src/config/cities.json').read_text())
CITY = CONFIG['cities'][CONFIG['activeCity']]
WEST, SOUTH, EAST, NORTH = CITY['bounds']
EVIDENCE_WEST, EVIDENCE_SOUTH, EVIDENCE_EAST, EVIDENCE_NORTH = CITY['evidenceBounds']
