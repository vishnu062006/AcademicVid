from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from tts import synthesize_narration
from slides import build_section_slides

result = extract_chapter('jesc101.pdf')
chapter = structure_chapter(result['clean_text'])

section = chapter.sections[0]

synthesize_narration(section.narration, "test_narration.mp3")
slide_paths = build_section_slides(section, chapter.subject, "test_slides")
print(slide_paths)

from video_builder import build_section_video

video_path = build_section_video(slide_paths, "test_narration.mp3", "test_section_video.mp4")
print("Video saved to:", video_path)