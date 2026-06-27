# DocuTrack

A document issuance and verification system. A professor uploads an assignment
template, issues per-student encrypted packages (AES-256-GCM with an RSA-PSS
signed, tamper-evident header), and students download, decrypt, and submit
answers. Built with FastAPI + SQLite and a static HTML/JS frontend.

> Academic/thesis project. See the security notes below before deploying.

## Requirements

- Python 3.11+
- Dependencies in `requirements.txt`

## Setup

```bash
python -m venv .venv
. .venv/Scripts/activate      # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set values (see **Configuration**). The app
runs without them in local development, but the defaults are ephemeral and
insecure.

## Run

```bash
uvicorn server.app:app --reload --port 8000
```

Then open http://localhost:8000. Seeded demo accounts (password `Passw0rd!`):

- `prof.carig@docutrack.edu` — professor
- `k.lewins@docutrack.edu`, `t.capulong@docutrack.edu`, `j.fabian@docutrack.edu` — students

## Configuration

| Variable | Required in prod | Default (dev) | Purpose |
|----------|------------------|---------------|---------|
| `SECRET` | yes | random per start | JWT signing secret |
| `MASTER_KEY` | yes | insecure fallback | Wraps stored AES content keys |
| `ALLOWED_ORIGINS` | recommended | localhost | CORS allow-list (comma-separated) |
| `DATABASE_PATH` | no | `server/docutrack.db` | SQLite location |
| `MAX_UPLOAD_BYTES` | no | 25 MiB | Upload size cap |
| `MAX_ZIP_UNCOMPRESSED_BYTES` | no | 50 MiB | Zip-bomb guard |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` | no | 5 / 300 | Login throttle |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against an isolated temporary database and ephemeral keys (configured
in `server/tests/conftest.py`), so they never touch your real data and need no
setup. `server/tests/test_security.py` covers the security guarantees
(authz/role handling, header auth, login throttling, key wrapping, filename
sanitization, upload limits, and locked-down demo endpoints).

## Security notes

- Self-registration always creates a **student**; professor accounts are
  provisioned by seeding, not the public API.
- Authentication uses `Authorization: Bearer <token>`. Browser-driven downloads
  fall back to a `?token=` query parameter.
- AES content keys are wrapped with `MASTER_KEY` before storage. Set a real
  `MASTER_KEY` (and `SECRET`) in production.
- Private signing material (`server/prof_keys.json`, `server/keys/`) and the
  SQLite database are git-ignored and must never be committed.
