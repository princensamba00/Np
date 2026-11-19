"""python-docx renderer for the shared paginated layout."""
from __future__ import annotations
import os, re
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import layout_engine as le
import font_utils as fu

ROOT = '/home/user/Np'
NAVY = RGBColor(0x13,0x1D,0x44)
GREY = RGBColor(0x6B,0x70,0x7D)
CREAM = 'FFFBF7'
NAVY_HEX = '131D44'
DOTTED_HEX = 'CED6F8'
RULE_HEX = 'D9D9D9'
WHITE = RGBColor(0xFF,0xFF,0xFF)
BLACK = RGBColor(0,0,0)

# ---------------------------------------------------------------------------
# Low-level OOXML helpers
# ---------------------------------------------------------------------------
def set_run_font(run, name='Glacial Indifference', size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.rFonts
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts'); rPr.insert(0, rFonts)
    for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'):
        rFonts.set(qn(a), name)
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color

def no_hyphen(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    el = OxmlElement('w:suppressAutoHyphens'); pPr.append(el)
    pPr.append(OxmlElement('w:keepLines'))

def set_para_border(paragraph, edge='bottom', color='131D44', size='12', space='4'):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = pPr.find(qn('w:pBdr'))
    if pBdr is None:
        pBdr = OxmlElement('w:pBdr'); pPr.append(pBdr)
    e = OxmlElement('w:'+edge)
    e.set(qn('w:val'),'single'); e.set(qn('w:sz'),size)
    e.set(qn('w:space'),space); e.set(qn('w:color'),color)
    pBdr.append(e)

def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),'clear'); shd.set(qn('w:color'),'auto'); shd.set(qn('w:fill'),fill)
    tcPr.append(shd)

def set_cell_margins(cell, top=40, start=70, bottom=40, end=70):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m, v in (('top',top),('start',start),('bottom',bottom),('end',end)):
        node = OxmlElement('w:'+m)
        node.set(qn('w:w'), str(v)); node.set(qn('w:type'),'dxa')
        tcMar.append(node)

def set_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge, val, color, sz in (
        ('top','single',NAVY_HEX,'8'), ('bottom','single',NAVY_HEX,'8'),
        ('insideH','single',DOTTED_HEX,'4'), ('insideV','nil',None,None),
        ('left','nil',None,None), ('right','nil',None,None)):
        e = OxmlElement('w:'+edge)
        e.set(qn('w:val'),val)
        if color: e.set(qn('w:color'),color); e.set(qn('w:sz'),sz)
        borders.append(e)
    tblPr.append(borders)

def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement('w:tblHeader'); el.set(qn('w:val'),'true'); trPr.append(el)

def cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:cantSplit'))

def set_outline_level(style, level):
    pPr = style.element.get_or_add_pPr()
    el = OxmlElement('w:outlineLvl'); el.set(qn('w:val'), str(level-1)); pPr.append(el)
    pPr.append(OxmlElement('w:keepNext'))
    pPr.append(OxmlElement('w:keepLines'))

def set_settings(doc):
    settings = doc.settings.element
    # disable automatic hyphenation document-wide
    ah = settings.find(qn('w:autoHyphenation'))
    if ah is None:
        ah = OxmlElement('w:autoHyphenation'); settings.append(ah)
    ah.set(qn('w:val'),'0')
    dnh = settings.find(qn('w:doNotHyphenateCaps'))
    if dnh is None:
        settings.append(OxmlElement('w:doNotHyphenateCaps'))
    uf = settings.find(qn('w:updateFields'))
    if uf is None:
        uf = OxmlElement('w:updateFields'); settings.append(uf)
    uf.set(qn('w:val'),'true')

def add_field(paragraph, instr, cached=None, font_size=None, bold=None, color=None):
    r = paragraph.add_run()
    set_run_font(r, size=font_size, bold=bold, color=color)
    fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'),'begin'); r._r.append(fc)
    r2 = paragraph.add_run(); set_run_font(r2, size=font_size, bold=bold, color=color)
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'),'preserve'); it.text = instr
    r2._r.append(it)
    r3 = paragraph.add_run(); set_run_font(r3, size=font_size, bold=bold, color=color)
    fc2 = OxmlElement('w:fldChar'); fc2.set(qn('w:fldCharType'),'separate'); r3._r.append(fc2)
    if cached is not None:
        r4 = paragraph.add_run(cached); set_run_font(r4, size=font_size, bold=bold, color=color)
    r5 = paragraph.add_run(); set_run_font(r5, size=font_size, bold=bold, color=color)
    fc3 = OxmlElement('w:fldChar'); fc3.set(qn('w:fldCharType'),'end'); r5._r.append(fc3)
    return paragraph

