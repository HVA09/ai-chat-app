from pathlib import Path

from app.services import storage


def test_local_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "S3_BUCKET", "")
    path = tmp_path / "example.txt"
    path.write_text("hello", encoding="utf-8")

    storage.put_file(path, "users/1/example.txt", "text/plain")
    body = storage.open_file("users/1/example.txt", path)
    assert body.read() == b"hello"
    body.close()

    storage.delete_file("users/1/example.txt", path)
    assert not path.exists()
