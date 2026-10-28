"""
Applies Issue 5 ("Report a problem" button) to app.py and strings.py.

Needs Issues 1, 3, 2 and 4 already applied (it checks).
Branch first:   git checkout -b feature/report-problem
Run from the project root (next to app.py and strings.py):
    python3 apply_issue5.py

Then paste Vishnu's form link and entry ids into the constants at the top of app.py.
Checks every marker first and refuses to write anything if one is missing.
Delete this script afterwards; do not commit it.
"""
import ast
import sys

CONSTANTS_ANCHOR = "SESSION_MAX_AGE_SECONDS = 6 * 60 * 60  # tmp_sessions folders older than this are deleted\n"
CONSTANTS_NEW = CONSTANTS_ANCHOR + '''
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
'''

BLOCK_REPORT = r'''def report_form_is_set_up() -> bool:
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


'''

STRINGS_EN = '''        "report_button": "Report a problem with this lesson",
        "report_not_ready": "The report form link has not been set up yet.",
'''
STRINGS_KN = '''        "report_button": "ಈ ಪಾಠದಲ್ಲಿ ಸಮಸ್ಯೆ ವರದಿ ಮಾಡಿ",  # NEEDS REVIEW
        "report_not_ready": "ವರದಿ ಫಾರ್ಮ್ ಲಿಂಕ್ ಇನ್ನೂ ಸಿದ್ಧವಾಗಿಲ್ಲ.",  # NEEDS REVIEW
'''


def swap_insert_before(src, marker, new, name):
    if src.count(marker) != 1:
        sys.exit(f"STOP: expected exactly one match for {name}, found {src.count(marker)}. Nothing was changed.")
    return src.replace(marker, new + marker)


def rep(src, old, new, name):
    if src.count(old) != 1:
        sys.exit(f"STOP: expected exactly one match for {name}, found {src.count(old)}. Nothing was changed.")
    return src.replace(old, new)


def insert_after_nth_line(src, prefix, n, text, name):
    """Insert `text` after the n-th (0-based) line that starts with `prefix`."""
    pos = -1
    for _ in range(n + 1):
        pos = src.find(prefix, pos + 1)
        if pos < 0:
            sys.exit(f"STOP: could not find {name} in strings.py. Nothing was changed.")
    end = src.find("\n", pos) + 1
    return src[:end] + text + src[end:]


def patch_app(src):
    if "def render_report_button" in src:
        sys.exit("app.py already has render_report_button. Looks like Issue 5 was applied already.")
    for needed in ("def get_selection", "def _chapter_is_valid", "def render_completion", "SESSION_MAX_AGE_SECONDS"):
        if needed not in src:
            sys.exit(f"STOP: app.py has no '{needed}'. Apply Issues 1, 3, 2 and 4 first. Nothing was changed.")

    src = rep(
        src,
        "import uuid\nfrom pathlib import Path\n",
        "import uuid\nfrom pathlib import Path\nfrom urllib.parse import quote, urlencode\n",
        "imports",
    )
    src = rep(src, CONSTANTS_ANCHOR, CONSTANTS_NEW, "constants")
    src = swap_insert_before(src, "def render_completion(", BLOCK_REPORT, "render_completion")
    # Remember the language the lesson was made in.
    src = rep(
        src,
        "            st.session_state.chapter = chapter\n            # Keep the experience one-click",
        "            st.session_state.chapter = chapter\n            st.session_state.lesson_language = language\n            # Keep the experience one-click",
        "remember lesson language",
    )
    # Button on the finished-lesson screen, just above "Create another lesson".
    src = rep(
        src,
        '    st.markdown("")\n    if st.button(t("btn_another")',
        '    render_report_button(output_type)\n    st.markdown("")\n    if st.button(t("btn_another")',
        "completion screen button",
    )
    return src


def patch_strings(src):
    if '"report_button"' in src:
        sys.exit("strings.py already has report_button. Looks like Issue 5 was applied already.")
    if '"review_back"' not in src:
        sys.exit("STOP: strings.py has no review_back. Apply Issue 4 first. Nothing was changed.")
    prefix = '        "review_back": '
    src = insert_after_nth_line(src, prefix, 0, STRINGS_EN, "English review_back")
    src = insert_after_nth_line(src, prefix, 1, STRINGS_KN, "Kannada review_back")
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
    print("Done. Now paste the real form link + entry ids into the constants at the top of app.py.")


if __name__ == "__main__":
    main()