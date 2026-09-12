def validate_narration_length(chapter, min_words=180, max_words=300):
    issues = []
    for i, section in enumerate(chapter.sections):
        word_count = len(section.narration.split())
        if not (min_words <= word_count <= max_words):
            issues.append(
                f"Section {i} ('{section.title}'): {word_count} words "
                f"(expected {min_words}-{max_words})"
            )
    return issues