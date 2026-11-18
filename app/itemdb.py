"""Read-only access to the case data (grievances) the .NET app keeps in Azure SQL: the item context for Mode A and
a guarded SELECT runner for Mode B. Every connection is read-only (and the validator below only lets SELECTs through)."""
import re
import uuid
from contextlib import closing
from datetime import date, datetime
from functools import lru_cache

import pyodbc

from .chatdb import _conn_str

SUPPORTED_TYPES = ("grievance",)

ALLOWED_TABLES = ("Grievances", "GrievanceActions", "GrievanceNotes", "GrievanceAttachments", "GrievanceStatuses",
                  "DecisionTypes", "WorkflowSteps", "WorkflowStepActions", "Attachments", "ComplaintStatuses",
                  "ComplexityLevels", "ContractTypes", "FormCategories", "IssueStatuses", "Jurisdictions", "LegalForms",
                  "OutputTypes", "PracticeAreas")
_ALLOWED = {t.lower() for t in ALLOWED_TABLES}
MAX_ROWS = 100
QUERY_TIMEOUT_S = 15
MAX_ATTACHMENTS = 10


def _connect():
    return closing(pyodbc.connect(_conn_str, readonly=True))


# ---------------------------------------------------------------- Mode A: item context
def _val(v) -> str:
    return "-" if v is None or v == "" else str(v)


def _name(en, ar) -> str:
    return " / ".join(x for x in (en, ar) if x) or "-"


def item_context(item_type: str, item_id: str) -> tuple[str, list[dict]] | None:
    """(context_text, attachments) for the item, or None when it does not exist or is deleted."""
    if item_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported item type {item_type!r}; supported: {', '.join(SUPPORTED_TYPES)}")
    try:
        gid = str(uuid.UUID(str(item_id)))
    except ValueError:
        return None
    with _connect() as c:
        cur = c.cursor()
        g = cur.execute(
            "SELECT g.*, s.NameEn AS StatusEn, s.NameAr AS StatusAr, d.NameEn AS DecEn, d.NameAr AS DecAr, "
            "r.GrievanceNumber AS RelNumber, r.Title AS RelTitle, ws.DisplayNameEn AS StepEn, ws.DisplayNameAr AS StepAr "
            "FROM dbo.Grievances g LEFT JOIN dbo.GrievanceStatuses s ON s.Id = g.GrievanceStatusId "
            "LEFT JOIN dbo.DecisionTypes d ON d.Id = g.DecisionTypeId "
            "LEFT JOIN dbo.Grievances r ON r.Id = g.RelatedGrievanceId "
            "LEFT JOIN dbo.WorkflowSteps ws ON ws.Id = g.CurrentWorkflowStepId "
            "WHERE g.Id = ? AND g.IsDeleted = 0", gid).fetchone()
        if not g:
            return None
        notes = cur.execute("SELECT Note, CreatedDate FROM dbo.GrievanceNotes WHERE GrievanceId = ? AND IsDeleted = 0 "
                            "ORDER BY CreatedDate", gid).fetchall()
        actions = cur.execute(
            "SELECT a.CreatedDate, a.Reason, wa.DisplayNameEn AS ActEn, wa.DisplayNameAr AS ActAr, "
            "ws.DisplayNameEn AS StepEn, ws.DisplayNameAr AS StepAr, st.NameEn AS ToEn, st.NameAr AS ToAr "
            "FROM dbo.GrievanceActions a LEFT JOIN dbo.WorkflowStepActions wa ON wa.Id = a.WorkflowStepActionId "
            "LEFT JOIN dbo.WorkflowSteps ws ON ws.Id = wa.WorkflowStepId "
            "LEFT JOIN dbo.GrievanceStatuses st ON st.Id = wa.StatusId "
            "WHERE a.GrievanceId = ? AND a.IsDeleted = 0 ORDER BY a.CreatedDate", gid).fetchall()
        files = cur.execute(
            "SELECT DISTINCT TOP (?) a.Id, a.FileName FROM dbo.GrievanceAttachments ga "
            "JOIN dbo.Attachments a ON a.Id = ga.AttachmentId AND a.IsDeleted = 0 AND a.IsActive = 1 "
            "WHERE ga.GrievanceId = ? ORDER BY a.FileName", MAX_ATTACHMENTS, gid).fetchall()
    attachments = [{"id": str(f.Id).upper(), "name": f.FileName} for f in files]
    related = f"{_val(g.RelNumber)} {_val(g.RelTitle)}" if g.RelatedGrievanceId else "-"
    lines = ["GRIEVANCE",
             f"Number: {_val(g.GrievanceNumber)}", f"Title: {_val(g.Title)}",
             f"Status: {_name(g.StatusEn, g.StatusAr)}", f"Priority: {_val(g.Priority)}",
             f"Decision type: {_name(g.DecEn, g.DecAr)}", f"Decision number: {_val(g.DecisionNumber)}",
             f"Decision notification date: {_val(g.DecisionNotificationDate)}",
             f"Submission deadline: {_val(g.SubmissionDeadline)}", f"Response deadline: {_val(g.ResponseDeadline)}",
             f"Current workflow step: {_name(g.StepEn, g.StepAr)}", f"Related grievance: {related}",
             f"Created: {_val(g.CreatedDate)}", f"Last modified: {_val(g.ModifiedDate)}",
             f"Description:\n{_val(g.Description)}", "", f"NOTES ({len(notes)})"]
    lines += [f"- [{_val(n.CreatedDate)}] {_val(n.Note)}" for n in notes]
    lines += ["", f"ACTIONS ({len(actions)})"]
    lines += [f"- [{_val(a.CreatedDate)}] step: {_name(a.StepEn, a.StepAr)}; action: {_name(a.ActEn, a.ActAr)}; "
              f"resulting status: {_name(a.ToEn, a.ToAr)}; reason: {_val(a.Reason)}" for a in actions]
    lines += ["", f"ATTACHMENTS ({len(attachments)})"] + [f"- {a['name']}" for a in attachments]
    return "\n".join(lines), attachments


