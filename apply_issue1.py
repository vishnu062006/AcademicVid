"""
Applies Issue 1 (Kannada UI) to app.py.

Run from the project root, next to app.py and strings.py:
    python3 apply_issue1.py

It edits app.py in place (git keeps the old version), checks that the result is
valid Python, and refuses to write anything if a marker is not found.
Delete this script afterwards; do not commit it.
"""
import ast
import sys

SRC = "app.py"

SEP = "# ---------------------------------------------------------------------\n"

# ----------------------------------------------------------------------
# New code blocks
# ----------------------------------------------------------------------
BLOCK_HERO_SIDEBAR = r'''def inject_language_css() -> None:
    """Extra CSS for the language toggle, Kannada text shaping and small screens."""
    css = """
    <style>
    .field-label {
        color: #c7ccda; font-size: .85rem; font-weight: 600; margin: 12px 0 6px;
    }
    /* Language toggle: two compact buttons that stay side by side, even at 360px. */
    [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor) {
        flex-wrap: nowrap !important; max-width: 360px; gap: 8px !important;
        margin: 0 0 14px;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor)
    > div[data-testid="column"] {
        min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;
    }
    [data-testid="stMainBlockContainer"] div[data-testid="stHorizontalBlock"]:has(.lang-anchor)
    div[data-testid="stButton"] > button {
        min-height: 48px !important; padding: 8px 14px !important;
        justify-content: center !important; text-align: center !important;
        font-size: 15px !important;
    }
    /* Longer Kannada text must wrap instead of overflowing. */
    .hero-subtitle, .learning-promise span, .meta-pill, .section-heading,
    .section-description, .chapter-title, .chapter-hint, .format-card-caption,
    .action-copy, .field-label {
        overflow-wrap: anywhere; max-width: 100%;
    }
    .stButton > button, .stDownloadButton > button {
        height: auto !important; white-space: normal !important;
    }
    .stButton > button p, .stDownloadButton > button p { white-space: normal !important; }
    </style>
    """
    if st.session_state.get("selected_language") == "Kannada":
        css += """
        <style>
        /* Negative letter-spacing breaks Kannada conjuncts; use roomier line height. */
        h1, h2, h3, .brand-name, .hero-title, .section-heading, .chapter-title,
        .action-title, .eyebrow, .step-label, .brand-caption, .action-kicker, .chip {
            letter-spacing: 0 !important;
        }
        .hero-title { font-size: clamp(1.8rem, 6.5vw, 3rem) !important; line-height: 1.3 !important; }
        .hero-subtitle, .section-description, .chapter-hint, .action-copy,
        .format-card-caption { line-height: 1.8 !important; }
        </style>
        """
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


def _sidebar_label(text: str) -> None:
    st.sidebar.markdown(f'<div class="field-label">{text}</div>', unsafe_allow_html=True)


def render_sidebar() -> Tuple[str, Optional[str], object, Optional[str], Optional[str], Optional[str]]:
    # NOTE: widgets below use a fixed English label + a key + collapsed label, and we
    # draw the translated label ourselves. In Streamlit 1.31 a changed label makes a
    # widget reset, so translating the label directly would wipe the selected chapter
    # (or the uploaded PDF) every time the language is switched.
    st.sidebar.markdown(
        f"""
        <div class="brand-lockup">
          <div class="brand-mark">A</div>
          <div>
            <div class="brand-name">AcademicVid</div>
            <div class="brand-caption">{t("brand_caption")}</div>
          </div>
        </div>
        <div class="step-label">{t("source_label")}</div>
        """,
        unsafe_allow_html=True,
    )

    # Source selector: two buttons instead of a radio (button labels can change freely).
    source_cols = st.sidebar.columns(2, gap="small")
    for col, mode, label_key in zip(source_cols, SOURCE_OPTIONS, ("source_library", "source_upload")):
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
    source_mode = st.session_state.source_mode

    pdf_path = None
    uploaded_file = None
    selected_class = selected_subject = selected_chapter = None

    if source_mode == "Library":
        classes = list(CHAPTER_MANIFEST.keys())
        if not classes:
            st.sidebar.warning(t("lib_empty"))
        else:
            _sidebar_label(t("lib_class"))
            selected_class = st.sidebar.selectbox(
                "Class / grade", classes, key="sel_class", label_visibility="collapsed"
            )
            subjects = list(CHAPTER_MANIFEST.get(selected_class, {}).keys())
            if subjects:
                _sidebar_label(t("lib_subject"))
                selected_subject = st.sidebar.selectbox(
                    "Subject", subjects, key="sel_subject", label_visibility="collapsed"
                )
                chapters = list(CHAPTER_MANIFEST[selected_class].get(selected_subject, {}).keys())
                if chapters:
                    _sidebar_label(t("lib_chapter"))
                    selected_chapter = st.sidebar.selectbox(
                        "Chapter", chapters, key="sel_chapter", label_visibility="collapsed"
                    )
                    pdf_path = CHAPTER_MANIFEST[selected_class][selected_subject][selected_chapter]
                else:
                    st.sidebar.info(t("lib_no_chapters"))
            else:
                st.sidebar.info(t("lib_no_subjects"))
    else:
        _sidebar_label(t("upload_label"))
        uploaded_file = st.sidebar.file_uploader(
            "Chapter PDF",
            type=["pdf"],
            key="pdf_upload",
            label_visibility="collapsed",
        )
        # Streamlit's own "Drag and drop file here" text stays English in 1.31.1,
        # so explain it in the selected language right next to the uploader.
        st.sidebar.caption(t("upload_hint"))
        if uploaded_file is not None:
            st.sidebar.caption(t("upload_selected", name=uploaded_file.name))

    st.sidebar.markdown("---")
    st.sidebar.caption(t("sidebar_footer"))
    return source_mode, pdf_path, uploaded_file, selected_class, selected_subject, selected_chapter


'''

