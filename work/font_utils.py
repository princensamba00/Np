"""Shared font registration, glyph fallback and rich-text wrapping for the report."""
from __future__ import annotations
import os, re
from dataclasses import dataclass
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from fontTools.ttLib import TTFont as FTFont

ROOT = '/home/user/Np'
FONT_DIR = os.path.join(ROOT, 'work', 'fonts')
DEJAVU_DIR = '/usr/share/fonts/truetype/dejavu'

FONT_FILES = {
    'Glacial': os.path.join(FONT_DIR, 'glacialindifference-regular.ttf'),
    'Glacial-Bold': os.path.join(FONT_DIR, 'glacialindifference-bold.ttf'),
    'DejaVu': os.path.join(DEJAVU_DIR, 'DejaVuSans.ttf'),
    'DejaVu-Bold': os.path.join(DEJAVU_DIR, 'DejaVuSans-Bold.ttf'),
    'DejaVu-Oblique': os.path.join(DEJAVU_DIR, 'DejaVuSans.ttf'),
    'DejaVu-BoldOblique': os.path.join(DEJAVU_DIR, 'DejaVuSans-Bold.ttf'),
}

CMAPS = {}
REGISTERED = False

def cmap_for(path):
    if path in CMAPS: return CMAPS[path]
    font = FTFont(path)
    chars = set()
    for table in font['cmap'].tables:
        chars.update(table.cmap.keys())
    CMAPS[path] = chars
    return chars

def register_fonts():
    global REGISTERED
    if REGISTERED: return
    for name, path in FONT_FILES.items():
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily('Glacial', normal='Glacial', bold='Glacial-Bold',
                                  italic='DejaVu-Oblique', boldItalic='DejaVu-BoldOblique')
    REGISTERED = True

GLACIAL_CMAP = cmap_for(FONT_FILES['Glacial'])
DEJAVU_CMAP = cmap_for(FONT_FILES['DejaVu'])

# Private-use bullet from the source PDF, and typographic characters absent from Glacial.
BULLET_SRC = '\uf0b7'
BULLET_DST = '•'

def normalize_char(ch):
    if ch == BULLET_SRC: return BULLET_DST
    return ch

def font_for_char(ch, bold=False, italic=False):
    ch = normalize_char(ch)
    use_fallback = (
        italic or
        ch in ('≤','≥','«','»','•','–','—','\u2011','\u00a0') or
        ord(ch) not in GLACIAL_CMAP
    )
    if use_fallback:
        if bold and italic: return 'DejaVu-BoldOblique'
        if bold: return 'DejaVu-Bold'
        if italic: return 'DejaVu-Oblique'
        return 'DejaVu'
    return 'Glacial-Bold' if bold else 'Glacial'

@dataclass
class Segment:
    text: str
    font: str
    size: float
    color: Color

@dataclass
class Char:
    ch: str
    font: str
    size: float
    color: Color

    @property
    def width(self):
        return pdfmetrics.stringWidth(self.ch, self.font, self.size)

def runs_to_segments(runs, size=9.9, color=HexColor('#000000')):
    """Convert content.json rich runs into font-aware PDF segments."""
    if isinstance(color, str): color = HexColor(color)
    segs = []
    for run in runs:
        text = run.get('text','')
        bold = bool(run.get('bold', False))
        italic = bool(run.get('italic', False))
        buf, buf_font = '', None
        for ch in text:
            nch = normalize_char(ch)
            f = font_for_char(ch, bold, italic)
            if f != buf_font and buf:
                segs.append(Segment(buf, buf_font, size, color)); buf = ''
            buf += nch; buf_font = f
        if buf:
            segs.append(Segment(buf, buf_font, size, color))
    # merge neighbours with identical attributes
    merged = []
    for s in segs:
        if (merged and merged[-1].font == s.font and merged[-1].size == s.size
                and _color_key(merged[-1].color) == _color_key(s.color)):
            merged[-1].text += s.text
        else:
            merged.append(s)
    return merged

def segments_to_chars(segments):
    out = []
    for s in segments:
        for ch in s.text:
            out.append(Char(ch, s.font, s.size, s.color))
    return out

def _color_key(c):
    try: return c.hexval()
    except Exception: return str(c)

def chars_to_segments(chars):
    segs = []
    buf, f, sz, col, colkey = '', None, None, None, None
    for ch in chars:
        ck = _color_key(ch.color)
        if ch.font != f or ch.size != sz or ck != colkey:
            if buf: segs.append(Segment(buf, f, sz, col))
            buf, f, sz, col, colkey = '', ch.font, ch.size, ch.color, ck
        buf += ch.ch
    if buf: segs.append(Segment(buf, f, sz, col))
    return segs

@dataclass
class WordToken:
    chars: list

    @property
    def width(self): return sum(c.width for c in self.chars)

    def segments(self): return chars_to_segments(self.chars)

@dataclass
class SpaceToken:
    chars: list

    @property
    def width(self): return sum(c.width for c in self.chars)

