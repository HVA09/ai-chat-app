"""SQLAlchemy session helpers for short-lived pooled connections."""
from sqlalchemy.orm import Session


def commit_and_release_db_connection(db: Session) -> None:
    """Finish the current unit of work and return its connection to the pool.

    Call only at an intentional transaction boundary, immediately before waiting
    on external I/O (AI providers, embeddings, object storage, or a streamed
    response). This preserves loaded ORM attributes across the commit so a later
    access does not silently check out another connection.
    """
    commit = getattr(db, "commit", None)
    in_transaction = getattr(db, "in_transaction", None)
    if not callable(commit) or not callable(in_transaction):
        return

    db.expire_on_commit = False
    if not in_transaction():
        return

    if getattr(db, "is_active", True):
        commit()
    else:
        # A previous SQL error left the transaction in a failed state. Clear it
        # before subsequent work rather than keeping a poisoned checkout.
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            rollback()
