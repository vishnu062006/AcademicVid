from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from content_validators import validate_narration_length

test_pdfs = [
    "jesc101.pdf",   # <-- update these to your actual PDF filenames/paths
]

for pdf_path in test_pdfs:
    print(f"\n--- Testing {pdf_path} ---")
    result = extract_chapter(pdf_path)
    chapter = structure_chapter(result['clean_text'])
    issues = validate_narration_length(chapter)
    print(f"Sections: {len(chapter.sections)}, Issues: {issues or 'None'}")