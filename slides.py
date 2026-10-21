"""
Step 3: builds the lesson slides from the structured JSON.

One renderer (PyMuPDF) is used for BOTH English and Kannada, so every slide
looks the same and Kannada text is shaped correctly (conjuncts like ಕ್ರಿ, ಸ್ಥಾ)
with no system libraries needed - works on a Mac and on Streamlit Cloud.

Fonts (committed in assets/fonts/):
  NotoSansKannada-Regular/Bold.ttf  -> Kannada script
  DejaVuSans / DejaVuSans-Bold.ttf  -> Latin letters, digits, symbols (H2O -> H2O, arrows)
"""
import os
import re
import html

try:
    import pymupdf as fitz          # PyMuPDF >= 1.24.3
except ImportError:                 # older installs
    import fitz

CANVAS_SIZE = (1280, 720)
W, H = CANVAS_SIZE

_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("ACADEMICVID_FONT_DIR", os.path.join(_HERE, "assets", "fonts"))
_FONT_FILES = ["NotoSansKannada-Regular.ttf", "NotoSansKannada-Bold.ttf",
               "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]

SUBJECT_THEMES = {
    "Science":        {"bg": (14, 98, 81),   "accent": (255, 214, 10), "text": (255, 255, 255)},
    "Math":           {"bg": (17, 45, 78),   "accent": (255, 138, 0), "text": (255, 255, 255)},
    "Social Science": {"bg": (91, 33, 33),   "accent": (255, 205, 178), "text": (255, 255, 255)},
    "English":        {"bg": (35, 33, 71),   "accent": (150, 200, 255), "text": (255, 255, 255)},
    "Other":          {"bg": (40, 40, 40),   "accent": (200, 200, 200), "text": (255, 255, 255)},
}
WARN = (255, 99, 71)

# NOTE: Kannada labels should be reviewed by a native speaker / teacher.
LABELS = {
    "English": {"concept": "Concept", "example": "Real-Life Example",
                "key_points": "Key Points", "misconception": "Watch Out!",
                "equation": "Key Equation",
                "notes": "Study Notes", "subjects": {}},
    "Kannada": {"concept": "ಪರಿಕಲ್ಪನೆ", "example": "ದೈನಂದಿನ ಜೀವನದ ಉದಾಹರಣೆ",
                "key_points": "ಮುಖ್ಯ ಅಂಶಗಳು", "misconception": "ಎಚ್ಚರ!",
                "equation": "ಪ್ರಮುಖ ಸಮೀಕರಣ",
                "notes": "ಅಧ್ಯಯನ ಟಿಪ್ಪಣಿಗಳು",
                "subjects": {"Science": "ವಿಜ್ಞಾನ", "Math": "ಗಣಿತ",
                             "Social Science": "ಸಮಾಜ ವಿಜ್ಞಾನ", "English": "ಇಂಗ್ಲಿಷ್"}},
}

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
_checked = False


def check_fonts():
    """Fail early with a clear message if a font file is missing or is not a real font
    (e.g. an HTML error page saved as .ttf by a failed download)."""
    global _checked
    if _checked:
        return
    for name in _FONT_FILES:
        path = os.path.join(FONT_DIR, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing font file: {path}")
        try:
            fitz.Font(fontfile=path)
        except Exception as e:
            raise RuntimeError(
                f"{path} is not a valid font file ({e}). If it is ~300 KB it is probably an "
                f"HTML page from a failed download - replace it with the real .ttf.")
    _checked = True


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, c))) for c in rgb)


def _mix(c1, c2, t):
    """blend c1 towards c2 by t (0..1)"""
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


def _f(rgb):
    return tuple(c / 255 for c in rgb)


_SUB = str.maketrans("0123456789", "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089")


def _pretty_equation(eq: str, subject: str) -> str:
    """CaO + H2O -> Ca(OH)2  =>  CaO + H\u2082O \u2192 Ca(OH)\u2082  (subscripts for Science only)."""
    eq = eq.replace("->", "\u2192")
    if subject == "Science":
        eq = re.sub(r"(?<=[A-Za-z\)])(\d+)", lambda m: m.group(1).translate(_SUB), eq)
    return eq


