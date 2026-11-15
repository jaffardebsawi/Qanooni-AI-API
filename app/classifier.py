import json

from .clients import llm
from .models import Category
from .settings import settings

PROMPT = f"""You classify legal documents. Return JSON only:
{{"category": one of {[c.value for c in Category]},
 "document_type": short label (e.g. NDA, service agreement, court filing, legal memo, investigation report),
 "parties": [names],
 "dates": [ISO dates found],
 "language": "en" or "ar" etc,
 "confidence": 0..1}}
Category guide: contracts_agreements = contracts, NDAs, templates; cases = litigation, filings, judgments;
representative_help = advice/letters for a client or representative; law_reviews = analysis of laws/regulations;
investigations = internal/compliance investigation material."""


def classify(text: str) -> dict:
    r = llm.chat.completions.create(
        model=settings.classifier_model,
        messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": text[:12000]}],
        response_format={"type": "json_object"},
    )
    result = json.loads(r.choices[0].message.content)
    result["category"] = Category(result["category"]).value
    return result
