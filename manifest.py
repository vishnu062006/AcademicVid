"""
Single source of truth for the pre-indexed chapter library shown in the
"Library" picker (see app.py).

Structure: CHAPTER_MANIFEST[class][subject][chapter_display_name] = pdf_path

Only add an entry when its PDF is really in the repo. Run `python3 preflight.py`
after editing - it opens every path and fails if one is missing or unreadable.

Subject "Kannada" = Kannada language lessons (story / poem): they automatically use the
story/poem teaching style. These come from the KTBS 2026-27 Kannada First Language
Part 1 books, which use an old (non-Unicode) Kannada font, so the app reads their pages
with Gemini (OCR) the first time. Open each one once before a demo so it is cached.
"""

CHAPTER_MANIFEST = {
    "Class 9": {
        "Science": {
            "Chapter 2: Cell: The Building Block of Life": "iesc102.pdf",
        },
        "Math": {
            "Chapter 1: Orienting Yourself: The Use of Coordinates": "iemh101.pdf",
        },
        "Kannada": {
            "ಗದ್ಯ 1: ಪ್ರಜಾನಿಷ್ಠೆ": "kn9_prajanishte.pdf",
        },
    },
    "Class 10": {
        "Science": {
            "Chapter 1: Chemical Reactions and Equations": "jesc101.pdf",
            "Chapter 2: Acids, Bases and Salts": "jesc102.pdf",
        },
        "Math": {
            "Chapter 1: Real Numbers": "jemh101.pdf",
        },
        "Kannada": {
            "ಪದ್ಯ 1: ಸಂಕಲ್ಪಗೀತೆ": "kn10_sankalpageethe.pdf",
        },
    },
}