_KN_RUN = re.compile(r"([^\u0C80-\u0CFF\u200c\u200d]+)")


def _html_mixed(text: str) -> str:
    """Escape text and wrap non-Kannada runs (English, digits, symbols) in a span that
    uses DejaVu Sans, so Latin never falls back to a serif font beside Kannada."""
    out = []
    for i, part in enumerate(_KN_RUN.split(text)):
        if not part:
            continue
        esc = html.escape(part)
        out.append('<span class="lat">%s</span>' % esc if (i % 2 == 1 and part.strip()) else esc)
    return "".join(out)


class _Canvas:
    def __init__(self, subject):
        self.t = SUBJECT_THEMES.get(subject, SUBJECT_THEMES["Other"])
        self.bg = self.t["bg"]
        self.accent = self.t["accent"]
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=W, height=H)
        self.archive = fitz.Archive(FONT_DIR)
        self._background()

    # --- drawing -----------------------------------------------------------
    def _background(self):
        p = self.page
        top, bottom = _mix(self.bg, (255, 255, 255), 0.07), _mix(self.bg, (0, 0, 0), 0.38)
        steps = 48
        for i in range(steps):
            c = _mix(top, bottom, i / (steps - 1))
            y0, y1 = H * i / steps, H * (i + 1) / steps + 1
            p.draw_rect(fitz.Rect(0, y0, W, y1), color=None, fill=_f(c))
        # soft decorative circles
        p.draw_circle(fitz.Point(W - 90, 80), 230, color=None, fill=(1, 1, 1), fill_opacity=0.05)
        p.draw_circle(fitz.Point(70, H - 40), 170, color=None, fill=(1, 1, 1), fill_opacity=0.04)
        p.draw_rect(fitz.Rect(0, 0, W, 10), color=None, fill=_f(self.accent))

    def card(self, rect, fill=(255, 255, 255), opacity=0.11, bar=None, border=True):
        p = self.page
        p.draw_rect(rect, color=(1, 1, 1) if border else None, fill=_f(fill),
                    fill_opacity=opacity, stroke_opacity=0.18, width=1.5, radius=0.06)
        if bar:
            p.draw_rect(fitz.Rect(rect.x0 + 14, rect.y0 + 22, rect.x0 + 22, rect.y1 - 22),
                        color=None, fill=_f(bar), radius=0.5)

    def badge(self, center, r, glyph, fill, glyph_color=None):
        self.page.draw_circle(fitz.Point(*center), r, color=None, fill=_f(fill))
        gc = glyph_color or _mix(self.bg, (0, 0, 0), 0.55)
        css = ("@font-face{font-family:dv;font-weight:bold;src:url(DejaVuSans-Bold.ttf);}"
               "body{font-family:dv;font-weight:bold;color:%s;text-align:center;}"
               "p{font-size:%dpx;margin:0;}") % (_hex(gc), int(r * 1.25))
        rect = fitz.Rect(center[0] - r, center[1] - r * 0.92, center[0] + r, center[1] + r * 1.05)
        self.page.insert_htmlbox(rect, "<p>%s</p>" % html.escape(glyph), css=css, archive=self.archive)

    # --- text --------------------------------------------------------------
    def _css(self, body_px=40, color=(255, 255, 255), align="left", bold=False, line=1.45):
        return (
            "@font-face{font-family:kn;src:url(NotoSansKannada-Regular.ttf);}"
            "@font-face{font-family:kn;font-weight:bold;src:url(NotoSansKannada-Bold.ttf);}"
            "@font-face{font-family:dv;src:url(DejaVuSans.ttf);}"
            "@font-face{font-family:dv;font-weight:bold;src:url(DejaVuSans-Bold.ttf);}"
            "body{font-family:kn;color:%s;}"
            ".lat{font-family:dv;}"
            "p{font-size:%dpx;line-height:%s;margin:0;text-align:%s;%s}"
            "li{font-size:%dpx;line-height:%s;margin-bottom:10px;}"
        ) % (_hex(color), body_px, line, align, "font-weight:bold;" if bold else "", body_px, line)

    def text(self, rect, text, vcenter=False, **kw):
        html_text = "<p>%s</p>" % _html_mixed(text)
        css = self._css(**kw)
        if vcenter:  # measure on a scratch page, then shift the box so the text is centred
            scratch = fitz.open()
            sp, _ = scratch.new_page(width=W, height=H).insert_htmlbox(
                rect, html_text, css=css, archive=self.archive)
            scratch.close()
            if sp and sp > 0:
                rect = fitz.Rect(rect.x0, rect.y0 + sp / 2, rect.x1, rect.y1)
        spare, scale = self.page.insert_htmlbox(rect, html_text, css=css, archive=self.archive)
        if scale < 0.55:
            print(f"[slides] note: long text was shrunk to {scale:.0%} to fit: {text[:40]}...")

    def label(self, text, color=None):
        """Small heading at top-left with an accent underline."""
        color = color or self.accent
        self.text(fitz.Rect(64, 34, W - 330, 92), text, body_px=30, color=color, bold=True, line=1.2)
        self.page.draw_rect(fitz.Rect(66, 92, 150, 98), color=None, fill=_f(color), radius=0.5)

    def progress(self, idx, count):
        if idx is None or not count:
            return
        gap, r = 26, 7
        x0 = W - 64 - (count - 1) * gap
        for i in range(count):
            cur = (i == idx)
            self.page.draw_circle(fitz.Point(x0 + i * gap, 58), r + (2 if cur else 0), color=None,
                                  fill=_f(self.accent) if cur else (1, 1, 1),
                                  fill_opacity=1 if cur else 0.28)

    def footer(self, chapter_title):
        c = _mix(self.bg, (255, 255, 255), 0.55)
        self.text(fitz.Rect(64, H - 46, 420, H - 12), "AcademicVid", body_px=20, color=c, bold=True)
        if chapter_title:
            self.text(fitz.Rect(W - 760, H - 46, W - 64, H - 12), chapter_title, body_px=20,
                      color=c, align="right")

    def save(self, out_path):
        self.page.get_pixmap(dpi=72).save(out_path)
        self.doc.close()
        return out_path


