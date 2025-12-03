from __future__ import annotations

import os
from logging.config import fileConfig
from typing import Final

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy.pool import NullPool

from src.infrastructure.config.settings import settings
from src.infrastructure.db.database import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
ENV_VAR: Final[str] = "DATABASE_URL"


def get_url() -> str:
    url = settings.DATABASE_URL or os.getenv(ENV_VAR, "")
    if not url:
        raise RuntimeError(f"{ENV_VAR} is not set")
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    config.set_main_option("sqlalchemy.url", url)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {}, prefix="sqlalchemy.", poolclass=NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
