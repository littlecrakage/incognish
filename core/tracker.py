"""
tracker.py — all SQLite read/write operations.
Every function opens its own connection so it's thread-safe.
"""
import sqlite3
import json
from pathlib import Path

# Import here to avoid circular; config is at project root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH


# ── Connection ─────────────────────────────────────────────────────────────────

def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe for multi-thread reads
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profile (
            key   TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS requests (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            broker_id        TEXT NOT NULL,
            broker_name      TEXT NOT NULL,
            submitted_at     TEXT DEFAULT (datetime('now')),
            method           TEXT,
            status           TEXT DEFAULT 'pending',
            notes            TEXT,
            confirmed_at     TEXT,
            next_check_at    TEXT,
            run_id           TEXT
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            taken_at TEXT DEFAULT (datetime('now')),
            label    TEXT,
            data     TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            id           TEXT PRIMARY KEY,
            started_at   TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            total        INTEGER DEFAULT 0,
            succeeded    INTEGER DEFAULT 0,
            failed       INTEGER DEFAULT 0,
            log          TEXT
        );
    """)
    conn.commit()
    conn.close()


# ── Profile ────────────────────────────────────────────────────────────────────

def get_profile() -> dict:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM profile").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def save_profile(data: dict):
    conn = get_db()
    for key, value in data.items():
        conn.execute(
            "INSERT OR REPLACE INTO profile (key, value, updated_at) "
            "VALUES (?, ?, datetime('now'))",
            (key, value),
        )
    conn.commit()
    conn.close()


# ── Requests ───────────────────────────────────────────────────────────────────

def add_request(broker_id, broker_name, method, status, notes="", run_id=None):
    conn = get_db()
    conn.execute(
        """INSERT INTO requests
               (broker_id, broker_name, submitted_at, method, status, notes, run_id)
           VALUES (?, ?, datetime('now'), ?, ?, ?, ?)""",
        (broker_id, broker_name, method, status, notes, run_id),
    )
    conn.commit()
    conn.close()


def update_request(request_id: int, status: str, notes: str = None):
    conn = get_db()
    if notes is not None:
        conn.execute(
            "UPDATE requests SET status=?, notes=? WHERE id=?",
            (status, notes, request_id),
        )
    else:
        conn.execute("UPDATE requests SET status=? WHERE id=?", (status, request_id))
    conn.commit()
    conn.close()


def get_requests(broker_id=None, status=None, since=None, run_id=None) -> list:
    conn = get_db()
    query = "SELECT * FROM requests WHERE 1=1"
    params = []
    if broker_id:
        query += " AND broker_id=?"
        params.append(broker_id)
    if status:
        query += " AND status=?"
        params.append(status)
    if since:
        query += " AND submitted_at>=?"
        params.append(since)
    if run_id:
        query += " AND run_id=?"
        params.append(run_id)
    query += " ORDER BY submitted_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_per_broker() -> list:
    """Return the most recent request for each broker."""
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*
        FROM requests r
        INNER JOIN (
            SELECT broker_id, MAX(submitted_at) AS max_at
            FROM requests
            GROUP BY broker_id
        ) latest ON r.broker_id = latest.broker_id AND r.submitted_at = latest.max_at
        ORDER BY r.broker_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_db()
    total = conn.execute("SELECT COUNT(DISTINCT broker_id) FROM requests").fetchone()[0]
    statuses = conn.execute("""
        SELECT status, COUNT(*) AS cnt
        FROM (
            SELECT broker_id, status
            FROM requests r1
            WHERE submitted_at = (
                SELECT MAX(submitted_at) FROM requests r2
                WHERE r2.broker_id = r1.broker_id
            )
        )
        GROUP BY status
    """).fetchall()
    recent_runs = conn.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return {
        "brokers_contacted": total,
        "statuses": {r["status"]: r["cnt"] for r in statuses},
        "recent_runs": [dict(r) for r in recent_runs],
    }


# ── Runs ───────────────────────────────────────────────────────────────────────

def save_run(run_id, total, succeeded, failed, log_lines: list):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO runs
               (id, started_at, completed_at, total, succeeded, failed, log)
           VALUES (?, datetime('now'), datetime('now'), ?, ?, ?, ?)""",
        (run_id, total, succeeded, failed, "\n".join(log_lines)),
    )
    conn.commit()
    conn.close()


def get_run(run_id) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Snapshots ──────────────────────────────────────────────────────────────────

def take_snapshot(label: str = "") -> int:
    data = get_latest_per_broker()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO snapshots (label, data) VALUES (?, ?)",
        (label, json.dumps(data)),
    )
    snapshot_id = cur.lastrowid
    conn.commit()
    conn.close()
    return snapshot_id


def get_snapshots() -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, taken_at, label FROM snapshots ORDER BY taken_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_snapshot(snapshot_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["data"] = json.loads(result["data"])
    return result
