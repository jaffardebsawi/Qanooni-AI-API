import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from . import chatdb, db
from . import generate as gen_mod
from .clients import llm
from .extract import extract_text
from .models import MessageCreate
from .render import is_arabic
from .settings import settings
from .store import search

HISTORY_MESSAGES = 20
TOP_K = 6
TENANT = "default"
MAX_ATTACHMENT_CHARS = 20000  # per attached file, so a huge PDF cannot blow up the prompt
DISCLAIMER = "This is AI-generated legal information, not legal advice. Have a qualified lawyer review it."

# Citations are switched off for now: the model is not asked to cite and `sources` is not returned.
SYSTEM = """You are a legal advisor / legal representative assistant.
Use the SOURCES (the company's document library) and the ATTACHMENTS (files the user sent in this chat) when they are relevant.
If they do not contain the answer, say so plainly, then give general guidance clearly marked as general.
Never invent facts, clauses, case numbers or citations. Ask a short clarifying question if the request is ambiguous.
Reply in the user's language."""

INTENT_PROMPT = """Decide what the user's latest chat message asks for. Return JSON {"intent": one of
"generate"  - wants a NEW legal document drafted (contract, NDA, agreement, letter ...), e.g. "make me an NDA";
"continue"  - answers or adds details for the document currently being drafted (only when a draft is in progress);
"revise"    - asks to change the document already drafted (only when a finished draft exists), e.g. "make the term 5 years";
"question"  - anything else: a legal question, asking about documents, general chat}.
Questions ABOUT documents or law are "question" even when they mention a contract."""

T = {
    "en": {"ready": "Your document \"{title}\" is ready (version {v}). It is in the `generation.deliverable` field; download it as DOCX or PDF.",
           "need": "I need a few details to draft the {title}:", "pick": "Which document would you like me to draft? I can use one of these templates:",
           "revised": "Done. I updated \"{title}\" (version {v}): {summary}"},
    "ar": {"ready": "مستندك «{title}» جاهز (الإصدار {v}). يمكنك تنزيله بصيغة DOCX أو PDF.",
           "need": "أحتاج إلى بعض التفاصيل لصياغة {title}:", "pick": "أي مستند تود أن أصيغه؟ يمكنني استخدام أحد هذه القوالب:",
           "revised": "تم. عدّلت «{title}» (الإصدار {v}): {summary}"},
}


# ---- attachments ----

@lru_cache(maxsize=64)
def _attachment_text(att_id: str, name: str, rel_path: str) -> str:
    """Text of one stored attachment (OCR when scanned). Cached because OCR is slow and history re-reads old files."""
    root = Path(settings.attachments_root).resolve()
    path = (root / rel_path.replace("\\", "/")).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(422, f"Attachment file not found on the file server: {name}")
    text, _ = extract_text(name, path.read_bytes())
    return text[:MAX_ATTACHMENT_CHARS]


def _attachments_context(ids: list[str]) -> str:
    found = {a["id"]: a for a in chatdb.attachments(ids)}
    missing = [i for i in ids if i.lower() not in found]
    if missing:
        raise HTTPException(422, f"Unknown attachment id(s): {missing}")
    return "\n\n".join(f"[file: {a['name']}]\n{_attachment_text(a['id'], a['name'], a['path'])}" for a in found.values())


# ---- routing ----

def _active_generation(history: list[dict]) -> dict | None:
    """The document being drafted in this chat: the latest assistant message that carries a generation."""
    for m in reversed(history):
        gid = ((m.get("extra") or {}).get("generation") or {}).get("generation_id")
        if m["role"] == "assistant" and gid:
            return db.get("generations", gid)
    return None


