#!/usr/bin/env python3
import os, sqlite3, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "docutrack.db")
UPLOAD_DIR = os.path.join(ROOT, "uploads", "issuances")
os.makedirs(UPLOAD_DIR, exist_ok=True)

schema_sql = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS issuances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  assignment_id INTEGER NOT NULL,
  student_id INTEGER NOT NULL,
  header_json TEXT,
  signature_b64 TEXT,
  iv_b64 TEXT,
  ciphertext_path TEXT,
  tag_b64 TEXT,
  aes_key_b64 TEXT,
  status TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issuance_id INTEGER,
  student_id INTEGER,
  file_path TEXT,
  answer_hash TEXT NOT NULL,
  status TEXT,
  ground_truth TEXT,
  submitted_at DATETIME,
  created_at TEXT,
  FOREIGN KEY (issuance_id) REFERENCES issuances(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS verification_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  test_id TEXT,
  submission_id TEXT NOT NULL,
  issuance_id INTEGER,
  student_id INTEGER,
  ground_truth TEXT,
  header_hash TEXT,
  answer_hash TEXT,
  signature_valid INTEGER,
  gcm_auth_valid INTEGER,
  duplicate_flag INTEGER,
  duplicate_of_submission_id INTEGER,
  t_issued DATETIME,
  t_verification_start DATETIME,
  t_verification_end DATETIME,
  latency_ms INTEGER,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_submissions_answer_hash ON submissions(answer_hash);
CREATE INDEX IF NOT EXISTS idx_submissions_issuance_id ON submissions(issuance_id);
CREATE INDEX IF NOT EXISTS idx_issuances_student_id ON issuances(student_id);
"""

compat_columns = {
    "issuances": {
        "status": "TEXT",
        "created_at": "TEXT",
    },
    "submissions": {
        "file_path": "TEXT",
        "status": "TEXT",
        "ground_truth": "TEXT",
        "submitted_at": "DATETIME",
        "created_at": "TEXT",
    },
}

def ensure_compat_columns(cur):
    for table, columns in compat_columns.items():
        existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
        for column_name, column_type in columns.items():
            if column_name not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")

def create_db():
    if os.path.exists(DB):
        print("DB already exists at", DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executescript(schema_sql)
    ensure_compat_columns(cur)
    conn.commit()
    conn.close()
    print("Created/ensured DB and schema at:", DB)
    print("Uploads dir:", UPLOAD_DIR)

if __name__ == "__main__":
    create_db()