def add_complex_toc(doc, entries):
    """Insert an updateable TOC field with a cached, already-correct result."""
    p = doc.add_paragraph()
    p.style = doc.styles['TOC Heading'] if 'TOC Heading' in [s.name for s in doc.styles] else doc.styles['Normal']
    no_hyphen(p)
    r = p.add_run(); set_run_font(r, size=9.2)
    fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'),'begin'); fc.set(qn('w:dirty'),'true'); r._r.append(fc)
    r = p.add_run(); set_run_font(r, size=9.2)
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'),'preserve')
    it.text = 'TOC \\o "1-3" \\h \\z \\u'; r._r.append(it)
    r = p.add_run(); set_run_font(r, size=9.2)
    fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'),'separate'); r._r.append(fc)
    for e in entries:
        add_tab_entry(doc, e, style_prefix='TOC')
    p = doc.add_paragraph(); no_hyphen(p)
    r = p.add_run(); set_run_font(r, size=9.2)
    fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'),'end'); r._r.append(fc)

# ---------------------------------------------------------------------------
# Styles and sections
# ---------------------------------------------------------------------------
def get_or_add_style(doc, name, kind=WD_STYLE_TYPE.PARAGRAPH):
    for s in doc.styles:
        if s.name == name: return s
    return doc.styles.add_style(name, kind)

def configure_styles(doc):
    styles = doc.styles
    normal = styles['Normal']
    normal.font.name = 'Glacial Indifference'; normal.font.size = Pt(le.BODY_SIZE)
    set_run_font(normal.element.get_or_add_rPr().get_or_add_rFonts() if False else normal.element, 'Glacial Indifference') if False else None
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = Pt(le.BODY_LH)
    pf.space_after = Pt(le.BODY_AFTER)
    pf.widow_control = True
    # rFonts on style
    rPr = normal.element.get_or_add_rPr()
    rFonts = rPr.rFonts
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts'); rPr.insert(0,rFonts)
    for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'): rFonts.set(qn(a),'Glacial Indifference')

    for lvl, size in ((1,12.2),(2,10.4),(3,9.9)):
        st = styles[f'Heading {lvl}']
        st.font.name = 'Glacial Indifference'; st.font.size = Pt(size)
        st.font.bold = True; st.font.color.rgb = NAVY
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        st.paragraph_format.line_spacing = Pt(size*1.6)
        st.paragraph_format.space_before = Pt(0)
        st.paragraph_format.space_after = Pt({1:12,2:6,3:4}[lvl])
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.keep_together = True
        rPr = st.element.get_or_add_rPr(); rFonts = rPr.rFonts
        if rFonts is None: rFonts = OxmlElement('w:rFonts'); rPr.insert(0,rFonts)
        for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'): rFonts.set(qn(a),'Glacial Indifference')
        set_outline_level(st, lvl)

    cap = get_or_add_style(doc, 'Report Caption', WD_STYLE_TYPE.PARAGRAPH)
    cap.font.name='Glacial Indifference'; cap.font.size=Pt(9); cap.font.italic=True; cap.font.color.rgb=NAVY
    cap.paragraph_format.keep_with_next=True; cap.paragraph_format.space_after=Pt(5)
    cap.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT

    for i in (1,2,3):
        st = get_or_add_style(doc, f'TOC {i}', WD_STYLE_TYPE.PARAGRAPH)
        st.font.name='Glacial Indifference'; st.font.size=Pt(9.2)
        st.paragraph_format.space_after=Pt(0.5)
        st.paragraph_format.line_spacing=Pt(le.LIST_LH)
        st.paragraph_format.left_indent = Pt(14*(i-1))

    th = get_or_add_style(doc, 'TOC Heading', WD_STYLE_TYPE.PARAGRAPH)
    th.font.name='Glacial Indifference'; th.font.size=Pt(9.2)

def configure_section(section):
    section.page_width = Pt(le.A4_W); section.page_height = Pt(le.A4_H)
    section.left_margin = Pt(le.M_L); section.right_margin = Pt(le.M_R)
    section.top_margin = Pt(le.TOP); section.bottom_margin = Pt(le.BOTTOM)
    section.header_distance = Pt(26); section.footer_distance = Pt(26)
    section.different_first_page_header_footer = True

