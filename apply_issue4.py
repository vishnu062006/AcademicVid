"""
Applies Issue 4 (optional script review step) to app.py and strings.py.

Needs Issues 1, 3 and 2 already applied (it checks).
Branch first:   git checkout -b feature/script-review
Run from the project root (next to app.py and strings.py):
    python3 apply_issue4.py

Checks every marker first and refuses to write anything if one is missing.
Delete this script afterwards; do not commit it.
"""
import ast
import sys

BLOCK_REVIEW = r'''SUBJECT_OPTIONS = ["Science", "Math", "Social Science", "English", "Other"]


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


'''

CHECKBOX_OLD = "        # Full-width buttons (no side columns) so nothing is squeezed on a phone.\n"
CHECKBOX_NEW = '''        # Optional teacher step. OFF by default so the one-click flow is unchanged.
        # The choice is also kept in a plain session key (widget state is dropped
        # whenever this screen is not drawn).
        review_on = st.checkbox(
            t("review_checkbox"),
            value=st.session_state.get("review_enabled", False),
            key="review_cb",
        )
        st.session_state.review_enabled = review_on

''' + CHECKBOX_OLD

ROUTE_OLD = '''            st.session_state.app_state = "generating_media"
            status.update(label=t("status_lesson_ready"), state="complete")
'''
ROUTE_NEW = '''            if st.session_state.get("review_enabled"):
                st.session_state.app_state = "review"
                status.update(label=t("status_lesson_review"), state="complete")
            else:
                st.session_state.app_state = "generating_media"
                status.update(label=t("status_lesson_ready"), state="complete")
'''

EN_ANCHOR = '        "tech_details": "Technical details",\n'
KN_ANCHOR = '        "tech_details": "ತಾಂತ್ರಿಕ ವಿವರಗಳು",  # NEEDS REVIEW\n'

