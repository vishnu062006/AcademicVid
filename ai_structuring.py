"""
Step 2 of the pipeline: one Gemini call per chapter (not per image/section),
returns strict JSON validated against schema.py -> Chapter.
Supports both English and Kannada narration via the `language` parameter.
"""
import os
import json

# gRPC's built-in DNS resolver fails on networks whose DNS server is an IPv6 link-local
# address (seen on a home router: "Could not contact DNS servers"). The OS resolver works
# everywhere, so use it. Must be set before google.generativeai (gRPC) is imported.
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

import google.generativeai as genai
from pydantic import ValidationError

from schema import Chapter, GEMINI_RESPONSE_SCHEMA
from content_validators import validate_narration_length, validate_kannada_script
from kannada_quality import fix_known_terms, find_glitches

MODEL_NAME = "gemini-3.5-flash-lite"
# A whole lesson is one long reply. On the free tier we measured 66 s for just 2 topics,
# so 60 s was too short and full chapters timed out. 240 s leaves room for a full chapter.
GEMINI_TIMEOUT_SECONDS = 240

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

SYSTEM_PROMPT_KANNADA = """You are an expert NCERT curriculum teacher creating structured
video lesson content in KANNADA for Class 6-12 Karnataka state board students who are
preparing for board exams. Your explanations must build real understanding AND directly
help students score well in exams — both matter equally.

Write ALL text fields below in natural, conversational, school-level Kannada — the way a
real Kannada-medium teacher speaks to students, NOT formal literary Kannada, NOT stiff
machine-translated Kannada. Use Kannada script (ಕನ್ನಡ ಲಿಪಿ) throughout, never
transliteration (never write Kannada using English letters).

Common scientific/technical terms that Karnataka classrooms normally say in English even
while speaking Kannada (e.g. "oxygen", "chemical reaction", "atom", "equation") may be kept
in English within the Kannada sentence — this natural code-switching is expected and
preferred over forcing awkward or confusing Kannada translations of technical terms.

For the given chapter text, break it into logical sections (one per major concept/heading).
For EACH section, produce (all in Kannada except key_equation and where noted):

- title: the section heading, in Kannada (keep the NCERT term recognizable — Karnataka
  students should be able to match this to their textbook heading)

- hook: one-line real-life relevance, in Kannada, using Karnataka/Indian daily-life context

- concept: the core idea in 2-3 sentences, in Kannada. Be specific and concrete, not
  abstract — include the actual mechanism, reason, or process, not just a restatement of
  the definition. Use exact terminology expected in Karnataka board exam answers.

- indian_example: a relatable Karnataka/Indian daily-life example, in Kannada (avoid
  generic examples — prefer things a Karnataka student would immediately recognize)

- key_points: array of exactly 3 must-remember facts, in Kannada, phrased the way a
  student would need to write them in a 1-2 mark Karnataka board exam answer — precise,
  correct terminology, not casual paraphrasing

- misconception: one common mistake students make on THIS specific topic that costs marks
  in exams, in Kannada. Be specific to this concept, not generic.

- narration: a warm, teacher-style spoken explanation IN KANNADA. HARD REQUIREMENT: at
  least 180 words and no more than 300 words (Kannada words, counted by spaces) — this is
  validated programmatically.

  CRITICAL: this text will be converted to Kannada speech using text-to-speech. NEVER
  write raw chemical formulas, mathematical notation, or symbols in narration (e.g. do
  not write "Fe3O4", "CaO + H2O", "x^2"). Always spell them out in spoken Kannada words
  the way a teacher would say them aloud, code-switching to English for the technical term
  itself where natural (e.g. say the compound name in English, explain around it in
  Kannada).

  Structure it as: (1) restate the hook as a question, in Kannada, (2) explain the concept
  by walking through the reasoning/mechanism in Kannada — go deeper than the on-screen
  text, don't just reread it, (3) walk through the Indian/Karnataka example in vivid
  detail, in Kannada, (4) mention the misconception explicitly, explain WHY students get
  confused, and correct it, in Kannada, (5) end with a one-line recap in Kannada, in
  different words than key_points.

  Speak slowly and clearly, as if pausing between ideas — write natural spoken pauses
  using sentence breaks, not one long run-on paragraph.

- quiz: one MCQ with 4 options, in Kannada, phrased in the style and difficulty of actual
  Karnataka board exam or NCERT exemplar questions. Include the correct answer_index and
  a short explanation in Kannada clarifying WHY the other options are wrong.

- key_equation: if this section involves a chemical formula, equation, or mathematical
  expression, write it here EXACTLY as it should be displayed on screen, using standard
  formula notation (e.g. "Fe3O4", "CaO + H2O -> Ca(OH)2 + Heat") — this field is NOT
  translated, it stays in standard scientific notation regardless of language, since it
  is shown visually, not spoken. Leave as empty string if no formula/equation applies.

Rules:
- Output ONLY valid JSON matching the given schema. No markdown fences, no preamble, no
  commentary. JSON keys stay in English exactly as given (title, hook, concept, etc.) —
  only the VALUES are in Kannada.
- Do not invent facts not grounded in the source text.
- Keep language simple enough for a Class 6 student unless the source is clearly Class
  11/12 level — but never oversimplify to the point of dropping exam-relevant terminology.
- Prioritize what is most likely to be tested in exams when choosing key points and
  misconceptions.

CRITICAL: Use ONLY Kannada script (ಕನ್ನಡ). Never use Devanagari/Hindi script
or any other Indian language script. If unsure of a Kannada term, prefer
keeping it in English rather than defaulting to Hindi.

ABSOLUTE REQUIREMENT: Every single word must be either (a) valid Kannada script
(ಅಆಇಈಉಊಋಎಏಐಒಓಔ ಕಖಗಘಙ ಚಛಜಝಞ ಟಠಡಢಣ ತಥದಧನ ಪಫಬಭಮ ಯರಲವಶಷಸಹಳ, matras, etc.)
or (b) plain English letters (a-z, A-Z) for technical/scientific terms. NEVER use
Hindi/Devanagari script, Tamil script, Telugu script, Bengali script, or any other
script. If you are not certain a character is correct Kannada script, replace it
with the English equivalent word instead. Double-check every word before finalizing.

Use simple, natural, student-friendly Kannada while preserving scientific accuracy and including English equivalents in parentheses for difficult technical terms (e.g., ಉತ್ಕರ್ಷಣ (Oxidation), ಸ್ಥಾನಪಲ್ಲಟ (Displacement), ಆವಿ (Vapour)).

Only in the narration of the LAST section, end with one short, polite Kannada thank-you
and a line of encouragement for the students. Do NOT add a thank-you to any other section.
"""


