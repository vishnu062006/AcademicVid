from dotenv import load_dotenv
load_dotenv()

from pdf_parser import extract_chapter
from ai_structuring import structure_chapter

result = extract_chapter('jesc101.pdf')
chapter_kn = structure_chapter(result['clean_text'], language="Kannada")
print(chapter_kn.model_dump_json(indent=2))