def configure_header_footer(section):
    header = section.header
    hp = header.paragraphs[0]
    hp.text = ''
    no_hyphen(hp)
    hp.paragraph_format.tab_stops.add_tab_stop(Pt(le.CONTENT_W), WD_TAB_ALIGNMENT.RIGHT)
    r = hp.add_run('ICHESS, LLC'); set_run_font(r, size=7.2, bold=True, color=NAVY)
    r = hp.add_run('\t'); set_run_font(r, size=7.2, color=GREY)
    add_field(hp, 'STYLEREF 1 \\* MERGEFORMAT', cached='', font_size=7.2, color=GREY)
    set_para_border(hp, 'bottom', RULE_HEX, '6', '4')
    # institutional subtitle as a second header line, preserving source letterhead
    hp2 = header.add_paragraph()
    hp2.text=''; no_hyphen(hp2)
    r = hp2.add_run('International Center for Health Systems Strengthening')
    set_run_font(r, size=6.4, color=GREY)
    hp2.paragraph_format.space_after = Pt(0)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.text=''; no_hyphen(fp)
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run(); set_run_font(r, size=8.2, bold=True, color=NAVY)
    add_field(fp, 'PAGE \\* MERGEFORMAT', cached='0', font_size=8.2, bold=True, color=NAVY)

# ---------------------------------------------------------------------------
# Content renderers
# ---------------------------------------------------------------------------
def add_page_break(doc):
    p = doc.add_paragraph(); no_hyphen(p)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(); set_run_font(r, size=1)
    r.add_break(WD_BREAK.PAGE)