# ---------------------------------------------------------------------------
# Lesson modes. The JSON shape (schema.py) is the same for every mode, so every
# output (video, PPT, notes, flashcards) works unchanged; only the MEANING of the
# fields changes, and slides.get_labels() shows matching headings.
# ---------------------------------------------------------------------------
MODE_CHAPTER = "chapter"                # textbook chapter (science, maths, social...)
MODE_KANNADA_LIT = "kannada_literature" # Kannada subject: a story (ಗದ್ಯ) or poem (ಪದ್ಯ)
MODE_TOPICS = "topics"                  # custom subject + topic list, e.g. CSE
MODES = (MODE_CHAPTER, MODE_KANNADA_LIT, MODE_TOPICS)

SYSTEM_PROMPT_KANNADA_LITERATURE = """You are an experienced Kannada-medium teacher of the
KANNADA LANGUAGE subject for Karnataka state board students (Class 6-10 / PUC). The input is
a Kannada textbook lesson: either a story / prose lesson (ಗದ್ಯ) or a poem (ಪದ್ಯ).

This is NOT a science lesson. Do not explain it as concepts and facts. Teach it the way a good
Kannada teacher does in class: follow the story or poem IN ORDER, part by part, and help the
student enjoy it, understand it, and write good exam answers about it.

Write EVERYTHING in natural, school-level Kannada script (ಕನ್ನಡ ಲಿಪಿ). Never use English
letters, Hindi/Devanagari or any other script. Never transliterate.

Break the lesson into sections that follow the text in order: for a story, one section per
major part of the story (beginning, each important event, ending); for a poem, one section per
stanza or group of stanzas. Then add ONE final section about the whole lesson: its central
idea / message, the author or poet (only if the text names them), and the values it teaches.

For EACH section, the fields mean:

- title: a short Kannada heading for this part (e.g. "ಕಥೆಯ ಆರಂಭ", "ಮೊದಲ ಪದ್ಯಭಾಗ").

- hook: ಸಂದರ್ಭ - one or two lines that set the scene: where we are in the story/poem, who is
  speaking or what is happening. For the final section: why this lesson matters to students.

- concept: ಭಾವಾರ್ಥ / ಸಾರಾಂಶ - explain THIS part in simple, clear Kannada prose, in 3-5
  sentences, in the order it happens. For a poem, give the meaning of the lines (ಭಾವಾರ್ಥ),
  not a word-by-word translation.

- indian_example: ಜೀವನಕ್ಕೆ ಹೊಂದಾಣಿಕೆ - connect this part to the student's own life,
  family, village or school in Karnataka, or to the value it teaches (ಜೀವನ ಮೌಲ್ಯ).

- key_points: exactly 3 items. Prefer difficult words with their meanings, written as
  "ಪದ - ಅರ್ಥ" (e.g. "ನೇಸರ - ಸೂರ್ಯ"). If the part has fewer than 3 hard words, add the most
  important event, character trait or literary point (ಅಲಂಕಾರ, ಛಂದಸ್ಸು) a student must remember.

- misconception: ಗಮನಿಸಿ - one specific thing students often get wrong in exams about THIS
  part: confusing characters, the wrong speaker in a ಸಂದರ್ಭ question, a misread word or line,
  or mixing up the poet's name. Be specific, not generic.

- key_equation: the ONE most important line (or two lines) from the original text in this
  part, quoted EXACTLY as written in the input - the kind of line that comes in
  "ಸಂದರ್ಭ ಸಹಿತ ವಿವರಿಸಿ" exam questions. Copy it character for character from the input;
  never invent or "improve" a line. Leave it as an empty string if no line is worth quoting.

- narration: a warm, storytelling explanation IN KANNADA for text-to-speech, 150-300 words.
  Tell this part of the story (or explain these lines) as a teacher would aloud in class:
  set the scene, retell what happens with feeling, explain the meaning and the hard words,
  connect it to the student's life, and mention the common mistake. No symbols or numbers in
  digits; write them as words. In the LAST section only, end with one short, polite Kannada
  thank-you and a line of encouragement for the students.

- quiz: one question in Karnataka board style about this part (who said it, what happened,
  what a word means, or the meaning of a line), 4 options, the correct answer_index, and a
  short explanation in Kannada.

Rules:
- Output ONLY valid JSON matching the given schema. JSON keys stay in English; values in Kannada.
- subject must be "Kannada". chapter_title is the lesson's name as written in the text.
- Stay faithful to the text: do not add events, characters or lines that are not in it.
"""

