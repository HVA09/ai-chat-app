"""
Alembic environment script — يقرأ DATABASE_URL من إعدادات التطبيق نفسها (.env)
بدل ما يتكرر الإعداد في alembic.ini، ويستورد كل النماذج عشان --autogenerate يشتغل صح.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 — يسجّل كل الجداول في Base.metadata قبل المقارنة
from app.config import settings
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# رابط قاعدة البيانات الحقيقي يجي من إعدادات التطبيق (.env)، مو من alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """توليد SQL بدون الاتصال الفعلي بقاعدة البيانات (alembic upgrade --sql)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """الوضع المعتاد: اتصال حقيقي بقاعدة البيانات وتطبيق الـ migrations"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
