import pytest
from app.models import FileAttachment, User, UploadLease
from app.services.upload_leases import (
    claim_upload_lease,
    create_upload_lease,
    finalize_upload_lease,
    heartbeat_upload_lease,
    mark_upload_lease_cleanup_pending,
    queue_upload_lease,
)


def _create_user(client, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code in (200, 201), response.text


def test_upload_lease_claim_heartbeat_and_fencing(client, db_session):
    email = "upload-lease-cas@example.com"
    _create_user(client, email)
    user = db_session.query(User).filter(User.email == email).one()

    lease, ingress_token = create_upload_lease(
        db_session,
        user_id=user.id,
        object_key=f"users/{user.id}/lease-test.bin",
        staging_key=f"staging/{user.id}/lease-test",
    )
    lease_id = lease.id
    assert lease.status == "receiving"
    assert lease.generation == 1
    assert queue_upload_lease(
        db_session,
        lease_id=lease_id,
        generation=1,
        owner_token=ingress_token,
    )
    assert not queue_upload_lease(
        db_session,
        lease_id=lease_id,
        generation=1,
        owner_token=ingress_token,
    )

    claim = claim_upload_lease(db_session, lease_id=lease_id, lease_seconds=90)
    assert claim is not None
    generation, worker_token = claim
    assert generation == 2
    assert claim_upload_lease(db_session, lease_id=lease_id, lease_seconds=90) is None

    assert not heartbeat_upload_lease(
        db_session,
        lease_id=lease_id,
        generation=1,
        owner_token=ingress_token,
        lease_seconds=90,
    )
    assert heartbeat_upload_lease(
        db_session,
        lease_id=lease_id,
        generation=generation,
        owner_token=worker_token,
        lease_seconds=90,
    )
    assert mark_upload_lease_cleanup_pending(
        db_session,
        lease_id=lease_id,
        generation=generation,
        owner_token=worker_token,
    )
    assert not heartbeat_upload_lease(
        db_session,
        lease_id=lease_id,
        generation=generation,
        owner_token=worker_token,
        lease_seconds=90,
    )
    db_session.flush()
    persisted = db_session.get(UploadLease, lease_id)
    db_session.refresh(persisted)
    assert persisted.status == "cleanup_pending"
    assert persisted.owner_token_hash is None


def test_upload_lease_finalize_is_compare_and_swap(client, db_session):
    email = "upload-lease-finalize@example.com"
    _create_user(client, email)
    user = db_session.query(User).filter(User.email == email).one()
    lease, ingress_token = create_upload_lease(
        db_session,
        user_id=user.id,
        object_key=f"users/{user.id}/finalize-test.bin",
    )
    assert queue_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=1,
        owner_token=ingress_token,
    )
    generation, worker_token = claim_upload_lease(
        db_session, lease_id=lease.id, lease_seconds=90
    )

    assert not finalize_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=generation - 1,
        owner_token=worker_token,
        attachment_id=123,
    )
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="lease-test.csv",
        stored_filename="lease-test-finalize.csv",
        object_key=f"users/{user.id}/finalize-test.bin",
        content_type="text/csv",
        size_bytes=12,
    )
    db_session.add(attachment)
    db_session.flush()

    assert not finalize_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=generation,
        owner_token="not-the-owner",
        attachment_id=attachment.id,
    )
    assert finalize_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=generation,
        owner_token=worker_token,
        attachment_id=attachment.id,
    )
    assert not finalize_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=generation,
        owner_token=worker_token,
        attachment_id=attachment.id,
    )
    db_session.flush()
    persisted = db_session.get(UploadLease, lease.id)
    db_session.refresh(persisted)
    assert persisted.status == "committed"
    assert persisted.attachment_id == attachment.id


def test_deleted_account_lease_cannot_queue_claim_heartbeat_or_finalize(client, db_session):
    email = "upload-lease-deleted-owner@example.com"
    _create_user(client, email)
    user = db_session.query(User).filter(User.email == email).one()
    user_id = user.id

    ingress_lease, ingress_token = create_upload_lease(
        db_session,
        user_id=user_id,
        object_key=f"users/{user_id}/deleted-ingress.bin",
    )
    ingress_lease.user_id = None
    db_session.flush()

    assert not queue_upload_lease(
        db_session,
        lease_id=ingress_lease.id,
        generation=1,
        owner_token=ingress_token,
    )
    assert claim_upload_lease(
        db_session, lease_id=ingress_lease.id, lease_seconds=90
    ) is None

    worker_lease, worker_ingress_token = create_upload_lease(
        db_session,
        user_id=user_id,
        object_key=f"users/{user_id}/deleted-worker.bin",
    )
    assert queue_upload_lease(
        db_session,
        lease_id=worker_lease.id,
        generation=1,
        owner_token=worker_ingress_token,
    )
    generation, worker_token = claim_upload_lease(
        db_session, lease_id=worker_lease.id, lease_seconds=90
    )

    worker_lease.user_id = None
    db_session.flush()

    assert not heartbeat_upload_lease(
        db_session,
        lease_id=worker_lease.id,
        generation=generation,
        owner_token=worker_token,
        lease_seconds=90,
    )
    assert not finalize_upload_lease(
        db_session,
        lease_id=worker_lease.id,
        generation=generation,
        owner_token=worker_token,
        attachment_id=123,
    )
    # Recovery intent remains available after account deletion, but no object
    # deletion is performed by this state transition.
    assert mark_upload_lease_cleanup_pending(
        db_session,
        lease_id=worker_lease.id,
        generation=generation,
        owner_token=worker_token,
    )


@pytest.mark.parametrize("duration", [0, -1])
def test_claim_rejects_nonpositive_lease_duration(db_session, duration):
    with pytest.raises(ValueError, match="lease_seconds must be positive"):
        claim_upload_lease(db_session, lease_id="invalid-duration", lease_seconds=duration)


@pytest.mark.parametrize("duration", [0, -1])
def test_heartbeat_rejects_nonpositive_lease_duration(db_session, duration):
    with pytest.raises(ValueError, match="lease_seconds must be positive"):
        heartbeat_upload_lease(
            db_session,
            lease_id="invalid-duration",
            generation=1,
            owner_token="token",
            lease_seconds=duration,
        )
