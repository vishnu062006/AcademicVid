import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

from manifest import CHAPTER_MANIFEST
from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from slides import build_section_slides
from tts import synthesize_narration, VOICE_EN, VOICE_KN
from video_builder import build_section_video, concatenate_section_videos
from ppt_export import export_chapter_to_pptx
from transcript_export import export_transcript_pdf
from flashcards import generate_flashcards


load_dotenv()

BASE_TMP_DIR = "tmp_sessions"
OUTPUT_OPTIONS = {
    "Video": "video",
    "PPT": "ppt",
    "Transcript PDF": "transcript",
    "Flashcards": "flashcards",
}
OUTPUT_CAPTIONS = {
    "Video": "Animated lesson with AI narration",
    "PPT": "Editable presentation deck",
    "Transcript PDF": "Clean, printable study notes",
    "Flashcards": "Quick recall and revision cards",
}
SOURCE_OPTIONS = ["Library", "Upload PDF"]
LANGUAGE_OPTIONS = ["English", "Kannada"]

# ---------------------------------------------------------------------
# Session state and filesystem helpers
# ---------------------------------------------------------------------
def init_session_state() -> None:
    defaults = {
        "session_id": str(uuid.uuid4()),
        "app_state": "setup",
        "chapter": None,
        "selected_language": "English",
        "last_generated_type": "video",
        "selected_output_label": "Video",
        "source_mode": "Library",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_session_dir() -> str:
    path = os.path.join(BASE_TMP_DIR, st.session_state.session_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_uploaded_pdf(uploaded_file, session_dir: str) -> str:
    path = os.path.join(session_dir, "input.pdf")
    with open(path, "wb") as file:
        file.write(uploaded_file.getbuffer())
    return path


def reset_pipeline() -> None:
    st.session_state.app_state = "setup"
    st.session_state.chapter = None
    for key in (
        "final_video_path",
        "final_ppt_path",
        "final_transcript_path",
        "final_audio_path",
        "flashcards",
        "last_error",
    ):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------
# Premium dark UI
# ---------------------------------------------------------------------
def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        :root {
            --bg: #08090d;
            --surface: #101218;
            --surface-2: #151821;
            --border: rgba(255,255,255,.10);
            --border-hover: rgba(255,255,255,.22);
            --text: #f5f7fb;
            --muted: #9ba3b5;
            --accent: #c5ff4a;
            --accent-soft: rgba(197,255,74,.11);
            --purple: #a78bfa;
        }
        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }
        .stApp {
            background:
              radial-gradient(ellipse at 50% -8%, rgba(212,255,58,.035), transparent 34%),
              radial-gradient(ellipse at 80% 0%, rgba(111,76,255,.10), transparent 32%),
              radial-gradient(ellipse at 0% 25%, rgba(197,255,74,.045), transparent 30%),
              var(--bg);
            color: var(--text);
        }
        @keyframes textShine {
            to { background-position: 200% center; }
        }
        @keyframes aiPulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(197,255,74,.10), 0 0 14px rgba(197,255,74,.07);
                border-color: rgba(197,255,74,.45);
            }
            50% {
                box-shadow: 0 0 0 4px rgba(197,255,74,.08), 0 0 28px rgba(197,255,74,.20);
                border-color: rgba(197,255,74,.95);
            }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { right: 1rem; }
        .main .block-container {
            max-width: 1240px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        h1, h2, h3, h4, p, label, li { color: var(--text); }
        h1, h2, h3, .brand-name, .hero-title {
            font-family: 'Space Grotesk', sans-serif !important;
            letter-spacing: -.035em;
        }
        p, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: var(--muted);
        }
        [data-testid="stSidebar"] {
            background: rgba(12,14,19,.96);
            border-right: 1px solid var(--border);
            min-width: 300px !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] {
            font-size: .9rem !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            font-size: .9rem !important;
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
        [data-testid="stSidebar"] * { color: var(--text); }
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            font-size: 0.88rem !important;
        }
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] {
            min-width: 0 !important;
        }
        [data-testid="stSidebar"] label {
            color: #c7ccda !important;
            font-weight: 600 !important;
            margin-bottom: 6px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] > label,
        [data-testid="stSidebar"] div[data-testid="stFileUploader"] > label {
            margin-bottom: 6px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stSelectbox"],
        [data-testid="stSidebar"] div[data-testid="stFileUploader"] {
            margin-bottom: 10px !important;
        }
        .brand-lockup {
            display: flex; align-items: center; gap: 12px;
            margin: 4px 0 28px;
        }
        .brand-mark {
            display: flex; align-items: center; justify-content: center;
            width: 42px; height: 42px; border-radius: 13px;
            color: #0b0d0f; background: var(--accent);
            font: 800 20px 'Space Grotesk', sans-serif;
            box-shadow: 0 0 28px rgba(197,255,74,.13);
        }
        .brand-name { color: var(--text); font-size: 19px; font-weight: 700; }
        .brand-caption {
            color: var(--muted); font-size: 11px; margin-top: 1px;
            letter-spacing: .12em; text-transform: uppercase;
        }
        .eyebrow {
            color: var(--accent); font-size: 11px; font-weight: 700;
            letter-spacing: .17em; text-transform: uppercase;
            margin-bottom: 14px;
        }
        .hero {
            position: relative; overflow: hidden;
            padding: 38px 40px 36px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            background: linear-gradient(125deg, rgba(22,25,34,.97), rgba(13,15,21,.92));
            margin-bottom: 30px;
        }
        .hero:after {
            content: ''; position: absolute; width: 240px; height: 240px;
            right: -70px; top: -120px; border-radius: 50%;
            background: rgba(197,255,74,.09); filter: blur(35px);
            pointer-events: none;
        }
        .hero-title {
            color: var(--text); font-size: clamp(2.2rem, 5vw, 4rem);
            line-height: 1.04; font-weight: 700; max-width: 760px;
            margin: 0 0 16px;
        }
        .gradient-text {
            background: linear-gradient(90deg, #c5ff4a 0%, #a7f3d0 45%, #b7a4ff 100%);
            background-size: 200% auto;
            -webkit-background-clip: text; background-clip: text;
            color: transparent;
            animation: textShine 7s linear infinite;
        }
        .hero-subtitle {
            color: #a8afbf; font-size: 15px; line-height: 1.75;
            max-width: 720px; margin: 0;
        }
        .learning-promise {
            display: flex; flex-wrap: wrap; gap: 9px; margin-top: 20px;
        }
        .learning-promise span {
            display: inline-flex; align-items: center; gap: 7px;
            color: #d8deea; font-size: 12px;
            background: rgba(255,255,255,.035);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 10px; padding: 9px 12px;
        }
        .learning-promise b { color: var(--accent); font-weight: 700; }
        .hero-meta {
            display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px;
        }
        .meta-pill {
            color: #747c8d; font-size: 11px; letter-spacing: .04em;
            border: 1px solid rgba(255,255,255,.055); background: rgba(255,255,255,.018);
            padding: 7px 11px; border-radius: 99px;
        }
        .meta-pill.active {
            color: var(--accent);
            border-color: rgba(197,255,74,.42);
            background: rgba(197,255,74,.075);
            box-shadow: 0 0 18px rgba(197,255,74,.045);
        }
        /* Keep the setup workflow centered and readable on wide displays. */
        div[data-testid="stMainBlockContainer"] {
            max-width: 1120px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
        .setup-content {
            max-width: 840px;
            width: 100%;
            margin: 0 auto;
        }
        .section-heading {
            color: var(--text); font-family: 'Space Grotesk', sans-serif;
            font-size: 21px; font-weight: 700; letter-spacing: -.025em;
            margin: 6px 0 5px;
        }
        .section-description { color: var(--muted); font-size: 13px; margin-bottom: 17px; }
        .format-card-caption {
            min-height: 42px;
            margin: 8px 2px 18px;
            color: #9CA3AF;
            font-size: 13px;
            font-weight: 400;
            line-height: 1.5;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stButton"] > button {
            min-height: 78px;
            padding: 18px 20px !important;
            text-align: left !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            border-radius: 16px !important;
            transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stButton"] > button:hover {
            transform: translateY(-3px);
            border-color: rgba(212,255,58,.55) !important;
            box-shadow: 0 10px 24px -12px rgba(212,255,58,.22) !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stButton"] > button[kind="primary"] {
            background: rgba(197,255,74,.12) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--accent) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.12), 0 8px 24px rgba(197,255,74,.06) !important;
        }
        .step-label {
            color: var(--accent); font-size: 10px; font-weight: 700;
            letter-spacing: .16em; text-transform: uppercase; margin-bottom: 8px;
        }
        .panel {
            background: rgba(16,18,24,.84); border: 1px solid var(--border);
            border-radius: 18px; padding: 22px; margin: 12px 0 22px;
        }
        .chapter-card {
            background: rgba(16,18,24,.84); border: 1px solid var(--border);
            border-radius: 16px; padding: 18px 20px; margin: 12px 0 20px;
        }
        .chapter-card {
            min-height: 150px;
            padding: 24px 26px;
            margin: 12px 0 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .chapter-card .chip-row { margin-bottom: 16px; }
        .chapter-title { overflow-wrap: anywhere; line-height: 1.35; }
        .chapter-hint {
            color: #9CA3AF; font-size: 13px; line-height: 1.55; margin-top: 9px;
        }
        .action-panel {
            min-height: 150px;
            display: flex; flex-direction: column; justify-content: center;
            padding: 22px 24px;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(197,255,74,.055), rgba(167,139,250,.035));
            margin: 12px 0 12px;
        }
        .action-kicker {
            color: var(--accent); font-size: 10px; font-weight: 700;
            letter-spacing: .16em; margin-bottom: 9px;
        }
        .action-title {
            color: var(--text); font: 600 18px 'Space Grotesk', sans-serif;
            line-height: 1.3; margin-bottom: 7px;
        }
        .action-copy { color: #9CA3AF; font-size: 13px; line-height: 1.55; }
        @media (max-width: 760px) {
            .chapter-card, .action-panel { min-height: 0; }
        }
        .chip-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 16px; }
        .chip {
            padding: 5px 9px; border-radius: 99px; font-size: 10px;
            font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
            color: #c4cbd8; background: rgba(255,255,255,.055);
            border: 1px solid var(--border);
        }
        .chip-accent {
            color: #D4FF3A !important;
            background: rgba(212,255,58,.10) !important;
            border-color: rgba(212,255,58,.55) !important;
        }
        .chapter-title {
            color: var(--text); font: 700 18px 'Space Grotesk', sans-serif;
            line-height: 1.4; margin-top: 2px;
        }
        div[data-testid="stRadio"] > label,
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stFileUploader"] label {
            color: #dce1ec !important; font-weight: 600 !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] { gap: 10px; }

        /* Output-format cards: clean, balanced 2 × 2 grid. */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 14px !important;
            width: 100% !important;
            align-items: stretch !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            width: 100% !important;
            min-width: 0 !important;
            min-height: 108px !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 22px 24px !important;
            display: flex !important;
            align-items: center !important;
            border-radius: 16px !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            position: relative !important;
            transition: transform .3s cubic-bezier(.4,0,.2,1),
                        box-shadow .3s cubic-bezier(.4,0,.2,1),
                        border-color .3s ease,
                        background .3s ease !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            transform: translateY(-4px) scale(1.01) !important;
            border-color: rgba(212,255,58,.5) !important;
            box-shadow: 0 12px 24px -10px rgba(212,255,58,.15) !important;
            z-index: 2;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:last-child {
            min-width: 0 !important;
            width: 100% !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label p {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
                grid-template-columns: minmax(0, 1fr) !important;
            }
            [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
                min-height: 88px !important;
                padding: 18px 20px !important;
            }
        }
        /* Four output formats: balanced, centered 2 x 2 card grid. */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"]:has(input) div[role="radiogroup"] {
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 14px !important;
            max-width: 840px !important;
            margin: 0 auto !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            box-sizing: border-box !important;
            width: 100% !important;
            min-height: 118px !important;
            padding: 22px 24px !important;
            justify-content: flex-start !important;
            align-items: flex-start !important;
            border-radius: 16px !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stMarkdownContainer"] {
            width: 100% !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label p {
            color: #FFFFFF !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
            line-height: 1.35 !important;
            margin: 0 !important;
            white-space: normal !important;
        }
        /* Title is the radio label text; subtitle is a separate generated element.
           This avoids relying on Streamlit's Markdown newline parsing. */
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label
        [data-testid="stMarkdownContainer"] p {
            color: #FFFFFF !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            line-height: 1.35 !important;
            margin: 0 !important;
            white-space: normal !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label
        [data-testid="stMarkdownContainer"]::after {
            display: block !important;
            margin-top: 7px !important;
            color: #9CA3AF !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            line-height: 1.45 !important;
            white-space: normal !important;
        }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(1)
        [data-testid="stMarkdownContainer"]::after { content: "Animated lesson with AI narration"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(2)
        [data-testid="stMarkdownContainer"]::after { content: "Editable presentation deck"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(3)
        [data-testid="stMarkdownContainer"]::after { content: "Clean, printable study notes"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(4)
        [data-testid="stMarkdownContainer"]::after { content: "Quick recall and revision cards"; }
        [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            border-color: #D4FF3A !important;
            background: rgba(197,255,74,.075) !important;
            box-shadow: 0 0 0 1px rgba(212,255,58,.2), 0 10px 30px rgba(197,255,74,.06) !important;
        }
        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"] div[data-testid="stRadio"] div[role="radiogroup"] {
                grid-template-columns: minmax(0, 1fr) !important;
            }
        }
        /* Sidebar source selector: connected two-part segmented control. */
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 0 !important;
            width: 100% !important;
            padding: 4px !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            background: #0c0e13 !important;
            overflow: hidden !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
            flex: 1 1 50% !important;
            width: 50% !important;
            min-width: 0 !important;
            min-height: 38px !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            padding: 8px 6px !important;
            margin: 0 !important;
            border: 0 !important;
            border-radius: 8px !important;
            background: transparent !important;
            box-shadow: none !important;
            transform: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            background: var(--accent-soft) !important;
            box-shadow: inset 0 0 0 1px rgba(197,255,74,.35) !important;
        }
        [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label p {
            font-size: 12px !important;
            font-weight: 600 !important;
            text-align: center !important;
            white-space: nowrap !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label {
            border: 1px solid var(--border) !important;
            background: rgba(255,255,255,.025) !important;
            border-radius: 14px !important; padding: 22px 24px !important;
            transition: border .18s ease, background .18s ease, transform .18s ease;
            min-height: 92px;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            border-color: var(--border-hover) !important;
            transform: translateY(-1px);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            border-color: var(--accent) !important;
            background: var(--accent-soft) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.14), 0 8px 28px rgba(197,255,74,.035);
        }
        /* Hide Streamlit's native radio indicator; the card itself shows selection. */
        div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {
            display: none !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            gap: 0 !important;
            align-items: flex-start !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
            color: var(--text) !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            line-height: 1.35 !important;
            margin: 0 !important;
            white-space: pre-line !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.14), 0 8px 28px rgba(197,255,74,.06) !important;
        }
        /* Subtitle is rendered as the second line in each output card. */
        div[data-testid="stRadio"] div[role="radiogroup"] label p span {
            display: block !important;
            color: #9CA3AF !important;
            font-size: .85rem !important;
            font-weight: 400 !important;
            margin-top: 5px !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
            color: var(--text) !important;
        }
        div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
        div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
            background: #11141b !important; color: var(--text) !important;
            border: 1px solid var(--border) !important; border-radius: 11px !important;
        }
        div[data-baseweb="select"] > div:hover, div[data-baseweb="input"] > div:focus-within,
        div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus {
            border-color: rgba(197,255,74,.6) !important;
            box-shadow: 0 0 0 1px rgba(197,255,74,.12) !important;
        }
        [data-testid="stFileUploader"] section {
            background: rgba(255,255,255,.025) !important;
            border: 1px dashed rgba(255,255,255,.2) !important; border-radius: 13px !important;
        }
        [data-testid="stFileUploader"] section * { color: #cbd1df !important; }
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
            border: 1px solid transparent !important; border-radius: 11px !important;
            min-height: 46px; font-weight: 700 !important;
            transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: var(--accent) !important; color: #000000 !important;
            font-weight: 700 !important;
            box-shadow: 0 5px 22px rgba(197,255,74,.11) !important;
        }
        .stButton > button[kind="primary"] *,
        .stFormSubmitButton > button[kind="primary"] *,
        .stButton > button[kind="primary"]:disabled,
        .stFormSubmitButton > button[kind="primary"]:disabled {
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
            background: #d4ff79 !important; transform: translateY(-1px);
            box-shadow: 0 8px 28px rgba(197,255,74,.18) !important;
        }
        .stButton > button[kind="secondary"] {
            background: #171a22 !important; color: var(--text) !important;
            border-color: var(--border) !important;
        }
        .stButton > button:focus { box-shadow: 0 0 0 2px rgba(197,255,74,.3) !important; }
        /* During AI work, Streamlit displays an active status/progress region. */
        [data-testid="stStatusWidget"][data-state="running"] ~ * .stButton > button[kind="primary"],
        [data-testid="stStatusWidget"][data-state="running"] .stButton > button[kind="primary"] {
            animation: aiPulse 1.35s ease-in-out infinite !important;
        }
        .stButton > button[kind="primary"]:active {
            transform: translateY(1px) scale(.995) !important;
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        [data-testid="stExpander"] {
            background: rgba(255,255,255,.025); border: 1px solid var(--border);
            border-radius: 12px;
        }
        [data-testid="stProgressBar"] > div > div { background: var(--accent) !important; }
        hr { border-color: var(--border) !important; }
        .footer {
            color: #6f7789; font-size: 11px; text-align: center;
            margin-top: 44px; padding-top: 20px; border-top: 1px solid var(--border);
        }
        @media (max-width: 700px) {
            .main .block-container { padding: 1rem 1rem 3rem; }
            .hero { padding: 26px 22px; border-radius: 18px; }
            .hero-title { font-size: 2.25rem; }
            div[data-testid="stRadio"] div[role="radiogroup"] { flex-direction: column; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_and_hero() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">AI-powered learning workspace</div>
          <div class="hero-title">Learn it.<br><span class="gradient-text">See it. Remember it.</span></div>
          <p class="hero-subtitle">
            Turn your textbook chapter into a lesson that is easier to understand and remember.
            Learn with clear explanations, everyday examples, and narration in English or Kannada.
          </p>
          <div class="learning-promise">
            <span><b>✓</b> Simple, step-by-step explanations</span>
            <span><b>✦</b> Examples from everyday life</span>
            <span><b>ಕನ್ನಡ</b> Learn in English or Kannada</span>
          </div>
          <div class="hero-meta">
            <span class="meta-pill active">PDF → structured lesson</span>
            <span class="meta-pill">Clear explanations & examples</span>
            <span class="meta-pill">Ready-to-use study resources</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> Tuple[str, Optional[str], object, Optional[str], Optional[str], Optional[str]]:
    st.sidebar.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-mark">A</div>
          <div>
            <div class="brand-name">AcademicVid</div>
            <div class="brand-caption">AI Learning Studio</div>
          </div>
        </div>
        <div class="step-label">Workspace settings</div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.selectbox(
        "Narration language",
        LANGUAGE_OPTIONS,
        key="selected_language",
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="step-label">Source material</div>', unsafe_allow_html=True)
    source_mode = st.sidebar.radio(
        "Choose source",
        SOURCE_OPTIONS,
        horizontal=True,
        label_visibility="collapsed",
        key="source_mode",
    )

    pdf_path = None
    uploaded_file = None
    selected_class = selected_subject = selected_chapter = None

    if source_mode == "Library":
        classes = list(CHAPTER_MANIFEST.keys())
        if not classes:
            st.sidebar.warning("The library is empty. Upload a PDF to get started.")
        else:
            selected_class = st.sidebar.selectbox("Class / grade", classes)
            subjects = list(CHAPTER_MANIFEST.get(selected_class, {}).keys())
            if subjects:
                selected_subject = st.sidebar.selectbox("Subject", subjects)
                chapters = list(CHAPTER_MANIFEST[selected_class].get(selected_subject, {}).keys())
                if chapters:
                    selected_chapter = st.sidebar.selectbox("Chapter", chapters)
                    pdf_path = CHAPTER_MANIFEST[selected_class][selected_subject][selected_chapter]
                else:
                    st.sidebar.info("No chapters are available for this subject yet.")
            else:
                st.sidebar.info("No subjects are available for this class yet.")
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Drop in a chapter PDF",
            type=["pdf"],
            help="Choose a PDF chapter to turn into a learning resource.",
        )
        if uploaded_file is not None:
            st.sidebar.caption(f"Selected: {uploaded_file.name}")

    st.sidebar.markdown("---")
    st.sidebar.caption("Built for clearer learning, one chapter at a time.")
    return source_mode, pdf_path, uploaded_file, selected_class, selected_subject, selected_chapter


# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------
def execute_ai_structuring(pdf_path: str, language: str) -> None:
    try:
        with st.status("Analyzing your chapter…", expanded=True) as status:
            status.write("Extracting readable text from the PDF.")
            extracted = extract_chapter(pdf_path)
            clean_text = extracted.get("clean_text", "")
            if not clean_text.strip():
                raise ValueError("No readable text was found. Try a text-based PDF instead of a scanned document.")
            status.write("Structuring the chapter into a lesson with AI.")
            chapter = structure_chapter(clean_text, language=language)
            if not getattr(chapter, "sections", None):
                raise ValueError("The AI did not return any lesson sections. Please try again.")
            st.session_state.chapter = chapter
            # Keep the experience one-click: prepare the lesson, then generate
            # the selected resource without asking the learner to approve a script.
            st.session_state.app_state = "generating_media"
            status.update(label="Lesson prepared — starting generation", state="complete")
    except Exception as exc:
        st.session_state.last_error = str(exc)
        st.error(f"Could not prepare the script: {exc}")


def render_review_ui(output_type: str) -> None:
    chapter = st.session_state.chapter
    if chapter is None:
        st.error("No chapter is loaded. Start again from the workspace.")
        if st.button("Back to setup", type="primary"):
            reset_pipeline()
            st.rerun()
        return

    st.markdown('<div class="step-label">Step 02 / Refine</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Review your lesson script</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-description">Make the content yours before generating the final learning resource.</div>',
        unsafe_allow_html=True,
    )
    st.info("Review the AI-generated content and correct anything that needs attention before continuing.")

    with st.form("review_form"):
        # Some Chapter schema versions contain only sections, so don't assume
        # top-level title/subject attributes exist on the Pydantic model.
        chapter_title = st.text_input(
            "Chapter title",
            value=str(getattr(chapter, "title", "") or ""),
            help="Optional title for the lesson.",
        )
        chapter_subject = st.text_input(
            "Subject",
            value=str(getattr(chapter, "subject", "") or ""),
            help="Optional subject label.",
        )
        st.markdown("---")

        for i, section in enumerate(chapter.sections):
            with st.expander(f"SECTION {i + 1}  ·  {section.title}", expanded=(i == 0)):
                section.title = st.text_input(
                    "Section title", value=section.title, key=f"title_{i}"
                )
                left, right = st.columns(2)
                with left:
                    section.hook = st.text_area("Opening hook", value=section.hook, height=100, key=f"hook_{i}")
                    section.misconception = st.text_area(
                        "Common misconception", value=section.misconception, height=110, key=f"misc_{i}"
                    )
                with right:
                    section.concept = st.text_area("Core concept", value=section.concept, height=100, key=f"concept_{i}")
                    section.indian_example = st.text_area(
                        "Real-world example", value=section.indian_example, height=110, key=f"ex_{i}"
                    )
                section.key_points = [
                    item.strip()
                    for item in st.text_area(
                        "Key points (one per line)",
                        value="\n".join(section.key_points),
                        height=120,
                        key=f"kps_{i}",
                    ).splitlines()
                    if item.strip()
                ]
                section.narration = st.text_area(
                    "Narration script", value=section.narration, height=160, key=f"narration_{i}"
                )

        st.markdown("---")
        left, right = st.columns([3, 1])
        with left:
            submitted = st.form_submit_button(
                f"Continue to {output_type.replace('_', ' ').title()}",
                type="primary",
                use_container_width=True,
            )
        with right:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

    if submitted:
        # Preserve edited metadata only when the current Chapter model supports it.
        # Older schemas may not define these top-level fields.
        if hasattr(chapter, "title"):
            chapter.title = chapter_title
        if hasattr(chapter, "subject"):
            chapter.subject = chapter_subject
        st.session_state.chapter = chapter
        st.session_state.app_state = "generating_media"
        st.rerun()
    if cancelled:
        reset_pipeline()
        st.rerun()


def execute_media_generation(output_type: str, session_dir: str) -> None:
    chapter = st.session_state.chapter
    if chapter is None:
        st.error("No chapter is available to generate.")
        reset_pipeline()
        return

    selected_language = st.session_state.get("selected_language", "English")
    narration_voice = VOICE_KN if selected_language == "Kannada" else VOICE_EN

    try:
        with st.status("Building your learning resource…", expanded=True) as status:
            if output_type == "video":
                section_video_paths = []

                for i, section in enumerate(chapter.sections):
                    section_dir = os.path.join(session_dir, f"section_{i}")
                    slide_dir = os.path.join(section_dir, "slides")
                    os.makedirs(section_dir, exist_ok=True)

                    status.write(
                        f"Section {i + 1}/{len(chapter.sections)} · Building teaching slides"
                    )
                    slide_paths = build_section_slides(
                        section,
                        chapter.subject,
                        slide_dir,
                        language=selected_language,
                        chapter_title=chapter.chapter_title,
                    )

                    status.write(
                        f"Section {i + 1}/{len(chapter.sections)} · Synthesizing narration"
                    )
                    audio_path = os.path.join(section_dir, "narration.mp3")
                    synthesize_narration(
                        section.narration,
                        audio_path,
                        voice=narration_voice,
                    )

                    status.write(
                        f"Section {i + 1}/{len(chapter.sections)} · Assembling video"
                    )
                    video_path = os.path.join(section_dir, "video.mp4")
                    build_section_video(slide_paths, audio_path, video_path)
                    section_video_paths.append(video_path)

                final_path = os.path.join(session_dir, "final_output.mp4")
                status.write("Combining all lesson sections.")
                concatenate_section_videos(section_video_paths, final_path)
                st.session_state.final_video_path = final_path

            elif output_type == "ppt":
                status.write("Creating your editable presentation.")
                path = os.path.join(session_dir, "chapter.pptx")
                export_chapter_to_pptx(
                    chapter,
                    path,
                    language=selected_language,
                )
                st.session_state.final_ppt_path = path

                # Generate a separate narration MP3 alongside the PPT.
                # A narration failure must not invalidate the presentation.
                narration_text = "\n\n".join(
                    narration
                    for section in chapter.sections
                    if (
                        narration := str(
                            getattr(section, "narration", "") or ""
                        ).strip()
                    )
                )

                if narration_text:
                    status.write(
                        f"Creating {selected_language} narration audio."
                    )
                    audio_path = os.path.join(
                        session_dir, "chapter_narration.mp3"
                    )

                    try:
                        synthesize_narration(
                            narration_text,
                            audio_path,
                            voice=narration_voice,
                        )
                        st.session_state.final_audio_path = audio_path
                    except Exception as audio_exc:
                        st.session_state.pop("final_audio_path", None)
                        status.write(
                            "Presentation is ready, but narration audio "
                            f"could not be generated: {audio_exc}"
                        )
                else:
                    st.session_state.pop("final_audio_path", None)

            elif output_type == "transcript":
                status.write("Formatting your study notes as a PDF.")
                path = os.path.join(session_dir, "transcript.pdf")
                export_transcript_pdf(
                    chapter,
                    path,
                    language=selected_language,
                )
                st.session_state.final_transcript_path = path

            elif output_type == "flashcards":
                status.write("Generating question-and-answer flashcards.")
                st.session_state.flashcards = generate_flashcards(
                    chapter,
                    language=selected_language,
                )

            status.update(label="Your resource is ready", state="complete")
            st.session_state.app_state = "complete"

    except Exception as exc:
        st.session_state.last_error = str(exc)
        st.session_state.app_state = "error"
        st.error(f"Generation failed: {exc}")


def render_completion(output_type: str) -> None:
    st.markdown('<div class="step-label">Step 03 / Ready</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Your learning resource is ready</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-description">Open it here or download a copy for your next study session.</div>',
        unsafe_allow_html=True,
    )

    if output_type == "video":
        path = st.session_state.get("final_video_path")
        if path and os.path.exists(path):
            st.video(path)
            with open(path, "rb") as file:
                st.download_button(
                    "Download lesson video",
                    data=file,
                    file_name="academicvid_lesson.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
        else:
            st.warning("The video file could not be found in this session.")

    elif output_type == "ppt":
        path = st.session_state.get("final_ppt_path")
        if path and os.path.exists(path):
            with open(path, "rb") as file:
                st.download_button(
                    "Download editable presentation",
                    data=file,
                    file_name="academicvid_lesson.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
        else:
            st.warning("The presentation file could not be found in this session.")

        audio_path = st.session_state.get("final_audio_path")
        if audio_path and os.path.exists(audio_path):
            st.markdown("#### Lesson narration audio")
            st.audio(audio_path)
            with open(audio_path, "rb") as audio_file:
                st.download_button(
                    f"Download {st.session_state.get('selected_language', 'English')} narration (MP3)",
                    data=audio_file,
                    file_name="academicvid_narration.mp3",
                    mime="audio/mpeg",
                    use_container_width=True,
                )

    elif output_type == "transcript":
        path = st.session_state.get("final_transcript_path")
        if path and os.path.exists(path):
            with open(path, "rb") as file:
                st.download_button(
                    "Download transcript PDF",
                    data=file,
                    file_name="academicvid_study_notes.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.warning("The transcript PDF could not be found in this session.")

    elif output_type == "flashcards":
        cards = st.session_state.get("flashcards") or []
        if cards:
            st.caption(f"{len(cards)} cards generated")
            for i, card in enumerate(cards, start=1):
                with st.expander(f"CARD {i:02d}  ·  {card.get('front', 'Question')}"):
                    st.write(card.get("back", ""))
        else:
            st.warning("No flashcards were returned for this chapter.")

    chapter = st.session_state.get("chapter")
    if chapter:
        with st.expander("View structured lesson data"):
            st.json(chapter.model_dump() if hasattr(chapter, "model_dump") else chapter)

    st.markdown("")
    if st.button("Create another lesson", type="primary", use_container_width=True):
        reset_pipeline()
        st.rerun()


def render_error_state() -> None:
    st.markdown('<div class="section-heading">Something went wrong</div>', unsafe_allow_html=True)
    st.error(st.session_state.get("last_error", "An unexpected error occurred."))
    if st.button("Back to workspace", type="primary"):
        reset_pipeline()
        st.rerun()


# ---------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="AcademicVid — AI Learning Studio",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    inject_custom_css()
    render_brand_and_hero()

    source, library_pdf_path, uploaded_file, selected_class, selected_subject, selected_chapter = render_sidebar()
    pdf_path = None

    if source == "Library":
        pdf_path = library_pdf_path
    elif uploaded_file is not None:
        pdf_path = save_uploaded_pdf(uploaded_file, get_session_dir())

    if st.session_state.app_state == "setup":
        # STEP 1 — choose a chapter or upload a PDF.
        st.markdown('<div class="setup-content">', unsafe_allow_html=True)
        st.markdown('<div class="step-label">Step 01 / Choose your material</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-heading">What do you want to learn today?</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-description">Choose a chapter from the library or upload your own PDF. '
            'We’ll decide how to study it in the next step.</div>',
            unsafe_allow_html=True,
        )

        if pdf_path:
            if source == "Library":
                chips = (
                    '<span class="chip chip-accent">Library</span>'
                    f'<span class="chip">{selected_class or ""}</span>'
                    f'<span class="chip">{selected_subject or ""}</span>'
                )
                title = selected_chapter or Path(pdf_path).stem
            else:
                chips = '<span class="chip chip-accent">Your PDF</span>'
                title = uploaded_file.name if uploaded_file is not None else Path(pdf_path).name

            st.markdown(
                f'<div class="chapter-card"><div class="chip-row">{chips}</div>'
                f'<div class="chapter-title">{title}</div>'
                f'<div class="chapter-hint">Great choice! Your learning material is ready.</div></div>',
                unsafe_allow_html=True,
            )
            _, next_col = st.columns([2, 1])
            with next_col:
                if st.button("Next: Choose a learning format  →", type="primary", use_container_width=True):
                    st.session_state.app_state = "choose_output"
                    st.rerun()
        else:
            st.markdown(
                '<div class="panel"><div class="section-heading">Start with a chapter or PDF</div>'
                '<div class="section-description">Use the Source Material controls in the sidebar to choose a library chapter '
                'or upload your own PDF. Your selected material will appear here.</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.app_state == "choose_output":
        # STEP 2 — choose one output format, then generate it directly.
        st.markdown('<div class="setup-content">', unsafe_allow_html=True)
        st.markdown('<div class="step-label">Step 02 / Choose your learning style</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-heading">How would you like to learn?</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-description">Pick one format. You can go back and change your chapter at any time.</div>',
            unsafe_allow_html=True,
        )

        # Use Streamlit columns + buttons rather than a vertical radio widget.
        # This guarantees a real 2 × 2 layout across Streamlit versions.
        labels = list(OUTPUT_OPTIONS.keys())
        if st.session_state.selected_output_label not in labels:
            st.session_state.selected_output_label = labels[0]

        for row_start in (0, 2):
            card_cols = st.columns(2, gap="large")
            for offset, card_col in enumerate(card_cols):
                label = labels[row_start + offset]
                with card_col:
                    is_selected = st.session_state.selected_output_label == label
                    if st.button(
                        label,
                        key=f"format_card_{OUTPUT_OPTIONS[label]}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.selected_output_label = label
                        st.session_state.last_generated_type = OUTPUT_OPTIONS[label]
                        st.rerun()
                    st.markdown(
                        f'<div class="format-card-caption">{OUTPUT_CAPTIONS[label]}</div>',
                        unsafe_allow_html=True,
                    )

        selected_label = st.session_state.selected_output_label
        st.session_state.last_generated_type = OUTPUT_OPTIONS[selected_label]
        selected_caption = OUTPUT_CAPTIONS[selected_label]
        st.markdown(
            f'<div class="panel"><div class="step-label">YOUR SELECTED FORMAT</div>'
            f'<div class="section-heading">{selected_label}</div>'
            f'<div class="section-description">{selected_caption}</div></div>',
            unsafe_allow_html=True,
        )

        back_col, _ = st.columns([1, 2])
        with back_col:
            if st.button("← Back to chapter", use_container_width=True):
                st.session_state.app_state = "setup"
                st.rerun()

        # Keep the primary action and its AI progress/status centered in the workspace.
        _, action_col, _ = st.columns([1, 1.5, 1])
        with action_col:
            selected_output = st.session_state.last_generated_type
            action_labels = {
                "video": "Generate lesson video  →",
                "ppt": "Generate presentation  →",
                "transcript": "Create study notes  →",
                "flashcards": "Create flashcards  →",
            }
            if st.button(action_labels.get(selected_output, "Generate resource  →"), type="primary", use_container_width=True):
                if not pdf_path:
                    st.warning("Please select a chapter or upload a PDF first.")
                else:
                    execute_ai_structuring(pdf_path, st.session_state.selected_language)
                    if st.session_state.app_state == "generating_media":
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.app_state == "review":
        render_review_ui(st.session_state.last_generated_type)

    elif st.session_state.app_state == "generating_media":
        execute_media_generation(st.session_state.last_generated_type, get_session_dir())
        if st.session_state.app_state == "complete":
            st.rerun()

    elif st.session_state.app_state == "complete":
        render_completion(st.session_state.last_generated_type)

    elif st.session_state.app_state == "error":
        render_error_state()

    st.markdown(
        '<div class="footer">ACADEMICVID &nbsp;·&nbsp; AI LEARNING STUDIO &nbsp;·&nbsp; '
        'LEARN WITH CLARITY</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