# ---------------------------------------------------------------- Mode B: guarded SELECT
_TOKEN = re.compile(r"""\s+|(?P<str>'(?:[^']|'')*')|(?P<br>\[(?:[^\]]|\]\])+\])|(?P<word>[A-Za-z_][A-Za-z0-9_$#@]*)|"""
                    r"""(?P<num>\d+(?:\.\d+)?)|(?P<sym>.)""", re.S)
_FORBIDDEN = set("""insert update delete merge drop alter create exec execute grant revoke deny truncate into openrowset
openquery openjson opendatasource declare set use waitfor backup restore dbcc bulk kill shutdown reconfigure apply print
revert begin commit rollback transaction path""".split())
_FORBIDDEN_PREFIX = ("xp_", "sp_", "fn_", "sys", "information_schema")
_NOT_ALIAS = set("where join inner left right full cross outer on group order having union except intersect for option as".split())


def _tokens(sql: str) -> list[tuple[str, str]]:
    """[(kind, value)], kind in str/br/word/num/sym; words and bracketed names lower-cased (brackets removed).
    Rejects what a SELECT never needs: comments, ';', double quotes, @variables, #temp tables, bad quoting."""
    out, pos = [], 0
    while pos < len(sql):
        m = _TOKEN.match(sql, pos)
        pos = m.end()
        kind, v = m.lastgroup, m.group()
        if kind is None:
            continue
        if kind == "br":
            v = v[1:-1].replace("]]", "]")
        if kind in ("br", "word"):
            v = v.lower()
        if kind == "word" and ("@" in v or "#" in v):
            raise ValueError("Variables (@) and temp tables (#) are not allowed")
        if kind == "sym" and v in ';"`\\@#\'':
            raise ValueError(f"Character {v!r} is not allowed (one statement only, no comments, no quoted identifiers)")
        if kind == "sym" and out and out[-1][0] == "sym" and out[-1][1] + v in ("--", "/*", "*/"):
            raise ValueError("Comments (-- and /* */) are not allowed")
        out.append((kind, v))
    return out


@lru_cache(maxsize=1)
def _other_tables() -> frozenset:
    """Every table/view of the database that is NOT allowed (lower-case): their names may not appear anywhere."""
    with _connect() as c:
        rows = c.cursor().execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES").fetchall()
    return frozenset(r[0].lower() for r in rows) - _ALLOWED


