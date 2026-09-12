def generate_flashcards(chapter):
    cards = []
    for section in chapter.sections:
        cards.append({
            "front": f"What is {section.title}?",
            "back": section.concept,
        })
        for i, point in enumerate(section.key_points):
            cards.append({
                "front": f"{section.title} — Key Point {i+1}?",
                "back": point,
            })
    return cards