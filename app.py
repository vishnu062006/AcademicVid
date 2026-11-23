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
from ai_structuring import (
    structure_chapter, build_topics_input, MODE_CHAPTER, MODE_KANNADA_LIT, MODE_TOPICS,
)
from ocr import transcribe_notes, pdf_pages_as_images, MAX_FILES as OCR_MAX_FILES
from library import resolve_library_pdf, entry_is_available, LibraryDownloadError
from pdf_parser import looks_like_legacy_kannada
from slides import build_section_slides
from tts import synthesize_narration, VOICE_EN, VOICE_KN
from video_builder import build_section_video, concatenate_section_videos
from ppt_export import export_chapter_to_pptx
from transcript_export import export_transcript_pdf
from flashcards import generate_flashcards
from strings import t, LANGUAGE_LABELS
from branding import APP_NAME, FILE_PREFIX


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
# Teachers / students (main page) see only these two. The /bmsce admin page
# (pages/bmsce.py, password protected) also gets handwritten notes and custom topics.
PUBLIC_SOURCES = ["Library", "Upload PDF"]
ADMIN_SOURCES = ["Library", "Upload PDF", "Notes", "Topics"]
SOURCE_LABEL_KEYS = {
    "Library": "source_library",
    "Upload PDF": "source_upload",
    "Notes": "source_notes",
    "Topics": "source_topics",
}
# Lesson styles for uploaded PDFs / notes (library chapters get theirs from the subject).
LESSON_KINDS = {MODE_CHAPTER: "kind_chapter", MODE_KANNADA_LIT: "kind_kannada"}
# Custom-topic levels: internal English value -> strings.py key.
TOPIC_LEVELS = {
    "Engineering (B.E. / B.Tech)": "level_engineering",
    "PUC / Class 11-12": "level_puc",
    "School (Class 6-10)": "level_school",
    "Other": "level_other",
}
MAX_TOPICS = 12   # one section per topic; more would make Gemini's reply too long
LANGUAGE_OPTIONS = ["English", "Kannada"]
MAX_PDF_PAGES = 40
SESSION_MAX_AGE_SECONDS = 6 * 60 * 60  # tmp_sessions folders older than this are deleted