# ----------------------------------------------------------------------------
# slide types
# ----------------------------------------------------------------------------
def _slide_hook(section, subject, path, ctx):
    c = _Canvas(subject)
    c.label(section.title)
    c.progress(ctx["idx"], ctx["count"])
    c.badge((190, 372), 82, "?", c.accent)
    c.text(fitz.Rect(320, 190, W - 80, 560), section.hook, body_px=50, bold=True, line=1.4, vcenter=True)
    c.footer(ctx["chapter"])
    return c.save(path)


def _slide_concept(section, subject, path, ctx, lab):
    c = _Canvas(subject)
    c.label(lab["concept"])
    c.progress(ctx["idx"], ctx["count"])
    card = fitz.Rect(64, 130, W - 64, 640)
    c.card(card, bar=c.accent)
    c.text(fitz.Rect(card.x0 + 50, card.y0 + 34, card.x1 - 40, card.y1 - 30), section.concept, body_px=42, vcenter=True)
    c.footer(ctx["chapter"])
    return c.save(path)


def _slide_equation(section, subject, path, ctx, lab):
    c = _Canvas(subject)
    c.label(lab["equation"])
    c.progress(ctx["idx"], ctx["count"])
    card = fitz.Rect(64, 190, W - 64, 520)
    c.page.draw_rect(card, color=None, fill=(1, 1, 1), radius=0.07)
    c.page.draw_rect(fitz.Rect(card.x0 + 70, card.y1 - 44, card.x1 - 70, card.y1 - 36), color=None,
                     fill=_f(c.accent), radius=0.5)
    dark = _mix(c.bg, (0, 0, 0), 0.35)
    eq = _pretty_equation(section.key_equation, subject)
    c.text(fitz.Rect(card.x0 + 30, card.y0 + 20, card.x1 - 30, card.y1 - 30), eq,
           body_px=62, color=dark, align="center", bold=True, line=1.2, vcenter=True)
    c.footer(ctx["chapter"])
    return c.save(path)