def _intent(history: list[dict], gen: dict | None, content: str) -> str:
    state = None
    if gen:
        state = "finished draft exists" if gen.get("deliverable_id") else "draft in progress, waiting for: " + "; ".join(gen["pending"] or ["template choice"])
    recent = [{"role": m["role"], "content": m["content"][:300]} for m in history[-2:]]
    try:
        r = llm.chat.completions.create(
            model=settings.classifier_model, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": INTENT_PROMPT + " Respond with JSON only."},
                      {"role": "user", "content": json.dumps({"draft_state": state, "recent": recent, "message": content})}])
        intent = json.loads(r.choices[0].message.content).get("intent")
    except Exception:  # noqa: BLE001 - never block a chat on the router
        return "question"
    if intent == "continue" and not (gen and not gen.get("deliverable_id")):
        return "generate"
    if intent == "revise" and not (gen and gen.get("deliverable_id")):
        return "question"
    return intent if intent in ("generate", "continue", "revise") else "question"


# ---- replies ----

def _generation_reply(chat: dict, req: MessageCreate, intent: str, gen: dict | None, new_ids: list[str]) -> dict:
    lang = "ar" if is_arabic(req.message) else "en"
    t = T[lang]
    if intent == "revise":
        d = gen_mod.revise(gen["deliverable_id"], req.message)
        result = {"status": "revised", "generation_id": gen["generation_id"], "deliverable": d}
        answer = t["revised"].format(title=d["title"], v=d["version"], summary=d["versions"][-1]["note"])
    else:
        if intent == "generate":
            gen = gen_mod.create_generation(TENANT, None, None)
        result = gen_mod.step(gen, req.message, None)
        name = (result.get("template") or {}).get("name", "")
        if result["status"] == "needs_template":
            names = "\n".join(f"- {x['name']}" for x in result["available_templates"])
            answer = f"{t['pick']}\n{names}"
        elif result["status"] == "needs_info":
            answer = t["need"].format(title=name) + "\n" + "\n".join(f"{i}. {m['question']}" for i, m in enumerate(result["missing"], 1))
        else:
            d = result["deliverable"]
            answer = t["ready"].format(title=d["title"], v=d["version"])
    # saved in ChatMessages.Extra, so a refresh shows the download links and the next message finds the draft
    extra = {"generation": {"generation_id": result["generation_id"], "status": result["status"]}}
    if d := result.get("deliverable"):
        extra["generation"]["deliverable"] = {k: d[k] for k in ("deliverable_id", "title", "version", "download")}
    chatdb.add_exchange(chat["chat_id"], req.message, new_ids, answer, extra)
    return {"chat_id": chat["chat_id"], "action": "generation", "answer": answer, "generation": result, "disclaimer": DISCLAIMER}


def send_message(chat: dict, req: MessageCreate) -> dict:
    new_ids = [str(i) for i in req.attachment_ids]
    history = chatdb.last_messages(chat["chat_id"], HISTORY_MESSAGES)
    gen = _active_generation(history)
    intent = _intent(history, gen, req.message)
    if intent != "question":
        return _generation_reply(chat, req, intent, gen, new_ids)

    hits = search(TENANT, req.message, limit=TOP_K)
    # sources = [{"n": i, "document_id": h.payload["document_id"], "category": h.payload["category"],
    #             "document_type": h.payload.get("document_type"), "score": round(h.score, 4),
    #             "excerpt": h.payload["text"][:300]} for i, h in enumerate(hits, 1)]
    library = "\n\n".join(f"(document {h.payload['document_id']}, {h.payload.get('document_type')})\n{h.payload['text']}"
                          for h in hits) or "(no matching documents)"
    # files from the last 20 messages plus this one, each file once
    att_ids = list(dict.fromkeys([i for m in history for i in m["attachment_ids"]] + new_ids))
    files = _attachments_context(att_ids) if att_ids else "(none)"
    r = llm.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[{"role": "system", "content": f"{SYSTEM}\n\nSOURCES:\n{library}\n\nATTACHMENTS:\n{files}"},
                  *({"role": m["role"], "content": m["content"]} for m in history),
                  {"role": "user", "content": req.message}],
    )
    answer = r.choices[0].message.content
    chatdb.add_exchange(chat["chat_id"], req.message, new_ids, answer, None)
    return {"chat_id": chat["chat_id"], "action": "answer", "answer": answer, "disclaimer": DISCLAIMER}