# "Report a problem" Google Form
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
        "quiz_open",
        "quiz_result",
    ):
        st.session_state.pop(key, None)
    for key in [k for k in st.session_state.keys() if str(k).startswith("quiz_answer_")]:
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
# The AI answered too slowly (checked BEFORE network: a slow reply is not "no internet").
_SLOW_MARKERS = (
    "deadlineexceeded", "deadline exceeded", "deadline expired", "504", "readtimeout",
    "read timed out",
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
    if any(marker in blob for marker in _SLOW_MARKERS):
        return "err_slow", {}
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
    """Delete tmp_sessions/<id> folders untouched for 6+ hours (never the current one)."""
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
    """Loads custom CSS from style.css and injects it into Streamlit."""
    css_file = Path("style.css")
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("style.css not found. Please create it in the same directory.")

def inject_language_css() -> None:
    """Apply language-specific styling."""
    css = """
    <style>
    .field-label {
        color: var(--text);
        font-size: .85rem;
        font-weight: 600;
        margin: 12px 0 6px;
    }

    [data-testid="stAppViewBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor):not(:has(div[data-testid="stHorizontalBlock"])) {
        flex-wrap: nowrap !important;
        max-width: 360px;
        gap: 8px !important;
        margin: 0 0 14px;
    }

    [data-testid="stAppViewBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor):not(:has(div[data-testid="stHorizontalBlock"]))
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
            <div class="brand-name">{html.escape(APP_NAME)}</div>
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
        [data-testid="stAppViewBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.src-anchor) {
            flex-wrap: nowrap !important; gap: 8px !important; margin: 0 0 14px;
        }
        [data-testid="stAppViewBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.src-anchor)
        > div[data-testid="column"] {
            min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;
        }
        [data-testid="stAppViewBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor):not(:has(div[data-testid="stHorizontalBlock"]))
        div[data-testid="stButton"] > button,
        [data-testid="stAppViewBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.src-anchor)
        div[data-testid="stButton"] > button {
            min-height: 48px !important; padding: 8px 14px !important;
            justify-content: center !important; text-align: center !important;
            font-size: 15px !important;
        }
        /* Pickers and uploader: at least ~48px tall; 16px text avoids iOS zoom-on-focus. */
        [data-testid="stAppViewBlockContainer"] div[data-baseweb="select"] > div {
            min-height: 48px !important; font-size: 16px !important;
        }
        ul[role="listbox"] li { min-height: 44px; display: flex; align-items: center; }
        [data-testid="stFileUploader"] section { padding: 18px !important; }
        [data-testid="stFileUploader"] button { min-height: 48px !important; }
        .stDownloadButton > button, .stFormSubmitButton > button { min-height: 48px !important; }
        .brand-lockup { margin-bottom: 16px; }
        [data-testid="stAppViewBlockContainer"] img,
        [data-testid="stAppViewBlockContainer"] video,
        [data-testid="stAppViewBlockContainer"] audio { max-width: 100%; }
        @media (max-width: 640px) {
            [data-testid="stAppViewBlockContainer"] {
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


def render_source_picker(sources) -> None:
    """Chapter picker + PDF upload on the main page (phones hide the sidebar).

    Streamlit 1.31 deletes a widget's state when it is not drawn, and this picker is only
    drawn on the first screen. So every choice is also stored in plain session keys
    (pick_class, pick_subject, pick_chapter, upload_path, upload_name); get_selection()
    reads those on every screen. Widgets keep a fixed English label + key + collapsed
    label, and we draw the translated label, so switching language never resets them.
    """
    # Four sources as a 2 x 2 grid of buttons (stays 2 wide on phones, see the CSS).
    for row in (sources[:2], sources[2:]):
        if not row:
            continue
        cols = st.columns(2, gap="small")
        for col, mode in zip(cols, row):
            with col:
                if st.button(
                    t(SOURCE_LABEL_KEYS[mode]),
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

    if st.session_state.source_mode == "Notes":
        render_notes_picker()
        return
    if st.session_state.source_mode == "Topics":
        render_topics_picker()
        return

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
        render_lesson_kind_picker()


def render_lesson_kind_picker() -> None:
    """Normal subject chapter, or a Kannada-subject story/poem (different teaching style)."""
    _field_label(t("kind_label"))
    kinds = list(LESSON_KINDS)
    choice = st.selectbox(
        "Lesson type", kinds,
        index=_index_of(kinds, st.session_state.get("lesson_kind", MODE_CHAPTER)),
        format_func=lambda k: t(LESSON_KINDS[k]),
        key="sel_lesson_kind", label_visibility="collapsed",
    )
    st.session_state.lesson_kind = choice
    if choice == MODE_KANNADA_LIT:
        st.caption(t("kind_kannada_hint"))


@st.cache_data(show_spinner=False, max_entries=32)
def cached_transcribe(files):
    """OCR result per exact set of files, so re-reading the same photos costs no quota."""
    return transcribe_notes(list(files))


def render_notes_picker() -> None:
    """Handwritten / scanned notes: photos or a scanned PDF -> text the user can correct."""
    _field_label(t("notes_label"))
    uploads = st.file_uploader(
        "Notes", type=["jpg", "jpeg", "png", "webp", "pdf"], accept_multiple_files=True,
        key="notes_upload", label_visibility="collapsed",
    )
    st.caption(t("notes_hint", max=OCR_MAX_FILES))
    if uploads and len(uploads) > OCR_MAX_FILES:
        st.warning(t("notes_too_many", max=OCR_MAX_FILES))
        uploads = uploads[:OCR_MAX_FILES]

    if uploads and st.button(t("notes_read_btn"), type="primary", use_container_width=True):
        files = []
        for f in uploads:
            mime = f.type or ""
            if f.name.lower().endswith(".pdf"):
                mime = "application/pdf"
            files.append((f.getvalue(), mime))
        try:
            with st.spinner(t("notes_reading")):
                text = cached_transcribe(tuple(files))
        except Exception as exc:  # friendly message, never a traceback
            key, params = classify_error(exc)
            st.error(t(key, **params))
            text = None
        if text is not None:
            if not text.strip():
                st.error(t("notes_nothing_read"))
            st.session_state.notes_text = text
            st.session_state.notes_name = ", ".join(f.name for f in uploads)
            st.session_state.pop("notes_ta", None)   # show the new text, not the old edit

    if st.session_state.get("notes_text"):
        _field_label(t("notes_check_label"))
        st.caption(t("notes_check_hint"))
        edited = st.text_area(
            "Transcribed notes", value=st.session_state.notes_text, height=260,
            key="notes_ta", label_visibility="collapsed",
        )
        st.session_state.notes_text = edited
        render_lesson_kind_picker()


def _topic_lines(text: str):
    """Topic names: non-empty lines that are not '-' notes under a topic."""
    return [ln.strip() for ln in (text or "").splitlines()
            if ln.strip() and not ln.strip().startswith(("-", "•", "*"))]


def render_topics_picker() -> None:
    """Custom subject + topic list (e.g. CSE): no PDF, the AI teaches each topic."""
    st.caption(t("topics_intro"))
    _field_label(t("topics_subject"))
    subject = st.text_input(
        "Subject name", value=st.session_state.get("topic_subject", ""),
        placeholder=t("topics_subject_ph"), key="topic_subject_in", label_visibility="collapsed",
    )
    st.session_state.topic_subject = subject

    _field_label(t("topics_level"))
    levels = list(TOPIC_LEVELS)
    level = st.selectbox(
        "Level", levels, index=_index_of(levels, st.session_state.get("topic_level")),
        format_func=lambda k: t(TOPIC_LEVELS[k]), key="topic_level_in",
        label_visibility="collapsed",
    )
    st.session_state.topic_level = level

    _field_label(t("topics_list", max=MAX_TOPICS))
    topics = st.text_area(
        "Topics", value=st.session_state.get("topic_text", ""), height=220,
        placeholder=t("topics_list_ph"), key="topic_text_in", label_visibility="collapsed",
    )
    st.session_state.topic_text = topics
    count = len(_topic_lines(topics))
    if count > MAX_TOPICS:
        st.warning(t("topics_too_many", count=count, max=MAX_TOPICS))
    elif count:
        st.caption(t("topics_count", count=count))


def get_selection() -> dict:
    """Everything the later screens need about the chosen material, from stored picks.

    Keys: source, pdf_path, text (notes/topics), mode, title, cls, subject, chapter,
    upload_name, ready (True when the lesson can be made).
    """
    source = st.session_state.source_mode
    sel = {"source": source, "pdf_path": None, "library_entry": None, "text": None,
           "mode": MODE_CHAPTER,
           "title": "", "cls": None, "subject": None, "chapter": None, "upload_name": None,
           "ready": False}
    kind = st.session_state.get("lesson_kind", MODE_CHAPTER)
    if kind not in LESSON_KINDS:
        kind = MODE_CHAPTER

    if source == "Library":
        cls = st.session_state.get("pick_class")
        subject = st.session_state.get("pick_subject")
        chapter = st.session_state.get("pick_chapter")
        try:
            entry = CHAPTER_MANIFEST[cls][subject][chapter]
        except (KeyError, TypeError):
            entry = None
        # The PDF itself is fetched only when the lesson is made (it may be downloaded).
        sel.update(library_entry=entry, cls=cls, subject=subject, chapter=chapter,
                   title=chapter or "", ready=bool(entry) and entry_is_available(entry),
                   mode=MODE_KANNADA_LIT if subject == "Kannada" else MODE_CHAPTER)
    elif source == "Upload PDF":
        path = st.session_state.get("upload_path")
        if path and not os.path.exists(path):
            path = None
        name = st.session_state.get("upload_name")
        sel.update(pdf_path=path, upload_name=name, title=name or "", ready=bool(path), mode=kind)
    elif source == "Notes":
        text = (st.session_state.get("notes_text") or "").strip()
        name = st.session_state.get("notes_name") or ""
        sel.update(text=text, upload_name=name, title=name, ready=bool(text), mode=kind)
    elif source == "Topics":
        subject = (st.session_state.get("topic_subject") or "").strip()
        level = st.session_state.get("topic_level") or "Other"
        raw = st.session_state.get("topic_text") or ""
        count = len(_topic_lines(raw))
        sel.update(subject=subject, title=subject, mode=MODE_TOPICS,
                   ready=bool(subject) and 0 < count <= MAX_TOPICS,
                   text=build_topics_input(subject, level, raw) if subject and count else None)
    return sel


# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=64)
def cached_structure_chapter(clean_text: str, language: str, mode: str = MODE_CHAPTER):
    """One Gemini call per (text, language, lesson mode) for the life of the server.

    The same library chapter clicked again, by anyone, costs no quota. Errors are not
    cached, so a failed call is retried on the next click. Streamlit returns a fresh copy
    each time, so edits in the review form never change the cached lesson.
    """
    return structure_chapter(clean_text, language=language, mode=mode)


@st.cache_data(show_spinner=False, max_entries=64)
def cached_page_ocr(pdf_path: str, mtime: float) -> str:
    """Read a PDF from its page images (one Gemini call), once per file version."""
    return transcribe_notes(pdf_pages_as_images(pdf_path, max_pages=MAX_PDF_PAGES),
                            max_files=MAX_PDF_PAGES)


def get_pdf_text(pdf_path: str, status) -> str:
    """Chapter text from a PDF. Falls back to reading the page images when the text
    layer is unusable: a scanned PDF (no text) or Kannada typed in an old non-Unicode
    font (KTBS state textbooks), which would otherwise send junk to the AI."""
    status.write(t("status_extract"))
    text = extract_chapter(pdf_path).get("clean_text", "")
    if text.strip() and not looks_like_legacy_kannada(text):
        return text
    status.write(t("status_reading_pages"))
    return cached_page_ocr(pdf_path, os.path.getmtime(pdf_path))


def execute_ai_structuring(selection: dict, language: str) -> None:
    mode = selection.get("mode", MODE_CHAPTER)
    if mode == MODE_KANNADA_LIT:
        language = "Kannada"   # Kannada-subject lessons are always taught in Kannada
    try:
        with st.status(t("status_analyzing"), expanded=True) as status:
            pdf_path = selection.get("pdf_path")
            if selection.get("library_entry") is not None:
                if not isinstance(selection["library_entry"], str):
                    status.write(t("status_downloading"))
                try:
                    pdf_path = resolve_library_pdf(selection["library_entry"])
                except LibraryDownloadError as exc:
                    raise FriendlyError("err_library_download") from exc
            if pdf_path:
                clean_text = get_pdf_text(pdf_path, status)
            else:
                clean_text = selection.get("text") or ""
            if not clean_text.strip():
                raise FriendlyError("err_no_text")
            status.write(t("status_structure"))
            chapter = cached_structure_chapter(clean_text, language, mode)
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


def _apply_review_edits(chapter, chapter_title: str, chapter_subject: str, edits):
    """Build an edited COPY of the chapter. Returns None if the edits are not valid.

    The original chapter is never touched, so a bad submit leaves nothing half-edited.
    Every narration must be non-empty (edge-tts fails on empty text).
    """
    try:
        data = chapter.model_dump()
        data["chapter_title"] = chapter_title
        data["subject"] = chapter_subject
        for section_data, edit in zip(data["sections"], edits):
            section_data.update(edit)
        if any(not str(s.get("narration") or "").strip() for s in data["sections"]):
            return None
        return type(chapter).model_validate(data)
    except Exception:
        return None


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
        edited = _apply_review_edits(chapter, chapter_title, chapter_subject, edits)
        if edited is None:
            st.error(t("review_invalid"))
            return
        # Every output (video, PPT, notes PDF, flashcards) reads this same edited object.
        st.session_state.chapter = edited
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

    # The language Gemini wrote the lesson in, not the current UI language.
    selected_language = st.session_state.get(
        "lesson_language", st.session_state.get("selected_language", "English")
    )
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
    sel = get_selection()
    if sel["source"] == "Library":
        chapter_label = " / ".join(x for x in (sel["cls"], sel["subject"], sel["chapter"]) if x)
    elif sel["source"] == "Topics":
        chapter_label = "Custom topics: " + (sel["subject"] or "")
    elif sel["source"] == "Notes":
        chapter_label = "Handwritten notes: " + (sel["upload_name"] or "")
    else:
        chapter_label = "Uploaded PDF: " + (sel["upload_name"] or "")
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
            background: var(--surface-2); color: var(--text) !important;
            font-weight: 700; text-decoration: none !important;
            overflow-wrap: anywhere;
        }
        a.report-link:hover { border-color: var(--border-hover); }
        </style>
        """
        f'<a class="report-link" href="{url}" target="_blank" rel="noopener noreferrer">'
        f'⚑&nbsp; {t("report_button")}</a>',
        unsafe_allow_html=True,
    )


