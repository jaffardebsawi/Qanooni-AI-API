from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from . import chat as chat_mod
from . import chatdb, db, itemdb
from . import generate as gen_mod
from . import templates_store as ts
from .extract import extract_text
from .ingest import new_job, run_job
from .models import (Category, ChatRequest, GenerationCreate, GenerationMessage, IngestRequest, ReviseRequest,
                     TemplateFromDocument)
from .routes_cases import router as cases_router
from .settings import settings
from .store import get_source_path, search


# Fixed for now: every chat is accessed as this user (dbo.AppUsers.Id) until real users are wired in.
STATIC_USER_ID = "D841C067-CE0D-4F7E-902F-08DF2C9481E0"


def require_key(x_api_key: str | None = Header(None)):
    if x_api_key != settings.api_key:
        raise HTTPException(401, "Invalid API key")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.fail_interrupted_jobs()
    yield


app = FastAPI(
    title="Legal Advisor API",
    version="0.1.0",
    description="Ingestion pipeline: extract/OCR -> AI classification -> chunk/embed -> Qdrant. "
                "Chat with retrieval, and document generation from templates.",
    dependencies=[Depends(require_key)],
    lifespan=lifespan,
)


app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])


# ---- templates ----

@app.get("/v1/templates", tags=["templates"])
def list_templates(tenant_id: str = "default"):
    """Built-in and tenant templates. Each lists its `fields` so a UI can render a form."""
    return [ts.public(t) for t in ts.list_templates(tenant_id)]


