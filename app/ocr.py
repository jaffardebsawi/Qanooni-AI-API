"""Client for the NebrasFlow OCR webhook (Azure Document Intelligence), adapted from Dynamic Agent/ocrscript.py."""
import base64

import requests

from .settings import settings


def ocr_file(name: str, data: bytes, timeout: int = 600) -> str:
    body = {"Attachments": [{"Name": name, "StringBase64Content": base64.b64encode(data).decode("ascii"), "BinaryContent": None}]}
    r = requests.post(settings.ocr_url, json=body, timeout=timeout)
    r.raise_for_status()
    return _collect_text(r.json())


def _collect_text(node) -> str:
    """Response shape is undocumented; take known text keys, else join all strings."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(t for t in map(_collect_text, node) if t)
    if isinstance(node, dict):
        for key in ("Content", "content", "Text", "text", "Result", "result"):
            if key in node:
                return _collect_text(node[key])
        return "\n".join(t for t in map(_collect_text, node.values()) if t)
    return ""
