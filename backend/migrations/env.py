from alembic import context
from app.database import get_engine

def run():
    with get_engine(migration=True).connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
run()
