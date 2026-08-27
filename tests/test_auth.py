"""Tests for the authentication module (app/auth.py)."""

from app import auth


def test_hash_round_trip():
    encoded = auth.hash_password("s3cret-pw")
    assert encoded.startswith("pbkdf2_sha256$")
    assert "s3cret-pw" not in encoded            # not stored in plaintext
    assert auth.verify_password("s3cret-pw", encoded)


def test_verify_rejects_wrong_password():
    encoded = auth.hash_password("correct-horse")
    assert not auth.verify_password("wrong-horse", encoded)


def test_verify_rejects_malformed_encoding():
    assert not auth.verify_password("anything", "not-an-encoded-hash")


def test_add_user_and_authenticate(tmp_path):
    path = str(tmp_path / "users.csv")
    ok, _ = auth.add_user("alice", "alice@example.com", "pw123456",
                          role="user", path=path)
    assert ok

    record = auth.authenticate("alice", "pw123456", path=path)
    assert record is not None
    assert record["username"] == "alice"
    assert record["role"] == "user"
    assert "password" not in record              # never returned to callers

    assert auth.authenticate("alice", "wrong", path=path) is None


def test_add_user_rejects_duplicate_username(tmp_path):
    path = str(tmp_path / "users.csv")
    auth.add_user("bob", "bob@example.com", "password1", path=path)

    ok, msg = auth.add_user("BOB", "other@example.com", "password1", path=path)
    assert not ok                                # case-insensitive clash
    assert "taken" in msg.lower()


def test_add_user_rejects_duplicate_email(tmp_path):
    path = str(tmp_path / "users.csv")
    auth.add_user("carol", "carol@example.com", "password1", path=path)

    ok, msg = auth.add_user("dave", "CAROL@example.com", "password1", path=path)
    assert not ok
    assert "email" in msg.lower()


def test_add_user_requires_all_fields(tmp_path):
    path = str(tmp_path / "users.csv")
    ok, _ = auth.add_user("", "x@example.com", "pw", path=path)
    assert not ok


def test_load_users_seeds_admin(tmp_path):
    path = str(tmp_path / "users.csv")
    df = auth.load_users(path)
    assert (df["role"].str.lower() == "admin").any()
    admin = auth.authenticate(auth.SEED_ADMIN_USERNAME,
                              auth.SEED_ADMIN_PASSWORD, path=path)
    assert admin is not None and admin["role"] == "admin"
