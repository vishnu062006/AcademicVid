"""
Applies Issue 3 (safety + friendly errors) to app.py and strings.py.

Branch first:   git checkout -b feature/errors-and-safety
Run from the project root (next to app.py and strings.py):
    python3 apply_issue3.py

Checks every marker first and refuses to write anything if one is missing.
Delete this script afterwards; do not commit it.
"""
import ast
import sys

SEP = "# ---------------------------------------------------------------------\n"

# ----------------------------------------------------------------------
# New helper code, inserted before the "Premium dark UI" section of app.py
# ----------------------------------------------------------------------
BLOCK_HELPERS = r'''# ---------------------------------------------------------------------
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


'''

BLOCK_STRUCTURING = r'''def execute_ai_structuring(pdf_path: str, language: str) -> None:
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
            # Keep the experience one-click: prepare the lesson, then generate
            # the selected resource without asking the learner to approve a script.
            st.session_state.app_state = "generating_media"
            status.update(label=t("status_lesson_ready"), state="complete")
    except Exception as exc:
        set_error(exc, retry_state="choose_output")


'''

BLOCK_ERROR_STATE = r'''def render_error_state() -> None:
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


'''

UPLOAD_OLD = """    elif uploaded_file is not None:
        pdf_path = save_uploaded_pdf(uploaded_file, get_session_dir())
"""
UPLOAD_NEW = """    elif uploaded_file is not None:
        saved_path = save_uploaded_pdf(uploaded_file, get_session_dir())
        problem = check_pdf(saved_path)
        if problem is None:
            pdf_path = saved_path
        else:
            st.error(problem.message())
            try:
                os.remove(saved_path)
            except OSError:
                pass
"""

STRINGS_EN = '''        "err_generation": "Generation failed: {error}",
        "err_quota": "Today’s free AI limit has been reached. Please try again in a few minutes, or tomorrow.",
        "err_network": "Could not connect to the internet or the AI service. Please check your connection and try again.",
        "err_too_long": "This PDF has {pages} pages. The limit is {limit} pages, so lessons stay quick on slow connections. Please upload a shorter chapter.",
        "err_unreadable_pdf": "This PDF could not be opened. It may be damaged or password-protected. Please try another file.",
        "err_unexpected": "Something went wrong while making your lesson. Please try again.",
        "btn_try_again": "Try again",
        "tech_details": "Technical details",
'''
STRINGS_KN = '''        "err_generation": "ರಚನೆ ವಿಫಲವಾಯಿತು: {error}",  # NEEDS REVIEW
        "err_quota": "ಇಂದಿನ ಉಚಿತ AI ಮಿತಿ ಮುಗಿದಿದೆ. ದಯವಿಟ್ಟು ಕೆಲವು ನಿಮಿಷಗಳ ನಂತರ ಅಥವಾ ನಾಳೆ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_network": "ಇಂಟರ್ನೆಟ್ ಅಥವಾ AI ಸೇವೆಗೆ ಸಂಪರ್ಕಿಸಲು ಆಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_too_long": "ಈ PDF ನಲ್ಲಿ {pages} ಪುಟಗಳಿವೆ. ನಿಧಾನ ಇಂಟರ್ನೆಟ್‌ನಲ್ಲೂ ಪಾಠ ಬೇಗ ತಯಾರಾಗಲು ಮಿತಿ {limit} ಪುಟಗಳು. ದಯವಿಟ್ಟು ಚಿಕ್ಕ ಅಧ್ಯಾಯವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",  # NEEDS REVIEW
        "err_unreadable_pdf": "ಈ PDF ಅನ್ನು ತೆರೆಯಲು ಆಗಲಿಲ್ಲ. ಅದು ಹಾನಿಗೊಂಡಿರಬಹುದು ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್ ಇರಬಹುದು. ದಯವಿಟ್ಟು ಬೇರೆ ಫೈಲ್ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_unexpected": "ನಿಮ್ಮ ಪಾಠ ತಯಾರಿಸುವಾಗ ಏನೋ ತಪ್ಪಾಯಿತು. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "btn_try_again": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",  # NEEDS REVIEW
        "tech_details": "ತಾಂತ್ರಿಕ ವಿವರಗಳು",  # NEEDS REVIEW
'''
STRINGS_EN_OLD = '        "err_generation": "Generation failed: {error}",\n'
STRINGS_KN_OLD = '        "err_generation": "ರಚನೆ ವಿಫಲವಾಯಿತು: {error}",  # NEEDS REVIEW\n'


def swap(src, start, end, new, name):
    i = src.find(start)
    j = src.find(end, i) if i >= 0 else -1
    if i < 0 or j < 0:
        sys.exit(f"STOP: could not find markers for {name}. Nothing was changed.")
    return src[:i] + new + src[j:]


def rep(src, old, new, name):
    if src.count(old) != 1:
        sys.exit(f"STOP: expected exactly one match for {name}, found {src.count(old)}. Nothing was changed.")
    return src.replace(old, new)


