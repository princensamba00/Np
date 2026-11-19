"""Deterministic A4 pagination shared by the PDF and DOCX renderers."""
from __future__ import annotations
import re, copy, json
from dataclasses import dataclass, field
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
import font_utils as fu

fu.register_fonts()

A4_W, A4_H = 595.28, 841.89
M_L = M_R = 59.5
TOP = 62.0
BOTTOM = 60.0
CONTENT_W = A4_W - M_L - M_R
CONTENT_H = A4_H - TOP - BOTTOM

NAVY = HexColor('#131D44')
GREY = HexColor('#6B707D')
RULE = HexColor('#D9D9D9')
DOTTED = HexColor('#CED6F8')
CREAM = HexColor('#FFFBF7')
YELLOW = HexColor('#FFDE59')
PERIWINKLE = HexColor('#8DA1FF')
BLACK = HexColor('#000000')
WHITE = HexColor('#FFFFFF')

BODY_SIZE = 9.9
BODY_LH = 13.4
BODY_AFTER = 4.0
BULLET_AFTER = 3.0
TABLE_SIZE = 8.0
DENSE_TABLE_SIZE = 7.2
LIST_SIZE = 9.2
LIST_LH = 10.2
LIST_AFTER = 0.5

@dataclass
class Item:
    kind: str
    data: dict = field(default_factory=dict)
    height: float = 0.0
    keep_with_next: bool = False
    new_page: bool = False
    heading_id: str | None = None
    bookmark_level: int | None = None
    section_label: str | None = None

@dataclass
class Page:
    page_no: int
    items: list
    section_label: str
    is_cover: bool = False

# ---------------------------------------------------------------------------
# Item constructors
# ---------------------------------------------------------------------------
def H(text, level, key=None, new_page=False):
    label = re.sub(r'^(?:I|II|III|IV|V)\.\s*', '', text)
    label = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', label).strip().upper()
    return Item('heading', {'text': text, 'level': level}, keep_with_next=True,
                new_page=new_page, heading_id=key or text,
                bookmark_level=level, section_label=label or None)

def SUB(text, new_page=False):
    return H(text, 2, new_page=new_page)

def P(runs, justify=True):
    return Item('body', {'runs': runs, 'justify': justify})

def BULLET(runs):
    return Item('bullet', {'runs': runs})

def CAP(text):
    return Item('caption', {'text': text}, keep_with_next=True)

def SIG(lines):
    return Item('signature', {'lines': lines})

def LIST(entries, name='list', new_page=False):
    return Item('list_block', {'entries': entries, 'name': name}, new_page=new_page)

def AUTO_TOC(entries):
    return Item('auto_toc', {'entries': entries, 'name': 'auto_toc'})

def TABLE(name, caption, rows, font_size=TABLE_SIZE, new_page=False):
    widths = compute_col_widths(rows, font_size, CONTENT_W)
    return Item('table', {'name': name, 'caption': caption, 'rows': rows,
                          'col_widths': widths, 'font_size': font_size},
                new_page=new_page, keep_with_next=False)

def COVER():
    return Item('cover', {}, new_page=True)

# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------
def text_runs(text, bold=False, italic=False):
    return [{'text': fu.nbsp_text(text), 'bold': bold, 'italic': italic}]

def measure_rich(runs, size, max_width, justify=False):
    segs = fu.runs_to_segments(runs, size, BLACK)
    _, n = fu.wrap_segments(segs, max_width, size=size, justify=justify)
    return n * (size * 1.42)

def compute_col_widths(rows, font_size, total):
    if not rows: return [total]
    n = max(len(r) for r in rows)
    natural = []
    for c in range(n):
        w = 0.0
        for r in rows:
            cell = str(r[c]) if c < len(r) else ''
            w = max(w, pdfmetrics.stringWidth(cell, 'Glacial', font_size))
        natural.append(w + 12)
    s = sum(natural)
    if s <= total:
        # distribute spare space to the widest column
        extra = total - s
        i = natural.index(max(natural))
        natural[i] += extra
        return natural
    scale = total / s
    widths = [max(42.0, w*scale) for w in natural]
    # renormalise after min clamp
    s2 = sum(widths)
    return [w*total/s2 for w in widths]