BLOCK_STRUCTURING = r'''def execute_ai_structuring(pdf_path: str, language: str) -> None:
    try:
        with st.status(t("status_analyzing"), expanded=True) as status:
            status.write(t("status_extract"))
            extracted = extract_chapter(pdf_path)
            clean_text = extracted.get("clean_text", "")
            if not clean_text.strip():
                raise ValueError(t("err_no_text"))
            status.write(t("status_structure"))
            chapter = structure_chapter(clean_text, language=language)
            if not getattr(chapter, "sections", None):
                raise ValueError(t("err_no_sections"))
            st.session_state.chapter = chapter
            # Keep the experience one-click: prepare the lesson, then generate
            # the selected resource without asking the learner to approve a script.
            st.session_state.app_state = "generating_media"
            status.update(label=t("status_lesson_ready"), state="complete")
    except Exception as exc:
        st.session_state.last_error = str(exc)
        st.error(t("err_prepare", error=exc))


'''

BLOCK_MEDIA_COMPLETE_ERROR = r'''def execute_media_generation(output_type: str, session_dir: str) -> None:
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
                        status.write(t("ppt_audio_failed", error=audio_exc))
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
        st.session_state.last_error = str(exc)
        st.session_state.app_state = "error"
        st.error(t("err_generation", error=exc))


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

    st.markdown("")
    if st.button(t("btn_another"), type="primary", use_container_width=True):
        reset_pipeline()
        st.rerun()


def render_error_state() -> None:
    st.markdown(f'<div class="section-heading">{t("error_heading")}</div>', unsafe_allow_html=True)
    st.error(st.session_state.get("last_error", t("error_default")))
    if st.button(t("btn_back_workspace"), type="primary"):
        reset_pipeline()
        st.rerun()


'''

