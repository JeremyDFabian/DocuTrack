# server/tests/test_security.py
"""Regression tests for the security fixes.

Each test maps to a hardening change so the guarantees stay enforced as the
codebase evolves.
"""
import io
import os
import uuid

import pytest

from server.tests.helpers import login, auth, PDF, PROF_EMAIL, STUDENT_EMAIL


def _unique_email():
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


# --- #1: self-registration cannot escalate to professor ---
def test_self_registration_is_always_student(client):
    email = _unique_email()
    r = client.post("/auth/register", json={
        "email": email, "name": "Mallory", "role": "professor", "password": "pw12345678",
    })
    assert r.status_code == 200, r.text
    me = login(client, email, "pw12345678")
    assert me["role"] == "student"
    # ...and the resulting token cannot reach professor-only endpoints.
    r = client.get("/users/students", headers=auth(me["token"]))
    assert r.status_code == 403


# --- #7: auth required, and the Authorization header works ---
def test_missing_token_is_rejected(client):
    assert client.get("/prof/issuances").status_code == 401


def test_bearer_header_auth_works(client):
    prof = login(client, PROF_EMAIL)
    r = client.get("/users/students", headers=auth(prof["token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 1


# --- #9: login throttling ---
def test_login_throttle_blocks_brute_force(client):
    email = _unique_email()
    client.post("/auth/register", json={
        "email": email, "name": "Brute", "role": "student", "password": "correct-horse",
    })
    codes = [client.post("/auth/login", json={"email": email, "password": "wrong"}).status_code
             for _ in range(7)]
    assert codes.count(429) >= 1
    assert codes[:5] == [401, 401, 401, 401, 401]


# --- #3 + #6 + #11: round trip, filename sanitization, no plaintext on disk ---
def _issue_to_student(client, prof_token):
    prof = auth(prof_token)
    r = client.post("/prof/assignments/upload", headers=prof,
                    data={"title": "HW"}, files={"file": ("t.pdf", PDF, "application/pdf")})
    assert r.status_code == 200, r.text
    aid = r.json()["assignment_id"]

    students = client.get("/users/students", headers=prof).json()
    sid = students[0]["id"]
    r = client.post("/prof/assignments/issue", headers=prof,
                    json={"assignment_id": aid, "student_ids": [sid]})
    assert r.status_code == 200, r.text
    return r.json()["issued"][0]["issuance_id"], sid, students[0]["email"]


def test_wrapped_key_round_trip_and_no_plaintext_on_disk(client):
    prof = login(client, PROF_EMAIL)
    iss, _, stu_email = _issue_to_student(client, prof["token"])
    stu = login(client, stu_email)

    r = client.get(f"/student/decrypt/{iss}", headers=auth(stu["token"]))
    assert r.status_code == 200
    assert r.content == PDF  # wrapped AES key decrypts correctly

    # #11: decrypted plaintext must not be persisted to disk.
    store = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "decrypted")
    leaked = os.path.join(store, f"issuance_{iss}_decrypted.pdf")
    assert not os.path.exists(leaked)


def test_submission_filename_cannot_traverse(client):
    prof = login(client, PROF_EMAIL)
    iss, _, stu_email = _issue_to_student(client, prof["token"])
    stu = login(client, stu_email)

    r = client.post(f"/student/submit/{iss}", headers=auth(stu["token"]),
                    files={"file": ("../../evil.pdf", b"answer", "application/pdf")})
    assert r.status_code == 200, r.text

    server_dir = os.path.dirname(os.path.dirname(__file__))
    assert not os.path.exists(os.path.join(server_dir, "evil.pdf"))
    assert not os.path.exists(os.path.join(os.path.dirname(server_dir), "evil.pdf"))


# --- #12: demo signing endpoints require professor auth ---
def test_demo_sign_requires_professor(client):
    # no token
    r = client.post("/api/demo/sign-header", data={"header_json": "{}"})
    assert r.status_code == 401

    # student token
    email = _unique_email()
    client.post("/auth/register", json={
        "email": email, "name": "S", "role": "student", "password": "pw12345678"})
    stu = login(client, email, "pw12345678")
    r = client.post("/api/demo/sign-header", headers=auth(stu["token"]),
                    data={"header_json": "{}"})
    assert r.status_code == 403


# --- #6: key wrapping unit tests (new + legacy formats) ---
def test_key_wrapping_roundtrip_and_legacy():
    from server.crypto import wrap_key, unwrap_key, b64e
    key = os.urandom(32)
    assert unwrap_key(wrap_key(key)) == key          # new wrapped format
    assert unwrap_key(b64e(key)) == key              # legacy plain-b64 fallback


# --- #10: upload size cap ---
def test_read_upload_enforces_size_cap():
    from server.app import read_upload
    from fastapi import HTTPException

    class _F:
        def __init__(self, data):
            self.file = io.BytesIO(data)

    assert read_upload(_F(b"small"), max_bytes=10) == b"small"
    with pytest.raises(HTTPException) as exc:
        read_upload(_F(b"x" * 50), max_bytes=10)
    assert exc.value.status_code == 413


# --- #2: app refuses the old hardcoded secret default ---
def test_no_hardcoded_secret_default():
    from server import app as appmod
    assert appmod.SECRET != "dev-secret-for-jwt"


# --- #8: CORS is not a wildcard ---
def test_cors_not_wildcard():
    from server import app as appmod
    assert "*" not in appmod.ALLOWED_ORIGINS