def patch_app(src):
    if "class FriendlyError" in src:
        sys.exit("app.py already has FriendlyError. Looks like Issue 3 was applied already.")

    src = rep(src, "import os\nimport uuid\n", "import html\nimport os\nimport shutil\nimport time\nimport uuid\n", "stdlib imports")
    src = rep(
        src,
        "import streamlit as st\nfrom dotenv import load_dotenv\n",
        "import streamlit as st\nfrom dotenv import load_dotenv\nimport fitz  # PyMuPDF, already a dependency; used to count PDF pages\n",
        "fitz import",
    )
    src = rep(
        src,
        'LANGUAGE_OPTIONS = ["English", "Kannada"]\n',
        'LANGUAGE_OPTIONS = ["English", "Kannada"]\nMAX_PDF_PAGES = 40\nSESSION_MAX_AGE_SECONDS = 6 * 60 * 60  # tmp_sessions folders older than this are deleted\n',
        "constants",
    )
    src = rep(
        src,
        '        "flashcards",\n        "last_error",\n    ):',
        '        "flashcards",\n        "last_error",\n        "last_error_key",\n        "last_error_params",\n        "last_error_detail",\n        "retry_state",\n    ):',
        "reset_pipeline keys",
    )
    # Helpers go right before the CSS section.
    marker = SEP + "# Premium dark UI"
    src = rep(src, marker, BLOCK_HELPERS + marker, "helpers insertion point")

    src = swap(src, "def execute_ai_structuring(", "def render_review_ui(", BLOCK_STRUCTURING, "structuring")
    src = swap(src, "def render_error_state() -> None:", SEP + "# Main app", BLOCK_ERROR_STATE, "error screen")

    src = rep(
        src,
        '    except Exception as exc:\n        st.session_state.last_error = str(exc)\n        st.session_state.app_state = "error"\n        st.error(t("err_generation", error=exc))\n',
        '    except Exception as exc:\n        set_error(exc, retry_state="generating_media")\n',
        "media error handler",
    )
    src = rep(
        src,
        'status.write(t("ppt_audio_failed", error=audio_exc))',
        'audio_key, audio_params = classify_error(audio_exc)\n                        status.write(t("ppt_audio_failed", error=t(audio_key, **audio_params)))',
        "ppt audio message",
    )

    # main(): cleanup, upload check, escaping, jump to error screen.
    src = rep(src, "    init_session_state()\n    inject_custom_css()\n", "    init_session_state()\n    cleanup_old_sessions()\n    inject_custom_css()\n", "main startup")
    src = rep(src, UPLOAD_OLD, UPLOAD_NEW, "upload block")
    src = rep(src, """f'<span class="chip">{selected_class or ""}</span>'""", """f'<span class="chip">{html.escape(selected_class or "")}</span>'""", "class chip")
    src = rep(src, """f'<span class="chip">{selected_subject or ""}</span>'""", """f'<span class="chip">{html.escape(selected_subject or "")}</span>'""", "subject chip")
    src = rep(src, "title = selected_chapter or Path(pdf_path).stem", "title = html.escape(selected_chapter or Path(pdf_path).stem)", "library title")
    src = rep(
        src,
        "title = uploaded_file.name if uploaded_file is not None else Path(pdf_path).name",
        "title = html.escape(uploaded_file.name if uploaded_file is not None else Path(pdf_path).name)",
        "upload title",
    )
    src = rep(
        src,
        '                    if st.session_state.app_state == "generating_media":\n                        st.rerun()\n',
        '                    if st.session_state.app_state in ("generating_media", "error"):\n                        st.rerun()\n',
        "rerun after structuring",
    )
    src = rep(
        src,
        '        execute_media_generation(st.session_state.last_generated_type, get_session_dir())\n        if st.session_state.app_state == "complete":\n            st.rerun()\n',
        '        execute_media_generation(st.session_state.last_generated_type, get_session_dir())\n        if st.session_state.app_state in ("complete", "error"):\n            st.rerun()\n',
        "rerun after media",
    )
    return src


def patch_strings(src):
    if '"err_quota"' in src:
        sys.exit("strings.py already has err_quota. Looks like Issue 3 was applied already.")
    src = rep(src, STRINGS_EN_OLD, STRINGS_EN, "English err_generation line")
    src = rep(src, STRINGS_KN_OLD, STRINGS_KN, "Kannada err_generation line")
    return src


def main():
    with open("app.py", encoding="utf-8") as f:
        app_src = f.read()
    with open("strings.py", encoding="utf-8") as f:
        str_src = f.read()

    new_app = patch_app(app_src)
    new_str = patch_strings(str_src)
    for name, code in (("app.py", new_app), ("strings.py", new_str)):
        try:
            ast.parse(code)
        except SyntaxError as exc:
            sys.exit(f"STOP: patched {name} has a syntax error ({exc}). Nothing was changed.")

    with open("app.py", "w", encoding="utf-8") as f:
        f.write(new_app)
    with open("strings.py", "w", encoding="utf-8") as f:
        f.write(new_str)
    print("Done. app.py and strings.py updated. Now run: streamlit run app.py")


if __name__ == "__main__":
    main()