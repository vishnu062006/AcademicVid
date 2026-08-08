# AcademicVid 📚🎥

### Turn an NCERT chapter into a short, narrated learning video.

**AcademicVid** is an AI-powered educational video generation pipeline built to transform textbook chapters into structured, student-friendly video lessons.

Upload an NCERT chapter → let Gemini break it into concepts → automatically generate teaching slides → add natural Indian-English narration with Edge TTS → and get a complete educational video.

**Live Demo:**
https://academicvid-43ncy5utis6kwfdybwpubb.streamlit.app/

---

## ✨ What It Does

AcademicVid takes a raw textbook PDF and turns it into a structured video lesson without requiring the teacher to manually create slides, write a script, or record narration.

```text
              ┌─────────────────┐
              │   NCERT PDF     │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │  PDF Extraction │
              │ pdfplumber/fitz │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │ Gemini AI       │
              │ Lesson Struct.  │
              └────────┬────────┘
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
   Teaching Slides             Narration
      Pillow                  Edge TTS
          │                         │
          └────────────┬────────────┘
                       ↓
              ┌─────────────────┐
              │  MoviePy        │
              │ Video Assembly  │
              └────────┬────────┘
                       ↓
              🎬 Final Video
```

---

## 🚀 Features

### 📄 Intelligent PDF Extraction

AcademicVid doesn't simply dump the PDF text into an LLM.

It:

* Extracts clean text using **pdfplumber**
* Uses **PyMuPDF** to detect headings based on font-size differences
* Removes page numbers, headers, footers and figure captions
* Handles repeated-character artifacts found in some NCERT PDFs
* Preserves the chapter's logical structure

---

### 🧠 AI-Powered Lesson Structuring

A chapter is processed through **Google Gemini** and converted into a strict structured schema.

For every major concept, AcademicVid generates:

* 🎯 A real-world hook
* 💡 A simple concept explanation
* 🇮🇳 An Indian-context example
* 📌 Three key points
* ⚠️ A common misconception
* 🎙️ A 60–90 second teacher-style narration
* ❓ A multiple-choice quiz

The generated response is validated using **Pydantic**, ensuring the downstream video pipeline receives predictable structured data.

---

### 🎨 Automatically Generated Teaching Slides

Instead of relying on random stock images, AcademicVid generates consistent educational slides directly from the structured lesson.

Each section follows:

```text
Hook
  ↓
Concept
  ↓
Real-Life Example
  ↓
Key Points
  ↓
Common Misconception
```

Slides are rendered programmatically using **Pillow** at 1280×720 resolution.

Subject-specific themes are automatically applied for:

* 🔬 Science
* 📐 Mathematics
* 🌍 Social Science
* 📖 English
* 📚 Other subjects

---

### 🎙️ Natural AI Narration

Narration is generated using **Microsoft Edge TTS** through `edge-tts`.

No Google Cloud billing account or service-account setup is required.

Current voices include:

| Language            | Voice                 |
| ------------------- | --------------------- |
| 🇮🇳 Indian English | `en-IN-NeerjaNeural`  |
| 🇮🇳 Indian English | `en-IN-PrabhatNeural` |
| ಕನ್ನಡ Kannada       | `kn-IN-SapnaNeural`   |
| ಕನ್ನಡ Kannada       | `kn-IN-GaganNeural`   |

Speech rate can also be adjusted for slower or faster classroom-style explanations.

---

### 🎬 Automated Video Assembly

MoviePy combines the generated slides and narration into complete lesson videos.

The pipeline:

1. Generates the section slides
2. Creates a narration track
3. Calculates the narration duration
4. Synchronizes the slides with the audio
5. Creates a video for each section
6. Concatenates all sections into one final video

The result is a ready-to-watch educational video directly inside the Streamlit application.

---

## 🧩 Architecture

```text
                    ┌──────────────┐
                    │   Streamlit  │
                    │      UI      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  PDF Upload  │
                    └──────┬───────┘
                           │
                           ▼
              ┌────────────────────────┐
              │     PDF Parser         │
              │ pdfplumber + PyMuPDF   │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │      Gemini AI         │
              │ Structured Lesson JSON │
              └────────────┬───────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
        ┌────────────────┐   ┌────────────────┐
        │ Slide Renderer │   │   Edge TTS     │
        │    Pillow      │   │    Narration   │
        └───────┬────────┘   └───────┬────────┘
                │                    │
                └──────────┬─────────┘
                           ▼
                    ┌──────────────┐
                    │   MoviePy    │
                    │ Video Builder│
                    └──────┬───────┘
                           │
                           ▼
                    🎬 Final Video
```