def row_height(row, col_widths, font_size):
    max_lines = 1
    for i, cell in enumerate(row):
        if i >= len(col_widths): break
        segs = fu.runs_to_segments(text_runs(str(cell)), font_size, BLACK)
        _, n = fu.wrap_segments(segs, col_widths[i]-9, size=font_size)
        max_lines = max(max_lines, n)
    return max(16.5, max_lines * (font_size*1.28) + 5.0)

def table_row_heights(rows, col_widths, font_size):
    return [22.0] + [row_height(r, col_widths, font_size) for r in rows[1:]]

def measure_table(item):
    rows = item.data['rows']; cw = item.data['col_widths']; fs = item.data['font_size']
    return sum(table_row_heights(rows, cw, fs)) + 4.0

def toc_level(text):
    if re.match(r'^(?:I|II|III|IV|V)\.\s', text): return 1
    if re.match(r'^\d+\.\d+\.', text): return 2
    if text.startswith('Annexe '): return 2
    return 1

def list_entry_height(entry):
    text = entry['text']; marker = str(entry.get('page',''))
    indent = 14 if entry.get('indent',0) else 0
    avail = CONTENT_W - indent - 48
    segs = fu.runs_to_segments(text_runs(text), LIST_SIZE, BLACK)
    _, n = fu.wrap_segments(segs, avail, size=LIST_SIZE)
    h = n * LIST_LH + LIST_AFTER
    if len(marker) > 6: h += LIST_LH  # long artefact on its own line
    return h

def measure_list_block(item):
    return sum(list_entry_height(e) for e in item.data['entries'])

def measure(item):
    k = item.kind
    if k == 'cover': return CONTENT_H
    if k == 'heading':
        lvl = item.data['level']
        if lvl == 1: return 38.0
        if lvl == 2: return 23.0
        return 19.0
    if k == 'body':
        return measure_rich(item.data['runs'], BODY_SIZE, CONTENT_W, item.data.get('justify',True)) + BODY_AFTER
    if k == 'bullet':
        return measure_rich(item.data['runs'], BODY_SIZE, CONTENT_W-18, False) + BULLET_AFTER
    if k == 'caption': return 13.0 + 5.0
    if k == 'signature': return 34.0
    if k == 'list_block' or k == 'auto_toc': return measure_list_block(item)
    if k == 'table': return measure_table(item)
    return 10.0

# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------
def split_table(item, avail):
    rows = item.data['rows']; cw = item.data['col_widths']; fs = item.data['font_size']
    heights = table_row_heights(rows, cw, fs)
    header_h = heights[0]
    if avail < header_h + heights[1] + 4 if len(heights)>1 else avail < header_h+20:
        return None, item
    take, h = 0, header_h
    for rh in heights[1:]:
        if h + rh + 4 > avail: break
        h += rh; take += 1
    if take == 0: return None, item
    frag = copy.deepcopy(item)
    frag.data['rows'] = [rows[0]] + rows[1:1+take]
    frag.height = h + 4
    rem = None
    if 1+take < len(rows):
        rem = copy.deepcopy(item)
        rem.data['rows'] = [rows[0]] + rows[1+take:]
        rem.data['caption'] = ''  # caption only on first page
        rem.new_page = False
        rem.height = measure_table(rem)
    return frag, rem

def split_list_block(item, avail):
    entries = item.data['entries']
    heights = [list_entry_height(e) for e in entries]
    take, h = 0, 0.0
    for eh in heights:
        if h + eh > avail: break
        h += eh; take += 1
    if take == 0: return None, item
    frag = copy.deepcopy(item)
    frag.data['entries'] = entries[:take]; frag.height = h
    rem = None
    if take < len(entries):
        rem = copy.deepcopy(item)
        rem.data['entries'] = entries[take:]; rem.height = sum(heights[take:])
    return frag, rem

