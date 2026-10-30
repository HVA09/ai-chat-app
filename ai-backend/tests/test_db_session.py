"""Tests for returning SQLAlchemy pool connections at external-I/O boundaries."""
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from app.services.db_session import commit_and_release_db_connection


def test_commit_and_release_returns_connection_without_expiring_loaded_values(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pool-release.sqlite3'}",
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
    )
    base = declarative_base()

    class PoolProbe(base):
        __tablename__ = "pool_release_probe"
        id = Column(Integer, primary_key=True)
        value = Column(String, nullable=False)

    base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=True)

    try:
        with session_factory() as db:
            db.add(PoolProbe(value="loaded before external I/O"))
            db.commit()

            probe = db.query(PoolProbe).one()
            assert engine.pool.checkedout() == 1

            commit_and_release_db_connection(db)

            assert engine.pool.checkedout() == 0
            assert probe.value == "loaded before external I/O"
            assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()


def test_release_is_safe_when_no_transaction_is_open(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pool-release-idle.sqlite3'}",
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
    )
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as db:
            assert engine.pool.checkedout() == 0
            commit_and_release_db_connection(db)
            assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()
