"""Fill template markup and render it as a plain legal document (DOCX and PDF)."""
import re
from pathlib import Path
from xml.sax.saxutils import escape

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from fpdf import FPDF
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

_COND = re.compile(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", re.S)
_LEGAL_SUFFIX = re.compile(r"\s+(plc|ltd|limited|llc|l\.l\.c\.|inc\.?|corp\.?|corporation|co\.?|gmbh|fze|fzco|pjsc)\.?$", re.I)


def short_name(full: str) -> str:
    """'JD Sports Fashion plc' -> 'JD Sports Fashion'."""
    return _LEGAL_SUFFIX.sub("", full.strip()) or full


def with_defaults(fields: dict, spec: list[dict]) -> dict:
    """Apply declared defaults, then derive *_short names from the matching *_name fields."""
    values = {f["key"]: f["default"] for f in spec if f.get("default") is not None}
    values.update({k: v for k, v in fields.items() if v not in (None, "")})
    for key in [k for k in values if k.endswith("_name")]:
        values.setdefault(key[: -len("_name")] + "_short", short_name(values[key]))
    return values


def fill(body: str, values: dict) -> str:
    body = _COND.sub(lambda m: m.group(2) if values.get(m.group(1)) else "", body)
    body = re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m.group(1), "")), body)
    body = re.sub(r"([^()\n]+?) \(\1\)", r"\1", body)  # "John Smith (John Smith)" -> "John Smith"
    return re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"


_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_AR_LETTERS = "أبجدهوزحطي"
FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"


def is_arabic(text: str) -> bool:
    """True when Arabic letters make up the bulk of the alphabetic characters."""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and len(_ARABIC.findall(text)) / len(letters) > 0.4


def structure(body: str, lang: str = "en") -> list[tuple[str, str]]:
    """Markup -> [(kind, text)] with automatic clause numbering."""
    out, n, k, letter = [], 0, 0, 0
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            out.append(("heading_plain", line[4:]))
        elif line.startswith("## "):
            n, k, letter = n + 1, 0, 0
            out.append(("heading", f"{n}. {line[3:]}"))
        elif line.startswith("# "):
            out.append(("title", line[2:]))
        elif line.startswith("- "):
            k, letter = k + 1, 0
            out.append(("para", f"{n}.{k} {line[2:]}"))
        elif line.startswith("* "):
            letter += 1
            mark = _AR_LETTERS[(letter - 1) % len(_AR_LETTERS)] if lang == "ar" else chr(96 + letter)
            out.append(("item", f"({mark}) {line[2:]}"))
        elif line.startswith("@sign "):
            out.append(("sign", line[6:]))
        else:
            out.append(("text", line))
    return out


def _sign_lines(party: str, lang: str = "en") -> list[str]:
    if lang == "ar":
        return [f"وقّع باسم ولصالح {party}", "التوقيع: " + "_" * 36, "المفوّض بالتوقيع",
                "الاسم: " + "_" * 39, "الصفة: " + "_" * 38, "تاريخ التوقيع: " + "_" * 30]
    return [f"Signed for and on behalf of {party}", "Signature: " + "_" * 36, "Authorised signatory",
            "Name: " + "_" * 39, "Title: " + "_" * 38, "Date of signature: " + "_" * 30]


def _rtl_paragraph(p) -> None:
    """Mark a python-docx paragraph right-to-left (alignment then follows the reading direction)."""
    p._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
    for r in p.runs:
        rpr = r._r.get_or_add_rPr()
        rpr.append(OxmlElement("w:rtl"))
        if r.bold:
            rpr.append(OxmlElement("w:bCs"))


