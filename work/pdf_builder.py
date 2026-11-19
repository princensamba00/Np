"""ReportLab renderer for the shared paginated layout."""
from __future__ import annotations
import os, re
from PIL import Image
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
import layout_engine as le
import font_utils as fu

le.fu.register_fonts()

ROOT = '/home/user/Np'

def y_bottom(y_top, size):
    return le.A4_H - y_top - size * 0.92

def draw_spaced(c, text, x, y_top, font, size, color, spacing=1.2,
                align='left', max_width=None):
    chars = [fu.normalize_char(ch) for ch in text]
    widths = [pdfmetrics.stringWidth(ch, font, size) for ch in chars]
    total = sum(widths) + spacing * max(0, len(chars)-1)
    if align == 'right' and max_width is not None:
        x = x + max_width - total
    elif align == 'center' and max_width is not None:
        x = x + (max_width - total)/2
    baseline = y_bottom(y_top, size)
    c.setFont(font, size); c.setFillColor(color)
    cursor = x
    for ch, w in zip(chars, widths):
        c.drawString(cursor, baseline, ch)
        cursor += w + spacing
    return total

def draw_header_footer(c, page):
    if page.is_cover: return
    # running header, two lines on the left to preserve the institutional letterhead
    draw_spaced(c, 'ICHESS, LLC', le.M_L, 35.6, 'Glacial-Bold', 7.2, le.NAVY, 1.9)
    inst = 'International Center for Health Systems Strengthening'
    c.setFont('Glacial', 6.4); c.setFillColor(le.GREY)
    c.drawString(le.M_L, y_bottom(44.5, 6.4), inst)
    draw_spaced(c, page.section_label or '', le.M_L, 35.6, 'Glacial', 7.2,
                le.GREY, 1.7, align='right', max_width=le.CONTENT_W)
    # header rule
    c.setStrokeColor(le.RULE); c.setLineWidth(0.7)
    c.line(le.M_L, le.A4_H-55.0, le.A4_W-le.M_R, le.A4_H-55.0)
    # footer: source-style split rule with centered spaced page number
    num = f'{page.print_no or page.page_no:02d}'
    label = ' '.join(num)
    c.setStrokeColor(le.RULE); c.setLineWidth(0.6)
    c.line(le.M_L, 47, 270, 47)
    c.line(325, 47, le.A4_W-le.M_R, 47)
    draw_spaced(c, label, 0, le.A4_H-34, 'Glacial-Bold', 8.2, le.NAVY, 1.2,
                align='center', max_width=le.A4_W)

def draw_cover(c, page):
    # navy band inspired by Md_ref.pdf pp.11–21
    c.setFillColor(le.NAVY); c.rect(0, le.A4_H-46, le.A4_W, 46, stroke=0, fill=1)
    c.setFillColor(le.YELLOW); c.rect(0, le.A4_H-49, le.A4_W, 3, stroke=0, fill=1)
    # logos
    top = os.path.join(ROOT,'work/assets/logos_top_crop.png')
    ich = os.path.join(ROOT,'work/assets/logo_ichess_crop.png')
    if os.path.exists(top):
        iw, ih = Image.open(top).size
        w = 330.0; h = w*ih/iw
        c.drawImage(ImageReader(top), le.M_L, le.A4_H-70-h, width=w, height=h,
                    preserveAspectRatio=True, mask='auto')
    # title rules
    rule_y1, rule_y2 = 250.0, 430.0
    c.setStrokeColor(le.NAVY); c.setLineWidth(2.0)
    c.line(le.M_L, le.A4_H-rule_y1, le.A4_W-le.M_R, le.A4_H-rule_y1)
    c.line(le.M_L, le.A4_H-rule_y2, le.A4_W-le.M_R, le.A4_H-rule_y2)
    c.setStrokeColor(le.YELLOW); c.setLineWidth(1.0)
    c.line(le.M_L, le.A4_H-(rule_y2+4), le.M_L+115, le.A4_H-(rule_y2+4))
    c.setStrokeColor(le.PERIWINKLE)
    c.line(le.A4_W-le.M_R-115, le.A4_H-(rule_y2+4), le.A4_W-le.M_R, le.A4_H-(rule_y2+4))
    title_lines = [
        'Rapport du diagnostic opérationnel',
        'rapide de la préparation des',
        'établissements de santé pour les',
        'services de santé maternelle, néonatale',
        'et infantile, paludisme et nutrition',
    ]
    y = 267.0
    for line in title_lines:
        segs = fu.runs_to_segments(le.text_runs(line, bold=True), 20.5, le.NAVY)
        fu.draw_rich(c, segs, le.M_L, y, le.CONTENT_W, le.A4_H,
                     size=20.5, line_height=33.0, align='center')
        y += 33.0
    if os.path.exists(ich):
        iw, ih = Image.open(ich).size
        w = 190.0; h = w*ih/iw
        c.drawImage(ImageReader(ich), (le.A4_W-w)/2, le.A4_H-530-h,
                    width=w, height=h, preserveAspectRatio=True, mask='auto')
    segs = fu.runs_to_segments(le.text_runs('Kinshasa, Octobre 2026', bold=True), 11.0, le.NAVY)
    fu.draw_rich(c, segs, le.M_L, 632.0, le.CONTENT_W, le.A4_H,
                 size=11.0, line_height=16.0, align='center')