def split_item(item, avail):
    if item.kind == 'table': return split_table(item, avail)
    if item.kind in ('list_block','auto_toc'): return split_list_block(item, avail)
    return None, item

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
def paginate(items):
    pages, cur, used = [], [], 0.0
    section = 'PRÉFACE'
    page_no = 1
    pending_label = None

    def finish(is_cover=False):
        nonlocal cur, used, page_no
        if not cur: return
        cover = is_cover or any(i.kind == 'cover' for i in cur)
        pages.append(Page(page_no, cur, section or 'PRÉFACE', cover))
        page_no += 1
        cur, used = [], 0.0

    for idx, item in enumerate(items):
        h = measure(item)
        if item.kind == 'cover':
            finish()
            cur = [item]; used = CONTENT_H
            section = 'PRÉFACE'
            continue
        if item.new_page and cur:
            finish()
        if item.section_label and item.kind == 'heading' and item.data['level'] == 1:
            section = item.section_label
        # orphan protection for headings/captions: keep room for the next block too
        next_h = measure(items[idx+1]) if idx+1 < len(items) else 0.0
        needed = next_h if next_h else 42.0
        if item.keep_with_next and cur and used + h + needed > CONTENT_H:
            finish()
        if used + h <= CONTENT_H:
            cur.append(item); used += h
            continue
        frag, rem = split_item(item, CONTENT_H - used)
        if frag is not None:
            cur.append(frag); used += measure(frag)
            finish()
            if rem is not None:
                # put remainder on the fresh page, preserving its new_page flag semantics
                rh = measure(rem)
                if rh <= CONTENT_H:
                    cur.append(rem); used += rh
                else:
                    frag2, rem2 = split_item(rem, CONTENT_H)
                    if frag2 is not None:
                        cur.append(frag2); used += measure(frag2)
                    if rem2 is not None:
                        # rare: recursively continue on next page
                        while rem2 is not None:
                            finish()
                            f2, rem2 = split_item(rem2, CONTENT_H)
                            if f2 is None: break
                            cur.append(f2); used = measure(f2)
            continue
        finish()
        rh = measure(item)
        if rh > CONTENT_H:
            f2, rem2 = split_item(item, CONTENT_H)
            if f2 is not None:
                cur.append(f2); used = measure(f2)
                if rem2 is not None:
                    # continue remainder in a loop
                    stack = [rem2]
                    while stack:
                        r = stack.pop()
                        finish()
                        f3, r3 = split_item(r, CONTENT_H)
                        if f3 is not None:
                            cur.append(f3); used = measure(f3)
                        if r3 is not None: stack.append(r3)
            continue
        cur.append(item); used = rh
    finish()
    return pages

def collect_heading_pages(pages):
    out = {}
    for p in pages:
        for it in p.items:
            if it.kind == 'heading' and it.heading_id:
                out.setdefault(it.heading_id, p.page_no)
    return out

def update_auto_toc(pages, heading_pages):
    for p in pages:
        for it in p.items:
            if it.kind != 'auto_toc': continue
            new = []
            for e in it.data['entries']:
                ee = dict(e)
                key = e.get('key')
                if key in heading_pages:
                    ee['page'] = str(heading_pages[key])
                new.append(ee)
            it.data['entries'] = new

