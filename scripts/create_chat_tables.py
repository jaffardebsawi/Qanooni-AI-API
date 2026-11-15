"""Create dbo.Chats and dbo.ChatMessages in the Qannoni Azure SQL database. Safe to re-run (skips existing tables)."""
import os
from pathlib import Path

import pyodbc

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

DDL = [
    ("dbo.Chats", """
CREATE TABLE dbo.Chats (
    Id           uniqueidentifier NOT NULL CONSTRAINT PK_Chats PRIMARY KEY,
    UserId       uniqueidentifier NOT NULL CONSTRAINT FK_Chats_AppUsers REFERENCES dbo.AppUsers(Id),
    Title        nvarchar(200)    NULL,
    CreatedDate  datetime2        NOT NULL CONSTRAINT DF_Chats_Created DEFAULT SYSUTCDATETIME(),
    IsDeleted    bit              NOT NULL CONSTRAINT DF_Chats_IsDeleted DEFAULT 0
);
CREATE INDEX IX_Chats_User ON dbo.Chats (UserId, CreatedDate DESC);"""),
    ("dbo.ChatMessages", """
CREATE TABLE dbo.ChatMessages (
    Id             uniqueidentifier NOT NULL CONSTRAINT PK_ChatMessages PRIMARY KEY,
    ChatId         uniqueidentifier NOT NULL CONSTRAINT FK_ChatMessages_Chats REFERENCES dbo.Chats(Id),
    Role           nvarchar(20)     NOT NULL CONSTRAINT CK_ChatMessages_Role CHECK (Role IN ('user', 'assistant')),
    Content        nvarchar(max)    NOT NULL,
    AttachmentIds  nvarchar(max)    NULL,
    Extra          nvarchar(max)    NULL,
    CreatedDate    datetime2        NOT NULL CONSTRAINT DF_ChatMessages_Created DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_ChatMessages_Chat ON dbo.ChatMessages (ChatId, CreatedDate);"""),
]

d = sorted(x for x in pyodbc.drivers() if "SQL Server" in x)[-1]
conn = pyodbc.connect(
    f"DRIVER={{{d}}};SERVER={os.environ['SQL_SERVER']},{os.environ['SQL_PORT']};DATABASE={os.environ['SQL_DATABASE']};"
    f"UID={os.environ['SQL_USER']};PWD={os.environ['SQL_PASSWORD']};Encrypt=yes;Connection Timeout=30",
    autocommit=False,
)
cur = conn.cursor()
try:
    for name, ddl in DDL:
        if cur.execute("SELECT OBJECT_ID(?, 'U')", name).fetchone()[0]:
            print(f"{name}: already exists, skipped")
            continue
        cur.execute(ddl)
        print(f"{name}: created")
    conn.commit()
except Exception:
    conn.rollback()
    raise

for name, _ in DDL:
    print(f"\n{name}")
    for c in cur.execute("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
                         "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME=? ORDER BY ORDINAL_POSITION", name.split(".")[1]).fetchall():
        print(f"   {c[0]:15} {c[1]}({c[2]}) null={c[3]}")
