"""Client for the .NET attachment service (download, upload) plus small file helpers."""
import io
import re
from urllib.parse import unquote

import docx
import requests

from .extract import extract_text
from .settings import settings

MAX_CHARS = 20000
TIMEOUT = 60
GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class AttachmentError(Exception):
    pass


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.attachments_token}"}


def _file_name(header: str, fallback: str) -> str:
    m = re.search(r"filename\*\s*=\s*[^']*'[^']*'([^;]+)", header, re.I)
    if m:
        return unquote(m.group(1).strip().strip('"'))
    m = re.search(r'filename\s*=\s*"?([^";]+)"?', header, re.I)
    return m.group(1).strip() if m else fallback


def download(attachment_id: str) -> tuple[str, bytes]:
    url = settings.attachments_base_url.rstrip("/") + settings.attachments_download_path
    try:
        r = requests.get(url, params={"id": attachment_id}, headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as e:
        raise AttachmentError(f"Could not reach the attachment service: {e}") from e
    if r.status_code == 401:
        raise AttachmentError("Attachment service rejected the token (401); it is probably expired.")
    if r.status_code == 404:
        raise AttachmentError(f"Attachment {attachment_id} was not found (404).")
    if r.status_code != 200:
        raise AttachmentError(f"Attachment download failed (HTTP {r.status_code}).")
    return _file_name(r.headers.get("Content-Disposition", ""), attachment_id), r.content


def read_text(attachment_id: str) -> tuple[str, str]:
    """(file_name, text). Re-reads every time. Only download failures raise."""
    name, data = download(attachment_id)
    try:
        text, _ = extract_text(name, data)
    except Exception as e:
        return name, f"[could not read this file: {e}]"
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[truncated]"
    return name, text


def _find_id(obj) -> str | None:
    if isinstance(obj, str):
        m = GUID_RE.search(obj)
        return m.group(0) if m else None
    if isinstance(obj, dict):
        for k, v in obj.items():  # prefer keys named id
            if k.lower() in ("id", "attachmentid") and v:
                found = _find_id(v) or (str(v) if isinstance(v, (str, int)) else None)
                if found:
                    return found
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            found = _find_id(v)
            if found:
                return found
    return None


def upload(filename: str, data: bytes) -> str:
    url = settings.attachments_base_url.rstrip("/") + settings.attachments_upload_path
    try:
        r = requests.post(url, headers=_headers(), files={"files": (filename, data)},
                          data={"attachmentType": "0"}, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise AttachmentError(f"Could not reach the attachment service: {e}") from e
    if r.status_code == 401:
        raise AttachmentError("Attachment service rejected the token (401); it is probably expired.")
    if not r.ok:
        raise AttachmentError(f"Upload failed (HTTP {r.status_code}): {r.text[:300]}")
    try:
        found = _find_id(r.json())
    except ValueError:
        found = _find_id(r.text)
    if not found:
        raise AttachmentError(f"Upload worked but no attachment id was found in the response: {r.text[:300]}")
    return found


def build_file(filename: str, content: str) -> bytes:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext in ("txt", "md"):
        return content.encode("utf-8")
    if ext == "docx":
        d = docx.Document()
        for line in content.split("\n"):
            d.add_paragraph(line)
        buf = io.BytesIO()
        d.save(buf)
        return buf.getvalue()
    raise ValueError(f"Unsupported file type for {filename!r}; use .docx, .txt or .md")