# ---------------------------------------------------------------------------
# Build the full flow from content.json
# ---------------------------------------------------------------------------
def build_items(content):
    items = []
    items.append(COVER())

    # Préface
    items.append(H('Préface', 1, key='Préface', new_page=True))
    for para in content['front']['preface']['paragraphs']:
        items.append(P(text_runs(para)))
    items.append(SIG(content['front']['preface']['signature']))

    # Remerciements
    items.append(H('Remerciements', 1, key='Remerciements', new_page=True))
    for para in content['front']['remerciements']['paragraphs']:
        items.append(P(text_runs(para)))
    items.append(SIG(content['front']['remerciements']['signature']))

    # Table des matières source, page numbers preserved exactly
    items.append(H('Table des matières', 1, key='TOC source', new_page=True))
    toc_entries = []
    for e in content['toc_source']:
        lvl = toc_level(e['text'])
        toc_entries.append({'text': e['text'], 'page': e['page'],
                            'indent': 1 if lvl == 2 else 0, 'bold': lvl == 1})
    items.append(LIST(toc_entries, 'toc_source'))

    # Automatic / updateable table of contents with final page numbers.
    # The entries are filled after every other heading has been created.
    items.append(H('Table des matières', 1, key='TOC automatique', new_page=True))
    auto_toc_item = AUTO_TOC([])
    items.append(auto_toc_item)

    # Liste des figures et tableaux
    items.append(H('Liste des figures et tableaux', 1, key='Liste des figures et tableaux', new_page=True))
    items.append(SUB('Liste des figures'))
    fig_entries = [{'text': e['text'], 'page': e['page'], 'indent':1, 'bold':False}
                   for e in content['list_figures']]
    items.append(LIST(fig_entries, 'figures'))
    items.append(SUB('Liste des tableaux'))
    tab_entries = [{'text': e['text'], 'page': e['page'], 'indent':1, 'bold':False}
                   for e in content['list_tables']]
    items.append(LIST(tab_entries[:15], 'tables_1'))
    items.append(LIST(tab_entries[15:], 'tables_2', new_page=True))
    items.append(SUB('Tableaux des annexes'))
    anx_entries = [{'text': e['text'], 'page': e['page'], 'indent':1, 'bold':False}
                   for e in content['annex_tables']]
    items.append(LIST(anx_entries[:22], 'annexes_1'))
    items.append(LIST(anx_entries[22:], 'annexes_2', new_page=True))

    # Abréviations et acronymes: two source tables with repeated header
    items.append(H('Abréviations et acronymes', 1, key='Abréviations et acronymes', new_page=True))
    items.append(TABLE('abbrev_1', '', content['tables']['abbrev_1'], TABLE_SIZE))
    items.append(TABLE('abbrev_2', '', content['tables']['abbrev_2'], TABLE_SIZE))

    # Body blocks
    key_counter = 0
    for b in content['body_blocks']:
        t = b['type']
        if t.startswith('h'):
            lvl = b['level'] or 1
            key = f"body:{b['page']}:{key_counter}"; key_counter += 1
            newp = (lvl == 1 and b['text'].startswith(('Résumé exécutif','I.','II.'))) \
                   or b['text'].startswith('2.9.')
            items.append(H(b['text'], lvl, key=key, new_page=newp))
        elif t == 'body':
            items.append(P(b['runs']))
        elif t == 'bullet':
            items.append(BULLET(b['runs']))
        elif t == 'caption':
            items.append(CAP(b['text']))
        elif t == 'table':
            name = b['table']; rows = content['tables'][name]
            fs = DENSE_TABLE_SIZE if name in ('table_3','table_5','table_4','table_6') else TABLE_SIZE
            ti = TABLE(name, b['caption'], rows, fs)
            if name == 'table_6':
                # keep the rule labels intact on one line
                ti.data['col_widths'] = [112.0, CONTENT_W-112.0]
            items.append(ti)
        else:
            raise ValueError('unknown block '+t)

    heading_catalog = []
    for it in items:
        if (it.kind == 'heading' and it.heading_id
                and it.heading_id != 'TOC automatique' and it.data['level'] <= 3):
            heading_catalog.append({
                'text': it.data['text'], 'level': it.data['level'],
                'key': it.heading_id, 'page': '0',
                'indent': max(0, it.data['level']-1), 'bold': it.data['level']==1,
            })
    auto_toc_item.data['entries'] = heading_catalog
    return items

def build_pages(content):
    items = build_items(content)
    pages = paginate(items)
    hp = collect_heading_pages(pages)
    update_auto_toc(pages, hp)
    # rebuild once so the auto-TOC page numbers are the ones from the final layout
    # (the layout itself is stable because only the numeric strings changed width).
    return pages, hp
