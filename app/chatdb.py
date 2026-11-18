"""Read-only access to the chat history the .NET app keeps in Azure SQL (dbo.Chats, dbo.ChatMessages)."""
from contextlib import closing

import pyodbc

from .settings import settings

# dbo.ChatMessages.Role. Only 1 (user) exists in the data so far; 2 (assistant) is assumed. Other values are skipped.
ROLES = {1: "user", 2: "assistant"}


def _pick_driver() -> str:
    """Best installed SQL Server ODBC driver. "SQL Server Native Client" is skipped on purpose: it is deprecated and
    often broken, and sorting driver names alphabetically would pick it over the working ones."""
    installed = pyodbc.drivers()
    for name in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
        if name in installed:
            return name
    raise RuntimeError(f"No usable SQL Server ODBC driver found. Installed drivers: {installed}")


_conn_str = (f"DRIVER={{{_pick_driver()}}};SERVER={settings.sql_server},{settings.sql_port};DATABASE={settings.sql_database};"
             f"UID={settings.sql_user};PWD={settings.sql_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30")


def recent_messages(chat_id: str, user_id: str, limit: int) -> list[dict] | None:
    """The newest `limit` messages of the user's chat, oldest first; None when the chat does not exist,
    is deleted or belongs to someone else. The connection is read-only, so this can never write."""
    with closing(pyodbc.connect(_conn_str, readonly=True)) as c:
        cur = c.cursor()
        if not cur.execute("SELECT 1 FROM dbo.Chats WHERE Id = ? AND UserId = ? AND IsDeleted = 0", chat_id, user_id).fetchone():
            return None
        rows = cur.execute("SELECT TOP (?) Role, Content FROM dbo.ChatMessages WHERE ChatId = ? AND IsDeleted = 0 "
                           "ORDER BY CreatedDate DESC", limit, chat_id).fetchall()
    return [{"role": ROLES[r.Role], "content": r.Content} for r in reversed(rows) if r.Role in ROLES]


def recent_attachment_ids(chat_id: str, limit: int) -> list[str]:
    """Ids (uppercase GUID strings) of the live attachments linked to the newest `limit` non-deleted messages of the
    chat, newest message first, no duplicates. The caller has already checked that the chat is the user's."""
    with closing(pyodbc.connect(_conn_str, readonly=True)) as c:
        rows = c.cursor().execute(
            "SELECT a.Id FROM (SELECT TOP (?) Id, CreatedDate FROM dbo.ChatMessages WHERE ChatId = ? AND IsDeleted = 0 "
            "ORDER BY CreatedDate DESC) m "
            "JOIN dbo.ChatMessageAttachments ma ON ma.ChatMessageId = m.Id "
            "JOIN dbo.Attachments a ON a.Id = ma.AttachmentId AND a.IsDeleted = 0 AND a.IsActive = 1 "
            "ORDER BY m.CreatedDate DESC", limit, chat_id).fetchall()
    return list(dict.fromkeys(str(r.Id).upper() for r in rows))
