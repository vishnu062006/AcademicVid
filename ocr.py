"""
Handwritten / scanned notes -> plain text, using Gemini's vision (no system libraries,
works on Streamlit Cloud). One Gemini call reads all the pages together.

    transcribe_notes([(bytes, "image/jpeg"), (bytes, "application/pdf"), ...]) -> str

The text is shown to the user to check and correct BEFORE it becomes a lesson,
because handwriting can be misread.
"""
import io
import os

import google.generativeai as genai

from ai_structuring import MODEL_NAME, GEMINI_TIMEOUT_SECONDS

MAX_FILES = 10
MAX_IMAGE_SIDE = 2000        # px; enough for handwriting, keeps uploads and tokens small
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
PDF_TYPE = "application/pdf"

OCR_PROMPT = """You are reading a student's or teacher's notes: handwritten pages, photos of a
notebook or blackboard, or a scanned document. Transcribe ALL the text, page by page, in order.

Rules:
- Write exactly what is written. Do not summarise, explain, correct facts, or add anything.
- Keep the structure: headings on their own line, bullet points as "- ", numbered lists as numbers.
- Keep the original script: Kannada stays in Kannada script, English stays in English.
- Write formulas and equations in plain text, e.g. "H2O", "x^2 + 5x + 6 = 0", "a/b".
- Describe a diagram in one line in square brackets, e.g. [Diagram: parts of a flower].
- If a word cannot be read, write [unclear]. Never guess a whole sentence.
- Separate pages with a line containing only "---".
- Output only the transcription, with no preamble.
"""


def _shrink_image(data: bytes, mime: str):
    """Downscale big phone photos. Returns (bytes, mime); falls back to the original."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)          # phone photos are often stored rotated
        if max(img.size) <= MAX_IMAGE_SIDE and mime in IMAGE_TYPES:
            return data, mime
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        out = io.BytesIO()
        img.convert("RGB").save(out, format="JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return data, mime


def pdf_pages_as_images(pdf_path: str, max_pages: int = 40, dpi: int = 110):
    """Render PDF pages to PNG (bytes, mime) pairs, for PDFs whose text layer is unusable:
    scans, or Kannada typed in an old non-Unicode font (KTBS textbooks)."""
    import fitz
    out = []
    with fitz.open(pdf_path) as doc:
        for i in range(min(doc.page_count, max_pages)):
            out.append((doc[i].get_pixmap(dpi=dpi).tobytes("png"), "image/png"))
    return out


def transcribe_notes(files, timeout: int = GEMINI_TIMEOUT_SECONDS, max_files: int = MAX_FILES) -> str:
    """files: list of (bytes, mime_type). Returns the transcribed text ('' if nothing read)."""
    parts = [OCR_PROMPT]
    for data, mime in files[:max_files]:
        if mime in IMAGE_TYPES:
            data, mime = _shrink_image(data, mime)
        elif mime != PDF_TYPE:
            continue
        parts.append({"mime_type": mime, "data": data})
    if len(parts) == 1:
        return ""

    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(MODEL_NAME, generation_config={"temperature": 0})
    response = model.generate_content(parts, request_options={"timeout": timeout})
    return (response.text or "").strip()
