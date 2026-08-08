"""
Step 2 of the pipeline: one Gemini call per chapter (not per image/section),
returns strict JSON validated against schema.py -> Chapter.
"""
import os
import json
import google.generativeai as genai
from pydantic import ValidationError

from schema import Chapter, GEMINI_RESPONSE_SCHEMA

MODEL_NAME = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """You are an expert NCERT curriculum teacher creating structured
video lesson content for Class 6-12 Indian students (Karnataka state board priority).

For the given chapter text, break it into logical sections (one per major concept/heading).
For EACH section, produce:
- title: the section heading from the NCERT text
- hook: one-line real-life relevance, using Indian context
- concept: the core idea in 2-3 simple sentences, plain language
- indian_example: a relatable Indian daily-life example (avoid generic/Western examples)
- key_points: array of exactly 3 must-remember facts
- misconception: one common mistake students make on this topic
- narration: a 60-90 second teacher-style spoken explanation, warm and conversational,
  as if speaking directly to a Class 6-12 student. No markdown, no symbols, no stage directions.
- quiz: one MCQ with 4 options, the correct answer_index, and a short explanation

Rules:
- Output ONLY valid JSON matching the given schema. No markdown fences, no preamble, no commentary.
- Do not invent facts not grounded in the source text.
- Keep language simple enough for a Class 6 student unless the source is clearly Class 11/12 level.
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
    Sends the whole chapter in ONE call. Retries on invalid JSON / schema
    mismatch (Gemini JSON mode is reliable but not 100%).
    """
    model = _get_model()
    last_error = None

    for attempt in range(max_retries + 1):
        response = model.generate_content(chapter_text)
        raw_text = response.text

        try:
            data = json.loads(raw_text)
            chapter = Chapter.model_validate(data)
            return chapter
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Gemini failed to return valid structured JSON after {max_retries + 1} attempts: {last_error}"
    )