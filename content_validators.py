import re

def validate_narration_length(chapter, min_words=180, max_words=300, language="English"):
    """
    Checks each section's narration word count against expected bounds.
    Word-count-based validation is a rough proxy for spoken duration —
    works reasonably for English, but Kannada (like other Indic scripts)
    doesn't map word-count to speaking time the same way, so a separate,
    looser range is used until this can be replaced with actual audio
    duration checks (see get_audio_duration in tts.py for a more accurate
    long-term fix).
    """
    if language == "Kannada":
        min_words, max_words = 60, 200

    issues = []
    for i, section in enumerate(chapter.sections):
        word_count = len(section.narration.split())
        if not (min_words <= word_count <= max_words):
            issues.append(
                f"Section {i} ('{section.title}'): {word_count} words "
                f"(expected {min_words}-{max_words})"
            )
    return issues


# Kannada Unicode block: U+0C80–U+0CFF
KANNADA_RANGE = re.compile(r'[\u0C80-\u0CFF]')
# Allowed: Kannada script, English letters/digits, common punctuation/whitespace
ALLOWED_CHARS = re.compile(r'^[\u0C80-\u0CFFa-zA-Z0-9\s.,!?()\-+=/।॥ಂ%\'"]+$')
# Explicitly flag other Indic scripts commonly seen leaking in
FOREIGN_SCRIPT_RANGES = {
    "Devanagari (Hindi)": re.compile(r'[\u0900-\u097F]'),
    "Tamil": re.compile(r'[\u0B80-\u0BFF]'),
    "Telugu": re.compile(r'[\u0C00-\u0C7F]'),
    "Bengali": re.compile(r'[\u0980-\u09FF]'),
}


def validate_kannada_script(chapter):
    """
    Flags any text field containing characters from a non-Kannada Indic
    script (Hindi/Tamil/Telugu/Bengali etc slipping in due to model
    confusion). English and Kannada are both allowed; anything else isn't.
    """
    issues = []
    text_fields = ["title", "hook", "concept", "indian_example", "misconception", "narration"]

    for i, section in enumerate(chapter.sections):
        for field in text_fields:
            value = getattr(section, field, "")
            for script_name, pattern in FOREIGN_SCRIPT_RANGES.items():
                if pattern.search(value):
                    issues.append(
                        f"Section {i} ('{section.title}') field '{field}': "
                        f"contains {script_name} characters — {value[:60]}..."
                    )
        for point in section.key_points:
            for script_name, pattern in FOREIGN_SCRIPT_RANGES.items():
                if pattern.search(point):
                    issues.append(f"Section {i} key_point contains {script_name}: {point[:60]}...")

    return issues