@dataclass
class Line:
    tokens: list
    width: float
    extra_per_space: float = 0.0

    @property
    def natural_width(self): return sum(t.width for t in self.tokens)

    @property
    def justified_width(self):
        n = sum(1 for t in self.tokens if isinstance(t, SpaceToken))
        return self.natural_width + n * self.extra_per_space

def tokenize_segments(segments):
    chars = segments_to_chars(segments)
    tokens, word, spaces = [], [], []
    def flush_word():
        nonlocal word
        if word:
            tokens.append(WordToken(word)); word = []
    def flush_spaces():
        nonlocal spaces
        if spaces:
            tokens.append(SpaceToken(spaces)); spaces = []
    for ch in chars:
        is_break = ch.ch.isspace() and ch.ch not in ('\u00a0', '\u2011')
        if is_break:
            flush_word(); spaces.append(ch)
        else:
            flush_spaces(); word.append(ch)
    flush_word(); flush_spaces()
    return tokens

def _break_word(word_token, max_width):
    """Last-resort character break for a word that cannot fit on a line."""
    parts, cur, w = [], [], 0.0
    for ch in word_token.chars:
        if cur and w + ch.width > max_width:
            parts.append(WordToken(cur)); cur, w = [], 0.0
        cur.append(ch); w += ch.width
    if cur: parts.append(WordToken(cur))
    return parts

def wrap_segments(segments, max_width, size=9.9, justify=False, align='left'):
    """Return (lines, n_lines). No automatic hyphenation is ever performed."""
    tokens = tokenize_segments(segments)
    lines, cur, w = [], [], 0.0
    for token in tokens:
        if isinstance(token, WordToken):
            if token.width > max_width:
                if cur:
                    lines.append(cur); cur, w = [], 0.0
                for part in _break_word(token, max_width):
                    if cur and w + part.width > max_width:
                        lines.append(cur); cur, w = [], 0.0
                    cur.append(part); w += part.width
                continue
            if cur and w + token.width > max_width:
                lines.append(cur); cur, w = [], 0.0
            cur.append(token); w += token.width
        else:
            if cur:  # ignore leading spaces on a fresh line
                cur.append(token); w += token.width
    if cur: lines.append(cur)
    # strip trailing spaces
    clean = []
    for toks in lines:
        while toks and isinstance(toks[-1], SpaceToken): toks.pop()
        clean.append(toks)
    out = []
    for i, toks in enumerate(clean):
        natural = sum(t.width for t in toks)
        nspaces = sum(1 for t in toks if isinstance(t, SpaceToken))
        extra = 0.0
        if justify and i < len(clean)-1 and nspaces and natural < max_width:
            extra = (max_width - natural) / nspaces
        out.append(Line(toks, natural, extra))
    return out, len(out)

def draw_rich(canvas, segments, x, y_top, max_width, page_height, size=9.9,
              line_height=None, align='left', justify=False, color=None):
    """Draw rich text with explicit coordinates; y_top is measured from page top."""
    if line_height is None: line_height = size * 1.42
    lines, _ = wrap_segments(segments, max_width, size=size, justify=justify, align=align)
    for li, line in enumerate(lines):
        baseline = page_height - y_top - size * 0.92 - li * line_height
        if align == 'center':
            cursor = x + (max_width - line.justified_width) / 2.0
        elif align == 'right':
            cursor = x + (max_width - line.justified_width)
        else:
            cursor = x
        for token in line.tokens:
            if isinstance(token, WordToken):
                for seg in token.segments():
                    canvas.setFont(seg.font, size)
                    canvas.setFillColor(seg.color)
                    canvas.drawString(cursor, baseline, seg.text)
                    cursor += pdfmetrics.stringWidth(seg.text, seg.font, size)
            else:
                # draw a real space so text extraction retains word boundaries
                f = token.chars[0].font if token.chars else 'Glacial'
                canvas.setFont(f, size)
                canvas.setFillColor(token.chars[0].color if token.chars else HexColor('#000000'))
                canvas.drawString(cursor, baseline, ' ')
                cursor += token.width + line.extra_per_space
    return len(lines) * line_height

def rich_plain(runs):
    return ''.join(normalize_char(ch) for r in runs for ch in r.get('text',''))

def nbsp_text(text):
    """Nonbreaking spaces / hyphens for names, sigles, units and numbers."""
    repl = {
        'FHI 360':'FHI\u00a0360', 'ICHESS, LLC':'ICHESS,\u00a0LLC',
        'EpiC RDC':'EpiC\u00a0RDC', 'Projet EpiC':'Projet\u00a0EpiC',
        'Haut-Katanga':'Haut\u2011Katanga', 'Haut-Lomami':'Haut\u2011Lomami',
        'Kasaï-Central':'Kasaï\u2011Central', 'Kasaï-Oriental':'Kasaï\u2011Oriental',
        'contre-référence':'contre\u2011référence', '0–3 mois':'0–3\u00a0mois',
        '3–12 mois':'3–12\u00a0mois', ' %':'\u00a0%', 'p. ':'p.\u00a0',
    }
    for a,b in repl.items(): text = text.replace(a,b)
    return text.replace(BULLET_SRC, BULLET_DST)