STRINGS_EN = '''        "review_checkbox": "Review the script before generating (recommended for teachers)",
        "status_lesson_review": "Lesson prepared — ready for your review",
        "review_step": "Step 02 / Refine",
        "review_heading": "Review your lesson script",
        "review_desc": "Make the content yours before generating the final learning resource.",
        "review_info": "Review the AI-generated content and correct anything that needs attention before continuing. The narration script is what the video will say aloud.",
        "review_chapter_title": "Chapter title",
        "review_subject": "Subject",
        "review_section": "SECTION",
        "review_section_title": "Section title",
        "review_hook": "Opening hook",
        "review_concept": "Core concept",
        "review_misconception": "Common misconception",
        "review_example": "Real-world example",
        "review_key_points": "Key points (one per line)",
        "review_narration": "Narration script",
        "review_continue": "Continue to {format}",
        "review_cancel": "Cancel",
        "review_invalid": "Some edits are not valid. Please make sure no field is empty, then try again.",
        "review_no_chapter": "No chapter is loaded. Start again from the workspace.",
        "review_back": "Back to setup",
'''
STRINGS_KN = '''        "review_checkbox": "ರಚಿಸುವ ಮೊದಲು ಸ್ಕ್ರಿಪ್ಟ್ ಪರಿಶೀಲಿಸಿ (ಶಿಕ್ಷಕರಿಗೆ ಶಿಫಾರಸು)",  # NEEDS REVIEW
        "status_lesson_review": "ಪಾಠ ಸಿದ್ಧವಾಗಿದೆ — ನಿಮ್ಮ ಪರಿಶೀಲನೆಗೆ ಸಿದ್ಧ",  # NEEDS REVIEW
        "review_step": "ಹಂತ 02 / ಪರಿಷ್ಕರಿಸಿ",  # NEEDS REVIEW
        "review_heading": "ನಿಮ್ಮ ಪಾಠದ ಸ್ಕ್ರಿಪ್ಟ್ ಪರಿಶೀಲಿಸಿ",  # NEEDS REVIEW
        "review_desc": "ಅಂತಿಮ ಕಲಿಕಾ ಸಾಮಗ್ರಿ ರಚಿಸುವ ಮೊದಲು ವಿಷಯವನ್ನು ನಿಮ್ಮದಾಗಿಸಿ.",  # NEEDS REVIEW
        "review_info": "AI ರಚಿಸಿದ ವಿಷಯವನ್ನು ಪರಿಶೀಲಿಸಿ, ತಿದ್ದಬೇಕಾದುದನ್ನು ಸರಿಪಡಿಸಿ. ನಿರೂಪಣೆಯ ಸ್ಕ್ರಿಪ್ಟ್‌ನಲ್ಲಿರುವುದನ್ನೇ ವಿಡಿಯೋ ಧ್ವನಿಯಲ್ಲಿ ಹೇಳುತ್ತದೆ.",  # NEEDS REVIEW
        "review_chapter_title": "ಅಧ್ಯಾಯದ ಶೀರ್ಷಿಕೆ",  # NEEDS REVIEW
        "review_subject": "ವಿಷಯ",  # NEEDS REVIEW
        "review_section": "ವಿಭಾಗ",  # NEEDS REVIEW
        "review_section_title": "ವಿಭಾಗದ ಶೀರ್ಷಿಕೆ",  # NEEDS REVIEW
        "review_hook": "ಆರಂಭಿಕ ಆಕರ್ಷಣೆ",  # NEEDS REVIEW
        "review_concept": "ಮುಖ್ಯ ಪರಿಕಲ್ಪನೆ",  # NEEDS REVIEW
        "review_misconception": "ಸಾಮಾನ್ಯ ತಪ್ಪು ಕಲ್ಪನೆ",  # NEEDS REVIEW
        "review_example": "ನಿಜ ಜೀವನದ ಉದಾಹರಣೆ",  # NEEDS REVIEW
        "review_key_points": "ಮುಖ್ಯ ಅಂಶಗಳು (ಪ್ರತಿ ಸಾಲಿಗೆ ಒಂದು)",  # NEEDS REVIEW
        "review_narration": "ನಿರೂಪಣೆಯ ಸ್ಕ್ರಿಪ್ಟ್",  # NEEDS REVIEW
        "review_continue": "{format} ಗೆ ಮುಂದುವರಿಯಿರಿ",  # NEEDS REVIEW
        "review_cancel": "ರದ್ದುಮಾಡಿ",  # NEEDS REVIEW
        "review_invalid": "ಕೆಲವು ಬದಲಾವಣೆಗಳು ಸರಿಯಿಲ್ಲ. ಯಾವುದೇ ಕ್ಷೇತ್ರ ಖಾಲಿ ಇಲ್ಲವೆಂದು ಖಚಿತಪಡಿಸಿ, ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "review_no_chapter": "ಯಾವುದೇ ಅಧ್ಯಾಯ ಲೋಡ್ ಆಗಿಲ್ಲ. ಮುಖಪುಟದಿಂದ ಮತ್ತೆ ಆರಂಭಿಸಿ.",  # NEEDS REVIEW
        "review_back": "ಸೆಟಪ್‌ಗೆ ಹಿಂತಿರುಗಿ",  # NEEDS REVIEW
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
    if "def _chapter_is_valid" in src:
        sys.exit("app.py already has _chapter_is_valid. Looks like Issue 4 was applied already.")
    for needed in ("def render_source_picker", "def set_error", "def render_review_ui"):
        if needed not in src:
            sys.exit(f"STOP: app.py has no '{needed}'. Apply Issues 1, 3 and 2 first. Nothing was changed.")
    src = swap(src, "def render_review_ui(", "def execute_media_generation(", BLOCK_REVIEW, "review screen")
    src = rep(src, ROUTE_OLD, ROUTE_NEW, "route after structuring")
    src = rep(src, CHECKBOX_OLD, CHECKBOX_NEW, "checkbox position")
    src = rep(
        src,
        'if st.session_state.app_state in ("generating_media", "error"):',
        'if st.session_state.app_state in ("generating_media", "review", "error"):',
        "rerun after structuring",
    )
    return src


def patch_strings(src):
    if '"review_checkbox"' in src:
        sys.exit("strings.py already has review_checkbox. Looks like Issue 4 was applied already.")
    src = rep(src, EN_ANCHOR, EN_ANCHOR + STRINGS_EN, "English tech_details line (apply Issue 3 first)")
    src = rep(src, KN_ANCHOR, KN_ANCHOR + STRINGS_KN, "Kannada tech_details line (apply Issue 3 first)")
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