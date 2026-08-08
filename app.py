"""
Streamlit app. Every user session gets its own UUID-based temp directory
so concurrent users never collide on images/videos/audio files.
"""
import os
import uuid
import shutil
import streamlit as st
from dotenv import load_dotenv

from pdf_parser import extract_chapter
from ai_structuring import structure_chapter
from slides import build_section_slides
from tts import synthesize_narration
from video_builder import build_section_video, concatenate_section_videos

load_dotenv()

BASE_TMP_DIR = "tmp_sessions"


def get_session_dir() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    session_dir = os.path.join(BASE_TMP_DIR, st.session_state.session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def main():
    st.set_page_config(page_title="AcademicVid", page_icon=":movie_camera:", layout="wide")
    st.title("AcademicVid — NCERT Chapter to Video")

    session_dir = get_session_dir()

    uploaded_file = st.sidebar.file_uploader("Upload NCERT chapter PDF", type="pdf")

    if uploaded_file is None:
        st.info("Upload a chapter PDF to begin.")
        return

    pdf_path = os.path.join(session_dir, "input.pdf")
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.sidebar.button("Generate Video"):
        with st.status("Running pipeline...", expanded=True) as status:
            status.write("Step 1/5: Extracting text from PDF...")
            extracted = extract_chapter(pdf_path)

            status.write("Step 2/5: Structuring content with Gemini 2.5 Flash...")
            chapter = structure_chapter(extracted["clean_text"])
            st.session_state.chapter = chapter

            section_video_paths = []
            for i, section in enumerate(chapter.sections):
                status.write(f"Step 3/5: Building slides for section {i+1}: {section.title}")
                slide_dir = os.path.join(session_dir, f"section_{i}", "slides")
                slide_paths = build_section_slides(section, chapter.subject, slide_dir)

                status.write(f"Step 4/5: Generating narration audio for section {i+1}...")
                audio_path = os.path.join(session_dir, f"section_{i}", "narration.mp3")
                synthesize_narration(section.narration, audio_path)

                status.write(f"Step 5/5: Assembling video for section {i+1}...")
                video_path = os.path.join(session_dir, f"section_{i}", "video.mp4")
                build_section_video(slide_paths, audio_path, video_path)
                section_video_paths.append(video_path)

            status.write("Concatenating all sections into final video...")
            final_path = os.path.join(session_dir, "final_output.mp4")
            concatenate_section_videos(section_video_paths, final_path)

            status.update(label="Done!", state="complete")

        st.session_state.final_video_path = final_path

    if st.session_state.get("final_video_path") and os.path.exists(st.session_state.final_video_path):
        st.video(st.session_state.final_video_path)
        chapter = st.session_state.get("chapter")
        if chapter:
            with st.expander("See structured content (JSON)"):
                st.json(chapter.model_dump())


if __name__ == "__main__":
    main()