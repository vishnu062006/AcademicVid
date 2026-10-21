"""
Printable study notes (PDF) for a Chapter. Works for English AND Kannada.

Rendered with PyMuPDF so Kannada is shaped correctly. Designed for printing in
schools: white page, black text, thin rules - cheap to print in black & white.
"""
import os

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from slides import LABELS, FONT_DIR, check_fonts, _pretty_equation, _html_mixed

_CSS = """
@font-face{font-family:kn;src:url(NotoSansKannada-Regular.ttf);}
@font-face{font-family:kn;font-weight:bold;src:url(NotoSansKannada-Bold.ttf);}
@font-face{font-family:dv;src:url(DejaVuSans.ttf);}
@font-face{font-family:dv;font-weight:bold;src:url(DejaVuSans-Bold.ttf);}
body{font-family:kn;font-size:11.5pt;line-height:1.5;color:#111;}
.lat{font-family:dv;}
h1{font-size:23pt;font-weight:bold;margin:0 0 2pt 0;}
.sub{font-size:11pt;color:#444;margin:0 0 6pt 0;}
.rule{border-bottom:2pt solid #111;margin:2pt 0 12pt 0;}
h2{font-size:15pt;font-weight:bold;margin:16pt 0 3pt 0;border-bottom:0.75pt solid #999;padding-bottom:2pt;page-break-after:avoid;}
h3{font-size:11pt;font-weight:bold;color:#333;margin:9pt 0 1pt 0;page-break-after:avoid;}
p{margin:0 0 4pt 0;}
.hook{font-style:italic;color:#333;margin-bottom:5pt;}
ul{margin:0 0 4pt 0;padding-left:16pt;}
li{margin-bottom:3pt;}
.eq{font-family:dv;font-weight:bold;font-size:13pt;border:1pt solid #111;padding:6pt;margin:6pt 0;text-align:center;}
.warn{border-left:4pt solid #111;padding:4pt 8pt;margin-top:7pt;background-color:#eee;}
"""


def _h(text):
    return _html_mixed(str(text))


def _build_html(chapter, language):
    lab = LABELS.get(language, LABELS["English"])
    subject = lab["subjects"].get(chapter.subject, chapter.subject) if language == "Kannada" else chapter.subject
    parts = ['<h1>%s</h1>' % _h(chapter.chapter_title),
             '<p class="sub">%s <span class="lat">\u00b7</span> %s</p><div class="rule"></div>' % (_h(lab["notes"]), _h(subject))]
    for i, s in enumerate(chapter.sections, 1):
        parts.append('<h2>%d. %s</h2>' % (i, _h(s.title)))
        parts.append('<p class="hook">%s</p>' % _h(s.hook))
        parts.append('<h3>%s</h3><p>%s</p>' % (_h(lab["concept"]), _h(s.concept)))
        if getattr(s, "key_equation", None):
            parts.append('<h3>%s</h3><div class="eq">%s</div>' % (
                _h(lab["equation"]), _h(_pretty_equation(s.key_equation, chapter.subject))))
        parts.append('<h3>%s</h3><p>%s</p>' % (_h(lab["example"]), _h(s.indian_example)))
        parts.append('<h3>%s</h3><ul>%s</ul>' % (
            _h(lab["key_points"]), "".join("<li>%s</li>" % _h(p) for p in s.key_points)))
        parts.append('<div class="warn"><b>%s</b> %s</div>' % (_h(lab["misconception"]), _h(s.misconception)))
    return "".join(parts)


def export_transcript_pdf(chapter, out_path: str, language: str = "English") -> str:
    check_fonts()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    story = fitz.Story(html=_build_html(chapter, language), user_css=_CSS,
                       archive=fitz.Archive(FONT_DIR))
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (48, 44, -48, -56)
    tmp = out_path + ".tmp.pdf"
    writer = fitz.DocumentWriter(tmp)
    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()

    # footer with page numbers
    doc = fitz.open(tmp)
    n = len(doc)
    for i, page in enumerate(doc):
        page.insert_text((48, mediabox.height - 28), "AcademicVid", fontsize=8, color=(0.4, 0.4, 0.4))
        page.insert_text((mediabox.width - 80, mediabox.height - 28), f"{i + 1} / {n}",
                         fontsize=8, color=(0.4, 0.4, 0.4))
    doc.save(out_path)
    doc.close()
    os.remove(tmp)
    return out_path