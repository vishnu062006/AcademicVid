"""
Pre-make the AI lesson for every library chapter, in English and Kannada, and save it in
lessons/ (committed). Then a teacher who opens a library chapter never waits for Gemini
(1-4 minutes on the free tier) and no quota is used.

Run from the project root, after adding chapters to manifest.py or changing the prompts:
    python3 scripts/pregenerate_lessons.py            # only missing lessons
    python3 scripts/pregenerate_lessons.py --force    # re-make all of them

Calls Gemini one lesson at a time (the free tier refuses parallel calls).
Kannada-subject chapters (story / poem) are made in Kannada only.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from ai_structuring import structure_chapter, MODEL_NAME, MODE_CHAPTER, MODE_KANNADA_LIT  # noqa: E402
from cache_store import lesson_key, load_lesson, save_lesson, COMMITTED_LESSONS_DIR      # noqa: E402
from library import resolve_library_pdf                                                  # noqa: E402
from manifest import CHAPTER_MANIFEST                                                    # noqa: E402
from pdf_parser import extract_chapter, looks_like_legacy_kannada                        # noqa: E402


def main(force: bool) -> int:
    failures = 0
    for cls, subjects in CHAPTER_MANIFEST.items():
        for subject, chapters in subjects.items():
            mode = MODE_KANNADA_LIT if subject == "Kannada" else MODE_CHAPTER
            languages = ["Kannada"] if mode == MODE_KANNADA_LIT else ["English", "Kannada"]
            for title, entry in chapters.items():
                text = extract_chapter(resolve_library_pdf(entry))["clean_text"]
                if not text.strip() or looks_like_legacy_kannada(text):
                    print(f"SKIP  {cls} / {subject} / {title}: needs page OCR, made on first use")
                    continue
                for language in languages:
                    key = lesson_key(text, language, mode, MODEL_NAME)
                    label = f"{cls} / {subject} / {title} [{language}]"
                    if not force and os.path.exists(os.path.join(COMMITTED_LESSONS_DIR, key + ".json")):
                        print(f"HAVE  {label}")
                        continue
                    t0 = time.time()
                    try:
                        chapter = structure_chapter(text, language=language, mode=mode)
                        save_lesson(key, chapter, folder=COMMITTED_LESSONS_DIR)
                        assert load_lesson(key) is not None
                        print(f"MADE  {label}: {len(chapter.sections)} sections in {time.time() - t0:.0f}s",
                              flush=True)
                    except Exception as exc:
                        failures += 1
                        print(f"FAIL  {label}: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main("--force" in sys.argv))
