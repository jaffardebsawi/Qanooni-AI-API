import io
from pathlib import Path

import docx
from pypdf import PdfReader

from .ocr import ocr_file

MIN_CHARS_PER_PDF = 50
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def extract_text(name: str, data: bytes) -> tuple[str, bool]:
    """Return (text, used_ocr). Native extraction first; OCR for images and text-less PDFs."""
    ext = Path(name).suffix.lower()
    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="replace"), False
    if ext == ".docx":
        d = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs), False
    if ext == ".pdf":
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        if len(text.strip()) >= MIN_CHARS_PER_PDF:
            return text, False
        return ocr_file(name, data), True
    if ext in IMAGE_EXT:
        return ocr_file(name, data), True
    raise ValueError(f"Unsupported file type: {ext}")
