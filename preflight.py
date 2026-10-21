"""
Run before every demo / deploy:   python3 preflight.py          (offline checks)
                                  python3 preflight.py --live   (also pings Gemini + edge-tts)
Prints PASS / FAIL per check so problems show up BEFORE the review, not during it.
"""
import os, sys, shutil, importlib

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

results = []


def check(name, fn):
    try:
        msg = fn()
        results.append((True, name, msg or ""))
    except Exception as e:
        results.append((False, name, f"{type(e).__name__}: {str(e)[:800]}"))


# 1. libraries
def libs():
    missing = []
    for m in ("streamlit", "pydantic", "pdfplumber", "pymupdf", "pptx", "edge_tts", "moviepy", "dotenv", "google.generativeai"):
        try:
            importlib.import_module(m)
        except Exception:
            missing.append(m)
    if missing:
        raise RuntimeError("not installed: " + ", ".join(missing))
    import pymupdf
    ver = tuple(int(x) for x in pymupdf.__version__.split(".")[:3])
    if ver < (1, 24, 3):
        raise RuntimeError(f"PyMuPDF {pymupdf.__version__} is too old, need >= 1.24.3 (pip3 install -U pymupdf)")
    return f"PyMuPDF {pymupdf.__version__}"
check("Python libraries", libs)


# 2. fonts are REAL fonts (not HTML error pages)
def fonts():
    import pymupdf
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
    bad = []
    for f in ("NotoSansKannada-Regular.ttf", "NotoSansKannada-Bold.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        p = os.path.join(d, f)
        try:
            pymupdf.Font(fontfile=p)
        except Exception:
            bad.append(f)
    if bad:
        raise RuntimeError("missing or not real fonts: " + ", ".join(bad))
    return "4/4 valid"
check("Fonts in assets/fonts", fonts)


# 3. ffmpeg
def ffmpeg():
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()
check("ffmpeg available", ffmpeg)


# 4. API key
def key():
    if not (os.environ.get("GOOGLE_API_KEY") or "").strip():
        raise RuntimeError("GOOGLE_API_KEY not set (.env locally, Secrets on Streamlit Cloud)")
    return "set"
check("GOOGLE_API_KEY", key)


# 5. every library chapter: file exists, is a PDF, has real text (not a scan)
def manifest():
    import pdfplumber
    from manifest import CHAPTER_MANIFEST
    problems, n = [], 0
    for cls, subjects in CHAPTER_MANIFEST.items():
        for subj, chapters in subjects.items():
            for title, path in chapters.items():
                n += 1
                if not os.path.exists(path):
                    problems.append(f"{cls}/{subj}/{title}: FILE NOT FOUND ({path})")
                    continue
                with open(path, "rb") as fh:
                    if fh.read(5) != b"%PDF-":
                        problems.append(f"{cls}/{subj}/{title}: not a PDF")
                        continue
                with pdfplumber.open(path) as pdf:
                    pages = len(pdf.pages)
                    text = "".join((pdf.pages[i].extract_text() or "") for i in range(min(3, pages)))
                if len(text.strip()) < 200:
                    problems.append(f"{cls}/{subj}/{title}: almost no text - scanned PDF?")
                elif pages > 40:
                    problems.append(f"{cls}/{subj}/{title}: {pages} pages - is this a whole book, not a chapter?")
    if problems:
        raise RuntimeError("\n        ".join([""] + problems))
    return f"{n} chapters OK"
check("Library manifest", manifest)


# 6. repo hygiene
def hygiene():
    here = os.path.dirname(os.path.abspath(__file__))
    gi = open(os.path.join(here, ".gitignore")).read() if os.path.exists(os.path.join(here, ".gitignore")) else ""
    warn = []
    if ".env" not in gi:
        warn.append(".env is not in .gitignore (API key could be committed)")
    big = [f for f in os.listdir(here) if f.endswith((".mp4", ".mp3", ".gif"))]
    if big:
        warn.append("generated media in repo root: " + ", ".join(big[:4]))
    if warn:
        raise RuntimeError("; ".join(warn))
    return "clean"
check("Repo hygiene", hygiene)


# 7. optional live pings (network; costs a few free-tier tokens)
if "--live" in sys.argv:
    def gemini():
        import google.generativeai as genai
        from ai_structuring import MODEL_NAME
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        r = genai.GenerativeModel(MODEL_NAME).generate_content("Reply with the single word: ok", request_options={"timeout": 30})
        return f"{MODEL_NAME} -> {r.text.strip()[:20]}"
    check("Gemini reachable", gemini)

    def tts():
        import asyncio, tempfile, edge_tts
        out = []
        for voice, text in (("en-IN-NeerjaNeural", "Hello students."), ("kn-IN-SapnaNeural", "ನಮಸ್ಕಾರ ಮಕ್ಕಳೇ.")):
            f = tempfile.mktemp(suffix=".mp3")
            asyncio.run(edge_tts.Communicate(text, voice).save(f))
            out.append(f"{voice.split('-')[0]}:{os.path.getsize(f)}B")
        return " ".join(out)
    check("edge-tts English + Kannada voices", tts)

print()
for ok, name, msg in results:
    print(("PASS  " if ok else "FAIL  ") + name + (("  - " + msg) if msg else ""))
failed = sum(1 for ok, _, _ in results if not ok)
print(f"\n{len(results) - failed}/{len(results)} checks passed" + ("" if not failed else "  -> fix the FAIL lines before the demo"))
sys.exit(1 if failed else 0)
