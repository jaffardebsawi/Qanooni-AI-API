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
