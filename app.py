import html
import os
import shutil
import time
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode
from typing import Optional, Tuple

import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF, already a dependency; used to count PDF pages

from manifest import CHAPTER_MANIFEST
from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from slides import build_section_slides
from tts import synthesize_narration, VOICE_EN, VOICE_KN
from video_builder import build_section_video, concatenate_section_videos
from ppt_export import export_chapter_to_pptx
from transcript_export import export_transcript_pdf
from flashcards import generate_flashcards
from strings import t, LANGUAGE_LABELS


load_dotenv()

BASE_TMP_DIR = "tmp_sessions"
OUTPUT_OPTIONS = {
    "Video": "video",
    "PPT": "ppt",
    "Transcript PDF": "transcript",
    "Flashcards": "flashcards",
}
OUTPUT_CAPTIONS = {
    "Video": "Animated lesson with AI narration",
    "PPT": "Editable presentation deck",
    "Transcript PDF": "Clean, printable study notes",
    "Flashcards": "Quick recall and revision cards",
}
SOURCE_OPTIONS = ["Library", "Upload PDF"]
LANGUAGE_OPTIONS = ["English", "Kannada"]
MAX_PDF_PAGES = 40
SESSION_MAX_AGE_SECONDS = 6 * 60 * 60  # tmp_sessions folders older than this are deleted

# "Report a problem" Google Form (Vishnu creates the form and gives you these).
# How to get them: open the form -> three dots -> "Get pre-filled link" -> type any
# dummy value in the chapter, language and output-type questions -> "Get link".
# The copied link looks like:
#   https://docs.google.com/forms/d/e/<FORM_ID>/viewform?usp=pp_url&entry.123=x&entry.456=y&entry.789=z
# REPORT_FORM_URL is the part before the "?", and each entry.NNN goes in the dict below.
REPORT_FORM_URL = "https://docs.google.com/forms/d/e/PASTE_FORM_ID_HERE/viewform"
REPORT_FORM_ENTRIES = {
    "chapter": "entry.0000000001",   # question: which chapter
    "language": "entry.0000000002",  # question: lesson language
    "output": "entry.0000000003",    # question: output type (Video, PPT, ...)
}

# ---------------------------------------------------------------------
# Session state and filesystem helpers
# ---------------------------------------------------------------------
def init_session_state() -> None:
    defaults = {
        "session_id": str(uuid.uuid4()),
        "app_state": "setup",
        "chapter": None,
        "selected_language": "English",
        "last_generated_type": "video",
        "selected_output_label": "Video",
        "source_mode": "Library",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_session_dir() -> str:
    path = os.path.join(BASE_TMP_DIR, st.session_state.session_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_uploaded_pdf(uploaded_file, session_dir: str) -> str:
    path = os.path.join(session_dir, "input.pdf")
    with open(path, "wb") as file:
        file.write(uploaded_file.getbuffer())
    return path


def reset_pipeline() -> None:
    st.session_state.app_state = "setup"
    st.session_state.chapter = None
    for key in (
        "final_video_path",
        "final_ppt_path",
        "final_transcript_path",
        "final_audio_path",
        "flashcards",
        "last_error",
        "last_error_key",
        "last_error_params",
        "last_error_detail",
        "retry_state",
        "upload_path",
        "upload_name",
    ):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------
# Safety helpers: friendly errors, PDF checks, temp-folder cleanup
# ---------------------------------------------------------------------
class FriendlyError(Exception):
    """An error whose message is a strings.py key, shown to the user in their language."""

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def message(self) -> str:
        return t(self.key, **self.params)


_QUOTA_MARKERS = (
    "resourceexhausted", "resource_exhausted", "quota", "rate limit",
    "rate_limit", "too many requests", "429",
)
_NETWORK_MARKERS = (
    "connectionerror", "connectionrefused", "connecttimeout", "timeouterror",
    "timed out", "timeout", "name resolution", "getaddrinfo",
    "name or service not known", "failed to resolve", "network is unreachable",
    "no route to host", "max retries exceeded", "clientconnectorerror",
    "cannot connect", "serviceunavailable", "deadlineexceeded", "503",
)


def classify_error(exc: BaseException):
    """Map any exception to (strings.py key, params). Never raises."""
    if isinstance(exc, FriendlyError):
        return exc.key, exc.params
    chain = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__
    blob = " ".join(type(e).__name__ for e in chain).lower()
    blob += " " + " ".join(str(e) for e in chain).lower()
    if any(marker in blob for marker in _QUOTA_MARKERS):
        return "err_quota", {}
    if any(marker in blob for marker in _NETWORK_MARKERS):
        return "err_network", {}
    return "err_unexpected", {}


def set_error(exc: BaseException, retry_state: str) -> None:
    """Send the app to the friendly error screen. `retry_state` is where "Try again" goes."""
    key, params = classify_error(exc)
    st.session_state.last_error_key = key
    st.session_state.last_error_params = params
    st.session_state.last_error_detail = (
        "" if isinstance(exc, FriendlyError) else "{}: {}".format(type(exc).__name__, exc)
    )
    st.session_state.retry_state = retry_state
    st.session_state.app_state = "error"


def check_pdf(path: str) -> Optional[FriendlyError]:
    """Return a FriendlyError if the PDF cannot be opened or is too long, else None."""
    try:
        with fitz.open(path) as doc:
            if doc.needs_pass:
                return FriendlyError("err_unreadable_pdf")
            pages = doc.page_count
    except Exception:
        return FriendlyError("err_unreadable_pdf")
    if pages > MAX_PDF_PAGES:
        return FriendlyError("err_too_long", pages=pages, limit=MAX_PDF_PAGES)
    return None


def cleanup_old_sessions() -> None:
    """Delete tmp_sessions/<id> folders untouched for 6+ hours (never the current one).

    Runs once per browser session, so the folder cannot grow forever.
    """
    if st.session_state.get("cleanup_done"):
        return
    st.session_state.cleanup_done = True
    try:
        if not os.path.isdir(BASE_TMP_DIR):
            return
        current = st.session_state.session_id
        now = time.time()
        for name in os.listdir(BASE_TMP_DIR):
            path = os.path.join(BASE_TMP_DIR, name)
            if name == current or not os.path.isdir(path):
                continue
            newest = os.path.getmtime(path)
            for root, _dirs, files in os.walk(path):
                for file_name in files:
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, file_name)))
                    except OSError:
                        pass
            if now - newest > SESSION_MAX_AGE_SECONDS:
                shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass  # cleanup must never break the app