def draw_heading(c, item, y_top):
    text = item.data['text']; lvl = item.data['level']
    size = {1:12.2, 2:10.4, 3:9.9}[lvl]
    segs = fu.runs_to_segments(le.text_runs(text, bold=True), size, le.NAVY)
    fu.draw_rich(c, segs, le.M_L, y_top, le.CONTENT_W, le.A4_H,
                 size=size, line_height=size*1.6, align='left')
    if lvl == 1:
        c.setStrokeColor(le.NAVY); c.setLineWidth(0.9)
        c.line(le.M_L, le.A4_H-(y_top+24), le.A4_W-le.M_R, le.A4_H-(y_top+24))
        # small yellow/periwinkle accents from pp.11–21
        c.setStrokeColor(le.YELLOW); c.setLineWidth(2.0)
        c.line(le.M_L, le.A4_H-(y_top+27), le.M_L+42, le.A4_H-(y_top+27))
        c.setStrokeColor(le.PERIWINKLE)
        c.line(le.M_L+44, le.A4_H-(y_top+27), le.M_L+86, le.A4_H-(y_top+27))

def draw_body(c, item, y_top):
    segs = fu.runs_to_segments(item.data['runs'], le.BODY_SIZE, le.BLACK)
    fu.draw_rich(c, segs, le.M_L, y_top, le.CONTENT_W, le.A4_H,
                 size=le.BODY_SIZE, line_height=le.BODY_LH,
                 align='left', justify=item.data.get('justify', True))

def draw_bullet(c, item, y_top):
    # Replace the source private-use bullet with a typographic bullet; keep every word.
    runs = []
    for r in item.data['runs']:
        t = r['text'].replace(fu.BULLET_SRC, fu.BULLET_DST)
        runs.append({'text': t, 'bold': r.get('bold',False), 'italic': r.get('italic',False)})
    segs = fu.runs_to_segments(runs, le.BODY_SIZE, le.BLACK)
    fu.draw_rich(c, segs, le.M_L+6, y_top, le.CONTENT_W-18, le.A4_H,
                 size=le.BODY_SIZE, line_height=le.BODY_LH, align='left', justify=False)

def draw_caption(c, item, y_top):
    segs = fu.runs_to_segments(le.text_runs(item.data['text'], italic=True), 9.0, le.NAVY)
    fu.draw_rich(c, segs, le.M_L, y_top, le.CONTENT_W, le.A4_H,
                 size=9.0, line_height=12.8, align='left')

def draw_signature(c, item, y_top):
    lines = item.data['lines']
    for i, line in enumerate(lines[:2]):
        segs = fu.runs_to_segments(le.text_runs(line, bold=(i==0)),
                                   10.0 if i==0 else 9.0,
                                   le.NAVY if i==0 else le.GREY)
        fu.draw_rich(c, segs, le.M_L, y_top+i*15.0, le.CONTENT_W, le.A4_H,
                     size=10.0 if i==0 else 9.0, line_height=15.0, align='center')

def _entry_lines(entry, compact=False):
    size, lh, after = le.list_metrics(compact)
    text = entry['text']; bold = bool(entry.get('bold',False))
    segs = fu.runs_to_segments(le.text_runs(text, bold=bold), size, le.BLACK)
    indent = 14 if entry.get('indent',0) else 0
    x0 = le.M_L + indent
    avail = (le.A4_W-le.M_R) - x0 - 50
    lines, n = fu.wrap_segments(segs, avail, size=size)
    return segs, x0, avail, lines, n, size, lh