def write_docx(body: str, path: Path) -> None:
    lang = "ar" if is_arabic(body) else "en"
    d = docx.Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Inches(1)
    normal = d.styles["Normal"]
    normal.font.name, normal.font.size = "Times New Roman", Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    if lang == "ar":  # complex-script font and size, used for Arabic runs
        rfonts = normal.element.get_or_add_rPr().get_or_add_rFonts()
        rfonts.set(qn("w:cs"), "Arial")
        sz = OxmlElement("w:szCs")
        sz.set(qn("w:val"), "26")
        normal.element.get_or_add_rPr().append(sz)
    for kind, text in structure(body, lang):
        if kind == "title":
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(text).bold = True
            p.runs[0].font.size = Pt(14)
        elif kind in ("heading", "heading_plain"):
            p = d.add_paragraph()
            p.paragraph_format.space_before, p.paragraph_format.keep_with_next = Pt(10), True
            p.add_run(text).bold = True
        elif kind == "item":
            p = d.add_paragraph(text)
            # in a bidi paragraph the "left" indent is applied on the leading (right) side
            p.paragraph_format.left_indent = Inches(0.5)
        elif kind == "sign":
            lines = _sign_lines(text, lang)
            for i, line in enumerate(lines):
                p = d.add_paragraph()
                p.paragraph_format.space_before = Pt(18 if i == 0 else 0)
                p.paragraph_format.keep_with_next = i < len(lines) - 1
                p.add_run(line).bold = i == 0
                if lang == "ar":
                    _rtl_paragraph(p)
            continue
        else:
            p = d.add_paragraph(text)
        if lang == "ar":
            _rtl_paragraph(p)
    d.save(path)


def _write_pdf_rtl(body: str, path: Path) -> None:
    """Arabic PDF: fpdf2 with HarfBuzz shaping (letter joining) and bidi, using the bundled Amiri font."""
    pdf = FPDF(format="A4")
    pdf.set_margins(25.4, 25.4, 25.4)
    pdf.set_auto_page_break(True, 25.4)
    pdf.add_font("Amiri", "", str(FONT_DIR / "Amiri-Regular.ttf"))
    pdf.add_font("Amiri", "B", str(FONT_DIR / "Amiri-Bold.ttf"))
    pdf.set_text_shaping(True, direction="rtl")
    pdf.alias_nb_pages()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    def footer():
        pdf.set_y(-15)
        pdf.set_font("Amiri", "", 10)
        pdf.cell(0, 8, str(pdf.page_no()), align="C")

    pdf.footer = footer
    pdf.add_page()

    def para(text, style="", size=12, align="R", indent=0.0, before=0.0, after=2.0, h=7.0):
        pdf.set_font("Amiri", style, size)
        pdf.ln(before)
        pdf.set_x(pdf.l_margin)  # right edge of the cell sits `indent` in from the right margin
        pdf.multi_cell(width - indent, h, text, align=align, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(after)

    for kind, text in structure(body, "ar"):
        if kind == "title":
            para(text, "B", 16, "C", after=5, h=9)
        elif kind in ("heading", "heading_plain"):
            if pdf.will_page_break(30):
                pdf.add_page()
            para(text, "B", before=3)
        elif kind == "item":
            para(text, indent=12)
        elif kind == "sign":
            lines = _sign_lines(text, "ar")
            if pdf.will_page_break(60):
                pdf.add_page()
            pdf.ln(6)
            for i, line in enumerate(lines):
                para(line, "B" if i == 0 else "", after=0.5)
        else:
            para(text)
    pdf.output(str(path))


def write_pdf(body: str, path: Path) -> None:
    if is_arabic(body):
        return _write_pdf_rtl(body, path)
    base = ParagraphStyle("base", fontName="Times-Roman", fontSize=11, leading=14, spaceAfter=6)
    styles = {
        "title": ParagraphStyle("title", parent=base, fontName="Times-Bold", fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=12),
        "heading": ParagraphStyle("heading", parent=base, fontName="Times-Bold", spaceBefore=8, keepWithNext=1),
        "item": ParagraphStyle("item", parent=base, leftIndent=0.5 * inch),
    }
    styles["heading_plain"] = styles["heading"]
    flow = []
    for kind, text in structure(body):
        if kind == "sign":
            lines = _sign_lines(text)
            block = [Spacer(1, 14), Paragraph(f"<b>{escape(lines[0])}</b>", base)]
            block += [Paragraph(escape(line), ParagraphStyle("s", parent=base, spaceAfter=2)) for line in lines[1:]]
            flow.append(KeepTogether(block))
        else:
            flow.append(Paragraph(escape(text), styles.get(kind, base)))

    def page_number(canvas, doc):
        canvas.setFont("Times-Roman", 10)
        canvas.drawCentredString(A4[0] / 2, 0.5 * inch, str(doc.page))

    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=inch, rightMargin=inch, topMargin=inch,
                      bottomMargin=inch).build(flow, onFirstPage=page_number, onLaterPages=page_number)
