"""
Applies Issue 2 (mobile-first flow) to app.py and strings.py.

Needs Issues 1 and 3 already applied (it checks).
Branch first:   git checkout -b feature/mobile-flow
Run from the project root (next to app.py and strings.py):
    python3 apply_issue2.py

Checks every marker first and refuses to write anything if one is missing.
Delete this script afterwards; do not commit it.
"""
import ast
import sys

SEP = "# ---------------------------------------------------------------------\n"

BLOCK_PICKER = r'''def render_brand() -> None:
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


'''

BLOCK_MAIN = r'''def main() -> None:
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

        # Full-width buttons (no side columns) so nothing is squeezed on a phone.
        if st.button(t(f"action_{selected_output}"), type="primary", use_container_width=True):
            if not pdf_path:
                st.warning(t("warn_no_material"))
            else:
                execute_ai_structuring(pdf_path, st.session_state.selected_language)
                if st.session_state.app_state in ("generating_media", "error"):
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


'''

PANEL_EN = '''        "setup_panel_desc": (
            "Pick a chapter above, or switch to Upload PDF. "
            "Your selected material will appear here."
        ),
'''
PANEL_KN = '''        "setup_panel_desc": (  # NEEDS REVIEW
            "ಮೇಲೆ ಒಂದು ಅಧ್ಯಾಯವನ್ನು ಆರಿಸಿ, ಅಥವಾ “PDF ಅಪ್‌ಲೋಡ್” ಆಯ್ಕೆಮಾಡಿ. "
            "ನೀವು ಆರಿಸಿದ ಸಾಮಗ್ರಿ ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತದೆ."
        ),
'''


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
    if "def render_source_picker" in src:
        sys.exit("app.py already has render_source_picker. Looks like Issue 2 was applied already.")
    for needed in ("def check_pdf", "class FriendlyError", "def render_sidebar", "def _sidebar_label", "def cleanup_old_sessions"):
        if needed not in src:
            sys.exit(f"STOP: app.py has no '{needed}'. Apply Issues 1 and 3 first. Nothing was changed.")

    # Replace the sidebar (picker + upload) with main-page versions.
    src = swap(src, "def _sidebar_label(", SEP + "# Pipeline", BLOCK_PICKER, "sidebar section")
    src = swap(src, "def main() -> None:", 'if __name__ == "__main__":', BLOCK_MAIN, "main")
    src = rep(
        src,
        '        "retry_state",\n    ):',
        '        "retry_state",\n        "upload_path",\n        "upload_name",\n    ):',
        "reset_pipeline keys",
    )
    return src


def patch_strings(src):
    # Replace both setup_panel_desc blocks (English first, then Kannada).
    start = '        "setup_panel_desc": ('
    end = "        ),\n"
    out = src
    pos = 0
    for new in (PANEL_EN, PANEL_KN):
        i = out.find(start, pos)
        j = out.find(end, i) if i >= 0 else -1
        if i < 0 or j < 0:
            sys.exit("STOP: could not find setup_panel_desc in strings.py. Nothing was changed.")
        out = out[:i] + new + out[j + len(end):]
        pos = i + len(new)
    if out.count('"setup_panel_desc"') != 2 or "in the sidebar" in out or "ಸೈಡ್" in out:
        sys.exit("STOP: strings.py still mentions the sidebar after patching. Nothing was changed.")
    return out


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