def _slide_example(section, subject, path, ctx, lab):
    c = _Canvas(subject)
    c.label(lab["example"])
    c.progress(ctx["idx"], ctx["count"])
    card = fitz.Rect(64, 130, W - 64, 640)
    c.card(card)
    c.badge((card.x0 + 100, (card.y0 + card.y1) / 2), 52, "\u2605", c.accent)
    c.text(fitz.Rect(card.x0 + 190, card.y0 + 34, card.x1 - 40, card.y1 - 30),
           section.indian_example, body_px=42, vcenter=True)
    c.footer(ctx["chapter"])
    return c.save(path)


def _slide_keypoints(section, subject, path, ctx, lab):
    c = _Canvas(subject)
    c.label(lab["key_points"])
    c.progress(ctx["idx"], ctx["count"])
    pts = section.key_points[:5]
    top, bottom, gap = 125, H - 64, 18
    h = (bottom - top - gap * (len(pts) - 1)) / len(pts)
    for i, pt in enumerate(pts):
        y0 = top + i * (h + gap)
        rect = fitz.Rect(64, y0, W - 64, y0 + h)
        c.card(rect)
        c.badge((rect.x0 + 62, (rect.y0 + rect.y1) / 2), 32, str(i + 1), c.accent)
        c.text(fitz.Rect(rect.x0 + 120, rect.y0 + 10, rect.x1 - 30, rect.y1 - 8), pt,
               body_px=34, line=1.35, vcenter=True)
    c.footer(ctx["chapter"])
    return c.save(path)


def _slide_misconception(section, subject, path, ctx, lab):
    c = _Canvas(subject)
    c.label(lab["misconception"], color=WARN)
    c.progress(ctx["idx"], ctx["count"])
    card = fitz.Rect(64, 130, W - 64, 640)
    c.card(card, fill=(255, 255, 255), opacity=0.10, bar=WARN)
    c.badge((card.x0 + 110, (card.y0 + card.y1) / 2), 52, "!", WARN, glyph_color=(255, 255, 255))
    c.text(fitz.Rect(card.x0 + 200, card.y0 + 34, card.x1 - 40, card.y1 - 30),
           section.misconception, body_px=42, vcenter=True)
    c.footer(ctx["chapter"])
    return c.save(path)


# ----------------------------------------------------------------------------
def build_section_slides(section, subject: str, out_dir: str, language: str = "English",
                         chapter_title: str = "") -> list:
    """Render the slides for one section. Returns the image paths in order.
    language: "English" or "Kannada". chapter_title is shown in the footer (optional)."""
    check_fonts()
    os.makedirs(out_dir, exist_ok=True)
    lab = LABELS.get(language, LABELS["English"])
    p = lambda name: os.path.join(out_dir, name)

    plan = [("01_hook.png", lambda path, ctx: _slide_hook(section, subject, path, ctx)),
            ("02_concept.png", lambda path, ctx: _slide_concept(section, subject, path, ctx, lab))]
    if getattr(section, "key_equation", None):
        plan.append(("03_equation.png", lambda path, ctx: _slide_equation(section, subject, path, ctx, lab)))
    plan += [("04_example.png", lambda path, ctx: _slide_example(section, subject, path, ctx, lab)),
             ("05_keypoints.png", lambda path, ctx: _slide_keypoints(section, subject, path, ctx, lab)),
             ("06_misconception.png", lambda path, ctx: _slide_misconception(section, subject, path, ctx, lab))]

    paths = []
    for i, (name, fn) in enumerate(plan):
        ctx = {"idx": i, "count": len(plan), "chapter": chapter_title}
        paths.append(fn(p(name), ctx))
    return paths