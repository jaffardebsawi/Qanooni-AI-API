"""Document generation: pick a template, collect fields (asking for missing ones), render, revise."""
import difflib
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from . import db
from . import templates_store as ts
from .clients import llm
from .render import fill, with_defaults, write_docx, write_pdf
from .settings import settings

_dir = Path(settings.data_dir) / "deliverables"
_dir.mkdir(parents=True, exist_ok=True)


def _json(system: str, user: str, model: str | None = None) -> dict:
    r = llm.chat.completions.create(
        model=model or settings.classifier_model,
        messages=[{"role": "system", "content": system + " Respond with JSON only."}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
    )
    return json.loads(r.choices[0].message.content)


def _pick_template(tenant_id: str, message: str) -> str | None:
    cands = [{"template_id": t["template_id"], "name": t["name"], "description": t["description"], "language": t.get("language", "en")}
             for t in ts.list_templates(tenant_id)]
    out = _json("Pick the template that best fits the user's request. When templates of several languages fit, choose the one "
                "in the language the user wrote in, unless the user asks for a specific language. "
                'Return {"template_id": id or null if none fits}.',
                json.dumps({"templates": cands, "request": message}))
    return out.get("template_id") if out.get("template_id") in {c["template_id"] for c in cands} else None


def _as_written(value: str, message: str) -> str:
    """Party names must be copied from the user's message exactly; repair a model slip (e.g. one wrong Arabic letter)."""
    if value in message:
        return value
    words, n = message.split(), len(value.split())
    spans = [" ".join(words[i:i + n]).strip("،,.;:") for i in range(len(words) - n + 1)]
    best = difflib.get_close_matches(value, spans, n=1, cutoff=0.8)
    return best[0] if best else value


def _extract_fields(tpl: dict, current: dict, pending: list[str], message: str) -> tuple[dict, list[str]]:
    """Returns (values stated by the user, optional field keys the user wants but gave no content for)."""
    spec = [{"key": f["key"], "label": f["label"], "question": f["question"]} for f in tpl["fields"]]
    out = _json(
        "Extract field values for a legal document from the user's message. A value must be the actual content "
        "(a name, date, amount, list of items), never a restatement of the request such as 'with deliverables'. "
        "Use only what the user explicitly states; never guess or invent. If the message answers a pending question, "
        "map it to that field. "
        f"Write dates as 'D Month YYYY' (today is {date.today():%d %B %Y}), in the language of the template "
        f"({tpl.get('language', 'en')}; for Arabic use Arabic month names, e.g. '1 ديسمبر 2026'). "
        "Write names and other values exactly as the user gave them, in the user's own script. "
        'Return {"fields": {key: string or null}, "wanted_without_value": [keys of fields the user asked to include '
        "but gave no content for]}.",
        json.dumps({"fields": spec, "already_collected": current, "pending_questions": pending, "message": message}),
    )
    valid = {f["key"] for f in tpl["fields"]}
    values = {k: str(v).strip() for k, v in out.get("fields", {}).items() if k in valid and v not in (None, "")}
    values = {k: _as_written(v, message) if k.endswith("_name") else v for k, v in values.items()}
    no_default = {f["key"] for f in tpl["fields"] if f.get("default") is None}
    return values, [k for k in out.get("wanted_without_value", []) if k in no_default]


def create_generation(tenant_id: str, case_id: str | None, template_id: str | None) -> dict:
    gen = {"generation_id": str(uuid.uuid4()), "tenant_id": tenant_id, "case_id": case_id, "template_id": template_id,
           "fields": {}, "pending": [], "deliverable_id": None}
    db.put("generations", gen["generation_id"], gen)
    return gen


def step(gen: dict, message: str | None, fields: dict | None) -> dict:
    result = _step(gen, message, fields)
    db.put("generations", gen["generation_id"], gen)
    return result


def _step(gen: dict, message: str | None, fields: dict | None) -> dict:
    tenant = gen["tenant_id"]
    if not gen["template_id"] and message:
        gen["template_id"] = _pick_template(tenant, message)
    tpl = ts.get_template(gen["template_id"], tenant) if gen["template_id"] else None
    if not tpl:
        return {**_view(gen, None), "status": "needs_template",
                "available_templates": [ts.public(t) for t in ts.list_templates(tenant)]}
    if message:
        values, wanted = _extract_fields(tpl, gen["fields"], gen["pending"], message)
        gen["fields"].update(values)
        gen["wanted"] = sorted(set(gen.get("wanted", [])) | set(wanted))
    valid = {f["key"] for f in tpl["fields"]}
    gen["fields"].update({k: str(v) for k, v in (fields or {}).items() if k in valid and v not in (None, "")})
    # required fields, plus optional ones the user asked for but has not given content for yet
    missing = [f for f in tpl["fields"] if (f["required"] or f["key"] in gen.get("wanted", [])) and not gen["fields"].get(f["key"])]
    gen["pending"] = [f["question"] for f in missing]
    if missing:
        return {**_view(gen, tpl), "status": "needs_info", "missing": [{k: f[k] for k in ("key", "label", "question")} for f in missing]}
    if not gen["deliverable_id"]:
        gen["deliverable_id"] = _create_deliverable(gen, tpl)["deliverable_id"]
    return {**_view(gen, tpl), "status": "complete", "missing": [], "deliverable": deliverable_view(gen["deliverable_id"])}


def _view(gen: dict, tpl: dict | None) -> dict:
    assumed = {}
    if tpl:
        assumed = {f["key"]: f["default"] for f in tpl["fields"] if f.get("default") and not gen["fields"].get(f["key"])}
    return {"generation_id": gen["generation_id"], "template": {"template_id": tpl["template_id"], "name": tpl["name"]} if tpl else None,
            "fields": gen["fields"], "assumed_defaults": assumed}


# ---- deliverables (persisted on disk so they survive restarts) ----

def _meta_path(deliverable_id: str) -> Path:
    return _dir / deliverable_id / "meta.json"


def load_deliverable(deliverable_id: str) -> dict | None:
    p = _meta_path(deliverable_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _save_version(d: dict, body: str, note: str) -> None:
    v = len(d["versions"]) + 1
    folder = _dir / d["deliverable_id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"v{v}.md").write_text(body, encoding="utf-8")
    write_docx(body, folder / f"v{v}.docx")
    write_pdf(body, folder / f"v{v}.pdf")
    d["versions"].append({"version": v, "note": note, "created_at": datetime.now(timezone.utc).isoformat()})
    _meta_path(d["deliverable_id"]).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _create_deliverable(gen: dict, tpl: dict) -> dict:
    values = with_defaults(gen["fields"], tpl["fields"])
    d = {"deliverable_id": f"del-{uuid.uuid4().hex[:12]}", "tenant_id": gen["tenant_id"], "case_id": gen["case_id"],
         "template_id": tpl["template_id"], "title": tpl["name"], "fields": values, "versions": []}
    _save_version(d, fill(tpl["body"], values), "Generated from template")
    return d


def deliverable_view(deliverable_id: str) -> dict:
    d = load_deliverable(deliverable_id)
    v = d["versions"][-1]["version"]
    base = f"/v1/deliverables/{deliverable_id}"
    return {"deliverable_id": deliverable_id, "title": d["title"], "case_id": d["case_id"], "version": v, "versions": d["versions"],
            "fields": d["fields"], "download": {"docx": f"{base}/download?format=docx", "pdf": f"{base}/download?format=pdf"},
            "text": (_dir / deliverable_id / f"v{v}.md").read_text(encoding="utf-8")}


def file_for(deliverable_id: str, fmt: str, version: int | None) -> Path | None:
    d = load_deliverable(deliverable_id)
    if not d:
        return None
    v = version or d["versions"][-1]["version"]
    p = _dir / deliverable_id / f"v{v}.{fmt}"
    return p if p.exists() else None


def list_deliverables(tenant_id: str, case_id: str | None = None) -> list[dict]:
    out = []
    for p in sorted(_dir.glob("*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["tenant_id"] == tenant_id and (case_id is None or d["case_id"] == case_id):
            out.append({k: d[k] for k in ("deliverable_id", "title", "case_id", "template_id")} | {"version": len(d["versions"]),
                        "created_at": d["versions"][0]["created_at"]})
    return out


def revise(deliverable_id: str, instruction: str) -> dict:
    d = load_deliverable(deliverable_id)
    current = (_dir / deliverable_id / f"v{d['versions'][-1]['version']}.md").read_text(encoding="utf-8")
    out = _json(
        "You edit legal documents written in a plain-text markup (# title, ### plain heading, ## numbered clause heading, "
        "- numbered sub-clause, * lettered item, @sign Party). Apply ONLY the requested change and keep everything else "
        "word-for-word. Keep the document's language (write any added text in it) and do not write clause numbers. Return {\"body\": the full revised document, \"summary\": one sentence}.",
        json.dumps({"document": current, "instruction": instruction}),
        model=settings.azure_openai_deployment,
    )
    _save_version(d, out["body"].strip() + "\n", out.get("summary") or instruction)
    return deliverable_view(deliverable_id)
