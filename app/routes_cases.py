"""Case and document management endpoints."""
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import db
from . import generate as gen_mod
from .ingest import doc_key, new_job, now, run_job
from .models import CaseCreate, CaseStatus, CaseUpdate, Category, DocumentUpdate, IngestRequest
from .settings import settings
from .store import delete_document, update_document_payload

router = APIRouter()

SAFE_ID = re.compile(r"^[A-Za-z0-9][\w.-]{0,99}$")
UPLOAD_EXT = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


# ---- cases ----

def _case(case_id: str, tenant_id: str) -> dict:
    case = db.get("cases", case_id)
    if not case or case["tenant_id"] != tenant_id:
        raise HTTPException(404, "Case not found")
    return case


def _case_docs(tenant_id: str, case_id: str, limit: int = 200) -> list[dict]:
    return db.list_docs("documents", tenant_id, limit, where={"case_id": case_id})


@router.post("/v1/cases", status_code=201, tags=["cases"])
def create_case(req: CaseCreate):
    case = {"case_id": str(uuid.uuid4()), **req.model_dump(mode="json"), "created_at": now(), "updated_at": now()}
    db.put("cases", case["case_id"], case)
    return case


@router.get("/v1/cases", tags=["cases"])
def list_cases(tenant_id: str = "default", status: CaseStatus | None = None, category: Category | None = None, limit: int = 50):
    return db.list_docs("cases", tenant_id, limit, where={"status": status and status.value, "category": category and category.value})


@router.get("/v1/cases/{case_id}", tags=["cases"])
def get_case(case_id: str, tenant_id: str = "default"):
    case = _case(case_id, tenant_id)
    return {**case, "counts": {"documents": len(_case_docs(tenant_id, case_id, 10000)),
                               "deliverables": len(gen_mod.list_deliverables(tenant_id, case_id))}}


@router.patch("/v1/cases/{case_id}", tags=["cases"])
def update_case(case_id: str, req: CaseUpdate, tenant_id: str = "default"):
    case = _case(case_id, tenant_id)
    case.update(req.model_dump(mode="json", exclude_unset=True), updated_at=now())
    db.put("cases", case_id, case)
    return case


@router.delete("/v1/cases/{case_id}", status_code=204, tags=["cases"])
def delete_case(case_id: str, tenant_id: str = "default", force: bool = False):
    """Deletes the case record. Refuses (409) while documents are attached unless `force=true`, which detaches them."""
    _case(case_id, tenant_id)
    docs = _case_docs(tenant_id, case_id, 100000)
    if docs and not force:
        raise HTTPException(409, f"Case has {len(docs)} document(s); detach them or pass force=true")
    for doc in docs:
        _set_document_case(doc, None)
    db.delete("cases", case_id)


@router.get("/v1/cases/{case_id}/documents", tags=["cases"])
def case_documents(case_id: str, tenant_id: str = "default", limit: int = 200):
    _case(case_id, tenant_id)
    return _case_docs(tenant_id, case_id, limit)


@router.get("/v1/cases/{case_id}/deliverables", tags=["cases"])
def case_deliverables(case_id: str, tenant_id: str = "default"):
    _case(case_id, tenant_id)
    return gen_mod.list_deliverables(tenant_id, case_id)


# ---- documents ----

def _document(document_id: str, tenant_id: str) -> dict:
    doc = db.get("documents", doc_key(tenant_id, document_id))
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


def _set_document_case(doc: dict, case_id: str | None) -> None:
    doc.update(case_id=case_id, updated_at=now())
    db.put("documents", doc_key(doc["tenant_id"], doc["document_id"]), doc)
    if doc["status"] == "done":
        update_document_payload(doc["tenant_id"], doc["document_id"], {"case_id": case_id})


@router.post("/v1/documents", status_code=202, tags=["documents"])
async def upload_document(bg: BackgroundTasks, file: UploadFile = File(...), tenant_id: str = Form("default"),
                          document_id: str | None = Form(None), case_id: str | None = Form(None),
                          category: Category | None = Form(None)):
    """Upload a file and start ingestion (extract/OCR, classify, embed). Poll the returned `job`, or GET the document."""
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in UPLOAD_EXT:
        raise HTTPException(415, f"Unsupported file type; allowed: {sorted(UPLOAD_EXT)}")
    document_id = document_id or f"doc-{uuid.uuid4().hex[:12]}"
    if not SAFE_ID.match(document_id) or not SAFE_ID.match(tenant_id):
        raise HTTPException(422, "tenant_id and document_id may only contain letters, digits, '.', '_' and '-'")
    if case_id:
        _case(case_id, tenant_id)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds 25 MB")
    rel = f"uploads/{tenant_id}/{document_id}/{name}"
    dest = Path(settings.files_root) / rel
    shutil.rmtree(dest.parent, ignore_errors=True)  # re-upload under the same id replaces the file
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    req = IngestRequest(document_id=document_id, source_path=rel, tenant_id=tenant_id, case_id=case_id, category=category)
    job = new_job(req)
    bg.add_task(run_job, job["job_id"], req)
    return {"document": _document(document_id, tenant_id), "job": job}


@router.get("/v1/documents", tags=["documents"])
def list_documents(tenant_id: str = "default", case_id: str | None = None, category: Category | None = None,
                   status: str | None = None, limit: int = 100):
    return db.list_docs("documents", tenant_id, limit, where={"case_id": case_id, "category": category and category.value, "status": status})


@router.get("/v1/documents/{document_id}", tags=["documents"])
def get_document(document_id: str, tenant_id: str = "default"):
    return _document(document_id, tenant_id)


@router.patch("/v1/documents/{document_id}", tags=["documents"])
def update_document(document_id: str, req: DocumentUpdate, tenant_id: str = "default"):
    """Change category, case link or metadata. Search and chat filters pick the change up immediately."""
    doc = _document(document_id, tenant_id)
    payload = {}
    if req.case_id:
        _case(req.case_id, tenant_id)
        doc["case_id"] = payload["case_id"] = req.case_id
    elif req.detach_case:
        doc["case_id"] = payload["case_id"] = None
    if req.category:
        doc["category"] = payload["category"] = req.category.value
        doc["classification"] = {**doc.get("classification", {}), "category": req.category.value, "category_source": "caller"}
    if req.metadata is not None:
        doc["metadata"] = req.metadata
    doc["updated_at"] = now()
    db.put("documents", doc_key(tenant_id, document_id), doc)
    if payload and doc["status"] == "done":
        update_document_payload(tenant_id, document_id, payload)
    return doc


@router.delete("/v1/documents/{document_id}", status_code=204, tags=["documents"])
def remove_document(document_id: str, tenant_id: str = "default"):
    """Removes the record, its vectors and (for uploaded files) the stored file. Server-hosted source files are never deleted."""
    doc = _document(document_id, tenant_id)
    delete_document(tenant_id, document_id)
    if doc["source_path"].startswith(f"uploads/{tenant_id}/{document_id}/"):
        shutil.rmtree((Path(settings.files_root) / doc["source_path"]).parent, ignore_errors=True)
    db.delete("documents", doc_key(tenant_id, document_id))


@router.get("/v1/documents/{document_id}/download", tags=["documents"])
def download_document(document_id: str, tenant_id: str = "default"):
    doc = _document(document_id, tenant_id)
    root = Path(settings.files_root).resolve()
    path = (root / doc["source_path"]).resolve()
    if root not in path.parents or not path.exists():
        raise HTTPException(404, "File not found on the file server")
    return FileResponse(path, filename=doc["filename"])