@app.get("/v1/templates/{template_id}", tags=["templates"])
def get_template(template_id: str, tenant_id: str = "default"):
    t = ts.get_template(template_id, tenant_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@app.post("/v1/templates", status_code=201, tags=["templates"])
async def upload_template(file: UploadFile = File(...), tenant_id: str = Form("default")):
    """Upload your own document (docx, pdf, image, txt). The AI detects its fillable fields."""
    text, _ = extract_text(file.filename, await file.read())
    return ts.public(ts.create_from_text(tenant_id, text, {"filename": file.filename}))


@app.post("/v1/templates/from-document", status_code=201, tags=["templates"])
def template_from_document(req: TemplateFromDocument):
    """Turn an already-ingested document (e.g. contract ID 7) into a template."""
    source = get_source_path(req.tenant_id, req.document_id)
    if not source:
        raise HTTPException(404, "Document not ingested")
    path = Path(settings.files_root) / source
    text, _ = extract_text(path.name, path.read_bytes())
    return ts.public(ts.create_from_text(req.tenant_id, text, {"document_id": req.document_id}))


# ---- document generation ----

def _gen(generation_id: str) -> dict:
    gen = db.get("generations", generation_id)
    if not gen:
        raise HTTPException(404, "Generation not found")
    return gen


@app.post("/v1/generations", tags=["generation"])
def start_generation(req: GenerationCreate):
    """Start a document. Returns status `needs_template`, `needs_info` (with `missing` questions) or `complete`."""
    gen = gen_mod.create_generation(req.tenant_id, req.case_id, req.template_id)
    return gen_mod.step(gen, req.message, req.fields)


@app.post("/v1/generations/{generation_id}/messages", tags=["generation"])
def answer_generation(generation_id: str, req: GenerationMessage):
    """Answer the `missing` questions in natural language and/or pass `fields` directly."""
    return gen_mod.step(_gen(generation_id), req.message, req.fields)


@app.get("/v1/generations", tags=["generation"])
def list_generations(tenant_id: str = "default", limit: int = 50):
    return db.list_docs("generations", tenant_id, limit)


@app.get("/v1/deliverables/{deliverable_id}", tags=["generation"])
def get_deliverable(deliverable_id: str):
    if not gen_mod.load_deliverable(deliverable_id):
        raise HTTPException(404, "Deliverable not found")
    return gen_mod.deliverable_view(deliverable_id)


@app.post("/v1/deliverables/{deliverable_id}/revise", tags=["generation"])
def revise_deliverable(deliverable_id: str, req: ReviseRequest):
    """Apply a change in plain language; creates a new version."""
    if not gen_mod.load_deliverable(deliverable_id):
        raise HTTPException(404, "Deliverable not found")
    return gen_mod.revise(deliverable_id, req.instruction)


@app.get("/v1/deliverables/{deliverable_id}/download", tags=["generation"])
def download_deliverable(deliverable_id: str, format: str = "docx", version: int | None = None):
    if format not in ("docx", "pdf"):
        raise HTTPException(422, "format must be docx or pdf")
    path = gen_mod.file_for(deliverable_id, format, version)
    if not path:
        raise HTTPException(404, "Deliverable not found")
    d = gen_mod.load_deliverable(deliverable_id)
    return FileResponse(path, filename=f"{d['title']} v{path.stem[1:]}.{format}")


@app.post("/v1/ingestion/jobs", status_code=202, tags=["ingestion"])
def create_ingestion_job(req: IngestRequest, bg: BackgroundTasks):
    job = new_job(req)
    bg.add_task(run_job, job["job_id"], req)
    return job


@app.get("/v1/ingestion/jobs", tags=["ingestion"])
def list_ingestion_jobs(tenant_id: str = "default", limit: int = 50):
    return db.list_docs("jobs", tenant_id, limit)


@app.get("/v1/ingestion/jobs/{job_id}", tags=["ingestion"])
def get_ingestion_job(job_id: str):
    job = db.get("jobs", job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/v1/chat", tags=["chat"])
def chat(req: ChatRequest):
    """Streams the AI's answer to `message` as plain UTF-8 text, as it is written. The context is the chat's last 20
    messages (SQL), the files attached to them, and optionally an item (`item_type` + `item_id`, e.g. a grievance).
    Without an item the AI can query the database. Files the AI creates are announced by a last line
    `[[attachments:<id>,<id>]]`. Nothing is stored here. 422 on a bad item_type/item_id, 404 when the chat or item
    is not found. The legal disclaimer is in the `X-Disclaimer` response header."""
    item_type = req.item_type.strip().lower() if req.item_type else None
    if req.item_id and not item_type:
        raise HTTPException(422, "No item type was specified (item_id was sent without item_type)")
    if item_type and not req.item_id:
        raise HTTPException(422, "item_id is missing")
    if item_type and item_type not in itemdb.SUPPORTED_TYPES:
        raise HTTPException(422, f"Unknown item_type '{item_type}'. Supported types: {', '.join(itemdb.SUPPORTED_TYPES)}")
    history = chatdb.recent_messages(str(req.chat_id), STATIC_USER_ID, chat_mod.HISTORY_MESSAGES)
    if history is None:
        raise HTTPException(404, "Chat not found")
    item = None
    if item_type:
        item = itemdb.item_context(item_type, str(req.item_id))
        if item is None:
            raise HTTPException(404, f"Item not found: no {item_type} with id {req.item_id}")
    stream = chat_mod.stream_answer(req.message, history, item_type, item, [str(a) for a in req.attachment_ids],
                                    str(req.chat_id))
    return StreamingResponse(stream, media_type="text/plain; charset=utf-8", headers={"X-Disclaimer": chat_mod.DISCLAIMER})


@app.get("/v1/documents/search", tags=["documents"])
def search_documents(q: str, tenant_id: str = "default", category: Category | None = None, limit: int = 5):
    hits = search(tenant_id, q, category.value if category else None, limit)
    return [
        {"score": h.score, "document_id": h.payload["document_id"], "category": h.payload["category"],
         "document_type": h.payload.get("document_type"), "text": h.payload["text"][:300]}
        for h in hits
    ]


# registered last so the static /v1/documents/search route above wins over /v1/documents/{document_id}
app.include_router(cases_router)
