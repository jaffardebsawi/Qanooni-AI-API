import json
import re
import uuid
from pathlib import Path

from .builtin_templates import BUILTIN_TEMPLATES
from .clients import llm
from .render import is_arabic
from .settings import settings

_dir = Path(settings.data_dir) / "templates"
_dir.mkdir(parents=True, exist_ok=True)

CONVERT_PROMPT = """Convert the legal document below into a reusable fill-in template. Return JSON only:
{"name": str, "doc_type": str, "description": one sentence,
 "fields": [{"key": snake_case, "label": str, "question": a short question to ask the user, "required": bool, "default": str|null}],
 "body": the template text}
Rules for body (plain text markup):
- First line "# TITLE". Then keep the document's own wording, replacing party names, dates, amounts, durations and other
  case-specific details with {{key}} placeholders (the same key everywhere that value appears).
- Party full names must use keys ending in _name (for example party_a_name, client_name).
- "### Heading" for unnumbered headings (Parties, Background, Execution). "## Heading" for numbered clauses
  (do NOT write clause numbers, they are added automatically). "- text" for each numbered sub-clause.
  "* text" for lettered items (a), (b). End with "@sign {{party_name_key}}" per party.
- Wrap clauses that only apply when an optional field is given in {{#key}}...{{/key}}.
- Signature blocks stay blank for people to sign: never create fields for signatory names, titles or signature dates.
- Do not invent clauses. Fields with sensible standard values should be required=false with a default.
- Keep the document's own language (for example Arabic) for body, name, description, field labels and questions.
  Keys stay in English snake_case. Add "language": "ar" or "en"."""


def _load_custom() -> dict[str, dict]:
    return {t["template_id"]: t for t in (json.loads(p.read_text(encoding="utf-8")) for p in _dir.glob("*.json"))}


def list_templates(tenant_id: str) -> list[dict]:
    custom = [t for t in _load_custom().values() if t["tenant_id"] == tenant_id]
    return BUILTIN_TEMPLATES + custom


def get_template(template_id: str, tenant_id: str) -> dict | None:
    return next((t for t in list_templates(tenant_id) if t["template_id"] == template_id), None)


def create_from_text(tenant_id: str, text: str, source: dict | None = None) -> dict:
    r = llm.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[{"role": "system", "content": CONVERT_PROMPT}, {"role": "user", "content": text[:60000]}],
        response_format={"type": "json_object"},
    )
    t = json.loads(r.choices[0].message.content)
    keys = {f["key"] for f in t["fields"]}
    used = set(re.findall(r"\{\{[#/]?(\w+)\}\}", t["body"]))
    t["fields"] = [{"default": None, "required": True, **f} for f in t["fields"] if f["key"] in used]
    t["language"] = "ar" if is_arabic(t["body"]) else "en"
    t.update(template_id=f"tpl-{uuid.uuid4().hex[:12]}", tenant_id=tenant_id, source=source or {},
             unknown_placeholders=sorted(k for k in used - keys if not k.endswith("_short")))
    (_dir / f"{t['template_id']}.json").write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    return t


def public(t: dict) -> dict:
    return {k: v for k, v in t.items() if k != "body"}
