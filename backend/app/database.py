"""PostgreSQL access for the long-lived Python service (not a browser/edge driver)."""
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from app.config import get_settings

@lru_cache(maxsize=2)
def get_engine(*, migration=False):
    settings = get_settings()
    value = (settings.database_url_unpooled or settings.database_url) if migration else settings.database_url
    if not value:
        raise RuntimeError('Set DATABASE_URL in the root .env or .env.local before using PostgreSQL.')
    url = make_url(value)
    if url.drivername in ('postgres', 'postgresql'):
        url = url.set(drivername='postgresql+psycopg')
    query = dict(url.query)
    if url.host and url.host.endswith('.neon.tech'):
        query.setdefault('sslmode', 'require')
    url = url.set(query=query)
    options = {'connect_args': {'connect_timeout': 10}, 'hide_parameters': True}
    if migration:
        return create_engine(url, poolclass=NullPool, **options)
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2, pool_timeout=10, pool_recycle=300, **options)
