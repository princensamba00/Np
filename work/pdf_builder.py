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
    num = f'{page.page_no:02d}'
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
                 size=9.0, line_height=12.6, align='left')

def draw_signature(c, item, y_top):
    lines = item.data['lines']
    for i, line in enumerate(lines[:2]):
        segs = fu.runs_to_segments(le.text_runs(line, bold=(i==0)),
                                   10.0 if i==0 else 9.0,
                                   le.NAVY if i==0 else le.GREY)
        fu.draw_rich(c, segs, le.M_L, y_top+i*15.0, le.CONTENT_W, le.A4_H,
                     size=10.0 if i==0 else 9.0, line_height=15.0, align='center')

def _entry_lines(entry):
    text = entry['text']; bold = bool(entry.get('bold',False))
    segs = fu.runs_to_segments(le.text_runs(text, bold=bold), le.LIST_SIZE, le.BLACK)
    indent = 14 if entry.get('indent',0) else 0
    x0 = le.M_L + indent
    avail = (le.A4_W-le.M_R) - x0 - 50
    lines, n = fu.wrap_segments(segs, avail, size=le.LIST_SIZE)
    return segs, x0, avail, lines, n

def draw_list_entry(c, entry, y_top):
    segs, x0, avail, lines, n = _entry_lines(entry)
    marker = str(entry.get('page',''))
    x_right = le.A4_W - le.M_R
    # title
    fu.draw_rich(c, segs, x0, y_top, avail, le.A4_H,
                 size=le.LIST_SIZE, line_height=le.LIST_LH, align='left', justify=False)
    long_marker = len(marker) > 6
    # dotted leader on the last title line
    if not long_marker and lines:
        last = lines[-1]
        end = x0 + last.justified_width + 4
        c.setStrokeColor(le.DOTTED); c.setLineWidth(0.9); c.setDash(1,3)
        ly = le.A4_H - (y_top + (n-1)*le.LIST_LH + le.LIST_SIZE*0.55)
        if end < x_right - 30:
            c.line(end, ly, x_right-30, ly)
        c.setDash()
    # page marker
    msegs = fu.runs_to_segments(le.text_runs(marker, bold=True), 10.6, le.NAVY)
    if long_marker:
        fu.draw_rich(c, msegs, x_right-260, y_top+n*le.LIST_LH, 260, le.A4_H,
                     size=9.0, line_height=le.LIST_LH, align='right')
    else:
        fu.draw_rich(c, msegs, x_right-30, y_top+(n-1)*le.LIST_LH, 30, le.A4_H,
                     size=10.6, line_height=le.LIST_LH, align='right')

def draw_list_block(c, item, y_top):
    cy = y_top
    for e in item.data['entries']:
        draw_list_entry(c, e, cy)
        cy += le.list_entry_height(e)

def draw_table(c, item, y_top):
    rows = item.data['rows']; cw = item.data['col_widths']; fs = item.data['font_size']
    x0 = le.M_L; total = sum(cw)
    heights = le.table_row_heights(rows, cw, fs)
    cy = y_top
    # header
    h = heights[0]
    c.setFillColor(le.NAVY); c.rect(x0, le.A4_H-cy-h, total, h, stroke=0, fill=1)
    for j, cell in enumerate(rows[0]):
        segs = fu.runs_to_segments(le.text_runs(str(cell), bold=True), fs, le.WHITE)
        fu.draw_rich(c, segs, x0+sum(cw[:j])+5, cy+5, cw[j]-10, le.A4_H,
                     size=fs, line_height=fs*1.34, align='left')
    cy += h
    # body
    for ri, row in enumerate(rows[1:], start=1):
        rh = heights[ri]
        if ri % 2 == 0:
            c.setFillColor(le.CREAM); c.rect(x0, le.A4_H-cy-rh, total, rh, stroke=0, fill=1)
        for j, cell in enumerate(row):
            if j >= len(cw): break
            segs = fu.runs_to_segments(le.text_runs(str(cell)), fs, le.BLACK)
            fu.draw_rich(c, segs, x0+sum(cw[:j])+5, cy+3.5, cw[j]-10, le.A4_H,
                         size=fs, line_height=fs*1.34, align='left')
        c.setStrokeColor(le.DOTTED); c.setLineWidth(0.4)
        c.line(x0, le.A4_H-cy-rh, x0+total, le.A4_H-cy-rh)
        cy += rh
    # outer top/bottom rules
    c.setStrokeColor(le.NAVY); c.setLineWidth(0.8)
    c.line(x0, le.A4_H-y_top, x0+total, le.A4_H-y_top)
    c.line(x0, le.A4_H-cy, x0+total, le.A4_H-cy)

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
                cy += h
                if item.kind == 'heading' and item.bookmark_level:
                    c.addOutlineEntry(item.data['text'], key,
                                      level=max(0,item.bookmark_level-1), closed=False)
        c.showPage()
    c.save()
    return path
