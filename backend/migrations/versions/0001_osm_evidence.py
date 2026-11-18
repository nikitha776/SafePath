"""Initial OSM evidence cache; no inferred safety scores."""
from alembic import op
revision = '0001_osm_evidence'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('''CREATE TABLE osm_evidence (
        osm_type text NOT NULL CHECK (osm_type IN ('node','way','relation')),
        osm_id bigint NOT NULL,
        evidence_kind text NOT NULL CHECK (evidence_kind IN ('road','street_lamp')),
        geometry geometry(Geometry,4326) NOT NULL,
        tags jsonb NOT NULL DEFAULT '{}'::jsonb,
        source_url text NOT NULL,
        fetched_at timestamptz NOT NULL DEFAULT now(),
        source_updated_at timestamptz,
        PRIMARY KEY (osm_type,osm_id,evidence_kind)
    )''')
    op.execute('CREATE INDEX osm_evidence_geometry_idx ON osm_evidence USING gist(geometry)')

def downgrade():
    op.drop_table('osm_evidence')
