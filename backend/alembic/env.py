# backend/alembic/env.py

from logging.config import fileConfig
import logging

from alembic import context
from db import engine, Base  # use our FastAPI app's engine and Base

# Alembic Config object (reads alembic.ini etc.)
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Tell Alembic about our SQLAlchemy models
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the app's Engine."""
    connectable = engine

    # Enable batch mode automatically for SQLite (dev), not needed for Postgres (prod)
    render_as_batch = engine.url.get_backend_name().startswith("sqlite")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,               # detect type changes
            compare_server_default=True,     # detect server default changes
            render_as_batch=render_as_batch, # safer ALTERs on SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


# We only use online mode (engine is provided by our app)
run_migrations_online()
