from dotenv import load_dotenv
load_dotenv()

from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from slides import build_section_slides
   

result = extract_chapter('jemh101.pdf')
chapter_kn = structure_chapter(result['clean_text'], language="Kannada")
print(chapter_kn.model_dump_json(indent=2))
build_section_slides(chapter_kn.sections[0], chapter_kn.subject, "kn_slides", language="Kannada")