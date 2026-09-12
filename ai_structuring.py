"""
Step 2 of the pipeline: one Gemini call per chapter (not per image/section),
returns strict JSON validated against schema.py -> Chapter.
"""
import os
import json
import google.generativeai as genai
from pydantic import ValidationError

from schema import Chapter, GEMINI_RESPONSE_SCHEMA
from content_validators import validate_narration_length

MODEL_NAME = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """You are an expert NCERT curriculum teacher creating structured
video lesson content for Class 6-12 Indian students (Karnataka state board priority),
who are preparing for board exams. Your explanations must build real understanding
AND directly help students score well in exams — both matter equally.

For the given chapter text, break it into logical sections (one per major concept/heading).
For EACH section, produce:

- title: the section heading from the NCERT text

- hook: one-line real-life relevance, using Indian context

- concept: the core idea in 2-3 sentences. Be specific and concrete, not abstract —
  include the actual mechanism, reason, or process, not just a restatement of the
  definition. A student should understand WHY, not just WHAT. Use exact terminology
  that appears in NCERT and is expected in board exam answers (do not simplify away
  key terms students need to write in their answer sheets).

- indian_example: a relatable Indian daily-life example (avoid generic/Western
  examples). Prefer examples similar to ones that have appeared in NCERT or past
  board exam questions where possible.

- key_points: array of exactly 3 must-remember facts, phrased the way a student
  would need to write them in a 1-2 mark board exam answer — precise, using correct
  terminology, not casual paraphrasing.

- misconception: one common mistake students make on THIS specific topic that
  typically costs marks in exams (e.g. a frequently confused term, a common
  calculation error, a frequently missed step). Be specific to this concept,
  not generic ("students should study more").

- narration: a warm, teacher-style spoken explanation. HARD REQUIREMENT:
  the narration field must contain AT LEAST 220 words and NO MORE than 300
  words — count carefully, this is validated programmatically and content
  under 220 words will be rejected. If you find yourself finishing early,
  add more depth: an additional real-life angle, a deeper explanation of
  the mechanism, or a longer walkthrough of the misconception. Do not pad
  with repetition — add genuine additional explanation instead.

  CRITICAL: this text will be converted to audio using text-to-speech.
  NEVER write raw chemical formulas, mathematical notation, or symbols in
  narration (e.g. do not write "Fe3O4", "CaO + H2O", "x^2", "H2SO4").
  Instead, always spell them out in words exactly as a teacher would say
  them aloud — e.g. write "iron oxide" or "calcium oxide reacting with
  water" or "x squared". The written text should read exactly as it
  should be spoken.

  Structure it as: (1) restate the hook as a question, (2) explain the concept
  by walking through the reasoning/mechanism in your own words — go deeper
  than the on-screen text, don't just reread it, (3) walk through the Indian
  example in vivid detail, painting a picture, not just naming it, (4) mention
  the misconception explicitly, explain WHY students get confused, and correct
  it, (5) end with a one-line recap in different words than the key_points.

  Speak slowly and clearly, as if pausing between ideas — write natural spoken
  pauses using sentence breaks, not one long run-on paragraph.

- quiz: one MCQ with 4 options, phrased in the style and difficulty level of actual
  CBSE/Karnataka board exam or NCERT exemplar questions (not casual trivia-style
  questions). Include the correct answer_index and a short explanation that clarifies
  WHY the other options are wrong, not just why the right one is right.

- key_equation: if this section involves a chemical formula, equation, or
  mathematical expression central to the concept, write it here EXACTLY as
  it should be displayed on screen (e.g. "Fe3O4", "CaO + H2O -> Ca(OH)2 + Heat",
  "x^2 + 5x + 6 = 0"). Leave this as an empty string if the section has no
  formula/equation. This is shown visually on a slide — it is NOT spoken, so
  formula notation is fine here even though it must be avoided in narration.

Rules:
- Output ONLY valid JSON matching the given schema. No markdown fences, no preamble, no commentary.
- Do not invent facts not grounded in the source text.
- Keep language simple enough for a Class 6 student unless the source is clearly
  Class 11/12 level — but never oversimplify to the point of dropping exam-relevant
  terminology.
- Prioritize what is most likely to be tested in exams when choosing which key
  points and misconceptions to highlight.
"""


def _get_model():
    api_key = os.environ.get("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": GEMINI_RESPONSE_SCHEMA,
            "temperature": 0.4,
        },
        system_instruction=SYSTEM_PROMPT,
    )


def structure_chapter(chapter_text: str, max_retries: int = 2) -> Chapter:
    """
    Sends the whole chapter in ONE call. Retries on invalid JSON or schema
    mismatch. Narration length issues are logged as warnings, not treated
    as hard failures — a short section shouldn't discard an otherwise good
    chapter's worth of content.
    """
    model = _get_model()
    last_error = None
    last_valid_chapter = None

    for attempt in range(max_retries + 1):
        response = model.generate_content(chapter_text, request_options={"timeout": 60})
        raw_text = response.text

        try:
            data = json.loads(raw_text)
            chapter = Chapter.model_validate(data)
            last_valid_chapter = chapter

            issues = validate_narration_length(chapter)
            if issues:
                print(f"[Warning] Narration length issues (attempt {attempt + 1}): {issues}")
                if attempt < max_retries:
                    continue  # try again for a better result
                else:
                    print("[Warning] Max retries reached — proceeding with current chapter despite length issues.")
                    return chapter

            return chapter

        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            continue

    if last_valid_chapter is not None:
        return last_valid_chapter

    raise RuntimeError(
        f"Gemini failed to return valid structured JSON after {max_retries + 1} attempts: {last_error}"
    )