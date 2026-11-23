# AcademicVid audit (KREIS handover) - 15 Nov 2026

Scope: everything in the repo plus the uncommitted work on `main` (`app.py` CSS moved to
`style.css`, a new Kannada prompt line, `.streamlit/config.toml`). Checked by reading the code,
running `preflight.py`, scanning git history, and comparing CSS against the installed Streamlit 1.31.1.

Overall: the pipeline is solid (one Gemini call per chapter, a single Pydantic contract, Kannada
shaped through PyMuPDF, friendly errors, tmp cleanup). The problems are around it: a security
leak in history, a deploy that would break if pushed as-is, mobile CSS that never applies, and
quota use.

---

## Findings

### Critical
1. **Six Google API keys are in the public git history.** `github.com/vishnu062006/AcademicVid` is
   public, and old commits (e.g. `583f860 "done for now"` committed `.env`) hold six different
   `AIza...` keys plus a `CUSTOM_SEARCH_CX`. Deleting the file later does not remove them.
   The current key in `.env` is different and is NOT in history.

### High
2. **Pushing now would break the cloud UI.** `app.py` now loads `style.css`, but `style.css` is
   untracked. `.streamlit/config.toml` (the new light theme) is untracked too. Pushed as-is, the cloud app shows "style.css not found" and the default theme.
3. **The mobile and language-toggle CSS does nothing.** 23 rules (11 in `app.py`, 12 in `style.css`)
   start with `[data-testid="stMainBlockContainer"]`. That test id does not exist in Streamlit
   1.31.1 (it uses `stAppViewBlockContainer`). So the 48px tap targets, the 360px no-scroll rules,
   the side-by-side language/source buttons and the phone padding are not applied.
4. **Lesson language can differ from the voice.** `execute_media_generation` and the audio
   download label read `selected_language` (the UI toggle), not `lesson_language` (what Gemini wrote).
   Switch the toggle on the review or error screen and a Kannada script is read by the English voice
   with English slide labels (or the other way round).
5. **Gemini quota.** Every click calls Gemini again, even for the same library chapter. One click can
   cost up to 3 calls, because soft length warnings trigger retries, and the limits do not match the prompts
   (Kannada: prompt asks 180-300 words, validator wants 60-200; English: prompt 220-300, validator
   180-300). `GEMINI_RESPONSE_SCHEMA` also does not mark `key_points`, `misconception`, `narration` as
   required, so Gemini can omit them and Pydantic rejects the result: another retry.

### Medium
6. **New uncommitted prompt line** ("End every lesson with a polite Kannada thank-you...") sits in a
   per-section prompt, so every section's narration will likely end with a thank-you (repeated in the
   video). It also asks for "Kannada (English)" pairs, which partly contradicts the code-switching rule above it.
7. **Review form edits are applied before validation.** An invalid submit leaves a half-edited chapter.
   An empty narration passes validation and then fails in edge-tts.
8. **Colours left over from the dark theme** in `app.py`: `.field-label` `#c7ccda` and the report button
   `#171a22` on the new cream background. The labels are hard to read and the button looks out of place.
9. **"Report a problem" is still a placeholder** (`PASTE_FORM_ID_HERE`), so the button is disabled.

### Low / hygiene
10. Tracked junk: `app_backup.py`, `apply_issue1-5.py`, `FETCH_HEAD`, `transcript_export.py.save`,
    `final_output.mp4`, `videos/`, `images/`, `check.jpg`, `image.gif`, `kn_slides/`, test scripts
    (several are in `.gitignore` but were committed before). `.git` is 128 MB. `preflight.py` fails "Repo hygiene".
    Untracked `streamlit-debug.log` and `profile_run.py` should not be committed.
