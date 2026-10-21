"""
Quality guard for AI-generated Kannada content.

Gemini's Kannada is good but inconsistent between runs. Two kinds of problems seen so far:
 1. Glitches   - Latin letters/digits stuck inside a Kannada word ("ಉದಾಹರಣed", "ಒಡ್ಡ11ವುದು").
 2. Wrong terms - wrong or non-standard science words ("ಸ್ಥಾನಪಂಥ" instead of "ಸ್ಥಾನಪಲ್ಲಟ").

glitches  -> find_glitches(chapter)      : returns a list of problems (used to trigger a retry)
terms     -> fix_known_terms(chapter)    : deterministic replacement of known-wrong words

!! KNOWN_FIXES must be reviewed by a Kannada-medium science teacher before the pilot.
   Add every wrong term a reviewer finds; the fixer applies them on every generation.
"""
import re
from schema import Chapter

# wrong (as generated)  ->  correct (standard Karnataka-textbook term)
# Longer / more specific phrases first.
KNOWN_FIXES = {
    "ದ್ವೈತ ಸ್ಥಾನಪಂಥ": "ದ್ವಿ ಸ್ಥಾನಪಲ್ಲಟ",
    "ದ್ವೈತ ಸ್ಥಾನಪಲ್ಲಟ": "ದ್ವಿ ಸ್ಥಾನಪಲ್ಲಟ",
    "ದ್ವಿ-ಸ್ಥಾನಪಲ್ಲಡ": "ದ್ವಿ ಸ್ಥಾನಪಲ್ಲಟ",
    "ದ್ವಿ-ಸ್ಥಾನಪದ್ಧತಿ": "ದ್ವಿ ಸ್ಥಾನಪಲ್ಲಟ",
    "ಸ್ಥಾನಪಂಥ": "ಸ್ಥಾನಪಲ್ಲಟ",
    "ಸ್ಥಾನಪಲ್ಲಡ": "ಸ್ಥಾನಪಲ್ಲಟ",
    "ಸ್ಥಾನಪದ್ಧತಿ": "ಸ್ಥಾನಪಲ್ಲಟ",
    "ಉಕ್ಸೀಕರಣ": "ಉತ್ಕರ್ಷಣ",
    "ಹಾವಿಯ ನೀರು": "ನೀರಿನ ಆವಿ",
    "ಬಕೆಟ್": "ಬ್ರಾಕೆಟ್",
}

_KN = "\u0C80-\u0CFF"
# a Kannada letter directly touching an English letter or digit (no space) = glitch
_GLUE = re.compile(rf"[{_KN}][A-Za-z0-9]|[A-Za-z0-9][{_KN}]")
# allowed exceptions, e.g. "(aq) ಗಳನ್ನು" has a space so it is not matched anyway


def _walk(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_walk(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk(v, fn) for k, v in obj.items()}
    return obj


def fix_known_terms(chapter: Chapter) -> Chapter:
    """Return a copy of the chapter with every known-wrong term replaced.
    key_equation is left untouched (it is chemical notation, not Kannada)."""
    def fix(text):
        for wrong, right in KNOWN_FIXES.items():
            text = text.replace(wrong, right)
        return text

    data = chapter.model_dump()
    for sec in data["sections"]:
        eq = sec.get("key_equation")
        for k, v in list(sec.items()):
            if k != "key_equation":
                sec[k] = _walk(v, fix)
        sec["key_equation"] = eq
    return Chapter.model_validate(data)


def find_glitches(chapter: Chapter) -> list:
    """List of human-readable problems: Latin/digits glued to Kannada letters."""
    problems = []
    for i, sec in enumerate(chapter.sections):
        fields = {k: v for k, v in sec.model_dump().items() if k != "key_equation"}
        flat = []

        def collect(t):
            flat.append(t)
            return t
        _walk(fields, collect)
        for text in flat:
            m = _GLUE.search(text)
            if m:
                s = max(0, m.start() - 8)
                problems.append(f"Section {i}: mixed script near '{text[s:m.end() + 8]}'")
    return problems