def _valid_quizzes(chapter):
    """(section title, quiz) for every section whose quiz is complete and consistent."""
    out = []
    for section in getattr(chapter, "sections", []) or []:
        q = getattr(section, "quiz", None)
        if (q and str(q.question).strip() and 2 <= len(q.options) <= 4
                and 0 <= q.answer_index < len(q.options)):
            out.append((section.title, q))
    return out


def render_quiz_offer() -> None:
    """At the end of a lesson, ASK the teacher if they want a quiz; show it only on yes.

    The questions come from the same AI call as the lesson (one per section), so the quiz
    costs nothing extra. One column, full-width buttons: safe on phones.
    """
    quizzes = _valid_quizzes(st.session_state.get("chapter"))
    if not quizzes:
        return

    if not st.session_state.get("quiz_open"):
        st.markdown(
            f'<div class="panel"><div class="section-heading">{t("quiz_offer_title")}</div>'
            f'<div class="section-description">{t("quiz_offer_desc", n=len(quizzes))}</div></div>',
            unsafe_allow_html=True,
        )
        if st.button(t("quiz_offer_btn"), use_container_width=True, key="quiz_open_btn"):
            st.session_state.quiz_open = True
            st.rerun()
        return

    st.markdown(f'<div class="section-heading">{t("quiz_heading")}</div>', unsafe_allow_html=True)
    with st.form("quiz_form"):
        for i, (_title, q) in enumerate(quizzes, start=1):
            st.markdown(
                f'<div class="field-label">{i}. {html.escape(str(q.question))}</div>',
                unsafe_allow_html=True,
            )
            st.radio(
                f"Question {i}", options=[str(o) for o in q.options], index=None,
                key=f"quiz_answer_{i}", label_visibility="collapsed",
            )
        checked = st.form_submit_button(t("quiz_check"), type="primary", use_container_width=True)

    if checked:
        # Store the chosen option's position (None = not answered).
        result = []
        for i, (_t, q) in enumerate(quizzes, start=1):
            chosen = st.session_state.get(f"quiz_answer_{i}")
            opts = [str(o) for o in q.options]
            result.append(opts.index(chosen) if chosen in opts else None)
        st.session_state.quiz_result = result
    result = st.session_state.get("quiz_result")
    if result and len(result) == len(quizzes):
        score = sum(1 for given, (_t, q) in zip(result, quizzes) if given == q.answer_index)
        st.markdown(f"#### {t('quiz_score', score=score, total=len(quizzes))}")
        for i, (given, (_t, q)) in enumerate(zip(result, quizzes), start=1):
            right = str(q.options[q.answer_index])
            if given == q.answer_index:
                st.success(f"{i}. {t('quiz_correct')}")
            elif given is None:
                st.warning(f"{i}. {t('quiz_unanswered', answer=right)}")
            else:
                st.error(f"{i}. {t('quiz_wrong', answer=right)}")
            if str(q.explanation).strip():
                st.caption(str(q.explanation))


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
                    file_name=f"{FILE_PREFIX}_lesson.mp4",
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
                    file_name=f"{FILE_PREFIX}_lesson.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
        else:
            st.warning(t("warn_ppt_missing"))

        audio_path = st.session_state.get("final_audio_path")
        if audio_path and os.path.exists(audio_path):
            st.markdown(f"#### {t('audio_heading')}")
            st.audio(audio_path)
            audio_language = st.session_state.get(
                "lesson_language", st.session_state.get("selected_language", "English")
            )
            with open(audio_path, "rb") as audio_file:
                st.download_button(
                    t("dl_audio", language=t(f"lang_name_{audio_language}")),
                    data=audio_file,
                    file_name=f"{FILE_PREFIX}_narration.mp3",
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
                    file_name=f"{FILE_PREFIX}_study_notes.pdf",
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

    render_quiz_offer()
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
def main(admin: bool = False, set_config: bool = True) -> None:
    """The whole app. admin=True (only from pages/bmsce.py, after the password) adds the
    handwritten-notes and custom-topics sources; the public page never shows them."""
    if set_config:
        set_page_config()
    sources = ADMIN_SOURCES if admin else PUBLIC_SOURCES
    init_session_state()
    # Session state is shared between the main page and /bmsce. Switching page starts a
    # fresh flow, so nothing made on the admin page ever shows up on the public page.
    page_id = "admin" if admin else "public"
    if st.session_state.get("active_page") != page_id:
        st.session_state.active_page = page_id
        reset_pipeline()
    if st.session_state.source_mode not in sources:
        st.session_state.source_mode = "Library"
    render_page(sources)


def set_page_config() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} — AI Learning Studio",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def render_page(sources) -> None:
    cleanup_old_sessions()
    inject_custom_css()
    inject_language_css()
    inject_mobile_css()

    # Consolidate Header & Language toggle side-by-side
    header_left, header_right = st.columns([3, 1])
    with header_left:
        render_brand()
    with header_right:
        # Language is chosen at the start only. Once a lesson is being made, the
        # toggle is hidden so the script, voice and slides always match.
        if st.session_state.app_state == "setup":
            render_language_toggle()

    render_brand_and_hero()

    selection = get_selection()

    if st.session_state.app_state == "setup":
        # STEP 1 — choose a chapter or upload a PDF (all on the main page).
        st.markdown('<div class="setup-content">', unsafe_allow_html=True)
        st.markdown(f'<div class="step-label">{t("setup_step")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-heading">{t("setup_heading")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-description">{t("setup_desc")}</div>',
            unsafe_allow_html=True,
        )

        render_source_picker(sources)
        # Read the choice again: the picker above may have just changed it.
        selection = get_selection()

        if selection["ready"]:
            source = selection["source"]
            if source == "Library":
                chips = (
                    f'<span class="chip chip-accent">{t("chip_library")}</span>'
                    f'<span class="chip">{html.escape(selection["cls"] or "")}</span>'
                    f'<span class="chip">{html.escape(selection["subject"] or "")}</span>'
                )
            elif source == "Topics":
                chips = f'<span class="chip chip-accent">{t("chip_topics")}</span>'
            elif source == "Notes":
                chips = f'<span class="chip chip-accent">{t("chip_notes")}</span>'
            else:
                chips = f'<span class="chip chip-accent">{t("chip_pdf")}</span>'
            if selection["mode"] == MODE_KANNADA_LIT:
                chips += f'<span class="chip">{t("chip_kannada_lesson")}</span>'
            title = html.escape(selection["title"] or t("chip_notes"))

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
            if not selection["ready"]:
                st.warning(t("warn_no_material"))
            else:
                execute_ai_structuring(selection, st.session_state.selected_language)
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

    st.markdown(f'<div class="footer">{t("footer", app=html.escape(APP_NAME.upper()))}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()