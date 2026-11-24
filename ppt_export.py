"""
Step: export a structured Chapter into a downloadable .pptx, one slide per
section, so teachers can use it in class without the video player.

Implements issue #1 exactly:
    def export_chapter_to_pptx(chapter, out_path: str) -> str

Input : a Chapter object (schema.py) — chapter.sections is a list, each
        section has .title, .hook, .concept, .indian_example, .key_points,
        .misconception
Output: a .pptx file saved to out_path. Returns out_path (matches the
        return-a-path convention used by slides.py / video_builder.py).

No Gemini, TTS, or video code is touched. Colors are pulled from
slides.SUBJECT_THEMES so the deck visually matches the generated video.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from pptx.oxml.ns import qn
from lxml import etree

from slides import SUBJECT_THEMES, LABELS, get_labels, _pretty_equation

# Complex-script (Kannada) font. Nirmala UI ships with Windows 10+, which is what most
# school PCs run; other apps substitute a Kannada-capable font automatically.
KN_FONT = "Nirmala UI"


def _kn(run, language):
    """Mark a run's complex-script font so PowerPoint shapes Kannada properly."""
    if language != "Kannada":
        return
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:cs", "a:ea"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", KN_FONT)
    run.font.name = KN_FONT


BLANK_LAYOUT_INDEX = 6  # "Blank" layout in the default pptx template
TITLE_ONLY_LAYOUT_INDEX = 5  # "Title Only" layout


def _theme_colors(subject: str):
    theme = SUBJECT_THEMES.get(subject, SUBJECT_THEMES["Other"])
    return {
        "bg": RGBColor(*theme["bg"]),
        "accent": RGBColor(*theme["accent"]),
        "text": RGBColor(*theme["text"]),
    }


