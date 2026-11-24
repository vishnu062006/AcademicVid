"""
All visible UI text for AcademicVid, in English and Kannada.

Usage in app.py:
    from strings import t
    st.markdown(t("hero_eyebrow"))
    st.write(t("status_slides", i=1, n=5))   # {placeholders} are filled by t()

Rules:
- English is the master list. Every key must exist in English.
- If a key is missing in Kannada, t() silently shows the English text.
- If a key is missing everywhere, t() returns the key itself (never crashes).
- Do not translate the brand name "AcademicVid".
- Every Kannada line is marked "# NEEDS REVIEW": a native speaker must check
  the wording before the pilot.
"""
import streamlit as st

# Text shown on the language toggle buttons (always in their own language).
LANGUAGE_LABELS = {"English": "English", "Kannada": "ಕನ್ನಡ"}

STRINGS = {
    "English": {
        # --- Hero -------------------------------------------------------
        "hero_eyebrow": "AI-powered learning workspace",
        "hero_title_1": "Learn it.",
        "hero_title_2": "See it. Remember it.",
        "hero_subtitle": (
            "Turn your textbook chapter into a lesson that is easier to understand and remember. "
            "Learn with clear explanations, everyday examples, and narration in English or Kannada."
        ),
        "promise_1": "Simple, step-by-step explanations",
        "promise_2": "Examples from everyday life",
        "promise_3_badge": "ಕನ್ನಡ",
        "promise_3": "Learn in English or Kannada",
        "pill_1": "PDF → structured lesson",
        "pill_2": "Clear explanations & examples",
        "pill_3": "Ready-to-use study resources",
        # --- Sidebar ----------------------------------------------------
        "brand_caption": "AI Learning Studio",
        "source_label": "Source material",
        "source_library": "Library",
        "source_upload": "Upload PDF",
        "lib_empty": "The library is empty. Upload a PDF to get started.",
        "lib_class": "Class / grade",
        "lib_subject": "Subject",
        "lib_chapter": "Chapter",
        "lib_no_chapters": "No chapters are available for this subject yet.",
        "lib_no_subjects": "No subjects are available for this class yet.",
        "upload_label": "Drop in a chapter PDF",
        "upload_hint": "Drag your PDF here, or tap “Browse files” to choose it.",
        "upload_selected": "Selected: {name}",
        "source_notes": "Handwritten notes",
        "source_topics": "Custom topics",
        "kind_label": "What kind of lesson is this?",
        "kind_chapter": "Subject chapter (Science, Maths, Social...)",
        "kind_kannada": "Kannada subject: story or poem",
        "kind_kannada_hint": "The lesson will follow the story or poem part by part, in Kannada: meaning, word meanings, context lines and values.",
        "notes_label": "Photos of your notes, or a scanned PDF",
        "notes_hint": "Up to {max} photos or one scanned PDF. Take photos in good light, one page per photo.",
        "notes_too_many": "Only the first {max} files will be read.",
        "notes_read_btn": "Read my notes",
        "notes_reading": "Reading your notes... this can take up to a minute.",
        "notes_nothing_read": "No text could be read. Try clearer photos with more light.",
        "notes_check_label": "Check the text we read",
        "notes_check_hint": "Handwriting can be misread. Fix any wrong words here; the lesson is made from this text.",
        "topics_intro": "Type your own subject and the topics to cover. The lesson teaches every topic, one section each. No PDF needed.",
        "topics_subject": "Subject",
        "topics_subject_ph": "e.g. Operating Systems",
        "topics_level": "Level",
        "level_engineering": "Engineering (B.E. / B.Tech)",
        "level_puc": "PUC / Class 11-12",
        "level_school": "School (Class 6-10)",
        "level_other": "Other",
        "topics_list": "Topics, one per line (up to {max})",
        "topics_list_ph": "Process scheduling\n- FCFS, SJF, Round Robin\nDeadlocks\nPaging and segmentation",
        "topics_too_many": "{count} topics: please keep it to {max} or fewer. Split the rest into another lesson.",
        "topics_count": "{count} topics. Lines starting with '-' are your notes for the topic above them.",
        "sidebar_footer": "Built for clearer learning, one chapter at a time.",
        # --- Step 1: setup ---------------------------------------------
        "setup_step": "Step 01 / Choose your material",
        "setup_heading": "What do you want to learn today?",
        "setup_desc": (
            "Choose a library chapter, upload a PDF, photograph your handwritten notes, or type your own topics. "
            "We’ll decide how to study it in the next step."
        ),
        "chip_library": "Library",
        "chip_pdf": "Your PDF",
        "chip_topics": "Custom topics",
        "chip_notes": "Your notes",
        "chip_kannada_lesson": "Kannada story / poem",
        "chapter_ready": "Great choice! Your learning material is ready.",
        "btn_next_format": "Next: Choose a learning format  →",
        "setup_panel_title": "Start with a chapter or PDF",
        "setup_panel_desc": (
            "Pick a chapter above, or choose another source. "
            "Your selected material will appear here."
        ),
        # --- Step 2: choose format -------------------------------------
        "choose_step": "Step 02 / Choose your learning style",
        "choose_heading": "How would you like to learn?",
        "choose_desc": "Pick one format. You can go back and change your chapter at any time.",
        "format_video": "Video",
        "format_video_desc": "Animated lesson with AI narration",
        "format_ppt": "PPT",
        "format_ppt_desc": "Editable presentation deck",
        "format_transcript": "Transcript PDF",
        "format_transcript_desc": "Clean, printable study notes",
        "format_flashcards": "Flashcards",
        "format_flashcards_desc": "Quick recall and revision cards",
        "selected_format": "YOUR SELECTED FORMAT",
        "btn_back": "← Back to chapter",
        "action_video": "Generate lesson video  →",
        "action_ppt": "Generate presentation  →",
        "action_transcript": "Create study notes  →",
        "action_flashcards": "Create flashcards  →",
        "warn_no_material": "Please select a chapter or upload a PDF first.",
        # --- Generating -------------------------------------------------
        "status_analyzing": "Analyzing your chapter…",
        "status_extract": "Extracting readable text from the PDF.",
        "status_structure": "Structuring the chapter into a lesson with AI.",
        "status_lesson_ready": "Lesson prepared — starting generation",
        "err_no_text": "No readable text was found. If this is a scanned or photographed document, use \u201cHandwritten notes\u201d instead.",
        "err_no_sections": "The AI did not return any lesson sections. Please try again.",
        "err_prepare": "Could not prepare the script: {error}",
        "status_building": "Building your learning resource…",
        "status_slides": "Section {i}/{n} · Building teaching slides",
        "status_narration": "Section {i}/{n} · Synthesizing narration",
        "status_assembling": "Section {i}/{n} · Assembling video",
        "status_combining": "Combining all lesson sections.",
        "status_ppt": "Creating your editable presentation.",
        "status_audio": "Creating {language} narration audio.",
        "ppt_audio_failed": "Presentation is ready, but narration audio could not be generated: {error}",
        "ppt_voice_hint": "The voice is inside the slides. Open the file in PowerPoint and press Slide Show (F5): each slide reads itself out and moves on by itself.",
        "status_notes": "Formatting your study notes as a PDF.",
        "status_flashcards": "Generating question-and-answer flashcards.",
        "status_ready": "Your resource is ready",
        "err_no_chapter": "No chapter is available to generate.",
        "err_generation": "Generation failed: {error}",
        "err_quota": "Today’s free AI limit has been reached. Please try again in a few minutes, or tomorrow.",
        "status_downloading": "Getting the chapter from the official textbook website…",
        "status_reading_pages": "Reading the pages (this book uses an old Kannada font or is scanned)… this can take a minute.",
        "err_library_download": "Could not get this chapter from the official textbook website. Please try again in a few minutes, or upload the PDF yourself.",
        "quiz_offer_title": "Want a quick quiz on this lesson?",
        "quiz_offer_desc": "{n} short board-exam style questions, with answers and explanations. Useful to check what students remember.",
        "quiz_offer_btn": "Yes, show the quiz",
        "quiz_heading": "Quick quiz",
        "quiz_check": "Check answers",
        "quiz_score": "Score: {score} / {total}",
        "quiz_correct": "Correct!",
        "quiz_wrong": "Not quite. The correct answer is: {answer}",
        "quiz_unanswered": "Not answered. The correct answer is: {answer}",
        "status_cached": "This lesson was made before: ready instantly.",
        "status_slides_all": "Drawing the slides for all {n} sections…",
        "status_voice_all": "Recording the narration for all {n} sections at once…",
        "err_slow": "The AI service is busy and took too long to answer. Please try again in a minute.",
        "err_network": "Could not connect to the internet or the AI service. Please check your connection and try again.",
        "err_too_long": "This PDF has {pages} pages. The limit is {limit} pages, so lessons stay quick on slow connections. Please upload a shorter chapter.",
        "err_unreadable_pdf": "This PDF could not be opened. It may be damaged or password-protected. Please try another file.",
        "err_unexpected": "Something went wrong while making your lesson. Please try again.",
        "btn_try_again": "Try again",
        "tech_details": "Technical details",
        "review_checkbox": "Review the script before generating (recommended for teachers)",
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
        "report_button": "Report a problem with this lesson",
        "report_not_ready": "The report form link has not been set up yet.",
        "lang_name_English": "English",
        "lang_name_Kannada": "Kannada",
        # --- Step 3: complete ------------------------------------------
        "done_step": "Step 03 / Ready",
        "done_heading": "Your learning resource is ready",
        "done_desc": "Open it here or download a copy for your next study session.",
        "dl_video": "Download lesson video",
        "warn_video_missing": "The video file could not be found in this session.",
        "dl_ppt": "Download editable presentation",
        "warn_ppt_missing": "The presentation file could not be found in this session.",
        "audio_heading": "Lesson narration audio",
        "dl_audio": "Download {language} narration (MP3)",
        "dl_transcript": "Download transcript PDF",
        "warn_transcript_missing": "The transcript PDF could not be found in this session.",
        "cards_count": "{count} cards generated",
        "card_title": "CARD {num}  ·  {front}",
        "card_default_front": "Question",
        "warn_no_flashcards": "No flashcards were returned for this chapter.",
        "view_data": "View structured lesson data",
        "btn_another": "Create another lesson",
        # --- Error screen + footer -------------------------------------
        "error_heading": "Something went wrong",
        "error_default": "An unexpected error occurred.",
        "btn_back_workspace": "Back to workspace",
        "footer": "{app} &nbsp;·&nbsp; AI LEARNING STUDIO &nbsp;·&nbsp; LEARN WITH CLARITY",
    },
    "Kannada": {
        # --- Hero -------------------------------------------------------
        "hero_eyebrow": "AI ಆಧಾರಿತ ಕಲಿಕಾ ವೇದಿಕೆ",  # NEEDS REVIEW
        "hero_title_1": "ಕಲಿಯಿರಿ.",  # NEEDS REVIEW
        "hero_title_2": "ನೋಡಿ. ನೆನಪಿಡಿ.",  # NEEDS REVIEW
        "hero_subtitle": (  # NEEDS REVIEW
            "ನಿಮ್ಮ ಪಠ್ಯಪುಸ್ತಕದ ಅಧ್ಯಾಯವನ್ನು ಸುಲಭವಾಗಿ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಮತ್ತು ನೆನಪಿಡಲು ಸಹಾಯ ಮಾಡುವ ಪಾಠವನ್ನಾಗಿ ಪರಿವರ್ತಿಸಿ. "
            "ಸ್ಪಷ್ಟ ವಿವರಣೆ, ದಿನನಿತ್ಯದ ಉದಾಹರಣೆಗಳು ಮತ್ತು ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ನಿರೂಪಣೆಯೊಂದಿಗೆ ಕಲಿಯಿರಿ."
        ),
        "promise_1": "ಸರಳ, ಹಂತ ಹಂತದ ವಿವರಣೆಗಳು",  # NEEDS REVIEW
        "promise_2": "ದಿನನಿತ್ಯದ ಜೀವನದ ಉದಾಹರಣೆಗಳು",  # NEEDS REVIEW
        "promise_3_badge": "EN",  # NEEDS REVIEW
        "promise_3": "ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಕಲಿಯಿರಿ",  # NEEDS REVIEW
        "pill_1": "PDF → ರಚನಾತ್ಮಕ ಪಾಠ",  # NEEDS REVIEW
        "pill_2": "ಸ್ಪಷ್ಟ ವಿವರಣೆ ಮತ್ತು ಉದಾಹರಣೆಗಳು",  # NEEDS REVIEW
        "pill_3": "ಬಳಸಲು ಸಿದ್ಧ ಅಧ್ಯಯನ ಸಾಮಗ್ರಿ",  # NEEDS REVIEW
        # --- Sidebar ----------------------------------------------------
        "brand_caption": "AI ಕಲಿಕಾ ಸ್ಟುಡಿಯೋ",  # NEEDS REVIEW
        "source_label": "ಸಾಮಗ್ರಿಯ ಮೂಲ",  # NEEDS REVIEW
        "source_library": "ಗ್ರಂಥಾಲಯ",  # NEEDS REVIEW
        "source_upload": "PDF ಅಪ್‌ಲೋಡ್",  # NEEDS REVIEW
        "lib_empty": "ಗ್ರಂಥಾಲಯ ಖಾಲಿಯಾಗಿದೆ. ಪ್ರಾರಂಭಿಸಲು PDF ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",  # NEEDS REVIEW
        "lib_class": "ತರಗತಿ",  # NEEDS REVIEW
        "lib_subject": "ವಿಷಯ",  # NEEDS REVIEW
        "lib_chapter": "ಅಧ್ಯಾಯ",  # NEEDS REVIEW
        "lib_no_chapters": "ಈ ವಿಷಯಕ್ಕೆ ಇನ್ನೂ ಅಧ್ಯಾಯಗಳು ಲಭ್ಯವಿಲ್ಲ.",  # NEEDS REVIEW
        "lib_no_subjects": "ಈ ತರಗತಿಗೆ ಇನ್ನೂ ವಿಷಯಗಳು ಲಭ್ಯವಿಲ್ಲ.",  # NEEDS REVIEW
        "upload_label": "ಅಧ್ಯಾಯದ PDF ಇಲ್ಲಿ ಹಾಕಿ",  # NEEDS REVIEW
        "upload_hint": "PDF ಫೈಲ್ ಅನ್ನು ಇಲ್ಲಿ ಎಳೆದು ಬಿಡಿ, ಅಥವಾ “Browse files” ಒತ್ತಿ ಆಯ್ಕೆಮಾಡಿ.",  # NEEDS REVIEW
        "upload_selected": "ಆಯ್ಕೆ: {name}",  # NEEDS REVIEW
        "source_notes": "ಕೈಬರಹದ ಟಿಪ್ಪಣಿ",  # NEEDS REVIEW
        "source_topics": "ನಿಮ್ಮ ವಿಷಯಗಳು",  # NEEDS REVIEW
        "kind_label": "ಇದು ಯಾವ ರೀತಿಯ ಪಾಠ?",  # NEEDS REVIEW
        "kind_chapter": "ವಿಷಯದ ಅಧ್ಯಾಯ (ವಿಜ್ಞಾನ, ಗಣಿತ, ಸಮಾಜ...)",  # NEEDS REVIEW
        "kind_kannada": "ಕನ್ನಡ ವಿಷಯ: ಕಥೆ ಅಥವಾ ಪದ್ಯ",  # NEEDS REVIEW
        "kind_kannada_hint": "ಪಾಠವು ಕಥೆ ಅಥವಾ ಪದ್ಯವನ್ನು ಭಾಗ ಭಾಗವಾಗಿ ಅನುಸರಿಸುತ್ತದೆ: ಭಾವಾರ್ಥ, ಪದಗಳ ಅರ್ಥ, ಸಂದರ್ಭ ಮತ್ತು ಮೌಲ್ಯಗಳು.",  # NEEDS REVIEW
        "notes_label": "ನಿಮ್ಮ ಟಿಪ್ಪಣಿಗಳ ಫೋಟೋಗಳು ಅಥವಾ ಸ್ಕ್ಯಾನ್ ಮಾಡಿದ PDF",  # NEEDS REVIEW
        "notes_hint": "ಗರಿಷ್ಠ {max} ಫೋಟೋಗಳು ಅಥವಾ ಒಂದು ಸ್ಕ್ಯಾನ್ PDF. ಒಳ್ಳೆಯ ಬೆಳಕಿನಲ್ಲಿ, ಒಂದು ಫೋಟೋಗೆ ಒಂದು ಪುಟ.",  # NEEDS REVIEW
        "notes_too_many": "ಮೊದಲ {max} ಫೈಲ್‌ಗಳನ್ನು ಮಾತ್ರ ಓದಲಾಗುತ್ತದೆ.",  # NEEDS REVIEW
        "notes_read_btn": "ನನ್ನ ಟಿಪ್ಪಣಿ ಓದಿ",  # NEEDS REVIEW
        "notes_reading": "ನಿಮ್ಮ ಟಿಪ್ಪಣಿಗಳನ್ನು ಓದಲಾಗುತ್ತಿದೆ... ಒಂದು ನಿಮಿಷ ಆಗಬಹುದು.",  # NEEDS REVIEW
        "notes_nothing_read": "ಯಾವುದೇ ಪಠ್ಯ ಓದಲು ಆಗಲಿಲ್ಲ. ಹೆಚ್ಚು ಬೆಳಕಿನಲ್ಲಿ ಸ್ಪಷ್ಟ ಫೋಟೋ ತೆಗೆಯಿರಿ.",  # NEEDS REVIEW
        "notes_check_label": "ಓದಿದ ಪಠ್ಯವನ್ನು ಪರಿಶೀಲಿಸಿ",  # NEEDS REVIEW
        "notes_check_hint": "ಕೈಬರಹ ತಪ್ಪಾಗಿ ಓದಬಹುದು. ತಪ್ಪು ಪದಗಳನ್ನು ಇಲ್ಲಿ ಸರಿಪಡಿಸಿ; ಈ ಪಠ್ಯದಿಂದಲೇ ಪಾಠ ತಯಾರಾಗುತ್ತದೆ.",  # NEEDS REVIEW
        "topics_intro": "ನಿಮ್ಮ ವಿಷಯ ಮತ್ತು ಕಲಿಸಬೇಕಾದ ಟಾಪಿಕ್‌ಗಳನ್ನು ಬರೆಯಿರಿ. ಪ್ರತಿ ಟಾಪಿಕ್‌ಗೆ ಒಂದು ಭಾಗ. PDF ಬೇಕಿಲ್ಲ.",  # NEEDS REVIEW
        "topics_subject": "ವಿಷಯ",  # NEEDS REVIEW
        "topics_subject_ph": "ಉದಾ: Operating Systems",  # NEEDS REVIEW
        "topics_level": "ಹಂತ",  # NEEDS REVIEW
        "level_engineering": "ಎಂಜಿನಿಯರಿಂಗ್ (B.E. / B.Tech)",  # NEEDS REVIEW
        "level_puc": "ಪಿಯುಸಿ / 11-12ನೇ ತರಗತಿ",  # NEEDS REVIEW
        "level_school": "ಶಾಲೆ (6-10ನೇ ತರಗತಿ)",  # NEEDS REVIEW
        "level_other": "ಇತರೆ",  # NEEDS REVIEW
        "topics_list": "ಟಾಪಿಕ್‌ಗಳು, ಸಾಲಿಗೆ ಒಂದು (ಗರಿಷ್ಠ {max})",  # NEEDS REVIEW
        "topics_too_many": "{count} ಟಾಪಿಕ್‌ಗಳು: ದಯವಿಟ್ಟು {max} ಅಥವಾ ಕಡಿಮೆ ಇರಿಸಿ. ಉಳಿದವನ್ನು ಇನ್ನೊಂದು ಪಾಠವಾಗಿ ಮಾಡಿ.",  # NEEDS REVIEW
        "topics_count": "{count} ಟಾಪಿಕ್‌ಗಳು. '-' ನಿಂದ ಆರಂಭವಾಗುವ ಸಾಲುಗಳು ಮೇಲಿನ ಟಾಪಿಕ್‌ನ ಟಿಪ್ಪಣಿಗಳು.",  # NEEDS REVIEW
        "sidebar_footer": "ಒಂದು ಬಾರಿಗೆ ಒಂದು ಅಧ್ಯಾಯ — ಸ್ಪಷ್ಟ ಕಲಿಕೆಗಾಗಿ ರೂಪಿಸಲಾಗಿದೆ.",  # NEEDS REVIEW
        # --- Step 1: setup ---------------------------------------------
        "setup_step": "ಹಂತ 01 / ನಿಮ್ಮ ಸಾಮಗ್ರಿಯನ್ನು ಆರಿಸಿ",  # NEEDS REVIEW
        "setup_heading": "ಇಂದು ನೀವು ಏನು ಕಲಿಯಲು ಬಯಸುತ್ತೀರಿ?",  # NEEDS REVIEW
        "setup_desc": (  # NEEDS REVIEW
            "ಗ್ರಂಥಾಲಯದ ಅಧ್ಯಾಯ ಆರಿಸಿ, PDF ಅಪ್‌ಲೋಡ್ ಮಾಡಿ, ಕೈಬರಹದ ಟಿಪ್ಪಣಿಯ ಫೋಟೋ ಹಾಕಿ, ಅಥವಾ ನಿಮ್ಮ ವಿಷಯಗಳನ್ನು ಬರೆಯಿರಿ. "
            "ಅದನ್ನು ಹೇಗೆ ಕಲಿಯಬೇಕೆಂದು ಮುಂದಿನ ಹಂತದಲ್ಲಿ ಆರಿಸೋಣ."
        ),
        "chip_library": "ಗ್ರಂಥಾಲಯ",  # NEEDS REVIEW
        "chip_pdf": "ನಿಮ್ಮ PDF",  # NEEDS REVIEW
        "chip_topics": "ನಿಮ್ಮ ವಿಷಯಗಳು",  # NEEDS REVIEW
        "chip_notes": "ನಿಮ್ಮ ಟಿಪ್ಪಣಿ",  # NEEDS REVIEW
        "chip_kannada_lesson": "ಕನ್ನಡ ಕಥೆ / ಪದ್ಯ",  # NEEDS REVIEW
        "chapter_ready": "ಚೆನ್ನಾಗಿದೆ! ನಿಮ್ಮ ಕಲಿಕಾ ಸಾಮಗ್ರಿ ಸಿದ್ಧವಾಗಿದೆ.",  # NEEDS REVIEW
        "btn_next_format": "ಮುಂದೆ: ಕಲಿಕೆಯ ಮಾದರಿಯನ್ನು ಆರಿಸಿ  →",  # NEEDS REVIEW
        "setup_panel_title": "ಒಂದು ಅಧ್ಯಾಯ ಅಥವಾ PDF ಆರಿಸಿ",  # NEEDS REVIEW
        "setup_panel_desc": (  # NEEDS REVIEW
            "ಮೇಲೆ ಒಂದು ಅಧ್ಯಾಯವನ್ನು ಆರಿಸಿ, ಅಥವಾ ಬೇರೆ ಮೂಲವನ್ನು ಆಯ್ಕೆಮಾಡಿ. "
            "ನೀವು ಆರಿಸಿದ ಸಾಮಗ್ರಿ ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತದೆ."
        ),
        # --- Step 2: choose format -------------------------------------
        "choose_step": "ಹಂತ 02 / ನಿಮ್ಮ ಕಲಿಕೆಯ ಶೈಲಿಯನ್ನು ಆರಿಸಿ",  # NEEDS REVIEW
        "choose_heading": "ನೀವು ಹೇಗೆ ಕಲಿಯಲು ಬಯಸುತ್ತೀರಿ?",  # NEEDS REVIEW
        "choose_desc": "ಒಂದು ಮಾದರಿಯನ್ನು ಆರಿಸಿ. ಯಾವಾಗ ಬೇಕಾದರೂ ಹಿಂದೆ ಹೋಗಿ ಅಧ್ಯಾಯವನ್ನು ಬದಲಾಯಿಸಬಹುದು.",  # NEEDS REVIEW
        "format_video": "ವಿಡಿಯೋ",  # NEEDS REVIEW
        "format_video_desc": "AI ನಿರೂಪಣೆಯೊಂದಿಗೆ ಅನಿಮೇಟೆಡ್ ಪಾಠ",  # NEEDS REVIEW
        "format_ppt": "ಪ್ರೆಸೆಂಟೇಶನ್ (PPT)",  # NEEDS REVIEW
        "format_ppt_desc": "ಸಂಪಾದಿಸಬಹುದಾದ ಪ್ರೆಸೆಂಟೇಶನ್",  # NEEDS REVIEW
        "format_transcript": "ಅಧ್ಯಯನ ಟಿಪ್ಪಣಿಗಳು (PDF)",  # NEEDS REVIEW
        "format_transcript_desc": "ಮುದ್ರಿಸಲು ಸಿದ್ಧ, ಸ್ಪಷ್ಟ ಅಧ್ಯಯನ ಟಿಪ್ಪಣಿಗಳು",  # NEEDS REVIEW
        "format_flashcards": "ಫ್ಲ್ಯಾಶ್ ಕಾರ್ಡ್‌ಗಳು",  # NEEDS REVIEW
        "format_flashcards_desc": "ತ್ವರಿತ ಮರುಸ್ಮರಣೆ ಮತ್ತು ಪುನರಾವರ್ತನೆಗಾಗಿ ಕಾರ್ಡ್‌ಗಳು",  # NEEDS REVIEW
        "selected_format": "ನೀವು ಆರಿಸಿದ ಮಾದರಿ",  # NEEDS REVIEW
        "btn_back": "← ಅಧ್ಯಾಯಕ್ಕೆ ಹಿಂತಿರುಗಿ",  # NEEDS REVIEW
        "action_video": "ಪಾಠದ ವಿಡಿಯೋ ರಚಿಸಿ  →",  # NEEDS REVIEW
        "action_ppt": "ಪ್ರೆಸೆಂಟೇಶನ್ ರಚಿಸಿ  →",  # NEEDS REVIEW
        "action_transcript": "ಅಧ್ಯಯನ ಟಿಪ್ಪಣಿಗಳನ್ನು ರಚಿಸಿ  →",  # NEEDS REVIEW
        "action_flashcards": "ಫ್ಲ್ಯಾಶ್ ಕಾರ್ಡ್‌ಗಳನ್ನು ರಚಿಸಿ  →",  # NEEDS REVIEW
        "warn_no_material": "ದಯವಿಟ್ಟು ಮೊದಲು ಒಂದು ಅಧ್ಯಾಯವನ್ನು ಆರಿಸಿ ಅಥವಾ PDF ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",  # NEEDS REVIEW
        # --- Generating -------------------------------------------------
        "status_analyzing": "ನಿಮ್ಮ ಅಧ್ಯಾಯವನ್ನು ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ…",  # NEEDS REVIEW
        "status_extract": "PDF ನಿಂದ ಓದಬಹುದಾದ ಪಠ್ಯವನ್ನು ತೆಗೆಯಲಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "status_structure": "AI ಬಳಸಿ ಅಧ್ಯಾಯವನ್ನು ಪಾಠವಾಗಿ ರೂಪಿಸಲಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "status_lesson_ready": "ಪಾಠ ಸಿದ್ಧವಾಗಿದೆ — ರಚನೆ ಆರಂಭವಾಗುತ್ತಿದೆ",  # NEEDS REVIEW
        "err_no_text": "ಓದಬಹುದಾದ ಪಠ್ಯ ಸಿಗಲಿಲ್ಲ. ಇದು ಸ್ಕ್ಯಾನ್ ಅಥವಾ ಫೋಟೋ ದಾಖಲೆಯಾಗಿದ್ದರೆ, “ಕೈಬರಹದ ಟಿಪ್ಪಣಿ” ಆಯ್ಕೆ ಬಳಸಿ.",  # NEEDS REVIEW
        "err_no_sections": "AI ಯಾವುದೇ ಪಾಠ ವಿಭಾಗಗಳನ್ನು ನೀಡಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_prepare": "ಪಾಠದ ಸ್ಕ್ರಿಪ್ಟ್ ಸಿದ್ಧಪಡಿಸಲು ಆಗಲಿಲ್ಲ: {error}",  # NEEDS REVIEW
        "status_building": "ನಿಮ್ಮ ಕಲಿಕಾ ಸಾಮಗ್ರಿಯನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ…",  # NEEDS REVIEW
        "status_slides": "ವಿಭಾಗ {i}/{n} · ಬೋಧನಾ ಸ್ಲೈಡ್‌ಗಳನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ",  # NEEDS REVIEW
        "status_narration": "ವಿಭಾಗ {i}/{n} · ನಿರೂಪಣೆಯ ಧ್ವನಿ ತಯಾರಾಗುತ್ತಿದೆ",  # NEEDS REVIEW
        "status_assembling": "ವಿಭಾಗ {i}/{n} · ವಿಡಿಯೋ ಜೋಡಿಸಲಾಗುತ್ತಿದೆ",  # NEEDS REVIEW
        "status_combining": "ಎಲ್ಲಾ ಪಾಠ ವಿಭಾಗಗಳನ್ನು ಒಟ್ಟುಗೂಡಿಸಲಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "status_ppt": "ನಿಮ್ಮ ಸಂಪಾದಿಸಬಹುದಾದ ಪ್ರೆಸೆಂಟೇಶನ್ ತಯಾರಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "status_audio": "{language} ನಿರೂಪಣೆಯ ಆಡಿಯೋ ತಯಾರಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "ppt_audio_failed": "ಪ್ರೆಸೆಂಟೇಶನ್ ಸಿದ್ಧವಾಗಿದೆ, ಆದರೆ ನಿರೂಪಣೆಯ ಆಡಿಯೋ ರಚಿಸಲು ಆಗಲಿಲ್ಲ: {error}",  # NEEDS REVIEW
        "ppt_voice_hint": "ಧ್ವನಿ ಸ್ಲೈಡ್‌ಗಳ ಒಳಗೇ ಇದೆ. ಫೈಲ್ ಅನ್ನು PowerPoint ನಲ್ಲಿ ತೆರೆದು Slide Show (F5) ಒತ್ತಿ: ಪ್ರತಿ ಸ್ಲೈಡ್ ತಾನೇ ಓದಿ ಮುಂದಿನದಕ್ಕೆ ಹೋಗುತ್ತದೆ.",  # NEEDS REVIEW
        "status_notes": "ನಿಮ್ಮ ಅಧ್ಯಯನ ಟಿಪ್ಪಣಿಗಳನ್ನು PDF ಆಗಿ ರೂಪಿಸಲಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "status_flashcards": "ಪ್ರಶ್ನೆ-ಉತ್ತರ ಫ್ಲ್ಯಾಶ್ ಕಾರ್ಡ್‌ಗಳನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ.",  # NEEDS REVIEW
        "status_ready": "ನಿಮ್ಮ ಸಾಮಗ್ರಿ ಸಿದ್ಧವಾಗಿದೆ",  # NEEDS REVIEW
        "err_no_chapter": "ರಚಿಸಲು ಯಾವುದೇ ಅಧ್ಯಾಯ ಲಭ್ಯವಿಲ್ಲ.",  # NEEDS REVIEW
        "err_generation": "ರಚನೆ ವಿಫಲವಾಯಿತು: {error}",  # NEEDS REVIEW
        "err_quota": "ಇಂದಿನ ಉಚಿತ AI ಮಿತಿ ಮುಗಿದಿದೆ. ದಯವಿಟ್ಟು ಕೆಲವು ನಿಮಿಷಗಳ ನಂತರ ಅಥವಾ ನಾಳೆ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "status_downloading": "ಅಧಿಕೃತ ಪಠ್ಯಪುಸ್ತಕ ಜಾಲತಾಣದಿಂದ ಅಧ್ಯಾಯವನ್ನು ತರಲಾಗುತ್ತಿದೆ…",  # NEEDS REVIEW
        "status_reading_pages": "ಪುಟಗಳನ್ನು ಓದಲಾಗುತ್ತಿದೆ (ಈ ಪುಸ್ತಕ ಹಳೆಯ ಕನ್ನಡ ಫಾಂಟ್‌ನಲ್ಲಿದೆ ಅಥವಾ ಸ್ಕ್ಯಾನ್ ಆಗಿದೆ)… ಒಂದು ನಿಮಿಷ ಆಗಬಹುದು.",  # NEEDS REVIEW
        "err_library_download": "ಅಧಿಕೃತ ಪಠ್ಯಪುಸ್ತಕ ಜಾಲತಾಣದಿಂದ ಈ ಅಧ್ಯಾಯ ತರಲು ಆಗಲಿಲ್ಲ. ಕೆಲವು ನಿಮಿಷಗಳ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ, ಅಥವಾ PDF ಅನ್ನು ನೀವೇ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",  # NEEDS REVIEW
        "quiz_offer_title": "ಈ ಪಾಠದ ಮೇಲೆ ಒಂದು ಚಿಕ್ಕ ರಸಪ್ರಶ್ನೆ ಬೇಕೇ?",  # NEEDS REVIEW
        "quiz_offer_desc": "ಬೋರ್ಡ್ ಪರೀಕ್ಷೆ ಮಾದರಿಯ {n} ಪ್ರಶ್ನೆಗಳು, ಉತ್ತರ ಮತ್ತು ವಿವರಣೆಯೊಂದಿಗೆ. ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಎಷ್ಟು ನೆನಪಿದೆ ಎಂದು ತಿಳಿಯಲು ಉಪಯುಕ್ತ.",  # NEEDS REVIEW
        "quiz_offer_btn": "ಹೌದು, ರಸಪ್ರಶ್ನೆ ತೋರಿಸಿ",  # NEEDS REVIEW
        "quiz_heading": "ಚಿಕ್ಕ ರಸಪ್ರಶ್ನೆ",  # NEEDS REVIEW
        "quiz_check": "ಉತ್ತರ ಪರಿಶೀಲಿಸಿ",  # NEEDS REVIEW
        "quiz_score": "ಅಂಕ: {score} / {total}",  # NEEDS REVIEW
        "quiz_correct": "ಸರಿ ಉತ್ತರ!",  # NEEDS REVIEW
        "quiz_wrong": "ತಪ್ಪು. ಸರಿಯಾದ ಉತ್ತರ: {answer}",  # NEEDS REVIEW
        "quiz_unanswered": "ಉತ್ತರಿಸಿಲ್ಲ. ಸರಿಯಾದ ಉತ್ತರ: {answer}",  # NEEDS REVIEW
        "status_cached": "ಈ ಪಾಠ ಮೊದಲೇ ತಯಾರಾಗಿದೆ: ತಕ್ಷಣ ಸಿದ್ಧ.",  # NEEDS REVIEW
        "status_slides_all": "ಎಲ್ಲ {n} ಭಾಗಗಳ ಸ್ಲೈಡ್‌ಗಳನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ…",  # NEEDS REVIEW
        "status_voice_all": "ಎಲ್ಲ {n} ಭಾಗಗಳ ಧ್ವನಿಯನ್ನು ಒಟ್ಟಿಗೆ ರೆಕಾರ್ಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ…",  # NEEDS REVIEW
        "err_slow": "AI ಸೇವೆ ಈಗ ತುಂಬಾ ಕಾರ್ಯನಿರತವಾಗಿದೆ, ಉತ್ತರಿಸಲು ತಡವಾಯಿತು. ಒಂದು ನಿಮಿಷದ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_network": "ಇಂಟರ್ನೆಟ್ ಅಥವಾ AI ಸೇವೆಗೆ ಸಂಪರ್ಕಿಸಲು ಆಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_too_long": "ಈ PDF ನಲ್ಲಿ {pages} ಪುಟಗಳಿವೆ. ನಿಧಾನ ಇಂಟರ್ನೆಟ್‌ನಲ್ಲೂ ಪಾಠ ಬೇಗ ತಯಾರಾಗಲು ಮಿತಿ {limit} ಪುಟಗಳು. ದಯವಿಟ್ಟು ಚಿಕ್ಕ ಅಧ್ಯಾಯವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",  # NEEDS REVIEW
        "err_unreadable_pdf": "ಈ PDF ಅನ್ನು ತೆರೆಯಲು ಆಗಲಿಲ್ಲ. ಅದು ಹಾನಿಗೊಂಡಿರಬಹುದು ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್ ಇರಬಹುದು. ದಯವಿಟ್ಟು ಬೇರೆ ಫೈಲ್ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "err_unexpected": "ನಿಮ್ಮ ಪಾಠ ತಯಾರಿಸುವಾಗ ಏನೋ ತಪ್ಪಾಯಿತು. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",  # NEEDS REVIEW
        "btn_try_again": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",  # NEEDS REVIEW
        "tech_details": "ತಾಂತ್ರಿಕ ವಿವರಗಳು",  # NEEDS REVIEW
        "review_checkbox": "ರಚಿಸುವ ಮೊದಲು ಸ್ಕ್ರಿಪ್ಟ್ ಪರಿಶೀಲಿಸಿ (ಶಿಕ್ಷಕರಿಗೆ ಶಿಫಾರಸು)",  # NEEDS REVIEW
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
        "report_button": "ಈ ಪಾಠದಲ್ಲಿ ಸಮಸ್ಯೆ ವರದಿ ಮಾಡಿ",  # NEEDS REVIEW
        "report_not_ready": "ವರದಿ ಫಾರ್ಮ್ ಲಿಂಕ್ ಇನ್ನೂ ಸಿದ್ಧವಾಗಿಲ್ಲ.",  # NEEDS REVIEW
        "lang_name_English": "ಇಂಗ್ಲಿಷ್",  # NEEDS REVIEW
        "lang_name_Kannada": "ಕನ್ನಡ",  # NEEDS REVIEW
        # --- Step 3: complete ------------------------------------------
        "done_step": "ಹಂತ 03 / ಸಿದ್ಧ",  # NEEDS REVIEW
        "done_heading": "ನಿಮ್ಮ ಕಲಿಕಾ ಸಾಮಗ್ರಿ ಸಿದ್ಧವಾಗಿದೆ",  # NEEDS REVIEW
        "done_desc": "ಇಲ್ಲಿಯೇ ತೆರೆದು ನೋಡಿ, ಅಥವಾ ಮುಂದಿನ ಅಧ್ಯಯನಕ್ಕಾಗಿ ಒಂದು ಪ್ರತಿಯನ್ನು ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ.",  # NEEDS REVIEW
        "dl_video": "ಪಾಠದ ವಿಡಿಯೋ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",  # NEEDS REVIEW
        "warn_video_missing": "ಈ ಸೆಷನ್‌ನಲ್ಲಿ ವಿಡಿಯೋ ಫೈಲ್ ಸಿಗಲಿಲ್ಲ.",  # NEEDS REVIEW
        "dl_ppt": "ಸಂಪಾದಿಸಬಹುದಾದ ಪ್ರೆಸೆಂಟೇಶನ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",  # NEEDS REVIEW
        "warn_ppt_missing": "ಈ ಸೆಷನ್‌ನಲ್ಲಿ ಪ್ರೆಸೆಂಟೇಶನ್ ಫೈಲ್ ಸಿಗಲಿಲ್ಲ.",  # NEEDS REVIEW
        "audio_heading": "ಪಾಠದ ನಿರೂಪಣೆಯ ಆಡಿಯೋ",  # NEEDS REVIEW
        "dl_audio": "{language} ನಿರೂಪಣೆ (MP3) ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",  # NEEDS REVIEW
        "dl_transcript": "ಅಧ್ಯಯನ ಟಿಪ್ಪಣಿಗಳ PDF ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ",  # NEEDS REVIEW
        "warn_transcript_missing": "ಈ ಸೆಷನ್‌ನಲ್ಲಿ ಟಿಪ್ಪಣಿಗಳ PDF ಸಿಗಲಿಲ್ಲ.",  # NEEDS REVIEW
        "cards_count": "{count} ಕಾರ್ಡ್‌ಗಳನ್ನು ರಚಿಸಲಾಗಿದೆ",  # NEEDS REVIEW
        "card_title": "ಕಾರ್ಡ್ {num}  ·  {front}",  # NEEDS REVIEW
        "card_default_front": "ಪ್ರಶ್ನೆ",  # NEEDS REVIEW
        "warn_no_flashcards": "ಈ ಅಧ್ಯಾಯಕ್ಕೆ ಯಾವುದೇ ಫ್ಲ್ಯಾಶ್ ಕಾರ್ಡ್‌ಗಳು ಸಿಗಲಿಲ್ಲ.",  # NEEDS REVIEW
        "view_data": "ರಚನಾತ್ಮಕ ಪಾಠದ ಡೇಟಾ ನೋಡಿ",  # NEEDS REVIEW
        "btn_another": "ಇನ್ನೊಂದು ಪಾಠ ರಚಿಸಿ",  # NEEDS REVIEW
        # --- Error screen + footer -------------------------------------
        "error_heading": "ಏನೋ ತಪ್ಪಾಗಿದೆ",  # NEEDS REVIEW
        "error_default": "ಅನಿರೀಕ್ಷಿತ ದೋಷ ಉಂಟಾಗಿದೆ.",  # NEEDS REVIEW
        "btn_back_workspace": "ಮುಖಪುಟಕ್ಕೆ ಹಿಂತಿರುಗಿ",  # NEEDS REVIEW
        "footer": "{app} &nbsp;·&nbsp; AI ಕಲಿಕಾ ಸ್ಟುಡಿಯೋ &nbsp;·&nbsp; ಸ್ಪಷ್ಟತೆಯೊಂದಿಗೆ ಕಲಿಯಿರಿ",  # NEEDS REVIEW
    },
}


def t(key: str, **kwargs) -> str:
    """Return the text for `key` in the selected language.

    Falls back to English, then to the key itself. Never raises.
    Placeholders like {name} are filled from kwargs.
    """
    language = st.session_state.get("selected_language", "English")
    text = STRINGS.get(language, {}).get(key)
    if text is None:
        text = STRINGS["English"].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text