def draw_list_entry(c, entry, y_top, compact=False):
    segs, x0, avail, lines, n, size, lh = _entry_lines(entry, compact)
    marker = str(entry.get('page',''))
    x_right = le.A4_W - le.M_R
    # title
    fu.draw_rich(c, segs, x0, y_top, avail, le.A4_H,
                 size=size, line_height=lh, align='left', justify=False)
    long_marker = len(marker) > 6
    # dotted leader on the last title line
    if not long_marker and lines:
        last = lines[-1]
        end = x0 + last.justified_width + 4
        c.setStrokeColor(le.DOTTED); c.setLineWidth(0.9); c.setDash(1,3)
        ly = le.A4_H - (y_top + (n-1)*lh + size*0.55)
        if end < x_right - 30:
            c.line(end, ly, x_right-30, ly)
        c.setDash()
    # page marker
    msize = 9.0 if compact else 10.6
    msegs = fu.runs_to_segments(le.text_runs(marker, bold=True), msize, le.NAVY)
    if long_marker:
        fu.draw_rich(c, msegs, x_right-260, y_top+n*lh, 260, le.A4_H,
                     size=9.0, line_height=lh, align='right')
    else:
        fu.draw_rich(c, msegs, x_right-30, y_top+(n-1)*lh, 30, le.A4_H,
                     size=msize, line_height=lh, align='right')

def draw_list_block(c, item, y_top):
    compact = item.kind == 'auto_toc'
    cy = y_top
    for e in item.data['entries']:
        draw_list_entry(c, e, cy, compact)
        cy += le.list_entry_height(e, compact)

def _dark(hexcolor):
    try:
        s = hexcolor.lstrip('#')
        r, g, b = (int(s[i:i+2], 16)/255.0 for i in (0, 2, 4))
        return 0.299*r + 0.587*g + 0.114*b < 0.52
    except Exception:
        return False


def draw_table(c, item, y_top):
    rows = item.data['rows']; cw = item.data['col_widths']; fs = item.data['font_size']
    fills = item.data.get('fills')
    x0 = le.M_L; total = sum(cw)
    heights = le.table_row_heights(rows, cw, fs)
    cy = y_top
    for ri, row in enumerate(rows):
        rh = heights[ri]
        # fond de chaque cellule : couleurs source exactes (vert / jaune / rouge
        # conservent leur signification) ou charte pour les tableaux liminaires.
        for j, cell in enumerate(row):
            if j >= len(cw): break
            if fills:
                col = fills[ri][j] if j < len(fills[ri]) else None
            else:
                col = '#131D44' if ri == 0 else ('FFFBF7' if ri % 2 == 0 else 'FFFFFF')
            if col:
                c.setFillColor(HexColor('#'+col.lstrip('#')))
                c.rect(x0+sum(cw[:j]), le.A4_H-cy-rh, cw[j], rh, stroke=0, fill=1)
        for j, cell in enumerate(row):
            if j >= len(cw): break
            col = (fills[ri][j] if fills and j < len(fills[ri]) else None)
            dark = bool(col and _dark(col)) or (not fills and ri == 0)
            segs = fu.runs_to_segments(le.text_runs(str(cell), bold=(ri == 0)), fs,
                                       le.WHITE if dark else le.BLACK)
            fu.draw_rich(c, segs, x0+sum(cw[:j])+4, cy+3.2, cw[j]-8, le.A4_H,
                         size=fs, line_height=fs*1.28, align='left')
        c.setStrokeColor(le.RULE if fills else le.DOTTED); c.setLineWidth(0.35)
        c.line(x0, le.A4_H-cy-rh, x0+total, le.A4_H-cy-rh)
        if fills:
            xx = x0
            for w in cw[:-1]:
                xx += w
                c.line(xx, le.A4_H-cy-rh, xx, le.A4_H-cy)
        cy += rh
    # outer top/bottom rules
    c.setStrokeColor(le.NAVY); c.setLineWidth(0.8)
    c.line(x0, le.A4_H-y_top, x0+total, le.A4_H-y_top)
    c.line(x0, le.A4_H-cy, x0+total, le.A4_H-cy)


def draw_figure(c, item, y_top):
    d = item.data
    w, h = d['disp_w'], d['disp_h']
    x = le.M_L + (le.CONTENT_W - w)/2
    c.drawImage(ImageReader(os.path.join(ROOT, d['path'])),
                x, le.A4_H - y_top - h, width=w, height=h,
                preserveAspectRatio=True, mask='auto')
    if d.get('caption'):
        segs = fu.runs_to_segments(le.text_runs(d['caption'], italic=True), 9.0, le.NAVY)
        fu.draw_rich(c, segs, le.M_L, y_top+h+3, le.CONTENT_W, le.A4_H,
                     size=9.0, line_height=12.8, align='center')