11. Local Mac env: PyMuPDF is broken on Python 3.9 (`libmupdf.dylib` not loaded). Preflight fails 2 checks.
12. No upload size cap (Streamlit default is 200 MB). Set `server.maxUploadSize`.
13. Still open from CONTEXT.md: Kannada text not reviewed by a native speaker (`strings.py`
    `# NEEDS REVIEW`, `slides.LABELS`, `flashcards.py`, `KNOWN_FIXES`). Library has 2 chapters
    (`jesc102.pdf` is in the repo but not in the manifest). `google-generativeai` is deprecated.

---

## Tasks to finish the work

| # | Task | Fixes | Who |
|---|---|---|---|
| ~~T1~~ | Closed: the old keys were pushed by a senior and the current keys are different. | 1 | - |
| ✅ T2 | Make the deploy safe: track `style.css` and `.streamlit/config.toml` (fix `.gitignore`), add `maxUploadSize`, fix `stMainBlockContainer` -> `stAppViewBlockContainer`, fix the dark-theme colours. Check at 360px. | 2, 3, 8, 12 | Claude |
| ✅ T3 | Correctness: the language toggle is meant to work only at the start, so hide/lock it after setup (today it is shown on every screen) and keep using `lesson_language` once generation begins; validate review edits on a copy and reject an empty narration. | 4, 7 | Claude |
| ✅ T4 | Quota: cache structuring by (PDF hash, language), don't retry on soft length warnings, align limits with prompts, add the missing `required` fields. Move the thank-you to the last section only (or drop it). | 5, 6 | Claude |
| ✅ T5 | Repo clean-up: `git rm` the junk files (local copies kept), fix `.gitignore`, add `jesc102.pdf` to the manifest if wanted, make preflight pass. | 10, 11, 13 (part) | Claude |
| T6 | Handover items: create the Google Form and paste its link/entry ids; native-speaker review of Kannada strings. | 9, 13 | Vishnu / team |

**Done 23 Nov 2026 (not committed yet):** T2–T5. `preflight.py` passes 6/6. Checked in the app at 375px:
toggle only on step 1, 48px buttons, no sideways scroll. Also fixed: the header row was being squeezed
50/50 on phones (the toggle CSS matched the outer row too). Not checked: a real Gemini generation run.

---

## Backlog (built 23 Nov 2026, not committed yet)

1. ✅ **Handwritten notes OCR**: new "Handwritten notes" source. Photos (up to 10) or a scanned PDF are read
   by Gemini vision (`ocr.py`). The user checks and fixes the text, then makes the lesson.
2. ⏳ **App name**: still to decide. It now lives in ONE place: `APP_NAME` in `branding.py`
   (header, page title, footer, slides, notes PDF, download file names).
3. ✅ **Keep the app awake**: `.github/workflows/keep-awake.yml` + `scripts/keep_awake.py` visit the app every
   6 h in a headless browser and click "wake up" if it is asleep. Needs the repo variable `APP_URL` (see the file).
4. ✅ **CSE / custom topics**: new "Custom topics" source. Type a subject, level and up to 12 topics (with optional
   "-" notes). One section per topic, code/complexity on the formula slide, Indian real-world examples.
5. ✅ **Kannada subject (story / poem)**: new lesson style (`MODE_KANNADA_LIT` in `ai_structuring.py`). It follows the text
   in order, with ಸಂದರ್ಭ, ಭಾವಾರ್ಥ, ಪದಗಳ ಅರ್ಥ, a key line for "ಸಂದರ್ಭ ಸಹಿತ ವಿವರಿಸಿ", values, and its own slide/PPT/notes
   headings and flashcards. Library chapters with subject "Kannada" use it automatically; for uploads/notes pick
   "Kannada subject: story or poem".
6. ✅ **Pay-per-use estimate**: `COSTS.md` (≈₹1.7–2.5 per lesson on Gemini Flash-Lite paid tier).

**Found while testing:** on the free tier one lesson call took 66 s for just 2 topics. The old 60 s limit
made real lessons fail with a wrong "no internet" message. The limit is now 240 s, with a correct "AI is busy" message.
Also fixed: lesson generation failing on networks with an IPv6 DNS server (as on Vishnu's Mac).
