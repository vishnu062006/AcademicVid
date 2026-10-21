# Tasks for Vachana (UI side) - paste each one as a GitHub issue

**Before every task:** read `CONTEXT.md`. Only edit `app.py` and `strings.py` (and CSS inside `app.py`).
Do not change any function signature listed in CONTEXT.md. Work on a branch, open a PR, do not push to `main`.
**Nothing merges before the review (Oct 23).** Merge order: 1 -> 3 -> 2 -> 4 -> 5 (all touch `app.py`).

---

## Issue 1 - Kannada website (UI language)
**Branch:** `feature/kannada-ui`
**Goal:** a student who does not read English can use the whole site in Kannada.
**Do**
- Create `strings.py`: a dict `STRINGS = {"English": {...}, "Kannada": {...}}` with every visible label
  (hero text, step labels, buttons, captions, errors, footer, output-format names and descriptions).
- Add `t(key)` that reads `st.session_state.selected_language`; if a key is missing in Kannada, fall back to English (never crash).
- Replace the hard-coded strings in `app.py` with `t("...")`.
- Put a clear language toggle ("English | ಕನ್ನಡ") at the top of the MAIN page, not only in the sidebar.
- CSS: the current fonts (DM Sans, Space Grotesk) have no Kannada glyphs. Add `Noto Sans Kannada` to the Google Fonts
  import and to every `font-family` stack, with `'Nirmala UI', sans-serif` as fallback (works offline).
- Mark every Kannada string `# NEEDS REVIEW` - a native Kannada speaker must check the wording before the pilot.
**Don't:** translate the brand name "AcademicVid"; hard-code Kannada inside `app.py`.
**Known limit:** Streamlit's own widget text (e.g. the file uploader's "Drag and drop file here") stays English in 1.31.1. Add Kannada help text next to it.
**Done when**
- Switching language changes ALL visible text on every screen (setup, choose format, generating, complete, error).
- Longer Kannada text does not break the layout at 1280px or 360px wide.
- A missing key shows the English text instead of an error.
**Test:** run the full flow in both languages on desktop and at 360px width.

---

## Issue 2 - Mobile-first flow
**Branch:** `feature/mobile-flow`  (start after Issue 1 is merged)
**Goal:** the whole flow works on a phone WITHOUT opening the sidebar (it is hidden by default on phones).
**Do**
- Move the chapter picker (class / subject / chapter) and the PDF upload into the main page.
- Bigger tap targets (min ~48px high), one column on narrow screens, no horizontal scrolling.
- Remove the text that tells users to "use the sidebar".
**Done when:** at 360x800, a user can pick a chapter, pick a format, generate, and play/download without opening the sidebar.
**Test:** browser dev tools at 360px, plus a real phone on the deployed app.

---

## Issue 3 - Safety and friendly errors
**Branch:** `feature/errors-and-safety`  (start after Issue 1 is merged)
**Goal:** the app never shows a stack trace or breaks its own layout.
**Do**
- Wrap every user-controlled string (uploaded file name, chapter titles) in `html.escape()` before it goes into `unsafe_allow_html`.
- Friendly messages, in both languages (use `strings.py`), for: Gemini quota used up, no internet, scanned PDF (no text), PDF too long.
- Reject uploads with more than 40 pages and say why.
- At startup delete folders in `tmp_sessions/` older than 6 hours (never the current session).
**Done when**
- A file named `a&b<i>.pdf` does not break the page.
- Unplugging the network mid-run shows a friendly message and a "try again" button, not a traceback.
- `tmp_sessions/` does not grow forever.

---

## Issue 4 - Optional script review step (teacher-in-the-loop)
**Branch:** `feature/script-review`  (start after Issue 1 is merged)
**Goal:** a teacher can fix a wrong word in the AI's script BEFORE the video is made. Important for Kannada.
**Do**
- On the choose-format screen add a checkbox "Review the script before generating (recommended for teachers)", OFF by default
  so the one-click flow stays the same.
- If ticked, route to the existing `render_review_ui` after structuring, then generate from the EDITED chapter.
- Bug to fix: the review form reads/writes `chapter.title` but the field is `chapter_title`, so title edits are silently ignored.
- Show the form labels in the selected language.
**Done when:** editing one word in a Kannada narration appears in the video, the notes PDF and the flashcards; Cancel returns to setup.

---

## Issue 5 - "Report a problem" button
**Branch:** `feature/report-problem`  (start after Issue 1 is merged)
**Goal:** teachers can flag wrong content. First step of the teacher-review feature.
**Do**
- On the finished-lesson screen add a "Report a problem with this lesson" button that opens a Google Form in a new tab.
- Use the form's "Get pre-filled link" option so chapter, language and output type are filled in automatically
  (build the URL from `st.session_state`).
- Add the form link as a constant at the top of `app.py` (Vishnu creates the form and gives her the link).
**Don't:** store reports in a file in the repo or in `tmp_sessions/` - Streamlit Cloud's disk is wiped on every redeploy/reboot.
**Done when:** clicking the button opens the form with chapter, language and format already filled in.
