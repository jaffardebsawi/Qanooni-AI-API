"""Small JSON document store on SQLite (stdlib, no server). Holds ingestion jobs, chats and generations."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .settings import settings

KINDS = ("jobs", "chats", "generations", "cases", "documents")
_path = Path(settings.data_dir) / "app.db"
_path.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_path, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    return c


with closing(_conn()) as _c, _c:
    for _k in KINDS:
        _c.execute(f"CREATE TABLE IF NOT EXISTS {_k} (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, "
                   "data TEXT NOT NULL, updated_at TEXT NOT NULL)")
        _c.execute(f"CREATE INDEX IF NOT EXISTS {_k}_tenant ON {_k} (tenant_id, updated_at)")


def put(kind: str, doc_id: str, doc: dict) -> None:
    assert kind in KINDS
    with closing(_conn()) as c, c:
        c.execute(f"INSERT OR REPLACE INTO {kind} (id, tenant_id, data, updated_at) VALUES (?, ?, ?, ?)",
                  (doc_id, doc["tenant_id"], json.dumps(doc, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))


def get(kind: str, doc_id: str) -> dict | None:
    assert kind in KINDS
    with closing(_conn()) as c:
        row = c.execute(f"SELECT data FROM {kind} WHERE id = ?", (doc_id,)).fetchone()
    return json.loads(row[0]) if row else None


def delete(kind: str, doc_id: str) -> None:
    assert kind in KINDS
    with closing(_conn()) as c, c:
        c.execute(f"DELETE FROM {kind} WHERE id = ?", (doc_id,))


def list_docs(kind: str, tenant_id: str, limit: int = 50, where: dict | None = None) -> list[dict]:
    """Newest first. `where` filters on top-level JSON fields by equality (None values are ignored)."""
    assert kind in KINDS
    sql, args = f"SELECT data FROM {kind} WHERE tenant_id = ?", [tenant_id]
    for field, value in (where or {}).items():
        if value is not None:
            assert field.isidentifier()
            sql += f" AND json_extract(data, '$.{field}') = ?"
            args.append(value)
    with closing(_conn()) as c:
        rows = c.execute(sql + " ORDER BY updated_at DESC LIMIT ?", (*args, limit)).fetchall()
    return [json.loads(r[0]) for r in rows]


def fail_interrupted_jobs() -> int:
    """Jobs left queued/processing by a restart can never finish; mark them failed."""
    n = 0
    with closing(_conn()) as c:
        rows = c.execute("SELECT data FROM jobs").fetchall()
    for (data,) in rows:
        job = json.loads(data)
        if job["status"] in ("queued", "processing"):
            job.update(status="failed", error="Interrupted by a server restart; submit the job again")
            put("jobs", job["job_id"], job)
            n += 1
    return n