# ---------------------------------------------------------------------
# Premium dark UI
# ---------------------------------------------------------------------
def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Noto+Sans+Kannada:wght@400;500;600;700&display=swap');

        :root {
            --bg: #08090d;
            --surface: #101218;
            --surface-2: #151821;
            --border: rgba(255,255,255,.10);
            --border-hover: rgba(255,255,255,.22);
            --text: #f5f7fb;
            --muted: #9ba3b5;
            --accent: #c5ff4a;
            --accent-soft: rgba(197,255,74,.11);
            --purple: #a78bfa;
        }
        html, body, [class*="css"] {
            font-family: 'DM Sans', 'Noto Sans Kannada', 'Nirmala UI', sans-serif;
        }
        .stApp {
            background:
              radial-gradient(ellipse at 50% -8%, rgba(212,255,58,.035), transparent 34%),
              radial-gradient(ellipse at 80% 0%, rgba(111,76,255,.10), transparent 32%),
              radial-gradient(ellipse at 0% 25%, rgba(197,255,74,.045), transparent 30%),
              var(--bg);
            color: var(--text);
        }
        @keyframes textShine {
            to { background-position: 200% center; }
        }
        @keyframes aiPulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(197,255,74,.10), 0 0 14px rgba(197,255,74,.07);
                border-color: rgba(197,255,74,.45);
            }
            50% {
                box-shadow: 0 0 0 4px rgba(197,255,74,.08), 0 0 28px rgba(197,255,74,.20);
                border-color: rgba(197,255,74,.95);
            }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { right: 1rem; }
        .main .block-container {
            max-width: 1240px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        h1, h2, h3, h4, p, label, li { color: var(--text); }
        h1, h2, h3, .brand-name, .hero-title {
            font-family: 'Space Grotesk', 'Noto Sans Kannada', 'Nirmala UI', sans-serif !important;
            letter-spacing: -.035em;
        }
        p, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: var(--muted);
        }
        [data-testid="stSidebar"] {
            background: rgba(12,14,19,.96);
            border-right: 1px solid var(--border);
            min-width: 300px !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] {
            font-size: .9rem !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            font-size: .9rem !important;
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
        [data-testid="stSidebar"] * { color: var(--text); }
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            font-size: 0.88rem !important;
        }
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] {
            min-width: 0 !important;
        }
        [data-testid="stSidebar"] label {
            color: #c7ccda !important;
            font-weight: 600 !important;
            margin-bottom: 6px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] > label,
        [data-testid="stSidebar"] div[data-testid="stFileUploader"] > label {
            margin-bottom: 6px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stSelectbox"],
        [data-testid="stSidebar"] div[data-testid="stFileUploader"] {
            margin-bottom: 10px !important;
        }
        .brand-lockup {
            display: flex; align-items: center; gap: 12px;
            margin: 4px 0 28px;
        }
        .brand-mark {
            display: flex; align-items: center; justify-content: center;
            width: 42px; height: 42px; border-radius: 13px;
            color: #0b0d0f; background: var(--accent);
            font: 800 20px 'Space Grotesk', 'Noto Sans Kannada', 'Nirmala UI', sans-serif;
            box-shadow: 0 0 28px rgba(197,255,74,.13);
        }
        .brand-name { color: var(--text); font-size: 19px; font-weight: 700; }
        .brand-caption {
            color: var(--muted); font-size: 11px; margin-top: 1px;
            letter-spacing: .12em; text-transform: uppercase;
        }
        .eyebrow {
            color: var(--accent); font-size: 11px; font-weight: 700;
            letter-spacing: .17em; text-transform: uppercase;
            margin-bottom: 14px;
        }
        .hero {
            position: relative; overflow: hidden;
            padding: 38px 40px 36px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            background: linear-gradient(125deg, rgba(22,25,34,.97), rgba(13,15,21,.92));
            margin-bottom: 30px;
        }
        .hero:after {
            content: ''; position: absolute; width: 240px; height: 240px;
            right: -70px; top: -120px; border-radius: 50%;
            background: rgba(197,255,74,.09); filter: blur(35px);
            pointer-events: none;
        }
        .hero-title {
            color: var(--text); font-size: clamp(2.2rem, 5vw, 4rem);
            line-height: 1.04; font-weight: 700; max-width: 760px;
            margin: 0 0 16px;
        }
        .gradient-text {
            background: linear-gradient(90deg, #c5ff4a 0%, #a7f3d0 45%, #b7a4ff 100%);
            background-size: 200% auto;
            -webkit-background-clip: text; background-clip: text;
            color: transparent;
            animation: textShine 7s linear infinite;
        }
        .hero-subtitle {
            color: #a8afbf; font-size: 15px; line-height: 1.75;
            max-width: 720px; margin: 0;
        }
        .learning-promise {
            display: flex; flex-wrap: wrap; gap: 9px; margin-top: 20px;
        }
        .learning-promise span {
            display: inline-flex; align-items: center; gap: 7px;
            color: #d8deea; font-size: 12px;
            background: rgba(255,255,255,.035);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 10px; padding: 9px 12px;
        }
        .learning-promise b { color: var(--accent); font-weight: 700; }
        .hero-meta {
            display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px;
        }
        .meta-pill {
            color: #747c8d; font-size: 11px; letter-spacing: .04em;
            border: 1px solid rgba(255,255,255,.055); background: rgba(255,255,255,.018);
            padding: 7px 11px; border-radius: 99px;
        }
        .meta-pill.active {
            color: var(--accent);
            border-color: rgba(197,255,74,.42);
            background: rgba(197,255,74,.075);
            box-shadow: 0 0 18px rgba(197,255,74,.045);
        }
        /* Keep the setup workflow centered and readable on wide displays. */
        div[data-testid="stMainBlockContainer"] {
            max-width: 1120px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
        .setup-content {
            max-width: 840px;
            width: 100%;
            margin: 0 auto;
        }
        .section-heading {
            color: var(--text); font-family: 'Space Grotesk', 'Noto Sans Kannada', 'Nirmala UI', sans-serif;
            font-size: 21px; font-weight: 700; letter-spacing: -.025em;
            margin: 6px 0 5px;
        }
        .section-description { color: var(--muted); font-size: 13px; margin-bottom: 17px; }
        .format-card-caption {
            min-height: 42px;
            margin: 8px 2px 18px;
            color: #9CA3AF;
            font-size: 13px;
            font-weight: 400;
            line-height: 1.5;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stButton"] > button {
            min-height: 78px;
            padding: 18px 20px !important;
            text-align: left !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            border-radius: 16px !important;
            transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stButton"] > button:hover {
            transform: translateY(-3px);
            border-color: rgba(212,255,58,.55) !important;
            box-shadow: 0 10px 24px -12px rgba(212,255,58,.22) !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stButton"] > button[kind="primary"] {
            background: rgba(197,255,74,.12) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--accent) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.12), 0 8px 24px rgba(197,255,74,.06) !important;
        }
        .step-label {
            color: var(--accent); font-size: 10px; font-weight: 700;
            letter-spacing: .16em; text-transform: uppercase; margin-bottom: 8px;
        }
        .panel {
            background: rgba(16,18,24,.84); border: 1px solid var(--border);
            border-radius: 18px; padding: 22px; margin: 12px 0 22px;
        }
        .chapter-card {
            background: rgba(16,18,24,.84); border: 1px solid var(--border);
            border-radius: 16px; padding: 18px 20px; margin: 12px 0 20px;
        }
        .chapter-card {
            min-height: 150px;
            padding: 24px 26px;
            margin: 12px 0 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .chapter-card .chip-row { margin-bottom: 16px; }
        .chapter-title { overflow-wrap: anywhere; line-height: 1.35; }
        .chapter-hint {
            color: #9CA3AF; font-size: 13px; line-height: 1.55; margin-top: 9px;
        }
        .action-panel {
            min-height: 150px;
            display: flex; flex-direction: column; justify-content: center;
            padding: 22px 24px;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(197,255,74,.055), rgba(167,139,250,.035));
            margin: 12px 0 12px;
        }
        .action-kicker {
            color: var(--accent); font-size: 10px; font-weight: 700;
            letter-spacing: .16em; margin-bottom: 9px;
        }
        .action-title {
            color: var(--text); font: 600 18px 'Space Grotesk', 'Noto Sans Kannada', 'Nirmala UI', sans-serif;
            line-height: 1.3; margin-bottom: 7px;
        }
        .action-copy { color: #9CA3AF; font-size: 13px; line-height: 1.55; }
        @media (max-width: 760px) {
            .chapter-card, .action-panel { min-height: 0; }
        }
        .chip-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 16px; }
        .chip {
            padding: 5px 9px; border-radius: 99px; font-size: 10px;
            font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
            color: #c4cbd8; background: rgba(255,255,255,.055);
            border: 1px solid var(--border);
        }
        .chip-accent {
            color: #D4FF3A !important;
            background: rgba(212,255,58,.10) !important;
            border-color: rgba(212,255,58,.55) !important;
        }
        .chapter-title {
            color: var(--text); font: 700 18px 'Space Grotesk', 'Noto Sans Kannada', 'Nirmala UI', sans-serif;
            line-height: 1.4; margin-top: 2px;
        }
        div[data-testid="stRadio"] > label,
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stFileUploader"] label {
            color: #dce1ec !important; font-weight: 600 !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] { gap: 10px; }

        /* Output-format cards: clean, balanced 2 × 2 grid. */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 14px !important;
            width: 100% !important;
            align-items: stretch !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            width: 100% !important;
            min-width: 0 !important;
            min-height: 108px !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 22px 24px !important;
            display: flex !important;
            align-items: center !important;
            border-radius: 16px !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            position: relative !important;
            transition: transform .3s cubic-bezier(.4,0,.2,1),
                        box-shadow .3s cubic-bezier(.4,0,.2,1),
                        border-color .3s ease,
                        background .3s ease !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            transform: translateY(-4px) scale(1.01) !important;
            border-color: rgba(212,255,58,.5) !important;
            box-shadow: 0 12px 24px -10px rgba(212,255,58,.15) !important;
            z-index: 2;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:last-child {
            min-width: 0 !important;
            width: 100% !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label p {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
                grid-template-columns: minmax(0, 1fr) !important;
            }
            [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
                min-height: 88px !important;
                padding: 18px 20px !important;
            }
        }
        /* Four output formats: balanced, centered 2 x 2 card grid. */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"]:has(input) div[role="radiogroup"] {
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 14px !important;
            max-width: 840px !important;
            margin: 0 auto !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            box-sizing: border-box !important;
            width: 100% !important;
            min-height: 118px !important;
            padding: 22px 24px !important;
            justify-content: flex-start !important;
            align-items: flex-start !important;
            border-radius: 16px !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stMarkdownContainer"] {
            width: 100% !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label p {
            color: #FFFFFF !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
            line-height: 1.35 !important;
            margin: 0 !important;
            white-space: normal !important;
        }
        /* Title is the radio label text; subtitle is a separate generated element.
           This avoids relying on Streamlit's Markdown newline parsing. */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label
        [data-testid="stMarkdownContainer"] p {
            color: #FFFFFF !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            line-height: 1.35 !important;
            margin: 0 !important;
            white-space: normal !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label
        [data-testid="stMarkdownContainer"]::after {
            display: block !important;
            margin-top: 7px !important;
            color: #9CA3AF !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            line-height: 1.45 !important;
            white-space: normal !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(1)
        [data-testid="stMarkdownContainer"]::after { content: "Animated lesson with AI narration"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(2)
        [data-testid="stMarkdownContainer"]::after { content: "Editable presentation deck"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(3)
        [data-testid="stMarkdownContainer"]::after { content: "Clean, printable study notes"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(4)
        [data-testid="stMarkdownContainer"]::after { content: "Quick recall and revision cards"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            border-color: #D4FF3A !important;
            background: rgba(197,255,74,.075) !important;
            box-shadow: 0 0 0 1px rgba(212,255,58,.2), 0 10px 30px rgba(197,255,74,.06) !important;
        }
        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
                grid-template-columns: minmax(0, 1fr) !important;
            }
        }
        /* Sidebar source selector: connected two-part segmented control. */
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 0 !important;
            width: 100% !important;
            padding: 4px !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            background: #0c0e13 !important;
            overflow: hidden !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            flex: 1 1 50% !important;
            width: 50% !important;
            min-width: 0 !important;
            min-height: 38px !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            padding: 8px 6px !important;
            margin: 0 !important;
            border: 0 !important;
            border-radius: 8px !important;
            background: transparent !important;
            box-shadow: none !important;
            transform: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            background: var(--accent-soft) !important;
            box-shadow: inset 0 0 0 1px rgba(197,255,74,.35) !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label p {
            font-size: 12px !important;
            font-weight: 600 !important;
            text-align: center !important;
            white-space: nowrap !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label {
            border: 1px solid var(--border) !important;
            background: rgba(255,255,255,.025) !important;
            border-radius: 14px !important; padding: 22px 24px !important;
            transition: border .18s ease, background .18s ease, transform .18s ease;
            min-height: 92px;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            border-color: var(--border-hover) !important;
            transform: translateY(-1px);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            border-color: var(--accent) !important;
            background: var(--accent-soft) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.14), 0 8px 28px rgba(197,255,74,.035);
        }
        /* Hide Streamlit's native radio indicator; the card itself shows selection. */
        div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {
            display: none !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            gap: 0 !important;
            align-items: flex-start !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
            color: var(--text) !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            line-height: 1.35 !important;
            margin: 0 !important;
            white-space: pre-line !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.14), 0 8px 28px rgba(197,255,74,.06) !important;
        }
        /* Subtitle is rendered as the second line in each output card. */
        div[data-testid="stRadio"] div[role="radiogroup"] label p span {
            display: block !important;
            color: #9CA3AF !important;
            font-size: .85rem !important;
            font-weight: 400 !important;
            margin-top: 5px !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
            color: var(--text) !important;
        }
        div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
        div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
            background: #11141b !important; color: var(--text) !important;
            border: 1px solid var(--border) !important; border-radius: 11px !important;
        }
        div[data-baseweb="select"] > div:hover, div[data-baseweb="input"] > div:focus-within,
        div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus {
            border-color: rgba(197,255,74,.6) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.12) !important;
        }
        [data-testid="stFileUploader"] section {
            background: rgba(255,255,255,.025) !important;
            border: 1px dashed rgba(255,255,255,.2) !important; border-radius: 13px !important;
        }
        [data-testid="stFileUploader"] section * { color: #cbd1df !important; }
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
            border: 1px solid transparent !important; border-radius: 11px !important;
            min-height: 46px; font-weight: 700 !important;
            transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: var(--accent) !important; color: #000000 !important;
            font-weight: 700 !important;
            box-shadow: 0 5px 22px rgba(197,255,74,.11) !important;
        }
        .stButton > button[kind="primary"] *,
        .stFormSubmitButton > button[kind="primary"] *,
        .stButton > button[kind="primary"]:disabled,
        .stFormSubmitButton > button[kind="primary"]:disabled {
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
            background: #d4ff79 !important; transform: translateY(-1px);
            box-shadow: 0 8px 28px rgba(197,255,74,.18) !important;
        }
        .stButton > button[kind="secondary"] {
            background: #171a22 !important; color: var(--text) !important;
            border-color: var(--border) !important;
        }
        .stButton > button:focus { box-shadow: 0 0 0 2px rgba(197,255,74,.3) !important; }
        /* During AI work, Streamlit displays an active status/progress region. */
        [data-testid="stStatusWidget"][data-state="running"] ~ * .stButton > button[kind="primary"],
        [data-testid="stStatusWidget"][data-state="running"] .stButton > button[kind="primary"] {
            animation: aiPulse 1.35s ease-in-out infinite !important;
        }
        .stButton > button[kind="primary"]:active {
            transform: translateY(1px) scale(.995) !important;
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        [data-testid="stExpander"] {
            background: rgba(255,255,255,.025); border: 1px solid var(--border);
            border-radius: 12px;
        }
        [data-testid="stProgressBar"] > div > div { background: var(--accent) !important; }
        hr { border-color: var(--border) !important; }
        .footer {
            color: #6f7789; font-size: 11px; text-align: center;
            margin-top: 44px; padding-top: 20px; border-top: 1px solid var(--border);
        }
        @media (max-width: 700px) {
            .main .block-container { padding: 1rem 1rem 3rem; }
            .hero { padding: 26px 22px; border-radius: 18px; }
            .hero-title { font-size: 2.25rem; }
            div[data-testid="stRadio"] div[role="radiogroup"] { flex-direction: column; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_language_css() -> None:
    """Apply language-specific styling."""
    css = """
    <style>
    .field-label {
        color: #c7ccda;
        font-size: .85rem;
        font-weight: 600;
        margin: 12px 0 6px;
    }

    [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor) {
        flex-wrap: nowrap !important;
        max-width: 360px;
        gap: 8px !important;
        margin: 0 0 14px;
    }

    [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor)
    > div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }

    .hero-subtitle, .learning-promise span, .meta-pill,
    .section-heading, .section-description, .chapter-title,
    .chapter-hint, .format-card-caption, .action-copy, .field-label {
        overflow-wrap: anywhere;
        max-width: 100%;
    }

    .stButton > button, .stDownloadButton > button {
        height: auto !important;
        white-space: normal !important;
    }

    .stButton > button p, .stDownloadButton > button p {
        white-space: normal !important;
    }
    """

    if st.session_state.get("selected_language") == "Kannada":
        css += """
        h1, h2, h3, .brand-name, .hero-title, .section-heading,
        .chapter-title, .action-title, .eyebrow, .step-label,
        .brand-caption, .action-kicker, .chip {
            letter-spacing: 0 !important;
        }

        .hero-title {
            font-size: clamp(1.8rem, 6.5vw, 3rem) !important;
            line-height: 1.3 !important;
        }

        .hero-subtitle, .section-description, .chapter-hint,
        .action-copy, .format-card-caption {
            line-height: 1.8 !important;
        }
        """

    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

def render_language_toggle() -> None:
    """English | ಕನ್ನಡ toggle at the top of the main page."""
    current = st.session_state.get("selected_language", "English")
    cols = st.columns(2, gap="small")
    for col, language in zip(cols, LANGUAGE_OPTIONS):
        with col:
            if st.button(
                LANGUAGE_LABELS[language],
                key=f"lang_btn_{language}",
                type="primary" if current == language else "secondary",
                use_container_width=True,
            ):
                if current != language:
                    st.session_state.selected_language = language
                    st.rerun()
    with cols[1]:
        # Invisible marker so the CSS above can find this row of buttons.
        st.markdown('<span class="lang-anchor"></span>', unsafe_allow_html=True)


def render_brand_and_hero() -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">{t("hero_eyebrow")}</div>
          <div class="hero-title">{t("hero_title_1")}<br><span class="gradient-text">{t("hero_title_2")}</span></div>
          <p class="hero-subtitle">{t("hero_subtitle")}</p>
          <div class="learning-promise">
            <span><b>✓</b> {t("promise_1")}</span>
            <span><b>✦</b> {t("promise_2")}</span>
            <span><b>{t("promise_3_badge")}</b> {t("promise_3")}</span>
          </div>
          <div class="hero-meta">
            <span class="meta-pill active">{t("pill_1")}</span>
            <span class="meta-pill">{t("pill_2")}</span>
            <span class="meta-pill">{t("pill_3")}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_brand() -> None:
    st.markdown(
        f"""
        <div class="brand-lockup">
          <div class="brand-mark">A</div>
          <div>
            <div class="brand-name">AcademicVid</div>
            <div class="brand-caption">{t("brand_caption")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_mobile_css() -> None:
    """Phone-friendly layout: big tap targets, one column, no sideways scrolling."""
    st.markdown(
        """
        <style>
        /* Two-button rows (language, source) stay side by side even at 360px. */
        [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.src-anchor) {
            flex-wrap: nowrap !important; gap: 8px !important; margin: 0 0 14px;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.src-anchor)
        > div[data-testid="column"] {
            min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor)
        div[data-testid="stButton"] > button,
        [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.src-anchor)
        div[data-testid="stButton"] > button {
            min-height: 48px !important; padding: 8px 14px !important;
            justify-content: center !important; text-align: center !important;
            font-size: 15px !important;
        }
        /* Pickers and uploader: at least ~48px tall; 16px text avoids iOS zoom-on-focus. */
        [data-testid="stMainBlockContainer"] div[data-baseweb="select"] > div {
            min-height: 48px !important; font-size: 16px !important;
        }
        ul[role="listbox"] li { min-height: 44px; display: flex; align-items: center; }
        [data-testid="stFileUploader"] section { padding: 18px !important; }
        [data-testid="stFileUploader"] button { min-height: 48px !important; }
        .stDownloadButton > button, .stFormSubmitButton > button { min-height: 48px !important; }
        .brand-lockup { margin-bottom: 16px; }
        [data-testid="stMainBlockContainer"] img,
        [data-testid="stMainBlockContainer"] video,
        [data-testid="stMainBlockContainer"] audio { max-width: 100%; }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] {
                padding-left: 1rem !important; padding-right: 1rem !important;
                overflow-x: hidden;
            }
            .hero { padding: 20px 18px !important; margin-bottom: 20px; }
            .hero-title { font-size: 1.9rem !important; }
            .hero-subtitle { font-size: 14px; }
            .hero-meta, .learning-promise { display: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _field_label(text: str) -> None:
    st.markdown(f'<div class="field-label">{text}</div>', unsafe_allow_html=True)


def _index_of(options, value) -> int:
    return options.index(value) if value in options else 0


def render_source_picker() -> None:
    """Chapter picker + PDF upload on the main page (phones hide the sidebar).

    Streamlit 1.31 deletes a widget's state when it is not drawn, and this picker is only
    drawn on the first screen. So every choice is also stored in plain session keys
    (pick_class, pick_subject, pick_chapter, upload_path, upload_name); get_selection()
    reads those on every screen. Widgets keep a fixed English label + key + collapsed
    label, and we draw the translated label, so switching language never resets them.
    """
    cols = st.columns(2, gap="small")
    for col, mode, label_key in zip(cols, SOURCE_OPTIONS, ("source_library", "source_upload")):
        with col:
            if st.button(
                t(label_key),
                key=f"source_btn_{mode}",
                type="primary" if st.session_state.source_mode == mode else "secondary",
                use_container_width=True,
            ):
                if st.session_state.source_mode != mode:
                    st.session_state.source_mode = mode
                    st.rerun()
    with cols[1]:
        # Invisible marker so the CSS can find this row of buttons.
        st.markdown('<span class="src-anchor"></span>', unsafe_allow_html=True)

    if st.session_state.source_mode == "Library":
        classes = list(CHAPTER_MANIFEST.keys())
        if not classes:
            st.warning(t("lib_empty"))
            return
        prev_subject = st.session_state.get("pick_subject")
        prev_chapter = st.session_state.get("pick_chapter")
        st.session_state.pick_subject = None
        st.session_state.pick_chapter = None

        _field_label(t("lib_class"))
        selected_class = st.selectbox(
            "Class / grade", classes,
            index=_index_of(classes, st.session_state.get("pick_class")),
            key="sel_class", label_visibility="collapsed",
        )
        st.session_state.pick_class = selected_class

        subjects = list(CHAPTER_MANIFEST.get(selected_class, {}).keys())
        if not subjects:
            st.info(t("lib_no_subjects"))
            return
        _field_label(t("lib_subject"))
        selected_subject = st.selectbox(
            "Subject", subjects,
            index=_index_of(subjects, prev_subject),
            key="sel_subject", label_visibility="collapsed",
        )
        st.session_state.pick_subject = selected_subject

        chapters = list(CHAPTER_MANIFEST[selected_class].get(selected_subject, {}).keys())
        if not chapters:
            st.info(t("lib_no_chapters"))
            return
        _field_label(t("lib_chapter"))
        selected_chapter = st.selectbox(
            "Chapter", chapters,
            index=_index_of(chapters, prev_chapter),
            key="sel_chapter", label_visibility="collapsed",
        )
        st.session_state.pick_chapter = selected_chapter
    else:
        _field_label(t("upload_label"))
        uploaded_file = st.file_uploader(
            "Chapter PDF", type=["pdf"], key="pdf_upload", label_visibility="collapsed"
        )
        # Streamlit's own "Drag and drop file here" text stays English in 1.31.1,
        # so explain it in the selected language right next to the uploader.
        st.caption(t("upload_hint"))
        if uploaded_file is not None:
            saved_path = save_uploaded_pdf(uploaded_file, get_session_dir())
            problem = check_pdf(saved_path)
            if problem is None:
                st.session_state.upload_path = saved_path
                st.session_state.upload_name = uploaded_file.name
            else:
                st.error(problem.message())
                st.session_state.pop("upload_path", None)
                st.session_state.pop("upload_name", None)
                try:
                    os.remove(saved_path)
                except OSError:
                    pass
        if st.session_state.get("upload_name"):
            st.caption(t("upload_selected", name=st.session_state.upload_name))


def get_selection():
    """Return (source, pdf_path, class, subject, chapter, upload_name) from stored picks."""
    source = st.session_state.source_mode
    if source == "Library":
        cls = st.session_state.get("pick_class")
        subject = st.session_state.get("pick_subject")
        chapter = st.session_state.get("pick_chapter")
        try:
            path = CHAPTER_MANIFEST[cls][subject][chapter]
        except (KeyError, TypeError):
            path = None
        return source, path, cls, subject, chapter, None
    path = st.session_state.get("upload_path")
    if path and not os.path.exists(path):
        path = None
    return source, path, None, None, None, st.session_state.get("upload_name")


# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------
def execute_ai_structuring(pdf_path: str, language: str) -> None:
    try:
        with st.status(t("status_analyzing"), expanded=True) as status:
            status.write(t("status_extract"))
            extracted = extract_chapter(pdf_path)
            clean_text = extracted.get("clean_text", "")
            if not clean_text.strip():
                raise FriendlyError("err_no_text")
            status.write(t("status_structure"))
            chapter = structure_chapter(clean_text, language=language)
            if not getattr(chapter, "sections", None):
                raise FriendlyError("err_no_sections")
            st.session_state.chapter = chapter
            st.session_state.lesson_language = language
            # Keep the experience one-click: prepare the lesson, then generate
            # the selected resource without asking the learner to approve a script.
            if st.session_state.get("review_enabled"):
                st.session_state.app_state = "review"
                status.update(label=t("status_lesson_review"), state="complete")
            else:
                st.session_state.app_state = "generating_media"
                status.update(label=t("status_lesson_ready"), state="complete")
    except Exception as exc:
        set_error(exc, retry_state="choose_output")


SUBJECT_OPTIONS = ["Science", "Math", "Social Science", "English", "Other"]


def _review_label(key: str) -> None:
    st.markdown(f'<div class="field-label">{t(key)}</div>', unsafe_allow_html=True)


def _chapter_is_valid(chapter) -> bool:
    """Re-run the Pydantic checks on the edited chapter (works with v1 and v2)."""
    try:
        cls = type(chapter)
        data = chapter.model_dump() if hasattr(chapter, "model_dump") else chapter.dict()
        if hasattr(cls, "model_validate"):
            cls.model_validate(data)
        else:
            cls.parse_obj(data)
        return True
    except Exception:
        return False


def render_review_ui(output_type: str) -> None:
    chapter = st.session_state.chapter
    if chapter is None:
        st.error(t("review_no_chapter"))
        if st.button(t("review_back"), type="primary"):
            reset_pipeline()
            st.rerun()
        return

    st.markdown(f'<div class="step-label">{t("review_step")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-heading">{t("review_heading")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-description">{t("review_desc")}</div>', unsafe_allow_html=True)
    st.info(t("review_info"))

    # Widgets use a fixed label + key + collapsed label, and we draw the translated label,
    # so switching language never wipes what the teacher has typed (Streamlit 1.31 resets
    # a widget whose label changes). Edits are applied to the chapter only on submit.
    with st.form("review_form"):
        _review_label("review_chapter_title")
        chapter_title = st.text_input(
            "chapter_title",
            value=str(getattr(chapter, "chapter_title", "") or ""),
            key="rv_chapter_title",
            label_visibility="collapsed",
        )
        subjects = list(SUBJECT_OPTIONS)
        current_subject = str(getattr(chapter, "subject", "") or "Other")
        if current_subject not in subjects:
            subjects.append(current_subject)
        _review_label("review_subject")
        chapter_subject = st.selectbox(
            "subject",
            subjects,
            index=subjects.index(current_subject),
            key="rv_subject",
            label_visibility="collapsed",
        )
        st.markdown("---")

        edits = []
        for i, section in enumerate(chapter.sections):
            with st.expander(f"{t('review_section')} {i + 1}  ·  {section.title}", expanded=(i == 0)):
                _review_label("review_section_title")
                title = st.text_input(
                    "section_title", value=section.title, key=f"title_{i}", label_visibility="collapsed"
                )
                left, right = st.columns(2)
                with left:
                    _review_label("review_hook")
                    hook = st.text_area(
                        "hook", value=section.hook, height=100, key=f"hook_{i}", label_visibility="collapsed"
                    )
                    _review_label("review_misconception")
                    misconception = st.text_area(
                        "misconception", value=section.misconception, height=110, key=f"misc_{i}",
                        label_visibility="collapsed",
                    )
                with right:
                    _review_label("review_concept")
                    concept = st.text_area(
                        "concept", value=section.concept, height=100, key=f"concept_{i}",
                        label_visibility="collapsed",
                    )
                    _review_label("review_example")
                    indian_example = st.text_area(
                        "example", value=section.indian_example, height=110, key=f"ex_{i}",
                        label_visibility="collapsed",
                    )
                _review_label("review_key_points")
                key_points_text = st.text_area(
                    "key_points", value="\n".join(section.key_points), height=120, key=f"kps_{i}",
                    label_visibility="collapsed",
                )
                _review_label("review_narration")
                narration = st.text_area(
                    "narration", value=section.narration, height=160, key=f"narration_{i}",
                    label_visibility="collapsed",
                )
            edits.append(
                {
                    "title": title,
                    "hook": hook,
                    "misconception": misconception,
                    "concept": concept,
                    "indian_example": indian_example,
                    "key_points": [line.strip() for line in key_points_text.splitlines() if line.strip()],
                    "narration": narration,
                }
            )

        st.markdown("---")
        left, right = st.columns([3, 1])
        with left:
            submitted = st.form_submit_button(
                t("review_continue", format=t(f"format_{output_type}")),
                type="primary",
                use_container_width=True,
            )
        with right:
            cancelled = st.form_submit_button(t("review_cancel"), use_container_width=True)

    if submitted:
        try:
            for section, edit in zip(chapter.sections, edits):
                for field, value in edit.items():
                    setattr(section, field, value)
            chapter.chapter_title = chapter_title
            chapter.subject = chapter_subject
            valid = _chapter_is_valid(chapter)
        except Exception:
            valid = False
        if not valid:
            st.error(t("review_invalid"))
            return
        # Every output (video, PPT, notes PDF, flashcards) reads this same edited object.
        st.session_state.chapter = chapter
        st.session_state.app_state = "generating_media"
        st.rerun()
    if cancelled:
        reset_pipeline()
        st.rerun()


def execute_media_generation(output_type: str, session_dir: str) -> None:
    chapter = st.session_state.chapter
    if chapter is None:
        st.error(t("err_no_chapter"))
        reset_pipeline()
        return

    selected_language = st.session_state.get("selected_language", "English")
    narration_voice = VOICE_KN if selected_language == "Kannada" else VOICE_EN
    language_name = t(f"lang_name_{selected_language}")

    try:
        with st.status(t("status_building"), expanded=True) as status:
            if output_type == "video":
                section_video_paths = []
                total = len(chapter.sections)

                for i, section in enumerate(chapter.sections):
                    section_dir = os.path.join(session_dir, f"section_{i}")
                    slide_dir = os.path.join(section_dir, "slides")
                    os.makedirs(section_dir, exist_ok=True)

                    status.write(t("status_slides", i=i + 1, n=total))
                    slide_paths = build_section_slides(
                        section,
                        chapter.subject,
                        slide_dir,
                        language=selected_language,
                        chapter_title=chapter.chapter_title,
                    )

                    status.write(t("status_narration", i=i + 1, n=total))
                    audio_path = os.path.join(section_dir, "narration.mp3")
                    synthesize_narration(
                        section.narration,
                        audio_path,
                        voice=narration_voice,
                    )

                    status.write(t("status_assembling", i=i + 1, n=total))
                    video_path = os.path.join(section_dir, "video.mp4")
                    build_section_video(slide_paths, audio_path, video_path)
                    section_video_paths.append(video_path)

                final_path = os.path.join(session_dir, "final_output.mp4")
                status.write(t("status_combining"))
                concatenate_section_videos(section_video_paths, final_path)
                st.session_state.final_video_path = final_path

            elif output_type == "ppt":
                status.write(t("status_ppt"))
                path = os.path.join(session_dir, "chapter.pptx")
                export_chapter_to_pptx(
                    chapter,
                    path,
                    language=selected_language,
                )
                st.session_state.final_ppt_path = path

                # Generate a separate narration MP3 alongside the PPT.
                # A narration failure must not invalidate the presentation.
                narration_text = "\n\n".join(
                    narration
                    for section in chapter.sections
                    if (
                        narration := str(
                            getattr(section, "narration", "") or ""
                        ).strip()
                    )
                )

                if narration_text:
                    status.write(t("status_audio", language=language_name))
                    audio_path = os.path.join(
                        session_dir, "chapter_narration.mp3"
                    )

                    try:
                        synthesize_narration(
                            narration_text,
                            audio_path,
                            voice=narration_voice,
                        )
                        st.session_state.final_audio_path = audio_path
                    except Exception as audio_exc:
                        st.session_state.pop("final_audio_path", None)
                        audio_key, audio_params = classify_error(audio_exc)
                        status.write(t("ppt_audio_failed", error=t(audio_key, **audio_params)))
                else:
                    st.session_state.pop("final_audio_path", None)

            elif output_type == "transcript":
                status.write(t("status_notes"))
                path = os.path.join(session_dir, "transcript.pdf")
                export_transcript_pdf(
                    chapter,
                    path,
                    language=selected_language,
                )
                st.session_state.final_transcript_path = path

            elif output_type == "flashcards":
                status.write(t("status_flashcards"))
                st.session_state.flashcards = generate_flashcards(
                    chapter,
                    language=selected_language,
                )

            status.update(label=t("status_ready"), state="complete")
            st.session_state.app_state = "complete"

    except Exception as exc:
        set_error(exc, retry_state="generating_media")


def report_form_is_set_up() -> bool:
    return "PASTE_FORM_ID_HERE" not in REPORT_FORM_URL


def build_report_url(chapter_label: str, language: str, output_label: str) -> str:
    """Pre-filled Google Form link. Values are URL-encoded; nothing is stored by the app."""
    values = {
        REPORT_FORM_ENTRIES["chapter"]: chapter_label,
        REPORT_FORM_ENTRIES["language"]: language,
        REPORT_FORM_ENTRIES["output"]: output_label,
    }
    return REPORT_FORM_URL + "?usp=pp_url&" + urlencode(values, quote_via=quote)


def render_report_button(output_type: str) -> None:
    """'Report a problem with this lesson': opens the pre-filled form in a new tab."""
    source, _path, selected_class, selected_subject, selected_chapter, upload_name = get_selection()
    if source == "Library":
        chapter_label = " / ".join(x for x in (selected_class, selected_subject, selected_chapter) if x)
    else:
        chapter_label = "Uploaded PDF: " + (upload_name or "")
    # The language the lesson was actually made in (the UI language may have changed since).
    language = st.session_state.get("lesson_language", st.session_state.get("selected_language", "English"))
    output_label = next((label for label, oid in OUTPUT_OPTIONS.items() if oid == output_type), output_type)

    if not report_form_is_set_up():
        st.button(
            t("report_button"),
            disabled=True,
            help=t("report_not_ready"),
            use_container_width=True,
            key="report_disabled",
        )
        return

    url = html.escape(build_report_url(chapter_label, language, output_label), quote=True)
    st.markdown(
        """
        <style>
        a.report-link {
            display: block; box-sizing: border-box; width: 100%; text-align: center;
            min-height: 48px; padding: 13px 16px; margin: 8px 0 12px;
            border: 1px solid var(--border); border-radius: 11px;
            background: #171a22; color: var(--text) !important;
            font-weight: 700; text-decoration: none !important;
            overflow-wrap: anywhere;
        }
        a.report-link:hover { border-color: rgba(212,255,58,.55); }
        </style>
        """
        f'<a class="report-link" href="{url}" target="_blank" rel="noopener noreferrer">'
        f'⚑&nbsp; {t("report_button")}</a>',
        unsafe_allow_html=True,
    )


def render_completion(output_type: str) -> None:
    st.markdown(f'<div class="step-label">{t("done_step")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-heading">{t("done_heading")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-description">{t("done_desc")}</div>',
        unsafe_allow_html=True,
    )

    if output_type == "video":
        path = st.session_state.get("final_video_path")
        if path and os.path.exists(path):
            st.video(path)
            with open(path, "rb") as file:
                st.download_button(
                    t("dl_video"),
                    data=file,
                    file_name="academicvid_lesson.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
        else:
            st.warning(t("warn_video_missing"))

    elif output_type == "ppt":
        path = st.session_state.get("final_ppt_path")
        if path and os.path.exists(path):
            with open(path, "rb") as file:
                st.download_button(
                    t("dl_ppt"),
                    data=file,
                    file_name="academicvid_lesson.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
        else:
            st.warning(t("warn_ppt_missing"))

        audio_path = st.session_state.get("final_audio_path")
        if audio_path and os.path.exists(audio_path):
            st.markdown(f"#### {t('audio_heading')}")
            st.audio(audio_path)
            audio_language = st.session_state.get("selected_language", "English")
            with open(audio_path, "rb") as audio_file:
                st.download_button(
                    t("dl_audio", language=t(f"lang_name_{audio_language}")),
                    data=audio_file,
                    file_name="academicvid_narration.mp3",
                    mime="audio/mpeg",
                    use_container_width=True,
                )

    elif output_type == "transcript":
        path = st.session_state.get("final_transcript_path")
        if path and os.path.exists(path):
            with open(path, "rb") as file:
                st.download_button(
                    t("dl_transcript"),
                    data=file,
                    file_name="academicvid_study_notes.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.warning(t("warn_transcript_missing"))

    elif output_type == "flashcards":
        cards = st.session_state.get("flashcards") or []
        if cards:
            st.caption(t("cards_count", count=len(cards)))
            for i, card in enumerate(cards, start=1):
                front = card.get("front", t("card_default_front"))
                with st.expander(t("card_title", num=f"{i:02d}", front=front)):
                    st.write(card.get("back", ""))
        else:
            st.warning(t("warn_no_flashcards"))

    chapter = st.session_state.get("chapter")
    if chapter:
        with st.expander(t("view_data")):
            st.json(chapter.model_dump() if hasattr(chapter, "model_dump") else chapter)

    render_report_button(output_type)
    st.markdown("")
    if st.button(t("btn_another"), type="primary", use_container_width=True):
        reset_pipeline()
        st.rerun()


def render_error_state() -> None:
    st.markdown(f'<div class="section-heading">{t("error_heading")}</div>', unsafe_allow_html=True)
    key = st.session_state.get("last_error_key", "err_unexpected")
    params = st.session_state.get("last_error_params", {})
    st.error(t(key, **params))
    detail = st.session_state.get("last_error_detail")
    if detail:
        with st.expander(t("tech_details")):
            st.code(detail)

    left, right = st.columns(2)
    with left:
        if st.button(t("btn_try_again"), type="primary", use_container_width=True):
            target = st.session_state.get("retry_state", "choose_output")
            if target == "generating_media" and st.session_state.get("chapter") is None:
                target = "choose_output"
            st.session_state.app_state = target
            st.rerun()
    with right:
        if st.button(t("btn_back_workspace"), use_container_width=True):
            reset_pipeline()
            st.rerun()


# ---------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="AcademicVid — AI Learning Studio",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session_state()
    cleanup_old_sessions()
    inject_custom_css()
    inject_language_css()
    inject_mobile_css()
    render_brand()
    render_language_toggle()
    render_brand_and_hero()

    source, pdf_path, selected_class, selected_subject, selected_chapter, upload_name = get_selection()

    if st.session_state.app_state == "setup":
        # STEP 1 — choose a chapter or upload a PDF (all on the main page).
        st.markdown('<div class="setup-content">', unsafe_allow_html=True)
        st.markdown(f'<div class="step-label">{t("setup_step")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-heading">{t("setup_heading")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-description">{t("setup_desc")}</div>',
            unsafe_allow_html=True,
        )

        render_source_picker()
        # Read the choice again: the picker above may have just changed it.
        source, pdf_path, selected_class, selected_subject, selected_chapter, upload_name = get_selection()

        if pdf_path:
            if source == "Library":
                chips = (
                    f'<span class="chip chip-accent">{t("chip_library")}</span>'
                    f'<span class="chip">{html.escape(selected_class or "")}</span>'
                    f'<span class="chip">{html.escape(selected_subject or "")}</span>'
                )
                title = html.escape(selected_chapter or Path(pdf_path).stem)
            else:
                chips = f'<span class="chip chip-accent">{t("chip_pdf")}</span>'
                title = html.escape(upload_name or Path(pdf_path).name)

            st.markdown(
                f'<div class="chapter-card"><div class="chip-row">{chips}</div>'
                f'<div class="chapter-title">{title}</div>'
                f'<div class="chapter-hint">{t("chapter_ready")}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button(t("btn_next_format"), type="primary", use_container_width=True):
                st.session_state.app_state = "choose_output"
                st.rerun()
        else:
            st.markdown(
                f'<div class="panel"><div class="section-heading">{t("setup_panel_title")}</div>'
                f'<div class="section-description">{t("setup_panel_desc")}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.app_state == "choose_output":
        # STEP 2 — choose one output format, then generate it directly.
        st.markdown('<div class="setup-content">', unsafe_allow_html=True)
        st.markdown(f'<div class="step-label">{t("choose_step")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-heading">{t("choose_heading")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-description">{t("choose_desc")}</div>',
            unsafe_allow_html=True,
        )

        # Use Streamlit columns + buttons rather than a vertical radio widget.
        # Columns stack into one column on phones.
        # OUTPUT_OPTIONS keys stay English: they are internal ids, not display text.
        labels = list(OUTPUT_OPTIONS.keys())
        if st.session_state.selected_output_label not in labels:
            st.session_state.selected_output_label = labels[0]

        for row_start in (0, 2):
            card_cols = st.columns(2, gap="large")
            for offset, card_col in enumerate(card_cols):
                label = labels[row_start + offset]
                output_id = OUTPUT_OPTIONS[label]
                with card_col:
                    is_selected = st.session_state.selected_output_label == label
                    if st.button(
                        t(f"format_{output_id}"),
                        key=f"format_card_{output_id}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.selected_output_label = label
                        st.session_state.last_generated_type = output_id
                        st.rerun()
                    st.markdown(
                        f'<div class="format-card-caption">{t(f"format_{output_id}_desc")}</div>',
                        unsafe_allow_html=True,
                    )

        selected_label = st.session_state.selected_output_label
        selected_output = OUTPUT_OPTIONS[selected_label]
        st.session_state.last_generated_type = selected_output
        st.markdown(
            f'<div class="panel"><div class="step-label">{t("selected_format")}</div>'
            f'<div class="section-heading">{t(f"format_{selected_output}")}</div>'
            f'<div class="section-description">{t(f"format_{selected_output}_desc")}</div></div>',
            unsafe_allow_html=True,
        )

        # Optional teacher step. OFF by default so the one-click flow is unchanged.
        # The choice is also kept in a plain session key (widget state is dropped
        # whenever this screen is not drawn).
        review_on = st.checkbox(
            t("review_checkbox"),
            value=st.session_state.get("review_enabled", False),
            key="review_cb",
        )
        st.session_state.review_enabled = review_on

        # Full-width buttons (no side columns) so nothing is squeezed on a phone.
        if st.button(t(f"action_{selected_output}"), type="primary", use_container_width=True):
            if not pdf_path:
                st.warning(t("warn_no_material"))
            else:
                execute_ai_structuring(pdf_path, st.session_state.selected_language)
                if st.session_state.app_state in ("generating_media", "review", "error"):
                    st.rerun()
        if st.button(t("btn_back"), use_container_width=True):
            st.session_state.app_state = "setup"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.app_state == "review":
        render_review_ui(st.session_state.last_generated_type)

    elif st.session_state.app_state == "generating_media":
        execute_media_generation(st.session_state.last_generated_type, get_session_dir())
        if st.session_state.app_state in ("complete", "error"):
            st.rerun()

    elif st.session_state.app_state == "complete":
        render_completion(st.session_state.last_generated_type)

    elif st.session_state.app_state == "error":
        render_error_state()

    st.markdown(f'<div class="footer">{t("footer")}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
