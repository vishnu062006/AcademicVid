# AcademicVid - project context (read this first)

Karnataka State Government ed-tech project. Turns an NCERT chapter PDF into a short lesson
(video, PPT, printable notes PDF, flashcards) in **English or Kannada**. Target users:
students and teachers in government schools, often rural: slow internet, shared phones,
no budget. Everything runs on free tiers. Deployed on Streamlit Cloud. Final handover: March.

## How it works
PDF -> text (`pdf_parser.py`) -> ONE Gemini call returns structured JSON (`ai_structuring.py`)
-> validated by Pydantic (`schema.py`) -> every output is built from that same object:
slides (`slides.py`) + narration (`tts.py`, edge-tts) -> video (`video_builder.py`);
also `ppt_export.py`, `transcript_export.py`, `flashcards.py`.

## Files
| File | Job |
|---|---|
| `app.py` | Streamlit UI and the generation flow (Vachana's area) |
| `manifest.py` | Chapter library for the picker: class -> subject -> chapter -> pdf path |
| `schema.py` | `Chapter` / `Section` data contract. Change only with Vishnu |
| `ai_structuring.py` | English + Kannada prompts, retries, quality checks |
| `content_validators.py`, `kannada_quality.py` | Checks on AI output; known-wrong Kannada terms |
| `slides.py` | Slide images (PyMuPDF). `LABELS` dict holds EN/KN slide text |
| `tts.py` | edge-tts voices: `en-IN-NeerjaNeural`, `kn-IN-SapnaNeural` |
| `video_builder.py` | Slides + audio -> mp4 (H.264 + AAC, phone friendly) |
| `ppt_export.py`, `transcript_export.py`, `flashcards.py` | The other outputs |
| `preflight.py` | Run before every push/demo. Expect only the "hygiene" warning |
| `assets/fonts/` | Noto Sans Kannada + DejaVu Sans. Must be REAL font files |

## Data shape (all outputs read this)
`Chapter(chapter_title, subject, sections[])`. `Section(title, hook, concept, indian_example,
key_points[], misconception, narration, key_equation (optional), quiz (optional))`.
`subject` is one of Science / Math / Social Science / English / Other.

## Function signatures - do NOT change without asking Vishnu
```
extract_chapter(pdf_path) -> {"clean_text", "headings"}
structure_chapter(text, language="English") -> Chapter
synthesize_narration(text, out_path, voice=...)
build_section_slides(section, subject, out_dir, language="English", chapter_title="") -> [png paths]
build_section_video(slide_paths, audio_path, out_path); concatenate_section_videos(paths, out_path)
export_chapter_to_pptx(chapter, out_path, language="English")
export_transcript_pdf(chapter, out_path, language="English")
generate_flashcards(chapter, language="English") -> [{"front", "back"}]
```
`language` is the string `"English"` or `"Kannada"`.

## app.py flow
`st.session_state.app_state`: setup -> choose_output -> generating_media -> complete (or error).
`review` exists (`render_review_ui`) but nothing routes to it yet. Other keys: `chapter`,
`selected_language`, `last_generated_type`, `selected_output_label`, `source_mode`.
Generated files go in `tmp_sessions/<session id>/` (never cleaned up yet).

## Constraints that bite
- Streamlit is pinned to **1.31.1** (old). Newer widgets (`st.pills`, `st.dialog`, ...) do not exist.
- Cloud runs Python 3.12; Vishnu's Mac runs 3.9. Do not use 3.10+ only syntax unless you check.
- Never add a dependency that needs system libraries. Cloud only installs `packages.txt`
  (ffmpeg, cmake) plus `requirements.txt`.
- Kannada text needs shaping. Do not draw Kannada with Pillow. Use the PyMuPDF helpers in `slides.py`.
- Wrap any user-controlled text (file names, titles) in `html.escape()` before putting it in
  `unsafe_allow_html` markdown.
- No secrets in the repo. `GOOGLE_API_KEY` lives in `.env` locally and in Streamlit Secrets on the cloud.
- Free-tier Gemini quota is limited: do not call it in loops while testing the UI.

## Run / check / deploy
```
pip3 install -r requirements.txt
streamlit run app.py          # run from the project root
python3 preflight.py          # before every push
```
Push to `main` auto-redeploys the cloud app. Use a branch for anything risky.

## Known gaps (honest list)
- UI text is English only (all hard-coded) and the chapter picker lives in the sidebar (bad on phones)
- Kannada words/phrases are not yet validated by a native speaker (`KNOWN_FIXES` in `kannada_quality.py`,
  `LABELS` in `slides.py`, flashcard templates in `flashcards.py`)
- Library has 2 chapters (Class 10 Science ch1, Class 10 Math ch1)
- No pre-generated lessons: every click calls Gemini and renders live (slow, uses quota)
- No offline bundle, no usage analytics, no teacher flagging yet
- `google-generativeai` is deprecated; migrate to `google-genai` later