TOPIC_MODE_PREFIX = """IMPORTANT - THIS INPUT IS DIFFERENT FROM A TEXTBOOK CHAPTER.
The input is a teacher's own syllabus: a subject, a level, and a list of topics (sometimes
with short notes). There is no textbook text. Follow these rules, which OVERRIDE any rule
below that talks about a textbook, NCERT text, or "facts grounded in the source text":

- Create EXACTLY one section per topic, in the same order as the list. Do not skip, merge
  or add topics. Use the topic name as the section title.
- Teach each topic from your own knowledge, at the stated level, covering every point a
  student needs for exams and interviews at that level. If the teacher wrote notes under a
  topic, make sure every one of those points is covered.
- Accuracy matters more than anything else. Use standard, correct terminology. Never invent
  facts, APIs, commands, formulas or results; if something is uncertain, leave it out.
- For computer science: indian_example should be a real-world Indian example where it fits
  (UPI payments, IRCTC booking, Aadhaar, railway reservation queues, mobile recharge, etc.);
  key_equation may hold a formula, a time complexity (e.g. "O(n log n)"), or a SHORT piece of
  code or pseudo-code of at most 4 lines that is central to the topic; narration must never
  read code symbols aloud - describe what the code does in words.
- subject: use "Computer Science" for any computing subject, otherwise the closest value.
- chapter_title: the subject name the teacher gave.

"""


