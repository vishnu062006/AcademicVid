from dotenv import load_dotenv
load_dotenv()

from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from tts import synthesize_narration, VOICE_KN

result = extract_chapter('jesc101.pdf')
chapter_kn = structure_chapter(result['clean_text'], language="Kannada")

synthesize_narration(chapter_kn.sections[0].narration, "kannada_test.mp3", voice=VOICE_KN)
print("Saved: kannada_test.mp3")