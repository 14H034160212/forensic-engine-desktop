"""Document parsing: PDF / DOCX / PPTX / TXT -> clean deck text.

Errors a user can act on are raised as ParseError with a plain-language message (shown in the UI next
to the file name). Partial problems (e.g. some PDF pages are images) come back as a warning string.
"""
import io, re, logging, zipfile
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)     # 'invalid pdf header' etc. on bad files

SUPPORTED = "PDF, Word (.docx), PowerPoint (.pptx) or plain text"
_PAGE_MARK = re.compile(r"\[Slide/Page \d+\]")


class ParseError(ValueError):
    """A problem with the user's file, worded for the user."""


def _clean(t):
    t = t.replace("\x00", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _pdf_pages(data):
    """Text per page: pdfplumber (better layout), falling back to pypdf."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [(p.extract_text() or "") for p in pdf.pages]
        if sum(len(p.strip()) for p in pages) > 40:
            return pages
    except Exception:
        pass
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")       # many 'protected' PDFs only restrict editing (empty user pw)
        except Exception:
            ok = 0
        if not ok:
            raise _NeedsPassword()
    return [(p.extract_text() or "") for p in reader.pages]


class _NeedsPassword(Exception):
    pass


def parse_pdf(data: bytes):
    """-> (text, warning)."""
    try:
        pages = _pdf_pages(data)
    except Exception as e:
        if isinstance(e, _NeedsPassword) or "crypt" in str(e).lower() or "password" in str(e).lower():
            raise ParseError("This PDF is password-protected. Remove the password (or print it to a new "
                             "PDF) and upload it again.")
        raise ParseError("This PDF couldn't be read — it may be damaged or incomplete. Try exporting it "
                         "to PDF again, or paste the text instead.")
    if not pages:
        raise ParseError("This PDF has no pages.")
    blank = sum(1 for p in pages if len(p.strip()) < 20)
    if sum(len(p.strip()) for p in pages) < 80:
        raise ParseError("This PDF has no selectable text — it looks like scanned images. Run text "
                         "recognition (OCR) on it first (e.g. Adobe Acrobat's 'Scan & OCR'), or paste the "
                         "text instead.")
    warning = ""
    if blank:
        warning = (f"{blank} of {len(pages)} pages {'has' if blank == 1 else 'have'} no selectable text "
                   "(scanned images?) and " + ("was" if blank == 1 else "were") +
                   " skipped — the analysis only sees the text pages.")
    text = "\n\n".join(f"[Slide/Page {i}]\n{t}" for i, t in enumerate(pages, 1))
    return _clean(text), warning


def parse_docx(data: bytes) -> str:
    import docx
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception:
        raise ParseError("This Word file couldn't be read — it may be damaged. Open it in Word and save "
                         "it again as .docx, or paste the text instead.")
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    # also pull table cells (decks often use tables)
    for tbl in d.tables:
        for row in tbl.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return _clean("\n".join(parts))


def parse_pptx(data: bytes) -> str:
    """Slide text straight from the .pptx XML (a zip) — no extra dependency. Includes speaker notes,
    which in pitch decks often carry the actual claims."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        raise ParseError("This PowerPoint file couldn't be read — it may be damaged. Save it again as "
                         ".pptx or export it to PDF.")
    def num(name):
        m = re.search(r"(\d+)\.xml$", name)
        return int(m.group(1)) if m else 0
    def text_of(xml):
        runs = []
        for para in re.findall(r"<a:p\b.*?</a:p>", xml, re.S):
            t = "".join(re.findall(r"<a:t>([^<]*)</a:t>", para))
            if t.strip():
                runs.append(t)
        import html
        return html.unescape("\n".join(runs))
    slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)), key=num)
    if not slides:
        raise ParseError("This PowerPoint file has no slides.")
    out = []
    for n in slides:
        body = text_of(z.read(n).decode("utf-8", "ignore"))
        note_name = f"ppt/notesSlides/notesSlide{num(n)}.xml"
        notes = text_of(z.read(note_name).decode("utf-8", "ignore")) if note_name in z.namelist() else ""
        out.append(f"[Slide/Page {num(n)}]\n{body}" + (f"\n(Notes: {notes})" if notes.strip() else ""))
    return _clean("\n\n".join(out))


def _looks_like_text(data: bytes) -> bool:
    if b"\x00" in data[:4096]:
        return False
    sample = data[:8192].decode("utf-8", "replace")
    bad = sample.count("�") + sum(1 for c in sample if ord(c) < 32 and c not in "\n\r\t\f")
    return bad <= max(2, len(sample) // 100)


def parse_doc(filename: str, data: bytes):
    """-> (text, warning). Raises ParseError with a user-facing message for unusable files."""
    name = (filename or "").lower()
    if not data or not data.strip():
        raise ParseError("The file is empty.")
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":          # legacy OLE: .doc / .ppt / .xls
        raise ParseError("Old Office formats (.doc, .ppt, .xls) aren't supported. Save the file as "
                         ".docx / .pptx, or export it to PDF, and upload that.")
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return parse_pdf(data)
    if data[:2] == b"PK":                                         # zip container
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except Exception:
            names = []
        if "word/document.xml" in names or name.endswith(".docx"):
            text, warn = parse_docx(data), ""
        elif any(n.startswith("ppt/") for n in names) or name.endswith(".pptx"):
            text, warn = parse_pptx(data), ""
        else:
            raise ParseError(f"This file type isn't supported. Upload a {SUPPORTED} file.")
    elif _looks_like_text(data):
        text, warn = _clean(data.decode("utf-8", "ignore")), ""
    else:
        raise ParseError(f"This file type isn't supported. Upload a {SUPPORTED} file.")
    if len(_PAGE_MARK.sub("", text).strip()) < 20:
        raise ParseError("No readable text was found in this file.")
    return text, warn


def parse(filename: str, data: bytes) -> str:
    """Back-compat: text only (raises ParseError on unusable files)."""
    return parse_doc(filename, data)[0]