BLOCK_MAIN = r'''def main() -> None:
    st.set_page_config(
        page_title="AcademicVid — AI Learning Studio",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    inject_custom_css()
    inject_language_css()
    render_language_toggle()
    render_brand_and_hero()

    source, library_pdf_path, uploaded_file, selected_class, selected_subject, selected_chapter = render_sidebar()
    pdf_path = None

    if source == "Library":
        pdf_path = library_pdf_path
    elif uploaded_file is not None:
        pdf_path = save_uploaded_pdf(uploaded_file, get_session_dir())

    if st.session_state.app_state == "setup":
        # STEP 1 — choose a chapter or upload a PDF.
        st.markdown('<div class="setup-content">', unsafe_allow_html=True)
        st.markdown(f'<div class="step-label">{t("setup_step")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-heading">{t("setup_heading")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-description">{t("setup_desc")}</div>',
            unsafe_allow_html=True,
        )

        if pdf_path:
            if source == "Library":
                chips = (
                    f'<span class="chip chip-accent">{t("chip_library")}</span>'
                    f'<span class="chip">{selected_class or ""}</span>'
                    f'<span class="chip">{selected_subject or ""}</span>'
                )
                title = selected_chapter or Path(pdf_path).stem
            else:
                chips = f'<span class="chip chip-accent">{t("chip_pdf")}</span>'
                title = uploaded_file.name if uploaded_file is not None else Path(pdf_path).name

            st.markdown(
                f'<div class="chapter-card"><div class="chip-row">{chips}</div>'
                f'<div class="chapter-title">{title}</div>'
                f'<div class="chapter-hint">{t("chapter_ready")}</div></div>',
                unsafe_allow_html=True,
            )
            _, next_col = st.columns([2, 1])
            with next_col:
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
        # This guarantees a real 2 × 2 layout across Streamlit versions.
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

        back_col, _ = st.columns([1, 2])
        with back_col:
            if st.button(t("btn_back"), use_container_width=True):
                st.session_state.app_state = "setup"
                st.rerun()

        # Keep the primary action and its AI progress/status centered in the workspace.
        _, action_col, _ = st.columns([1, 1.5, 1])
        with action_col:
            if st.button(t(f"action_{selected_output}"), type="primary", use_container_width=True):
                if not pdf_path:
                    st.warning(t("warn_no_material"))
                else:
                    execute_ai_structuring(pdf_path, st.session_state.selected_language)
                    if st.session_state.app_state == "generating_media":
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.app_state == "review":
        render_review_ui(st.session_state.last_generated_type)

    elif st.session_state.app_state == "generating_media":
        execute_media_generation(st.session_state.last_generated_type, get_session_dir())
        if st.session_state.app_state == "complete":
            st.rerun()

    elif st.session_state.app_state == "complete":
        render_completion(st.session_state.last_generated_type)

    elif st.session_state.app_state == "error":
        render_error_state()

    st.markdown(f'<div class="footer">{t("footer")}</div>', unsafe_allow_html=True)


'''


def swap(src, start, end, new, name):
    i = src.find(start)
    if i < 0:
        sys.exit(f"STOP: could not find start marker for {name}. Nothing was changed.")
    j = src.find(end, i)
    if j < 0:
        sys.exit(f"STOP: could not find end marker for {name}. Nothing was changed.")
    return src[:i] + new + src[j:]


def replace_once(src, old, new, name):
    if old not in src:
        sys.exit(f"STOP: could not find {name}. Nothing was changed.")
    return src.replace(old, new)


def main():
    with open(SRC, encoding="utf-8") as f:
        src = f.read()

    if "from strings import" in src:
        sys.exit("app.py already imports strings. Looks like the patch was applied already.")

    # 1. Import t() and the language labels.
    src = replace_once(
        src,
        "from flashcards import generate_flashcards\n",
        "from flashcards import generate_flashcards\nfrom strings import t, LANGUAGE_LABELS\n",
        "flashcards import",
    )

    # 2. Fonts: add Noto Sans Kannada to the Google Fonts import and every font stack.
    src = replace_once(
        src,
        "family=Space+Grotesk:wght@400;500;600;700&display=swap",
        "family=Space+Grotesk:wght@400;500;600;700&family=Noto+Sans+Kannada:wght@400;500;600;700&display=swap",
        "Google Fonts import",
    )
    src = replace_once(
        src,
        "'DM Sans', sans-serif",
        "'DM Sans', 'Noto Sans Kannada', 'Nirmala UI', sans-serif",
        "DM Sans stack",
    )
    src = replace_once(
        src,
        "'Space Grotesk', sans-serif",
        "'Space Grotesk', 'Noto Sans Kannada', 'Nirmala UI', sans-serif",
        "Space Grotesk stack",
    )

    # 3. Swap whole functions for their translated versions.
    src = swap(src, "def render_brand_and_hero() -> None:", SEP + "# Pipeline", BLOCK_HERO_SIDEBAR, "hero + sidebar")
    src = swap(src, "def execute_ai_structuring(", "def render_review_ui(", BLOCK_STRUCTURING, "structuring")
    src = swap(src, "def execute_media_generation(", SEP + "# Main app", BLOCK_MEDIA_COMPLETE_ERROR, "media/complete/error")
    src = swap(src, "def main() -> None:", 'if __name__ == "__main__":', BLOCK_MAIN, "main")

    try:
        ast.parse(src)
    except SyntaxError as exc:
        sys.exit(f"STOP: the patched file has a syntax error ({exc}). Nothing was changed.")

    with open(SRC, "w", encoding="utf-8") as f:
        f.write(src)
    print("Done. app.py updated. Now run: streamlit run app.py")


if __name__ == "__main__":
    main()