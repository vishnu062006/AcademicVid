"""
Single source of truth for the pre-indexed chapter library shown in the
"Library" picker (see app.py).

Structure: CHAPTER_MANIFEST[class][subject][chapter_display_name] = pdf_path

Only add an entry when its PDF is really in the repo. Run `python3 preflight.py`
after editing - it opens every path and fails if one is missing or unreadable.
"""

CHAPTER_MANIFEST = {
    "Class 10": {
        "Science": {
            "Chapter 1: Chemical Reactions and Equations": "jesc101.pdf",
        },
        "Math": {
            "Chapter 1: Real Numbers": "jemh101.pdf",
        },
    },
}