def _system_prompt(language: str, mode: str) -> str:
    if mode == MODE_KANNADA_LIT:
        return SYSTEM_PROMPT_KANNADA_LITERATURE
    base = SYSTEM_PROMPT if language == "English" else SYSTEM_PROMPT_KANNADA
    if mode == MODE_TOPICS:
        return TOPIC_MODE_PREFIX + base
    return base


def build_topics_input(subject: str, level: str, topics_text: str) -> str:
    """Turn the custom-topics form into the text sent to Gemini (topic mode)."""
    return (
        "Subject: {}\nLevel: {}\n\nTopics to cover, in this order "
        "(lines starting with '-' under a topic are the teacher's notes for it):\n{}"
    ).format(subject.strip(), level.strip(), topics_text.strip())


def _get_model(language: str = "English", mode: str = MODE_CHAPTER):
    api_key = os.environ.get("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    prompt = _system_prompt(language, mode)
    return genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": GEMINI_RESPONSE_SCHEMA,
            "temperature": 0.4,
        },
        system_instruction=prompt,
    )


def structure_chapter(chapter_text: str, language: str = "English", max_retries: int = 2,
                      mode: str = MODE_CHAPTER) -> Chapter:
    """
    Sends the whole chapter in ONE call. Retries on invalid JSON or schema
    mismatch. Narration length issues are logged as warnings, not treated
    as hard failures — a short section shouldn't discard an otherwise good
    chapter's worth of content.

    language: "English" or "Kannada" — determines which prompt is used.
    mode: MODE_CHAPTER (default, unchanged behaviour), MODE_KANNADA_LIT (Kannada subject:
          story/poem; always written in Kannada) or MODE_TOPICS (custom topic list).
    """
    if mode not in MODES:
        mode = MODE_CHAPTER
    if mode == MODE_KANNADA_LIT:
        language = "Kannada"
    model = _get_model(language, mode)
    last_error = None
    last_valid_chapter = None

    for attempt in range(max_retries + 1):
        response = model.generate_content(chapter_text, request_options={"timeout": GEMINI_TIMEOUT_SECONDS})
        raw_text = response.text

        try:
            data = json.loads(raw_text)
            if mode == MODE_KANNADA_LIT:
                data["subject"] = "Kannada"   # always drive the story/poem labels and theme
            chapter = Chapter.model_validate(data)

            # KNOWN_FIXES are science-term corrections; they must not rewrite a story or poem.
            if language == "Kannada" and mode != MODE_KANNADA_LIT:
                chapter = fix_known_terms(chapter)

            last_valid_chapter = chapter

            # Length problems are only logged: a slightly short or long narration is
            # still a usable lesson, and a retry costs a whole Gemini call (free-tier quota).
            length_issues = validate_narration_length(chapter, language=language)
            if length_issues:
                print(f"[Warning] Narration length (attempt {attempt + 1}): {length_issues}")

            # Wrong script (Hindi letters, Latin glued into Kannada words) is a real defect
            # students would see and hear, so that one is worth another call.
            script_issues = []
            if language == "Kannada":
                script_issues = validate_kannada_script(chapter) + find_glitches(chapter)
            if script_issues and attempt < max_retries:
                print(f"[Warning] Kannada script issues (attempt {attempt + 1}), retrying: {script_issues}")
                continue
            if script_issues:
                print("[Warning] Max retries reached — using the chapter despite script issues.")

            return chapter

        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            continue

    if last_valid_chapter is not None:
        return last_valid_chapter

    raise RuntimeError(
        f"Gemini failed to return valid structured JSON after {max_retries + 1} attempts: {last_error}"
    )