def _set_background(slide, rgb: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb


def _add_textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    return tf


def _add_title_slide(prs: Presentation, chapter_title: str, subject: str, language: str = "English"):
    colors = _theme_colors(subject)
    layout = prs.slide_layouts[BLANK_LAYOUT_INDEX]
    slide = prs.slides.add_slide(layout)
    _set_background(slide, colors["bg"])

    tf = _add_textbox(slide, Inches(0.7), Inches(2.6), Inches(8.6), Inches(2.2))
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = chapter_title
    _kn(run, language)
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = colors["accent"]

    sub = tf.add_paragraph()
    sub.alignment = PP_ALIGN.CENTER
    sub_run = sub.add_run()
    sub_run.text = LABELS.get(language, LABELS["English"])["subjects"].get(subject, subject) if language == "Kannada" else subject
    _kn(sub_run, language)
    sub_run.font.size = Pt(20)
    sub_run.font.color.rgb = colors["text"]


def _add_section_slide(prs: Presentation, section, subject: str, language: str = "English"):
    lab = get_labels(language, subject)
    colors = _theme_colors(subject)
    layout = prs.slide_layouts[BLANK_LAYOUT_INDEX]
    slide = prs.slides.add_slide(layout)
    _set_background(slide, colors["bg"])

    # Title = section.title
    title_tf = _add_textbox(slide, Inches(0.5), Inches(0.35), Inches(9), Inches(0.9))
    title_p = title_tf.paragraphs[0]
    title_run = title_p.add_run()
    title_run.text = section.title
    _kn(title_run, language)
    title_run.font.size = Pt(30)
    title_run.font.bold = True
    title_run.font.color.rgb = colors["accent"]

    # Body = concept + indian_example
    body_tf = _add_textbox(slide, Inches(0.5), Inches(1.3), Inches(9), Inches(2.3))
    concept_p = body_tf.paragraphs[0]
    concept_run = concept_p.add_run()
    concept_run.text = section.concept
    _kn(concept_run, language)
    concept_run.font.size = Pt(18)
    concept_run.font.color.rgb = colors["text"]

    if getattr(section, "key_equation", None):
        eq_p = body_tf.add_paragraph()
        eq_p.space_before = Pt(8)
        eq_label = eq_p.add_run()
        eq_label.text = lab["equation"] + ": "
        eq_label.font.bold = True
        eq_label.font.size = Pt(16)
        eq_label.font.color.rgb = colors["accent"]
        _kn(eq_label, language)
        eq_run = eq_p.add_run()
        eq_run.text = _pretty_equation(section.key_equation, subject)
        eq_run.font.size = Pt(16)
        eq_run.font.bold = True
        eq_run.font.color.rgb = colors["text"]

    example_p = body_tf.add_paragraph()
    example_p.space_before = Pt(12)
    example_label = example_p.add_run()
    example_label.text = lab["example"] + ": "
    _kn(example_label, language)
    example_label.font.bold = True
    example_label.font.size = Pt(16)
    example_label.font.color.rgb = colors["accent"]

    example_run = example_p.add_run()
    example_run.text = section.indian_example
    _kn(example_run, language)
    example_run.font.size = Pt(16)
    example_run.font.color.rgb = colors["text"]

    # Bullet list = key_points
    points_tf = _add_textbox(slide, Inches(0.5), Inches(3.9), Inches(9), Inches(3.2))
    for i, point in enumerate(section.key_points):
        p = points_tf.paragraphs[0] if i == 0 else points_tf.add_paragraph()
        run = p.add_run()
        run.text = f"\u2022 {point}"
        _kn(run, language)
        run.font.size = Pt(16)
        run.font.color.rgb = colors["text"]
        p.space_after = Pt(8)


# ---------------------------------------------------------------------------
# Narration inside the deck: every slide carries its own voice clip, which starts by
# itself when the slide is shown; the slide moves on when the clip ends. So in
# Slide Show the voice always matches the slide on screen. (A teacher can still click
# to move on earlier: PowerPoint stops the clip and plays the next slide's.)
# ---------------------------------------------------------------------------
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_RT_AUDIO = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/audio"
_RT_VIDEO = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video"

_TIMING_XML = """<p:timing xmlns:p="{p}"><p:tnLst><p:par>
<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
 <p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
  <p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>
   <p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>
   <p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
    <p:par><p:cTn id="5" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold"
      nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
     <p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="6" dur="{ms}" fill="hold"/>
      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd>
    </p:childTnLst></p:cTn></p:par>
   </p:childTnLst></p:cTn></p:par>
  </p:childTnLst></p:cTn></p:par>
 </p:childTnLst></p:cTn>
 <p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
 <p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
 </p:seq>
 <p:audio><p:cMediaNode vol="80000" showWhenStopped="0"><p:cTn id="7" fill="hold" display="0">
  <p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>
  <p:endCondLst><p:cond evt="onStopAudio" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:endCondLst>
  </p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cMediaNode></p:audio>
</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>"""


def _speaker_icon_png() -> bytes:
    """A small speaker picture for the audio clip (only seen while editing)."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=64, height=64)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    page.draw_polyline([(10, 24), (22, 24), (36, 12), (36, 52), (22, 40), (10, 40), (10, 24)],
                       color=None, fill=(0.2, 0.2, 0.2), closePath=True)
    page.draw_bezier((44, 22), (50, 28), (50, 36), (44, 42), color=(0.2, 0.2, 0.2), width=3)
    page.draw_bezier((49, 15), (59, 25), (59, 39), (49, 49), color=(0.2, 0.2, 0.2), width=3)
    png = page.get_pixmap().tobytes("png")
    doc.close()
    return png


def _attach_narration(prs: Presentation, slide, mp3_path: str, seconds: float) -> None:
    import io
    shape = slide.shapes.add_movie(
        mp3_path, prs.slide_width - Inches(0.6), prs.slide_height - Inches(0.6),
        Inches(0.4), Inches(0.4), poster_frame_image=io.BytesIO(_speaker_icon_png()),
        mime_type="audio/mpeg",
    )
    # python-pptx only knows video: turn the clip into an audio clip.
    nvpr = shape._element.nvPicPr.nvPr
    vfile = nvpr.find(qn("a:videoFile"))
    rid = vfile.get(qn("r:link"))
    vfile.tag = qn("a:audioFile")
    rel = slide.part.rels[rid]
    if rel.reltype == _RT_VIDEO:
        rel._reltype = _RT_AUDIO
        rel.__dict__.pop("reltype", None)      # python-pptx caches the first value read
    if rel.reltype != _RT_AUDIO:
        raise RuntimeError("could not mark the narration as audio")
    old = slide._element.find("{%s}timing" % _P)
    if old is not None:
        slide._element.remove(old)
    ms = max(1, int(round(seconds * 1000)))
    timing = etree.fromstring(_TIMING_XML.format(p=_P, ms=ms, spid=shape.shape_id))
    transition = etree.Element("{%s}transition" % _P, advTm=str(ms + 300))
    # Element order in a slide: cSld, clrMapOvr, transition, timing, extLst
    anchor = slide._element.find("{%s}clrMapOvr" % _P)
    if anchor is None:
        anchor = slide._element.find("{%s}cSld" % _P)
    anchor.addnext(transition)
    transition.addnext(timing)


def export_chapter_to_pptx(chapter, out_path: str, language: str = "English",
                           audio_paths=None, audio_seconds=None) -> str:
    """
    Build a .pptx from a Chapter object: one title slide + one slide per
    section (title / concept + indian_example / key_points bullets).

    audio_paths / audio_seconds (optional): one narration mp3 and its length for every
    slide, title slide first. Each clip is put inside its slide and plays by itself.

    Returns out_path.
    """
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    _add_title_slide(prs, chapter.chapter_title, chapter.subject, language)

    for section in chapter.sections:
        _add_section_slide(prs, section, chapter.subject, language)

    if audio_paths:
        if len(audio_paths) != len(prs.slides) or len(audio_seconds or []) != len(prs.slides):
            raise ValueError("need one narration clip per slide")
        for slide, mp3, secs in zip(prs.slides, audio_paths, audio_seconds):
            _attach_narration(prs, slide, mp3, secs)

    prs.save(out_path)
    return out_path


if __name__ == "__main__":
    # Quick manual smoke test with dummy data matching schema.py's shape.
    from schema import Chapter, Section, Quiz

    dummy_chapter = Chapter(
        chapter_title="Chemical Reactions and Equations",
        subject="Science",
        sections=[
            Section(
                title="What is a Chemical Reaction?",
                hook="Ever noticed rust on an old gate?",
                concept="A chemical reaction is a process where substances "
                        "change into new substances with different properties.",
                indian_example="Rusting of iron gates and railings during "
                                "the monsoon in Indian households.",
                key_points=["Reactants become products", "New substances form",
                            "Energy is absorbed or released"],
                misconception="Mixing two liquids always means a reaction happened.",
                narration="Placeholder narration text for testing purposes only.",
                quiz=Quiz(
                    question="What forms when iron reacts with oxygen and moisture?",
                    options=["Rust", "Salt", "Gas", "Water"],
                    answer_index=0,
                    explanation="Iron reacts with oxygen and moisture to form rust (iron oxide).",
                ),
            )
        ],
    )
    export_chapter_to_pptx(dummy_chapter, "test_output.pptx")
    print("Saved test_output.pptx")