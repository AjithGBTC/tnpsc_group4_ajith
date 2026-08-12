import sys
from pathlib import Path

from alembic import context

# Render invokes the pre-deploy command from the repository root. Ensure the
# backend package is importable whether Alembic is started there or in backend/.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.base import Base
from app.core.config import get_settings
from app.models import course, entities  # noqa: F401

target_metadata = Base.metadata
context.config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("+asyncpg", "+psycopg"))

def run_migrations_offline() -> None:
    context.configure(url=context.config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool
    connectable = engine_from_config(context.config.get_section(context.config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
