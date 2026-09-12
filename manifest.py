"""
Single source of truth for the pre-indexed chapter library shown in the
"Pick from library" picker (see app.py).

Structure: CHAPTER_MANIFEST[class][subject][chapter_display_name] = pdf_path

`jesc101.pdf` is the one real NCERT PDF currently checked into the repo
root, so it's wired up as the real, working entry. The rest are placeholder
paths under ncert_pdfs/ — swap them for real files as they get added and
the dropdowns will pick them up automatically, no other code changes needed.
"""

CHAPTER_MANIFEST = {
    "Class 10": {
        "Science": {
            "Chapter 1: Chemical Reactions and Equations": "jesc101.pdf",
            # Add more real chapters here as PDFs land, e.g.:
            # "Chapter 2: Acids, Bases and Salts": "ncert_pdfs/class10/science/jesc102.pdf",
        },
        "Math": {
            "Chapter 1: Real Numbers": "ncert_pdfs/class10/math/jemh101.pdf",
        },
    },
    "Class 9": {
        "Science": {
            "Chapter 1: Matter in Our Surroundings": "ncert_pdfs/class9/science/iesc101.pdf",
        },
    },
}