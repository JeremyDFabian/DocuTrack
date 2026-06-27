# server/tests/helpers.py
"""Side-effect-free test helpers (safe to import from anywhere)."""

# Seeded demo credentials (created by the app's startup event).
SEED_PASSWORD = "Passw0rd!"
PROF_EMAIL = "prof.carig@docutrack.edu"
STUDENT_EMAIL = "j.fabian@docutrack.edu"

PDF = b"%PDF-1.4 minimal test document\n%%EOF"


def login(client, email, password=SEED_PASSWORD):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}
