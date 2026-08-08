"""
Single source of truth for the JSON contract. Every downstream module
(slides, tts, video, quiz, ppt) consumes this shape.
"""
from typing import List
from pydantic import BaseModel, Field


class Quiz(BaseModel):
    question: str
    options: List[str] = Field(min_length=2, max_length=4)
    answer_index: int
    explanation: str


class Section(BaseModel):
    title: str
    hook: str
    concept: str
    indian_example: str
    key_points: List[str] = Field(min_length=1, max_length=5)
    misconception: str
    narration: str  # 60-90s teacher-style spoken explanation
    quiz: Quiz


class Chapter(BaseModel):
    chapter_title: str
    subject: str  # drives slide color theme: Science / Math / Social Science / English
    sections: List[Section]


# Gemini structured-output schema (subset of JSON Schema Gemini accepts)
GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "chapter_title": {"type": "string"},
        "subject": {
            "type": "string",
            "enum": ["Science", "Math", "Social Science", "English", "Other"],
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "hook": {"type": "string"},
                    "concept": {"type": "string"},
                    "indian_example": {"type": "string"},
                    "key_points": {"type": "array", "items": {"type": "string"}},
                    "misconception": {"type": "string"},
                    "narration": {"type": "string"},
                    "quiz": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "string"}},
                            "answer_index": {"type": "integer"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["question", "options", "answer_index", "explanation"],
                    },
                },
                "required": [
                    "title", "hook", "concept", "indian_example",
                    "key_points", "misconception", "narration", "quiz",
                ],
            },
        },
    },
    "required": ["chapter_title", "subject", "sections"],
}