---

## 🛠️ Tech Stack

| Layer                 | Technology           |
| --------------------- | -------------------- |
| Frontend / UI         | Streamlit            |
| AI                    | Google Gemini        |
| PDF Parsing           | pdfplumber + PyMuPDF |
| Structured Validation | Pydantic             |
| Slide Generation      | Pillow               |
| Text-to-Speech        | Edge TTS             |
| Video Processing      | MoviePy              |
| Language              | Python               |

---

## 📁 Project Structure

```text
AcademicVid/
│
├── app.py                 # Streamlit application
├── pdf_parser.py          # PDF extraction & heading detection
├── ai_structuring.py      # Gemini lesson generation
├── schema.py              # Pydantic lesson schema
├── slides.py              # Educational slide generation
├── tts.py                 # Edge TTS narration
├── video_builder.py       # Video assembly
├── test_pipeline.py       # End-to-end pipeline tests
│
├── assets/
│   └── fonts/             # Fonts used for slide rendering
│
├── images/                 # Project assets
├── videos/                 # Video assets
│
├── requirements.txt
├── runtime.txt
├── packages.txt
├── .gitignore
└── ReadMe.md
```

---

## ⚙️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/vishnu062006/AcademicVid.git
cd AcademicVid
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**macOS / Linux**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Gemini

Create a `.env` file:

```env
GOOGLE_API_KEY=your_gemini_api_key
```

That's it for the AI configuration.

**Edge TTS does not require a separate cloud billing account or service-account credential.**

---

## ▶️ Run Locally

```bash
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

---

## 📖 Usage

1. Upload an NCERT chapter PDF.
2. Click **Generate Video**.
3. AcademicVid extracts and cleans the chapter.
4. Gemini identifies the major concepts and creates structured lesson content.
5. Teaching slides are generated for every section.
6. Edge TTS generates the narration.
7. MoviePy synchronizes the slides and narration.
8. All sections are combined into the final video.
9. Watch the generated lesson directly in the application.
10. Inspect the structured lesson JSON from the interface.

---

## 🎓 Designed For

AcademicVid is primarily designed around accessible educational content for:

* School students
* Government school learners
* Self-paced learners
* Teachers
* Educational institutions

The content-generation prompt is specifically designed around **Class 6–12 Indian students**, with an emphasis on relatable Indian examples and classroom-friendly explanations.

---

## 🧪 Current Pipeline

The current implementation is **Phase 1 — working end-to-end**.

```text
PDF
 ↓
Clean Text Extraction
 ↓
Chapter Structuring
 ↓
AI Lesson Generation
 ↓
Slide Generation
 ↓
Edge TTS Narration
 ↓
Section Videos
 ↓
Final Educational Video
```

The complete pipeline can now go from a chapter PDF to a playable educational video automatically.

---

## 🔮 Roadmap

AcademicVid is being developed toward a more complete educational content-generation platform.

### Coming Next

* 🇮🇳 Full Kannada narration support
* 🌐 Multi-language lessons
* 📝 Automatic subtitles
* ❓ Interactive quizzes
* 📚 Chapter-wise revision mode
* 🎯 Personalized difficulty levels
* 📊 Learning analytics
* 🎨 Animated educational diagrams
* 🔊 More narration voices
* 📱 Better mobile experience
* ⚡ Faster generation and caching

---

## 🌱 Why AcademicVid?

Textbooks contain the information students need, but reading a chapter doesn't always make learning engaging or accessible.

AcademicVid aims to bridge that gap by turning static textbook content into **short, structured, narrated lessons** that feel closer to having a teacher explain the chapter.

> **From textbook pages to a classroom-style video — automatically.**

---

## 👨‍💻 Author

Built by **Vishnu Mashalkar** as an AI-powered educational technology project focused on making textbook learning more accessible and engaging.

---

## 📜 License

This project is intended for educational and research purposes.
