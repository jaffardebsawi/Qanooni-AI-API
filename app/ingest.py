import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .classifier import classify
from .extract import extract_text
from .models import IngestRequest
from .settings import settings
from .store import upsert_document


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def doc_key(tenant_id: str, document_id: str) -> str:
    return f"{tenant_id}/{document_id}"


def new_job(req: IngestRequest) -> dict:
    job = {"job_id": str(uuid.uuid4()), "tenant_id": req.tenant_id, "document_id": req.document_id,
           "status": "queued", "created_at": now()}
    db.put("jobs", job["job_id"], job)
    # every ingested file gets a document record, so uploads and server files are listed the same way
    prev = db.get("documents", doc_key(req.tenant_id, req.document_id)) or {}
    db.put("documents", doc_key(req.tenant_id, req.document_id), {
        **prev, "document_id": req.document_id, "tenant_id": req.tenant_id, "filename": Path(req.source_path).name,
        "source_path": req.source_path, "case_id": req.case_id, "metadata": req.metadata, "status": "queued",
        "job_id": job["job_id"], "error": None, "created_at": prev.get("created_at") or now()})
    return job


def _update(job: dict, req: IngestRequest, **changes) -> None:
    job.update(changes)
    db.put("jobs", job["job_id"], job)
    key = doc_key(req.tenant_id, req.document_id)
    doc = db.get("documents", key)
    if doc and doc["job_id"] == job["job_id"]:  # ignore a superseded job
        cls = changes.get("classification") or {}
        doc.update(status=changes["status"], error=changes.get("error"), updated_at=now())
        if cls:
            doc.update(category=cls["category"], document_type=cls.get("document_type"), classification=cls,
                       chunks=changes["chunks"], used_ocr=changes["used_ocr"])
        db.put("documents", key, doc)


def run_job(job_id: str, req: IngestRequest) -> None:
    job = db.get("jobs", job_id)
    try:
        _update(job, req, status="processing")
        root = Path(settings.files_root).resolve()
        path = (root / req.source_path).resolve()
        if root not in path.parents:
            raise ValueError("source_path escapes the files root")
        text, used_ocr = extract_text(path.name, path.read_bytes())
        if not text.strip():
            raise ValueError("No text could be extracted")
        cls = classify(text)
        cls["category_source"] = "classifier"
        if req.category:
            cls["category"], cls["category_source"] = req.category.value, "caller"
        payload = {**req.metadata, **cls, "case_id": req.case_id, "source_path": req.source_path, "used_ocr": used_ocr}
        chunks = upsert_document(req.tenant_id, req.document_id, text, payload)
        _update(job, req, status="done", classification=cls, used_ocr=used_ocr, chunks=chunks, chars=len(text))
    except Exception as e:  # noqa: BLE001
        _update(job, req, status="failed", error=f"{type(e).__name__}: {e}")
        traceback.print_exc()
