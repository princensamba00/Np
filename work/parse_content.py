import fitz, json, re, os
from collections import Counter

SRC = 'Rapport_Diagnostic_Operationnel_Rapide_ESS_EpiC_RDC_FHI360_ICHESS_Rapport_final_version_propre_05-11-26.pdf'
REF = 'Md_ref.pdf'
os.makedirs('work', exist_ok=True)

# ---------------------------------------------------------------------------
# Palette and design facts extracted from Md_ref.pdf
# ---------------------------------------------------------------------------
DESIGN = {
    'navy': '#131D44', 'grey': '#6B707D', 'dotted': '#CED6F8',
    'cream': '#FFFBF7', 'yellow': '#FFDE59', 'blue': '#8DA1FF',
    'rule_grey': '#D9D9D9', 'page': [595.28, 841.89],
    'margin_left': 59.5, 'margin_right': 59.5,
    'header_rule_y_from_top': 48.5, 'body_top_from_top': 62.0,
    'font_regular': 'Glacial Indifference', 'font_bold': 'Glacial Indifference',
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def norm_spaces(s):
    return re.sub(r'[ \t]+', ' ', s.replace('\u00a0', ' ')).strip()

def dehyphen_join(a, b):
    a = a.rstrip(); b = b.lstrip()
    if not a or not b: return a + b
    if a.endswith('-') and b[:1].islower():
        return a + b
    return a + ' ' + b

def span_style(s):
    flags = s.get('flags', 0)
    return {
        'bold': bool(flags & 16),
        'italic': bool(flags & 2),
        'size': round(float(s.get('size', 11)), 1),
        'color': s.get('color', 0),
        'font': s.get('font', ''),
    }

def line_obj(page_no, block, line):
    spans = []
    for s in line['spans']:
        t = s['text']
        if not t: continue
        st = span_style(s)
        st['text'] = t
        spans.append(st)
    if not spans: return None
    text = ''.join(s['text'] for s in spans).rstrip()
    if not text.strip(): return None
    x0, y0, x1, y1 = line['bbox']
    all_bold = all(st['bold'] for st in spans if st['text'].strip())
    all_italic = all(st['italic'] for st in spans if st['text'].strip())
    green = any(st['color'] in (0x3A7C22, 0xE2841, 0x0E2841) for st in spans)
    return {
        'page': page_no, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
        'text': text, 'spans': spans, 'all_bold': all_bold,
        'all_italic': all_italic, 'green': green,
        'size': max(st['size'] for st in spans),
    }

def classify(line):
    t = norm_spaces(line['text'])
    if t.startswith('\uf0b7'):
        return 'bullet'
    if line['all_italic'] and re.match(r'Tableau\s+\d+\s*:', t, re.I):
        return 'caption'
    if re.match(r'^(I|II|III|IV|V)\.\s', t):
        return 'h1'
    if re.match(r'^\d+\.\d+\.\d+\.?\s', t):
        return 'h3'
    if re.match(r'^\d+\.\d+\.?\s', t):
        return 'h2'
    if line['all_bold'] and line['size'] >= 10.5 and len(t) < 180:
        if line['size'] >= 17 or line['green']:
            return 'h1'
        return 'h2'
    if line['all_bold'] and line['size'] >= 10 and len(t) < 120:
        return 'h2'
    return 'body'

def heading_level(kind, line):
    if kind == 'h1': return 1
    if kind == 'h3': return 3
    if kind == 'h2': return 2
    return None

def lines_to_rich(lines):
    """Join physical lines into one logical paragraph, preserving bold/italic runs."""
    out = []
    prev_plain = ''
    for i, line in enumerate(lines):
        plain = norm_spaces(line['text'])
        if i:
            if prev_plain.rstrip().endswith('-') and plain[:1].islower():
                sep = ''
            else:
                sep = ' '
            out.append({'text': sep, 'bold': False, 'italic': False})
        for st in line['spans']:
            out.append({'text': st['text'], 'bold': st['bold'], 'italic': st['italic']})
        prev_plain = plain
    # Trim trailing spaces from the last run
    while out and out[-1]['text'] and out[-1]['text'].isspace():
        out.pop()
    return out

def rich_plain(runs):
    return norm_spaces(''.join(r['text'] for r in runs))

# ---------------------------------------------------------------------------
# Cover, front-matter prose, signatures
# ---------------------------------------------------------------------------
src = fitz.open(SRC)
ref = fitz.open(REF)

def source_blocks(page_no):
    return [(b[0], b[1], b[2], b[3], b[4]) for b in src[page_no-1].get_text('blocks', sort=False)]

cover_lines = [l.strip() for l in source_blocks(1) if False]  # placeholder
cover = {
    'title_lines': [
        'Rapport du diagnostic opérationnel',
        'rapide de la préparation des',
        'établissements de santé pour les',
        'services de santé maternelle, néonatale',
        'et infantile, paludisme et nutrition',
    ],
    'date': 'Kinshasa, Octobre 2026',
    'institution': 'ICHESS, LLC',
    'institution_full': 'International Center for Health Systems Strengthening',
    'logos_top': 'work/assets/logos_top_crop.png',
    'logo_ichess': 'work/assets/logo_ichess_crop.png',
}

def front_page(page_no, heading):
    blocks = source_blocks(page_no)
    paras, signature, sig_buffer = [], [], []
    for x0,y0,x1,y1,text in blocks:
        t = text.strip()
        if not t: continue
        if y0 < 60 or y0 > 790: continue
        if t == heading: continue
        lines = [norm_spaces(l) for l in t.splitlines() if l.strip()]
        is_signature = (
            (y0 > 650 or (x0 > 300 and y0 > 500)) and
            len(t) < 250 and
            re.search(r'\b(MD|MPH|PhD|Directeur|Directrice|EpiC|ICHESS)\b', t)
        )
        if is_signature:
            sig_buffer.extend(lines)
            continue
        if sig_buffer:
            signature.extend(sig_buffer); sig_buffer = []
        val = lines[0]
        for l in lines[1:]: val = dehyphen_join(val, l)
        paras.append(val)
    if sig_buffer: signature.extend(sig_buffer)
    return {'heading': heading, 'paragraphs': paras, 'signature': signature}

front = {
    'preface': front_page(2, 'Préface'),
    'remerciements': front_page(3, 'Remerciements'),
}

# ---------------------------------------------------------------------------
# Clean transcription of source TOC / lists from the design model's front matter.
# These are source content, not model editorial content; the model PDF preserves
# them with usable Unicode while the source PDF's text layer is partly garbled.
# ---------------------------------------------------------------------------
def ref_blocks(page_no):
    return [(b[0], b[1], b[2], b[3], b[4]) for b in ref[page_no-1].get_text('blocks', sort=False)]

SECTION_TITLES = {
    'TABLE DES MATIÈRES', 'LISTE DES FIGURES ET TABLEAUX',
    'LISTE DES FIGURES', 'LISTE DES TABLEAUX', 'TABLEAUX DES ANNEXES',
    'ABRÉVIATIONS ET ACRONYMES', 'SIGLE SIGNIFICATION',
}

def parse_ref_entries(pages):
    raw = []
    for pno in pages:
        for x0,y0,x1,y1,text in ref_blocks(pno):
            t = text.strip()
            if not t or y0 < 60 or y0 > 790: continue
            if 'I C H E S S' in t or re.fullmatch(r'\d\s?\d', t): continue
            raw.append((pno,y0,x0,t))
    raw.sort(key=lambda r:(r[0],r[1],r[2]))
    entries = []
    pending = ''
    for pno,y0,x0,t in raw:
        lines = [l.strip() for l in t.splitlines() if l.strip()]
        if not lines: continue
        # A title/heading block has no page marker; never merge it with an entry.
        joined = norm_spaces(' '.join(lines))
        if joined in SECTION_TITLES:
            continue
        last = lines[-1]
        page_marker = None
        if re.fullmatch(r'\d{1,3}', last) or 'Erreur ! Signet non défini.' in last:
            page_marker = last
            text_lines = lines[:-1]
        else:
            text_lines = lines
        body = ' '.join(text_lines)
        if pending:
            body = dehyphen_join(pending, body)
            pending = ''
        if page_marker is None:
            pending = body
            continue
        body = norm_spaces(body)
        body = re.sub(r'\.{3,}', '', body).strip()
        if not body: continue
        entries.append({'text': body, 'page': page_marker, 'ref_page': pno})
    if pending:
        entries.append({'text': norm_spaces(pending), 'page': '', 'ref_page': pages[-1]})
    return entries

toc_source = parse_ref_entries([3,4])
# The model's pages 5–8 carry the figure list, table list and annex tables.
all_list_entries = parse_ref_entries([5,6,7,8])
list_figures = [e for e in all_list_entries if re.match(r'^Figure\s+\d+\s*:', e['text'])]
list_tables = [e for e in all_list_entries if re.match(r'^Tableau\s+\d+\s*:', e['text'])]
annex_tables = [e for e in all_list_entries if re.match(r'^Tableau\s+A\d+\s*:', e['text'])]

# ---------------------------------------------------------------------------
# Tables extracted from the source PDF itself
# ---------------------------------------------------------------------------
tables_raw = json.load(open('work/tables_raw.json'))
table_p17 = json.load(open('work/table_p17.json'))
table_p22 = json.load(open('work/table_p22.json'))
tables = {
    'abbrev_1': tables_raw['9'], 'abbrev_2': tables_raw['10'],
    'table_1': tables_raw['15'], 'table_2': table_p17,
    'table_3': tables_raw['20'], 'table_4': table_p22,
    'table_5': tables_raw['23'], 'table_6': tables_raw['24'],
}

# ---------------------------------------------------------------------------
# Body pages 11–25: semantic paragraph reconstruction
# ---------------------------------------------------------------------------
TABLE_REGIONS = {
    15: (507.8, 747.0, 'table_1'),
    17: (428.6, 575.3, 'table_2'),
    20: (114.1, 656.1, 'table_3'),
    22: (150.1, 381.5, 'table_4'),
    23: (85.5, 371.4, 'table_5'),
    24: (85.5, 400.1, 'table_6'),
}

def parse_body_page(page_no):
    page = src[page_no-1]
    lines = []
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            o = line_obj(page_no, b, l)
            if not o: continue
            if o['y0'] < 60 or o['y0'] > 790: continue
            if page_no in TABLE_REGIONS:
                y0,y1,_ = TABLE_REGIONS[page_no]
                if y0-1 <= o['y0'] <= y1+1: continue
            lines.append(o)
    # Stable reading order
    lines.sort(key=lambda o:(round(o['y0'],1), o['x0']))
    # Merge standalone private-use bullet glyphs with the text line to their right
    merged = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        if cur['text'].strip() == '\uf0b7' and i+1 < len(lines):
            nxt = lines[i+1]
            if abs(nxt['y0']-cur['y0']) < 2.0 and nxt['x0'] > cur['x0']+5:
                cur = dict(cur)
                cur['text'] = '\uf0b7 ' + nxt['text']
                cur['spans'] = cur['spans'] + [{'text':' ', 'bold':False, 'italic':False, 'size':11.5, 'color':0, 'font':''}] + nxt['spans']
                cur['x1'] = nxt['x1']; cur['y1'] = max(cur['y1'],nxt['y1'])
                i += 1
        merged.append(cur); i += 1
    lines = merged

    blocks = []
    cur_lines = []
    cur_kind = None
    prev_bottom = None

    def flush():
        nonlocal cur_lines, cur_kind
        if not cur_lines: return
        kind = cur_kind or 'body'
        runs = lines_to_rich(cur_lines)
        plain = rich_plain(runs)
        lvl = heading_level(kind, cur_lines[0])
        blocks.append({
            'type': kind, 'level': lvl, 'runs': runs, 'text': plain,
            'page': page_no, 'y0': cur_lines[0]['y0'], 'y1': cur_lines[-1]['y1'],
        })
        cur_lines, cur_kind = [], None

    for o in lines:
        kind = classify(o)
        # A heading/caption/bullet normally starts and ends its own block, but
        # consecutive lines of the SAME heading (e.g. "I." + "Introduction")
        # belong together.
        heading_kinds = ('h1','h2','h3')
        force_new = kind in ('h1','h2','h3','caption','bullet') or cur_kind in ('h1','h2','h3','caption')
        gap = None if prev_bottom is None else o['y0'] - prev_bottom
        if (cur_lines and cur_kind in heading_kinds and kind == cur_kind
                and gap is not None and gap <= 3.0
                and (not norm_spaces(cur_lines[-1]['text']).endswith(('.', ':', ';'))
                     or re.fullmatch(r'(?:I|II|III|IV|V)\.|\d+\.\d+\.',
                                    norm_spaces(cur_lines[-1]['text'])))):
            force_new = False
        if cur_lines and (force_new or (gap is not None and gap > 2.0)):
            flush()
        cur_lines.append(o)
        cur_kind = kind if cur_kind is None else cur_kind
        prev_bottom = o['y1']
    flush()

    # Insert the table flowable immediately after its caption.
    out = []
    for b in blocks:
        out.append(b)
        if b['type'] == 'caption' and page_no in TABLE_REGIONS:
            out.append({'type':'table','table':TABLE_REGIONS[page_no][2], 'page':page_no,
                        'caption':b['text']})
    return out

body_blocks = []
for p in range(11,26):
    body_blocks.extend(parse_body_page(p))

# ---------------------------------------------------------------------------
# Source inventory for quality control
# ---------------------------------------------------------------------------
inventory = {
    'source_pages': len(src),
    'source_text_chars': sum(len(p.get_text('text')) for p in src),
    'source_page_blocks': {},
    'tables': {k:{'rows':len(v),'cols':max(len(r) for r in v)} for k,v in tables.items()},
    'cover_images': 3,
    'toc_source_entries': len(toc_source),
    'figure_entries': len(list_figures),
    'table_entries': len(list_tables),
    'annex_table_entries': len(annex_tables),
    'body_blocks': len(body_blocks),
    'body_block_types': dict(Counter(b['type'] for b in body_blocks)),
}
for pno in range(1,26):
    inventory['source_page_blocks'][str(pno)] = len([b for b in source_blocks(pno) if b[4].strip()])

content = {
    'design': DESIGN,
    'cover': cover,
    'front': front,
    'toc_source': toc_source,
    'list_figures': list_figures,
    'list_tables': list_tables,
    'annex_tables': annex_tables,
    'tables': tables,
    'body_blocks': body_blocks,
    'inventory': inventory,
}
json.dump(content, open('work/content.json','w'), ensure_ascii=False, indent=1)

# Human-readable inventory
with open('work/inventaire_source.txt','w') as f:
    f.write('INVENTAIRE EXHAUSTIF DU DOCUMENT SOURCE\n')
    f.write('======================================\n\n')
    f.write(f'Pages source : {inventory["source_pages"]}\n')
    f.write(f'Caractères de texte extraits : {inventory["source_text_chars"]}\n')
    f.write(f'Images de couverture : {inventory["cover_images"]}\n')
    f.write(f'Entrées de la table des matières source : {inventory["toc_source_entries"]}\n')
    f.write(f'Entrées de la liste des figures : {inventory["figure_entries"]}\n')
    f.write(f'Entrées de la liste des tableaux : {inventory["table_entries"]}\n')
    f.write(f'Entrées des tableaux d\'annexes : {inventory["annex_table_entries"]}\n')
    f.write(f'Blocs sémantiques du corps : {inventory["body_blocks"]}\n')
    f.write(f'Types de blocs : {inventory["body_block_types"]}\n\n')
    f.write('Tableaux conservés (lignes × colonnes) :\n')
    for k,v in inventory['tables'].items():
        f.write(f'  {k}: {v["rows"]} × {v["cols"]}\n')
    f.write('\nTitres et sous-titres détectés dans le corps :\n')
    for b in body_blocks:
        if b['type'].startswith('h'):
            f.write(f'  p.{b["page"]:02d} H{b["level"]}  {b["text"]}\n')
print(json.dumps(inventory, ensure_ascii=False, indent=1))
print('figure entries', len(list_figures), [e['text'][:40] for e in list_figures[:3]])
print('list tables', len(list_tables), 'annex', len(annex_tables))
print('toc entries', len(toc_source), toc_source[:3], toc_source[-3:])
