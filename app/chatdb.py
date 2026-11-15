"""Chat history in Azure SQL (dbo.Chats, dbo.ChatMessages, dbo.Attachments). The .NET app creates chats; we add messages."""
import json
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pyodbc

from .settings import settings

_driver = sorted(d for d in pyodbc.drivers() if "SQL Server" in d)[-1]
_conn_str = (f"DRIVER={{{_driver}}};SERVER={settings.sql_server},{settings.sql_port};DATABASE={settings.sql_database};"
             f"UID={settings.sql_user};PWD={settings.sql_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30")


def _conn() -> pyodbc.Connection:
    return pyodbc.connect(_conn_str)


def create_chat(user_id: str, title: str | None) -> dict | None:
    """Insert a chat for `user_id`; None when that user does not exist."""
    chat_id = str(uuid.uuid4())
    with closing(_conn()) as c:
        cur = c.cursor()
        if not cur.execute("SELECT 1 FROM dbo.AppUsers WHERE Id = ?", user_id).fetchone():
            return None
        cur.execute("INSERT INTO dbo.Chats (Id, UserId, Title) VALUES (?, ?, ?)", chat_id, user_id, title)
        row = cur.execute("SELECT CreatedDate FROM dbo.Chats WHERE Id = ?", chat_id).fetchone()
        c.commit()
    return {"chat_id": chat_id, "user_id": user_id, "title": title, "created_date": str(row.CreatedDate)}


def get_chat(chat_id: str, user_id: str) -> dict | None:
    """The chat if it exists, is not deleted and belongs to `user_id`."""
    with closing(_conn()) as c:
        row = c.cursor().execute("SELECT Id, UserId, Title FROM dbo.Chats WHERE Id = ? AND UserId = ? AND IsDeleted = 0",
                                 chat_id, user_id).fetchone()
    return {"chat_id": str(row.Id).lower(), "user_id": str(row.UserId).lower(), "title": row.Title} if row else None


def last_messages(chat_id: str, limit: int) -> list[dict]:
    """The newest `limit` messages, oldest first."""
    with closing(_conn()) as c:
        rows = c.cursor().execute("SELECT TOP (?) Role, Content, AttachmentIds, Extra FROM dbo.ChatMessages "
                                  "WHERE ChatId = ? ORDER BY CreatedDate DESC", limit, chat_id).fetchall()
    return [{"role": r.Role, "content": r.Content, "attachment_ids": json.loads(r.AttachmentIds or "[]"),
             "extra": json.loads(r.Extra or "null")} for r in reversed(rows)]


def add_exchange(chat_id: str, user_text: str, attachment_ids: list[str], answer: str, extra: dict | None) -> None:
    """Save the user message and the assistant reply together, or neither."""
    t = datetime.now(timezone.utc).replace(tzinfo=None)
    with closing(_conn()) as c:
        cur = c.cursor()
        cur.execute("INSERT INTO dbo.ChatMessages (Id, ChatId, Role, Content, AttachmentIds, CreatedDate) VALUES (?, ?, 'user', ?, ?, ?)",
                    str(uuid.uuid4()), chat_id, user_text, json.dumps(attachment_ids) if attachment_ids else None, t)
        cur.execute("INSERT INTO dbo.ChatMessages (Id, ChatId, Role, Content, Extra, CreatedDate) VALUES (?, ?, 'assistant', ?, ?, ?)",
                    str(uuid.uuid4()), chat_id, answer, json.dumps(extra, ensure_ascii=False) if extra else None,
                    t + timedelta(milliseconds=20))  # the SQL driver rounds to ~3 ms; keep the pair ordered
        c.commit()


def attachments(ids: list[str]) -> list[dict]:
    """File name and stored path of the active attachments among `ids`."""
    if not ids:
        return []
    with closing(_conn()) as c:
        rows = c.cursor().execute(f"SELECT Id, FileName, Path FROM dbo.Attachments WHERE IsActive = 1 AND IsDeleted = 0 "
                                  f"AND Id IN ({','.join('?' * len(ids))})", *ids).fetchall()
    return [{"id": str(r.Id).lower(), "name": r.FileName, "path": r.Path} for r in rows]