def add_cover(doc):
    top = os.path.join(ROOT,'work/assets/logos_top_crop.png')
    ich = os.path.join(ROOT,'work/assets/logo_ichess_crop.png')
    if os.path.exists(top):
        p = doc.add_paragraph(); no_hyphen(p); p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after=Pt(40)
        p.add_run().add_picture(top, width=Inches(4.6))
    p = doc.add_paragraph(); no_hyphen(p)
    p.paragraph_format.space_before=Pt(60); p.paragraph_format.space_after=Pt(8)
    set_para_border(p,'bottom',NAVY_HEX,'16','1')
    for line in [
        'Rapport du diagnostic opérationnel',
        'rapide de la préparation des',
        'établissements de santé pour les',
        'services de santé maternelle, néonatale',
        'et infantile, paludisme et nutrition',
    ]:
        p = doc.add_paragraph(); no_hyphen(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run(fu.nbsp_text(line)); set_run_font(r, size=20.5, bold=True, color=NAVY)
    p = doc.add_paragraph(); no_hyphen(p)
    p.paragraph_format.space_after=Pt(40)
    set_para_border(p,'bottom',NAVY_HEX,'16','1')
    if os.path.exists(ich):
        p = doc.add_paragraph(); no_hyphen(p); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after=Pt(30)
        p.add_run().add_picture(ich, width=Inches(2.4))
    p = doc.add_paragraph(); no_hyphen(p); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('Kinshasa, Octobre 2026'); set_run_font(r, size=11, bold=True, color=NAVY)

def add_rich_paragraph(doc, runs, kind='body'):
    p = doc.add_paragraph(); no_hyphen(p)
    if kind == 'body':
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = Pt(le.BODY_LH)
        p.paragraph_format.space_after = Pt(le.BODY_AFTER)
    elif kind == 'bullet':
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.first_line_indent = Pt(-12)
        p.paragraph_format.line_spacing = Pt(le.BODY_LH)
        p.paragraph_format.space_after = Pt(le.BULLET_AFTER)
    elif kind == 'caption':
        p.style = doc.styles['Report Caption']
    for run in runs:
        txt = fu.nbsp_text(run.get('text','')).replace(fu.BULLET_SRC,fu.BULLET_DST)
        r = p.add_run(txt)
        set_run_font(r, size=le.BODY_SIZE, bold=run.get('bold',False),
                     italic=run.get('italic',False))
    return p

def add_heading(doc, item):
    lvl = item.data['level']
    p = doc.add_paragraph(style=f'Heading {lvl}')
    no_hyphen(p)
    r = p.add_run(fu.nbsp_text(item.data['text']))
    set_run_font(r, size={1:12.2,2:10.4,3:9.9}[lvl], bold=True, color=NAVY)
    p.paragraph_format.keep_with_next = True
    return p

def add_signature(doc, item):
    for i,line in enumerate(item.data['lines'][:2]):
        p = doc.add_paragraph(); no_hyphen(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after=Pt(0)
        r = p.add_run(fu.nbsp_text(line))
        set_run_font(r, size=10 if i==0 else 9, bold=(i==0),
                     color=NAVY if i==0 else GREY)

def add_tab_entry(doc, e, style_prefix=None):
    p = doc.add_paragraph(); no_hyphen(p)
    if style_prefix:
        lvl = min(3, max(1, int(e.get('level', e.get('indent',0)+1))))
        p.style = doc.styles[f'TOC {lvl}']
    else:
        p.paragraph_format.line_spacing = Pt(le.LIST_LH)
        p.paragraph_format.space_after = Pt(le.LIST_AFTER)
        if e.get('indent',0): p.paragraph_format.left_indent = Pt(14)
    p.paragraph_format.tab_stops.add_tab_stop(Pt(le.CONTENT_W - (14 if e.get('indent',0) else 0)),
                                              WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    r = p.add_run(fu.nbsp_text(e['text']))
    set_run_font(r, size=le.LIST_SIZE, bold=e.get('bold',False))
    marker = str(e.get('page',''))
    if len(marker) > 6:
        p2 = doc.add_paragraph(); no_hyphen(p2)
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p2.paragraph_format.space_after=Pt(0)
        r2 = p2.add_run(fu.nbsp_text(marker)); set_run_font(r2, size=9, bold=True, color=NAVY)
    else:
        r = p.add_run('\t'+marker); set_run_font(r, size=10.6, bold=True, color=NAVY)
    return p

def add_list_block(doc, item):
    for e in item.data['entries']:
        add_tab_entry(doc, e, style_prefix='TOC' if item.kind=='auto_toc' else None)

def add_table(doc, item):
    rows = item.data['rows']; cw = item.data['col_widths']; fs = item.data['font_size']
    if item.data.get('caption'):
        p = doc.add_paragraph(); no_hyphen(p); p.style=doc.styles['Report Caption']
        r = p.add_run(fu.nbsp_text(item.data['caption'])); set_run_font(r, size=9, italic=True, color=NAVY)
        p.paragraph_format.keep_with_next=True
    table = doc.add_table(rows=len(rows), cols=len(cw))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    for j,w in enumerate(cw):
        for row in table.rows:
            row.cells[j].width = Pt(w)
    for ri,row in enumerate(rows):
        cells = table.rows[ri].cells
        cant_split(table.rows[ri])
        if ri==0: repeat_header(table.rows[ri])
        for j,cell in enumerate(row[:len(cw)]):
            c = cells[j]
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(c)
            set_cell_shading(c, NAVY_HEX if ri==0 else (CREAM if ri%2==0 else 'FFFFFF'))
            p = c.paragraphs[0]; p.text=''; no_hyphen(p)
            p.paragraph_format.line_spacing = Pt(fs*1.28)
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(fu.nbsp_text(str(cell)))
            set_run_font(r, size=fs, bold=(ri==0), color=WHITE if ri==0 else BLACK)
    return table

def render_docx(pages, path, content=None):
    doc = Document()
    configure_styles(doc)
    configure_section(doc.sections[0])
    configure_header_footer(doc.sections[0])
    set_settings(doc)
    cp = doc.core_properties
    cp.title = 'Rapport du diagnostic opérationnel rapide — ESS, EpiC RDC, FHI 360, ICHESS'
    cp.subject = 'Contenu intégral du document source de 25 pages ; design Md_ref.pdf'
    cp.comments = 'Table des matières automatique : mettre à jour les champs dans Word si nécessaire.'

    first = True
    for page in pages:
        if not first: add_page_break(doc)
        first = False
        if page.is_cover:
            add_cover(doc); continue
        for item in page.items:
            if item.kind == 'heading': add_heading(doc, item)
            elif item.kind == 'body': add_rich_paragraph(doc, item.data['runs'], 'body')
            elif item.kind == 'bullet': add_rich_paragraph(doc, item.data['runs'], 'bullet')
            elif item.kind == 'caption':
                p = doc.add_paragraph(); no_hyphen(p); p.style=doc.styles['Report Caption']
                r = p.add_run(fu.nbsp_text(item.data['text'])); set_run_font(r, size=9, italic=True, color=NAVY)
                p.paragraph_format.keep_with_next=True
            elif item.kind == 'signature': add_signature(doc, item)
            elif item.kind == 'list_block': add_list_block(doc, item)
            elif item.kind == 'auto_toc':
                add_complex_toc(doc, item.data['entries'])
            elif item.kind == 'table': add_table(doc, item)
    doc.save(path)
    return path