def _check(sql: str) -> None:
    """Raise ValueError unless `sql` is one SELECT over allowed tables only."""
    toks = _tokens(sql)
    vals = [v for _, v in toks]
    if not toks or toks[0] not in (("word", "select"), ("word", "with")):
        raise ValueError("Only a single SELECT statement (or WITH ... SELECT) is allowed")
    for kind, v in toks:
        if kind in ("word", "br") and (v in _FORBIDDEN or v.startswith(_FORBIDDEN_PREFIX)):
            raise ValueError(f"{v!r} is not allowed in a read-only query (writes, procedures, system objects and the "
                             "Attachments.Path column are blocked)")
    blocked = _other_tables()
    for kind, v in toks:  # catches comma joins / table hints that the FROM parser below cannot see
        if kind in ("word", "br") and v in blocked:
            raise ValueError(f"Table {v!r} is not allowed. Allowed tables: {', '.join(ALLOWED_TABLES)}")
    ctes = {vals[i] for i in range(len(vals) - 2)
            if vals[0] == "with" and toks[i][0] == "word" and vals[i + 1] == "as" and vals[i + 2] == "("}
    tables = set()
    for i, (_, v) in enumerate(toks):
        if toks[i] not in (("word", "from"), ("word", "join")):
            continue
        j = i + 1
        if j < len(toks) and vals[j] == "(":  # subquery: its own FROM is checked on its own
            continue
        chain = []
        while j < len(toks) and toks[j][0] in ("word", "br"):
            chain.append(vals[j])
            j += 1
            if j < len(toks) and vals[j] == "." and j + 1 < len(toks):
                j += 1
            else:
                break
        if not chain or len(chain) > 2 or (len(chain) == 2 and chain[0] != "dbo"):
            raise ValueError("Tables must be written as Table or dbo.Table")
        t = chain[-1]
        if t in _ALLOWED:
            tables.add(t)
        elif not (len(chain) == 1 and t in ctes):
            raise ValueError(f"Table {t!r} is not allowed. Allowed tables: {', '.join(ALLOWED_TABLES)}")
        if j < len(toks) and vals[j] == "as":
            j += 1
        if j < len(toks) and toks[j][0] in ("word", "br") and vals[j] not in _NOT_ALIAS:
            j += 1
        if j < len(toks) and vals[j] == ",":
            raise ValueError("Comma joins are not allowed; use explicit JOIN ... ON")
    if not tables:
        raise ValueError(f"The query must read from at least one allowed table: {', '.join(ALLOWED_TABLES)}")
    if "attachments" in tables:
        for i, v in enumerate(vals):
            if v == "*" and not (0 < i < len(vals) - 1 and vals[i - 1] == "(" and vals[i + 1] == ")"):
                raise ValueError("'*' is not allowed when Attachments is used (it would include Path); list the columns")


def _json_safe(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (bytes, bytearray)):
        return f"<binary {len(v)} bytes>"
    return v.isoformat() if isinstance(v, (datetime, date)) else str(v)


def run_query(sql: str) -> list[dict]:
    """Run one validated read-only SELECT; at most 100 rows (a last row {"_truncated": ...} says when there were more).
    Raises ValueError with a message the AI can act on."""
    _check(sql.strip())
    try:
        with _connect() as c:
            c.timeout = QUERY_TIMEOUT_S
            cur = c.cursor()
            cur.execute(sql)
            names = []
            for d in cur.description or []:
                n = d[0] or "col"
                while n in names:
                    n += "_"
                names.append(n)
            rows = cur.fetchmany(MAX_ROWS + 1)
    except pyodbc.Error as e:
        raise ValueError(f"SQL error: {e.args[-1] if e.args else e}") from None
    out = [{n: _json_safe(v) for n, v in zip(names, r)} for r in rows[:MAX_ROWS]]
    if len(rows) > MAX_ROWS:
        out.append({"_truncated": f"more than {MAX_ROWS} rows; only the first {MAX_ROWS} are shown. Add filters or aggregate."})
    return out


@lru_cache(maxsize=1)
def schema_text() -> str:
    """Compact table/column/join description of the allowed tables for the AI prompt (Attachments.Path excluded)."""
    ph = ",".join("?" * len(ALLOWED_TABLES))
    with _connect() as c:
        cur = c.cursor()
        cols = cur.execute("SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'dbo' "
                           f"AND TABLE_NAME IN ({ph}) ORDER BY TABLE_NAME, ORDINAL_POSITION", *ALLOWED_TABLES).fetchall()
        fks = cur.execute("SELECT OBJECT_NAME(fk.parent_object_id) t, pc.name c, OBJECT_NAME(fk.referenced_object_id) rt, rc.name rc "
                          "FROM sys.foreign_key_columns fk JOIN sys.columns pc ON pc.object_id = fk.parent_object_id AND pc.column_id = fk.parent_column_id "
                          "JOIN sys.columns rc ON rc.object_id = fk.referenced_object_id AND rc.column_id = fk.referenced_column_id "
                          f"WHERE OBJECT_NAME(fk.parent_object_id) IN ({ph}) AND OBJECT_NAME(fk.referenced_object_id) IN ({ph})",
                          *ALLOWED_TABLES, *ALLOWED_TABLES).fetchall()
    by_table: dict[str, list[str]] = {}
    for r in cols:
        if (r.TABLE_NAME, r.COLUMN_NAME) != ("Attachments", "Path") and r.DATA_TYPE != "timestamp":
            by_table.setdefault(r.TABLE_NAME, []).append(f"{r.COLUMN_NAME} {r.DATA_TYPE}")
    text = ["Tables (schema dbo):"] + [f"- {t}({', '.join(by_table[t])})" for t in ALLOWED_TABLES if t in by_table]
    joins = [f"{r.t}.{r.c} -> {r.rt}.{r.rc}" for r in fks]
    if joins:
        text += ["Joins (foreign keys):"] + [f"- {j}" for j in joins]
    return "\n".join(text)
