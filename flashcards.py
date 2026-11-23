"""
Revision flashcards from a Chapter. Four Q&A cards per section, English or Kannada.
Returns a list of {"front": question, "back": answer} dicts (same shape as before).

NOTE: the Kannada question templates should be reviewed by a native speaker.
"""

_TEMPLATES = {
    "English": {
        "concept": "What is meant by \u201c{t}\u201d?",
        "example": "Give a real-life example of \u201c{t}\u201d.",
        "points": "State the key points of \u201c{t}\u201d.",
        "mistake": "What common mistake do students make in \u201c{t}\u201d?",
    },
    "Kannada": {
        "concept": "\u201c{t}\u201d ಎಂದರೇನು?",
        "example": "\u201c{t}\u201d ಕ್ಕೆ ದೈನಂದಿನ ಜೀವನದ ಒಂದು ಉದಾಹರಣೆ ಕೊಡಿ.",
        "points": "\u201c{t}\u201d ಯ ಮುಖ್ಯ ಅಂಶಗಳನ್ನು ತಿಳಿಸಿ.",
        "mistake": "\u201c{t}\u201d ನಲ್ಲಿ ವಿದ್ಯಾರ್ಥಿಗಳು ಮಾಡುವ ಸಾಮಾನ್ಯ ತಪ್ಪು ಯಾವುದು?",
    },
}


# Kannada-subject (story / poem) lessons: the fields hold meaning, life connection,
# word meanings and exam pitfalls, so the questions are asked that way. NEEDS REVIEW.
_KANNADA_LITERATURE = {
    "concept": "“{t}” ಭಾಗದ ಭಾವಾರ್ಥ / ಸಾರಾಂಶ ಏನು?",
    "example": "“{t}” ಭಾಗವು ನಮ್ಮ ಜೀವನಕ್ಕೆ ಹೇಗೆ ಹೊಂದುತ್ತದೆ?",
    "points": "“{t}” ಭಾಗದ ಕಠಿಣ ಪದಗಳ ಅರ್ಥ ಮತ್ತು ಮುಖ್ಯ ಅಂಶಗಳನ್ನು ತಿಳಿಸಿ.",
    "mistake": "“{t}” ಭಾಗದಲ್ಲಿ ಪರೀಕ್ಷೆಯಲ್ಲಿ ಗಮನಿಸಬೇಕಾದ ಅಂಶ ಯಾವುದು?",
}


def generate_flashcards(chapter, language: str = "English"):
    if getattr(chapter, "subject", "") == "Kannada":
        tpl = _KANNADA_LITERATURE
    else:
        tpl = _TEMPLATES.get(language, _TEMPLATES["English"])
    cards = []
    for s in chapter.sections:
        t = s.title
        cards.append({"front": tpl["concept"].format(t=t), "back": s.concept})
        cards.append({"front": tpl["example"].format(t=t), "back": s.indian_example})
        cards.append({"front": tpl["points"].format(t=t),
                      "back": "\n".join(f"\u2022 {p}" for p in s.key_points)})
        cards.append({"front": tpl["mistake"].format(t=t), "back": s.misconception})
    return cards