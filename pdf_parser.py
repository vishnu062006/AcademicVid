"""
pdf_parser.py
Replaces PyPDF2 with pdfplumber for cleaner text extraction.
Uses fitz (PyMuPDF) purely for font-size analysis to detect chapter/section
headings, then pdfplumber does the actual text pull per detected block.
"""
import re
import statistics
import fitz  # PyMuPDF
import pdfplumber


HEADER_FOOTER_MARGIN_PT = 50
PAGE_NUM_PATTERN = re.compile(r"^\s*\d{1,4}\s*$")
FIGURE_CAPTION_PATTERN = re.compile(r"^(fig(ure)?\.?\s*\d+)", re.IGNORECASE)
# Catches runs of the same character repeated 3+ times in a row (NCERT's
# fake-bold rendering trick, e.g. "AAAAAccccctttttiiiiivvvvv...")
STACKED_CHAR_PATTERN = re.compile(r"(.)\1{2,}")


def _collapse_stacked_chars(text: str) -> str:
    """
    Turns 'AAAAAccccctttttiiiiivvvvviiiiitttttyyyyy 11111.....11111'
    into 'Activity 1.1' by collapsing any character repeated 3+ times
    in a row down to a single instance. Safe for normal text because
    genuine English words almost never repeat a letter 3+ times in a row.
    """
    return STACKED_CHAR_PATTERN.sub(r"\1", text)


def _is_noise_line(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    if PAGE_NUM_PATTERN.match(text):
        return True
    if FIGURE_CAPTION_PATTERN.match(text):
        return True
    return False


def detect_headings(pdf_path: str, heading_size_ratio: float = 1.15):
    doc = fitz.open(pdf_path)
    all_sizes = []
    spans_by_page = []

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        page_spans = []
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = round(span["size"], 1)
                    text = span["text"].strip()
                    if not text:
                        continue
                    all_sizes.append(size)
                    page_spans.append((_collapse_stacked_chars(text), size, span["bbox"]))
        spans_by_page.append(page_spans)
    doc.close()

    if not all_sizes:
        return []

    body_size = statistics.mode(all_sizes)
    threshold = body_size * heading_size_ratio

    headings = []
    for page_num, page_spans in enumerate(spans_by_page):
        for text, size, bbox in page_spans:
            if size >= threshold and not _is_noise_line(text):
                headings.append((page_num, text, size))
    return headings


def extract_clean_text(pdf_path: str) -> str:
    cleaned_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            height = page.height
            words = page.extract_words()
            lines = {}
            for w in words:
                if w["top"] < HEADER_FOOTER_MARGIN_PT or w["bottom"] > height - HEADER_FOOTER_MARGIN_PT:
                    continue
                line_key = round(w["top"] / 3)
                lines.setdefault(line_key, []).append(w["text"])

            page_lines = []
            for key in sorted(lines.keys()):
                raw_line = " ".join(lines[key]).strip()
                line_text = _collapse_stacked_chars(raw_line)
                # Re-check noise AFTER collapsing — catches page numbers that
                # only look like page numbers once de-duplicated
                if not _is_noise_line(line_text):
                    # A line that's now ONLY a short number even after collapsing
                    # (page numbers sometimes stand alone on their own text line)
                    if PAGE_NUM_PATTERN.match(line_text):
                        continue
                    page_lines.append(line_text)
            cleaned_pages.append("\n".join(page_lines))

    return "\n\n".join(cleaned_pages).strip()


def extract_chapter(pdf_path: str) -> dict:
    return {
        "clean_text": extract_clean_text(pdf_path),
        "headings": detect_headings(pdf_path),
    }