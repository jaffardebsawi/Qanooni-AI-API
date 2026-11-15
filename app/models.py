from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class Category(str, Enum):
    contracts_agreements = "contracts_agreements"
    cases = "cases"
    representative_help = "representative_help"
    law_reviews = "law_reviews"
    investigations = "investigations"


class CaseStatus(str, Enum):
    open = "open"
    closed = "closed"
    archived = "archived"


class CaseCreate(BaseModel):
    tenant_id: str = "default"
    title: str
    description: str | None = None
    category: Category | None = None
    status: CaseStatus = CaseStatus.open


class CaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: Category | None = None
    status: CaseStatus | None = None


class DocumentUpdate(BaseModel):
    category: Category | None = None
    case_id: str | None = None  # attach to a case
    detach_case: bool = False  # set true to remove the case link
    metadata: dict | None = None


class ChatCreate(BaseModel):
    user_id: UUID  # dbo.AppUsers.Id of the chat's owner
    title: str | None = None


class MessageCreate(BaseModel):
    user_id: UUID  # dbo.AppUsers.Id of the chat's owner
    message: str
    attachment_ids: list[UUID] = []  # dbo.Attachments.Id of files sent with this message


class GenerationCreate(BaseModel):
    tenant_id: str = "default"
    case_id: str | None = None
    message: str | None = None  # e.g. "NDA for John at CBA with deliverables"
    template_id: str | None = None  # skip template selection
    fields: dict[str, str] | None = None  # values supplied directly (e.g. from a form)


class GenerationMessage(BaseModel):
    message: str | None = None  # answer to the questions in `missing`
    fields: dict[str, str] | None = None


class ReviseRequest(BaseModel):
    instruction: str  # e.g. "change the term to 5 years"


class TemplateFromDocument(BaseModel):
    tenant_id: str = "default"
    document_id: str  # an ingested document, e.g. contract ID 7


class IngestRequest(BaseModel):
    document_id: str
    source_path: str  # relative to FILES_ROOT
    tenant_id: str = "default"
    case_id: str | None = None
    category: Category | None = None  # caller override of the classifier's category
    metadata: dict = {}
