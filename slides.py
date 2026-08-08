"""
Step 3: builds visual slides directly from the JSON, no external image search.
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = (1280, 720)

SUBJECT_THEMES = {
    "Science":        {"bg": (14, 98, 81),   "accent": (255, 214, 10),  "text": (255, 255, 255)},
    "Math":           {"bg": (17, 45, 78),   "accent": (255, 138, 0),   "text": (255, 255, 255)},
    "Social Science": {"bg": (91, 33, 33),   "accent": (255, 205, 178), "text": (255, 255, 255)},
    "English":        {"bg": (35, 33, 71),   "accent": (150, 200, 255), "text": (255, 255, 255)},
    "Other":          {"bg": (40, 40, 40),   "accent": (200, 200, 200), "text": (255, 255, 255)},
}

FONT_DIR = os.environ.get("ACADEMICVID_FONT_DIR", "/System/Library/Fonts/Supplemental")
FONT_BOLD = os.path.join(FONT_DIR, "Arial Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Arial.ttf")


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _wrapped(draw, text, font, max_width):
    avg_char_w = draw.textlength("x", font=font) or 10
    wrap_width = max(10, int(max_width / avg_char_w))
    return textwrap.wrap(text, width=wrap_width)


def _base_slide(theme):
    img = Image.new("RGB", CANVAS_SIZE, theme["bg"])
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, CANVAS_SIZE[0], 12], fill=theme["accent"])
    return img, draw


def render_title_slide(title: str, subject: str, out_path: str) -> str:
    theme = SUBJECT_THEMES.get(subject, SUBJECT_THEMES["Other"])
    img, draw = _base_slide(theme)
    font = _load_font(FONT_BOLD, 64)
    lines = _wrapped(draw, title, font, CANVAS_SIZE[0] - 160)
    y = CANVAS_SIZE[1] // 2 - (len(lines) * 74) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((CANVAS_SIZE[0] - w) / 2, y), line, font=font, fill=theme["text"])
        y += 74
    img.save(out_path)
    return out_path


def render_text_slide(heading: str, body: str, subject: str, out_path: str,
                       body_font_size: int = 40) -> str:
    theme = SUBJECT_THEMES.get(subject, SUBJECT_THEMES["Other"])
    img, draw = _base_slide(theme)
    heading_font = _load_font(FONT_BOLD, 48)
    body_font = _load_font(FONT_REGULAR, body_font_size)

    draw.text((80, 60), heading, font=heading_font, fill=theme["accent"])

    lines = _wrapped(draw, body, body_font, CANVAS_SIZE[0] - 160)
    y = 180
    for line in lines:
        draw.text((80, y), line, font=body_font, fill=theme["text"])
        y += body_font_size + 14
    img.save(out_path)
    return out_path


def render_key_points_slide(key_points: list, subject: str, out_path: str) -> str:
    theme = SUBJECT_THEMES.get(subject, SUBJECT_THEMES["Other"])
    img, draw = _base_slide(theme)
    heading_font = _load_font(FONT_BOLD, 48)
    point_font = _load_font(FONT_REGULAR, 36)

    draw.text((80, 60), "Key Points", font=heading_font, fill=theme["accent"])
    y = 180
    for point in key_points:
        wrapped = _wrapped(draw, f"\u2022  {point}", point_font, CANVAS_SIZE[0] - 160)
        for line in wrapped:
            draw.text((80, y), line, font=point_font, fill=theme["text"])
            y += 46
        y += 20
    img.save(out_path)
    return out_path


def render_misconception_slide(misconception: str, subject: str, out_path: str) -> str:
    theme = SUBJECT_THEMES.get(subject, SUBJECT_THEMES["Other"])
    img, draw = _base_slide(theme)
    heading_font = _load_font(FONT_BOLD, 48)
    body_font = _load_font(FONT_REGULAR, 38)

    draw.text((80, 60), "Watch Out!", font=heading_font, fill=(255, 99, 71))
    lines = _wrapped(draw, misconception, body_font, CANVAS_SIZE[0] - 160)
    y = 180
    for line in lines:
        draw.text((80, y), line, font=body_font, fill=theme["text"])
        y += 52
    img.save(out_path)
    return out_path


def build_section_slides(section, subject: str, out_dir: str) -> list:
    """
    Returns an ordered list of (slide_path, narration_text) pairs for one section,
    matching PRD's Hook -> Concept -> Indian Example -> Key Points -> Misconception flow.
    Narration audio is generated once for the whole section (tts.py), so all slides
    in a section share the same audio clip duration split evenly unless you choose
    to narrate per-slide (see video_builder.py for both options).
    """
    os.makedirs(out_dir, exist_ok=True)
    slides = []

    p = os.path.join(out_dir, "01_hook.png")
    render_text_slide(section.title, section.hook, subject, p)
    slides.append(p)

    p = os.path.join(out_dir, "02_concept.png")
    render_text_slide("Concept", section.concept, subject, p)
    slides.append(p)

    p = os.path.join(out_dir, "03_example.png")
    render_text_slide("Real-Life Example", section.indian_example, subject, p)
    slides.append(p)

    p = os.path.join(out_dir, "04_keypoints.png")
    render_key_points_slide(section.key_points, subject, p)
    slides.append(p)

    p = os.path.join(out_dir, "05_misconception.png")
    render_misconception_slide(section.misconception, subject, p)
    slides.append(p)

    return slides