def draw_note(c, item, y_top):
    segs = fu.runs_to_segments(le.text_runs(item.data['text'], italic=True),
                               le.NOTE_SIZE, le.GREY)
    fu.draw_rich(c, segs, le.M_L, y_top, le.CONTENT_W, le.A4_H,
                 size=le.NOTE_SIZE, line_height=12.8, align='left', justify=False)


def draw_box(c, item, y_top):
    d = item.data
    paras = d['paragraphs']
    h = le.measure(item)
    c.setFillColor(HexColor('#D1DEEF'))
    c.rect(le.M_L, le.A4_H-y_top-h, le.CONTENT_W, h, stroke=0, fill=1)
    c.setStrokeColor(le.NAVY); c.setLineWidth(0.7)
    c.rect(le.M_L, le.A4_H-y_top-h, le.CONTENT_W, h, stroke=1, fill=0)
    cy = y_top + le.BOX_PAD
    segs = fu.runs_to_segments(le.text_runs(d['title'], bold=True, italic=True),
                               11.0, le.NAVY)
    fu.draw_rich(c, segs, le.M_L+le.BOX_PAD+3, cy, le.CONTENT_W-2*le.BOX_PAD-6,
                 le.A4_H, size=11.0, line_height=15.0, align='left')
    cy += 19.0
    for runs in paras:
        segs = fu.runs_to_segments(runs, le.BOX_SIZE, le.BLACK)
        fu.draw_rich(c, segs, le.M_L+le.BOX_PAD+3, cy,
                     le.CONTENT_W-2*le.BOX_PAD-6, le.A4_H,
                     size=le.BOX_SIZE, line_height=le.BOX_LH,
                     align='left', justify=True)
        cy += le.measure_rich(runs, le.BOX_SIZE, le.CONTENT_W-2*le.BOX_PAD-10, True) + le.BOX_AFTER


def draw_kpi(c, item, y_top):
    cells = item.data['cells']
    n = len(cells) or 1
    w = le.CONTENT_W/n
    for i, cell in enumerate(cells):
        x = le.M_L + i*w
        col = le.NAVY if i < 2 else HexColor('#0C8A76')
        c.setFillColor(col); c.rect(x, le.A4_H-y_top-le.KPI_H, w, le.KPI_H, stroke=0, fill=1)
        c.setStrokeColor(le.WHITE); c.setLineWidth(0.8)
        c.line(x+w, le.A4_H-y_top-le.KPI_H, x+w, le.A4_H-y_top)
        segs = fu.runs_to_segments(le.text_runs(cell['value'], bold=True), 18.0, le.WHITE)
        fu.draw_rich(c, segs, x+3, y_top+13, w-6, le.A4_H,
                     size=18.0, line_height=22.0, align='center')
        segs = fu.runs_to_segments(le.text_runs(cell['label']), 7.4, le.WHITE)
        fu.draw_rich(c, segs, x+3, y_top+39, w-6, le.A4_H,
                     size=7.4, line_height=9.6, align='center')

def render_pdf(pages, path):
    c = rl_canvas.Canvas(path, pagesize=(le.A4_W, le.A4_H), pageCompression=1)
    c.setTitle('Rapport du diagnostic opérationnel rapide — ESS, EpiC RDC, FHI 360, ICHESS')
    c.setSubject('Mise en page conforme à Md_ref.pdf ; contenu intégral du document source de 25 pages')
    for page in pages:
        key = f'page_{page.page_no}'
        c.bookmarkPage(key)
        if page.is_cover:
            draw_cover(c, page)
        else:
            draw_header_footer(c, page)
            cy = le.TOP
            for item in page.items:
                h = le.measure(item)
                if item.kind == 'heading': draw_heading(c, item, cy)
                elif item.kind == 'body': draw_body(c, item, cy)
                elif item.kind == 'bullet': draw_bullet(c, item, cy)
                elif item.kind == 'caption': draw_caption(c, item, cy)
                elif item.kind == 'signature': draw_signature(c, item, cy)
                elif item.kind in ('list_block','auto_toc'): draw_list_block(c, item, cy)
                elif item.kind == 'table': draw_table(c, item, cy)
                elif item.kind == 'figure': draw_figure(c, item, cy)
                elif item.kind == 'note': draw_note(c, item, cy)
                elif item.kind == 'box': draw_box(c, item, cy)
                elif item.kind == 'kpi': draw_kpi(c, item, cy)
                cy += h
                if item.kind == 'heading' and item.bookmark_level:
                    c.addOutlineEntry(item.data['text'], key,
                                      level=max(0,item.bookmark_level-1), closed=False)
        c.showPage()
    c.save()
    return path
