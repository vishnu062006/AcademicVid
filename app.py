import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from manifest import CHAPTER_MANIFEST
from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from slides import build_section_slides
from tts import synthesize_narration
from video_builder import build_section_video, concatenate_section_videos
from typing import Optional

# Import the additional output modules present in the source directory
from ppt_export import export_chapter_to_pptx
from transcript_export import export_transcript_pdf  # Updated to match your function name
from flashcards import generate_flashcards

load_dotenv()

BASE_TMP_DIR = "tmp_sessions"

OUTPUT_OPTIONS = {
    "Video": "video",
    "PPT": "ppt",
    "Transcript PDF": "transcript",
    "Flashcards": "flashcards",
}

SOURCE_OPTIONS = ["Pick from library", "Upload your own PDF"]


# -----------------------------------------------------------------------------
# App state / filesystem helpers
# -----------------------------------------------------------------------------

def get_session_dir() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    session_dir = os.path.join(BASE_TMP_DIR, st.session_state.session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def save_uploaded_pdf(uploaded_file, session_dir: str) -> str:
    pdf_path = os.path.join(session_dir, "input.pdf")

    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return pdf_path


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------

def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        /* ---------- Global ---------- */
        :root {
            --av-yellow: #FFD95A;
            --av-yellow-soft: #FFF4BF;
            --av-teal: #63D0CF;
            --av-teal-soft: #E4FAF8;
            --av-pink: #F7C4C9;
            --av-ink: #000000;
            --av-muted: #4A4A4A;
            --av-bg: #FFFDF7;
        }

        .stApp {
            background:
                radial-gradient(circle at 88% 8%, rgba(255,217,90,.18), transparent 20%),
                radial-gradient(circle at 18% 84%, rgba(99,208,207,.12), transparent 23%),
                var(--av-bg);
        }

        .main .block-container {
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* ---------- Sidebar Fixes (Dark Mode Override) ---------- */
        section[data-testid="stSidebar"] {
            background-color: var(--av-bg) !important;
            border-right: 3px solid #000000 !important;
        }
        
        section[data-testid="stSidebar"] * {
            color: #000000 !important;
        }

        /* ---------- Brand ---------- */
        .av-brand {
            display: flex;
            align-items: center;
            gap: 13px;
            margin-bottom: 1.8rem;
            animation: avFadeUp .55s ease-out both;
        }

        .av-brand-mark {
            width: 50px;
            height: 50px;
            display: grid;
            place-items: center;
            background: var(--av-yellow);
            border: 3px solid #000;
            box-shadow: 4px 4px 0px #000;
            font-size: 20px;
            font-weight: 900;
            color: #000;
            transition: transform .1s ease, box-shadow .1s ease;
        }

        .av-brand:hover .av-brand-mark {
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px #000;
        }

        .av-brand-name {
            font-size: 1.18rem;
            font-weight: 900;
            letter-spacing: -.02em;
            color: var(--av-ink);
        }

        .av-brand-sub {
            color: var(--av-muted);
            font-weight: 700;
            font-size: .83rem;
            margin-top: 1px;
        }

        /* ---------- Hero ---------- */
        .av-hero {
            position: relative;
            overflow: hidden;
            padding: 1.65rem 1.75rem 1.7rem;
            border: 3px solid #000;
            background: #FFFFFF;
            box-shadow: 8px 8px 0px #000;
            animation: avFadeUp .65s ease-out .08s both;
        }

        .av-eyebrow {
            color: #000;
            background: var(--av-teal);
            display: inline-block;
            padding: 2px 8px;
            border: 2px solid #000;
            font-size: .78rem;
            font-weight: 900;
            letter-spacing: .1em;
            text-transform: uppercase;
            margin-bottom: .65rem;
        }

        .av-title {
            position: relative;
            z-index: 1;
            font-size: clamp(2rem, 4vw, 3.1rem);
            line-height: 1.03;
            font-weight: 900;
            letter-spacing: -.045em;
            color: var(--av-ink);
            margin-bottom: .55rem;
        }

        .av-title span {
            background: var(--av-yellow);
            padding: 0 4px;
            border: 3px solid #000;
        }

        .av-subtitle {
            position: relative;
            z-index: 1;
            max-width: 690px;
            color: var(--av-ink);
            font-weight: 700;
            font-size: 1.1rem;
            line-height: 1.6;
        }

        /* ---------- Section headers ---------- */
        .av-section-head {
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 1rem;
            margin: 2.5rem 0 1rem;
        }

        .av-section-title {
            color: var(--av-ink);
            font-size: 1.4rem;
            font-weight: 900;
            text-transform: uppercase;
        }

        .av-section-note {
            color: #000;
            font-weight: 800;
            font-size: .9rem;
            background: var(--av-pink);
            padding: 4px 10px;
            border: 2px solid #000;
            box-shadow: 3px 3px 0px #000;
            text-transform: uppercase;
        }

        /* ---------- Output selector ---------- */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            gap: 16px;
        }

        div[data-testid="stRadio"] label {
            border: 3px solid #000000 !important;
            border-radius: 0px !important;
            padding: 14px 20px !important;
            background: #FFFFFF;
            box-shadow: 4px 4px 0px #000000 !important;
            transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
        }

        div[data-testid="stRadio"] label p {
            color: #000000 !important;
            font-weight: 900 !important;
            font-size: 1.15rem !important;
            margin: 0 !important;
        }

        div[data-testid="stRadio"] label:hover {
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px #000000 !important;
            background: var(--av-yellow-soft);
        }

        div[data-testid="stRadio"] label:has(input:checked) {
            background: var(--av-teal) !important;
            box-shadow: 2px 2px 0px #000000 !important;
            transform: translate(2px, 2px);
        }

        /* ---------- Info / Alert Boxes ---------- */
        div[data-testid="stAlert"] {
            background-color: var(--av-yellow);
            border: 3px solid #000000;
            border-radius: 0px;
            box-shadow: 5px 5px 0px #000000;
            color: #000000;
            margin-top: 1.5rem;
        }
        
        div[data-testid="stAlert"] p {
            color: #000000 !important;
            font-weight: 800 !important;
            font-size: 1.05rem;
        }

        /* ---------- Chapter card ---------- */
        .av-chapter {
            position: relative;
            overflow: hidden;
            padding: 1.35rem 1.45rem;
            border-radius: 0px;
            border: 3px solid #000;
            background: #FFFFFF;
            box-shadow: 5px 5px 0px #000;
            animation: avFadeUp .5s ease-out both;
            transition: transform .1s ease, box-shadow .1s ease;
        }

        .av-chapter:hover {
            transform: translate(-2px, -2px);
            box-shadow: 7px 7px 0px #000;
        }

        .av-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin-bottom: .8rem;
        }

        .av-chip {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border: 2px solid #000;
            font-size: .78rem;
            font-weight: 900;
            background: #FFFFFF;
            color: #000;
            text-transform: uppercase;
        }

        .av-chip-teal { background: var(--av-teal); }
        .av-chip-yellow { background: var(--av-yellow); }

        .av-chapter-title {
            position: relative;
            z-index: 1;
            font-size: 1.4rem;
            line-height: 1.25;
            font-weight: 900;
            color: var(--av-ink);
            margin-bottom: .4rem;
        }

        .av-chapter-meta {
            position: relative;
            z-index: 1;
            color: var(--av-muted);
            font-weight: 700;
            font-size: .9rem;
        }

        /* ---------- Buttons & Download Buttons ---------- */
        .stButton > button, div[data-testid="stDownloadButton"] > button {
            border: 3px solid #000 !important;
            border-radius: 0px !important;
            min-height: 3.5rem;
            background: var(--av-teal) !important;
            color: #000 !important;
            font-weight: 900 !important;
            font-size: 1.2rem !important;
            box-shadow: 6px 6px 0px #000 !important;
            letter-spacing: .02em;
            transition: transform .1s ease, box-shadow .1s ease;
        }

        .stButton > button:hover, div[data-testid="stDownloadButton"] > button:hover {
            transform: translate(-2px, -2px);
            box-shadow: 8px 8px 0px #000 !important;
            background: var(--av-yellow) !important;
        }

        .stButton > button:active, div[data-testid="stDownloadButton"] > button:active {
            transform: translate(3px, 3px);
            box-shadow: 3px 3px 0px #000 !important;
        }

        /* ---------- Upload dropzone fix ---------- */
        div[data-testid="stFileUploader"] section {
            border: 3px dashed #000 !important;
            border-radius: 0px !important;
            background: #FFFFFF !important;
            transition: background 0.1s ease;
        }
        
        div[data-testid="stFileUploader"] section * {
            color: #000000 !important;
        }

        div[data-testid="stFileUploader"] button {
            background: #000000 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 0px !important;
            font-weight: 900 !important;
            text-transform: uppercase;
        }

        div[data-testid="stFileUploader"] button:hover {
            background: var(--av-teal) !important;
            color: #000000 !important;
        }

        div[data-testid="stFileUploader"] section:hover {
            background: var(--av-teal-soft) !important;
        }

        /* ---------- Expanders (JSON / Flashcards) ---------- */
        .streamlit-expanderHeader {
            border: 3px solid #000 !important;
            border-radius: 0px !important;
            background: #FFFFFF !important;
            color: #000 !important;
            font-weight: 900 !important;
            box-shadow: 4px 4px 0px #000 !important;
            margin-bottom: 5px;
        }
        
        .streamlit-expanderContent {
            border: 3px solid #000 !important;
            border-top: none !important;
            background: #FAFAFA !important;
            color: #000 !important;
        }

        /* ---------- Loading Overlay ---------- */
        .av-loading-container {
            background-color: var(--av-yellow);
            border: 4px solid #000;
            box-shadow: 10px 10px 0px #000;
            padding: 4rem 2rem;
            text-align: center;
            margin: 2rem 0;
            animation: avFadeUp 0.3s ease-out both;
        }
        
        .av-loading-title {
            font-size: 3rem;
            font-weight: 900;
            color: #000;
            text-transform: uppercase;
            letter-spacing: 4px;
            animation: blink 1.5s infinite;
        }
        
        .av-loading-subtitle {
            font-size: 1.2rem;
            font-weight: 700;
            color: #000;
            background: var(--av-teal);
            border: 3px solid #000;
            padding: 8px 16px;
            display: inline-block;
            margin-top: 1.5rem;
            box-shadow: 4px 4px 0px #000;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        /* ---------- Motion ---------- */
        @keyframes avFadeUp {
            from { opacity: 0; transform: translateY(12px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# UI pieces
# -----------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.markdown(
        """
        <div class="av-side-brand" style="text-align: center; margin-bottom: 2rem; margin-top: 1rem;">
            <div style="color: #000; font-weight: 900; font-size: 1.6rem; text-transform: uppercase;">AcademicVid</div>
            <div style="color: #000; font-weight: 700; font-size: 0.85rem; border: 2px solid #000; background: #FFD95A; padding: 4px; margin-top: 8px;">TURN CHAPTERS INTO LESSONS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("<h3 style='color: #000; font-weight: 900; margin-top: 1rem;'>CHOOSE YOUR CHAPTER</h3>", unsafe_allow_html=True)

    source = st.sidebar.radio(
        "Source",
        SOURCE_OPTIONS,
        label_visibility="collapsed",
    )

    pdf_path = None
    uploaded_file = None
    selected_class = None
    selected_subject = None
    selected_chapter = None

    if source == "Pick from library":
        classes = list(CHAPTER_MANIFEST.keys())
        selected_class = st.sidebar.selectbox("Class", classes)

        subjects = list(CHAPTER_MANIFEST[selected_class].keys())
        selected_subject = st.sidebar.selectbox("Subject", subjects)

        chapters = list(CHAPTER_MANIFEST[selected_class][selected_subject].keys())

        if not chapters:
            st.sidebar.warning("No chapters have been added for this subject yet.")
        else:
            selected_chapter = st.sidebar.selectbox("Chapter", chapters)
            pdf_path = CHAPTER_MANIFEST[selected_class][selected_subject][selected_chapter]

    else:
        uploaded_file = st.sidebar.file_uploader(
            "Upload an NCERT chapter PDF",
            type=["pdf"],
            help="Upload the chapter PDF you want AcademicVid to process.",
        )

    return (
        source,
        pdf_path,
        uploaded_file,
        selected_class,
        selected_subject,
        selected_chapter,
    )


def render_brand_and_hero():
    st.markdown(
        """
        <div class="av-brand">
            <div class="av-brand-mark">AV</div>
            <div>
                <div class="av-brand-name">ACADEMICVID</div>
                <div class="av-brand-sub">AI-POWERED LEARNING</div>
            </div>
        </div>

        <div class="av-hero">
            <div class="av-eyebrow">YOUR WORKSPACE</div>
            <div class="av-title">LEARN IT. <span>SEE IT.</span> REMEMBER IT.</div>
            <div class="av-subtitle">
                Choose a chapter from the library or upload your own PDF,
                then turn it into a classroom-style learning experience.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_output_selector():
    st.markdown(
        """
        <div class="av-section-head">
            <div class="av-section-title">What do you want to create?</div>
            <div class="av-section-note">FORMAT SELECTOR</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_label = st.radio(
        "Output type",
        list(OUTPUT_OPTIONS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

    return OUTPUT_OPTIONS[selected_label]


def render_selected_chapter(
    source: str,
    selected_class: Optional[str],
    selected_subject: Optional[str],
    selected_chapter: Optional[str],
    uploaded_file,
):
    if source == "Pick from library":
        if not selected_chapter:
            return

        st.markdown(
            f"""
            <div class="av-chapter">
                <div class="av-chip-row">
                    <span class="av-chip av-chip-yellow">NCERT LIBRARY</span>
                    <span class="av-chip av-chip-teal">{selected_class}</span>
                    <span class="av-chip">{selected_subject}</span>
                </div>
                <div class="av-chapter-title">{selected_chapter}</div>
                <div class="av-chapter-meta">Ready for processing.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif uploaded_file is not None:
        st.markdown(
            f"""
            <div class="av-chapter">
                <div class="av-chip-row">
                    <span class="av-chip av-chip-yellow">CUSTOM PDF</span>
                    <span class="av-chip av-chip-teal">UPLOADED</span>
                </div>
                <div class="av-chapter-title">{uploaded_file.name}</div>
                <div class="av-chapter-meta">Ready for processing.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_generation_steps(output_type: str):
    st.markdown('<div class="av-result">', unsafe_allow_html=True)
    st.markdown(f'<div class="av-section-title" style="margin-bottom: 1rem;">YOUR GENERATED {output_type.upper()}</div>', unsafe_allow_html=True)

    # Render specific outputs based on generation type
    if output_type == "video" and st.session_state.get("final_video_path"):
        st.video(st.session_state.final_video_path)

    elif output_type == "ppt" and st.session_state.get("final_ppt_path"):
        with open(st.session_state.final_ppt_path, "rb") as f:
            st.download_button(
                label="DOWNLOAD PPT FILE", 
                data=f, 
                file_name="chapter_lesson.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

    elif output_type == "transcript" and st.session_state.get("final_transcript_path"):
        with open(st.session_state.final_transcript_path, "rb") as f:
            st.download_button(
                label="DOWNLOAD TRANSCRIPT PDF", 
                data=f, 
                file_name="transcript.pdf",
                mime="application/pdf"
            )

    elif output_type == "flashcards" and st.session_state.get("flashcards"):
        for i, card in enumerate(st.session_state.flashcards):
            with st.expander(f"CARD {i + 1}: {card.get('front', '').upper()}"):
                st.write(card.get("back", ""))

    chapter = st.session_state.get("chapter")
    if chapter:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("VIEW STRUCTURED LESSON CONTENT (JSON)"):
            st.json(chapter.model_dump())

    st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Unified Generation Pipeline
# -----------------------------------------------------------------------------

def run_pipeline(pdf_path: str, output_type: str, session_dir: str):
    # 1. Mount the big bold loading UI
    loading_placeholder = st.empty()
    with loading_placeholder.container():
        st.markdown(
            """
            <div class="av-loading-container">
                <div class="av-loading-title">GENERATING...</div>
                <div class="av-loading-subtitle">DO NOT CLOSE THIS WINDOW</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # 2. Run the actual pipeline logic beneath the loading UI overlay state
    with st.status("PROCESSING WORKFLOW...", expanded=True) as status:
        status.write("Extracting text from PDF...")
        extracted = extract_chapter(pdf_path)

        status.write("Structuring content with AI...")
        chapter = structure_chapter(extracted["clean_text"])
        st.session_state.chapter = chapter

        # Branch based on output type
        if output_type == "video":
            section_video_paths = []
            for i, section in enumerate(chapter.sections):
                status.write(f"Building slides for section {i + 1}...")
                slide_dir = os.path.join(session_dir, f"section_{i}", "slides")
                slide_paths = build_section_slides(section, chapter.subject, slide_dir)

                status.write(f"Generating narration for section {i + 1}...")
                audio_path = os.path.join(session_dir, f"section_{i}", "narration.mp3")
                synthesize_narration(section.narration, audio_path)

                status.write(f"Assembling video for section {i + 1}...")
                video_path = os.path.join(session_dir, f"section_{i}", "video.mp4")
                build_section_video(slide_paths, audio_path, video_path)
                section_video_paths.append(video_path)

            status.write("Combining all sections into final output...")
            final_path = os.path.join(session_dir, "final_output.mp4")
            concatenate_section_videos(section_video_paths, final_path)
            st.session_state.final_video_path = final_path

        elif output_type == "ppt":
            status.write("Building PPT file...")
            ppt_path = os.path.join(session_dir, "chapter.pptx")
            export_chapter_to_pptx(chapter, ppt_path)
            st.session_state.final_ppt_path = ppt_path

        elif output_type == "transcript":
            status.write("Building Transcript PDF...")
            transcript_path = os.path.join(session_dir, "transcript.pdf")
            export_transcript_pdf(chapter, transcript_path)  # Updated function name
            st.session_state.final_transcript_path = transcript_path
            
        elif output_type == "flashcards":
            status.write("Building Flashcards...")
            st.session_state.flashcards = build_flashcards(chapter)

        status.update(label="GENERATION COMPLETE!", state="complete")
        
    # 3. Remove the brutalist loading block so results are visible
    loading_placeholder.empty()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="AcademicVid",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()
    render_brand_and_hero()

    output_type = render_output_selector()

    (
        source,
        library_pdf_path,
        uploaded_file,
        selected_class,
        selected_subject,
        selected_chapter,
    ) = render_sidebar()

    session_dir = get_session_dir()
    pdf_path = None

    if source == "Pick from library":
        pdf_path = library_pdf_path
        render_selected_chapter(
            source,
            selected_class,
            selected_subject,
            selected_chapter,
            uploaded_file,
        )
    else:
        render_selected_chapter(
            source,
            selected_class,
            selected_subject,
            selected_chapter,
            uploaded_file,
        )

        if uploaded_file is not None:
            pdf_path = save_uploaded_pdf(uploaded_file, session_dir)
        else:
            st.info("Upload a PDF from the sidebar to get started.")

    can_generate = pdf_path is not None

    if can_generate:
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        left, center, right = st.columns([1.15, 1.5, 1.15])
        with center:
            if st.button(
                f"GENERATE {output_type.upper()}",
                type="primary",
                use_container_width=True,
            ):
                # Clear previous outputs to avoid confusion
                st.session_state.pop("final_video_path", None)
                st.session_state.pop("final_ppt_path", None)
                st.session_state.pop("final_transcript_path", None)
                st.session_state.pop("flashcards", None)
                st.session_state.pop("chapter", None)
                
                # Execute specific branch
                run_pipeline(pdf_path, output_type, session_dir)
                st.session_state.last_generated_type = output_type

    # Render results if they exist for the type we most recently generated
    last_type = st.session_state.get("last_generated_type")
    if last_type:
        render_generation_steps(last_type)


if __name__ == "__main__":
    main()