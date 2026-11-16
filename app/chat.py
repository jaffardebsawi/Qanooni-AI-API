from collections.abc import Iterator

from .clients import llm
from .settings import settings
from .store import search

HISTORY_MESSAGES = 20
TOP_K = 6
TENANT = "default"
DISCLAIMER = "This is AI-generated legal information, not legal advice. Have a qualified lawyer review it."

SYSTEM = """You are a legal advisor / legal representative assistant.
Use the SOURCES (the company's document library) when they are relevant.
If they do not contain the answer, say so plainly, then give general guidance clearly marked as general.
Never invent facts, clauses, case numbers or citations. Ask a short clarifying question if the request is ambiguous.
Reply in the user's language."""


def stream_answer(message: str, history: list[dict]) -> Iterator[str]:
    """The AI's answer to `message` given the earlier chat messages, as text pieces. Retrieval and the model call
    start here, so their errors surface before the response begins."""
    # the .NET app may already have saved this very message; do not show it to the model twice
    if history and history[-1] == {"role": "user", "content": message}:
        history = history[:-1]
    hits = search(TENANT, message, limit=TOP_K)
    library = "\n\n".join(f"(document {h.payload['document_id']}, {h.payload.get('document_type')})\n{h.payload['text']}"
                          for h in hits) or "(no matching documents)"
    stream = llm.chat.completions.create(
        model=settings.azure_openai_deployment, stream=True,
        messages=[{"role": "system", "content": f"{SYSTEM}\n\nSOURCES:\n{library}"}, *history, {"role": "user", "content": message}],
    )
    return (c.choices[0].delta.content for c in stream if c.choices and c.choices[0].delta.content)
