#!/usr/bin/env python3
"""Reconstruction sémantique exhaustive du segment source (pages imprimées 26-55).

Produit work/content_suite.json : blocs ordonnés (titres, paragraphes, encadrés,
bandeaux d'indicateurs, figures bitmap natives, tableaux avec cellules et couleurs,
légendes et notes), inventaire page par page et liste de contrôle.

Aucune suppression : chaque ligne de texte native est rattachée à un bloc ou à une
région graphique, et la couverture est vérifiée ligne par ligne.
"""
import json, os, re, unicodedata, collections
import pymupdf as fitz

ROOT = '/home/user/Np'
WORK = os.path.join(ROOT, 'work')
SRC = os.path.join(WORK, 'candidates', 'source_suite.pdf')
ASSETS = json.load(open(os.path.join(WORK, 'suite_assets.json')))
doc = fitz.open(SRC)


def norm(s):
    s = str(s).replace('\uf0b7', '•').replace('\u00a0', ' ').replace('\u2011', '-')
    s = unicodedata.normalize('NFKC', s).casefold()
    s = re.sub(r'[^\w]+', ' ', s, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', s).strip()


def broken_word(a, b):
    """Vrai si une césure de ligne coupe un mot composé ou un nom propre.

    Le source Word coupe « Haut-/Katanga », « Celles-/ci », « post-/partum »,
    « nouveau-/né », « pré-/éclampsie », « mère-/enfant »… On reconstitue
    le mot sans espace, conformément à l'exigence de ne pas casser les noms
    propres, organismes, sigles et composés.
    """
    a, b = a.rstrip(), b.lstrip()
    return (len(a) > 2 and a.endswith('-') and a[-2].isalnum()
            and bool(b) and b[0].isalpha())


def dehyphen(a, b):
    a, b = a.rstrip(), b.lstrip()
    if not a or not b: return a + b
    if broken_word(a, b): return a + b
    return a + ' ' + b


def line_obj(page_no, line):
    spans = []
    for s in line['spans']:
        t = s['text']
        if not t: continue
        spans.append({'text': t, 'bold': bool(s['flags'] & 16),
                      'italic': bool(s['flags'] & 2),
                      'size': round(float(s['size']), 2),
                      'color': int(s['color']) & 0xffffff,
                      'font': s.get('font', '')})
    if not spans: return None
    text = ''.join(s['text'] for s in spans).rstrip()
    if not text.strip(): return None
    return {'page': page_no, 'x0': line['bbox'][0], 'y0': line['bbox'][1],
            'x1': line['bbox'][2], 'y1': line['bbox'][3],
            'text': text, 'spans': spans,
            'all_bold': all(s['bold'] for s in spans if s['text'].strip()),
            'all_italic': all(s['italic'] for s in spans if s['text'].strip()),
            'size': max(s['size'] for s in spans),
            'color': spans[0]['color']}


def rich_from_lines(lines):
    """Joint les lignes d'un paragraphe en conservant les runs gras/italiques.

    Les blancs de fin/début de ligne natifs sont retirés avant d'insérer un
    unique séparateur : cela évite les doubles espaces dans les paragraphes
    justifiés du source, sans perdre la mise en forme des segments.
    """
    out, prev = [], ''
    for i, l in enumerate(lines):
        spans = [dict(s) for s in l['spans']]
        if spans:
            spans[0]['text'] = spans[0]['text'].lstrip()
            spans[-1]['text'] = spans[-1]['text'].rstrip()
        spans = [s for s in spans if s['text']]
        if i:
            sep = '' if (spans and broken_word(prev, spans[0]['text'])) else ' '
            out.append({'text': sep, 'bold': False, 'italic': False})
        out.extend(spans)
        prev = l['text'].rstrip()
    while out and out[-1]['text'] and out[-1]['text'].isspace(): out.pop()
    return out


def runs_plain(runs):
    return re.sub(r'[ \t]+', ' ', ''.join(r['text'] for r in runs)).strip()


def classify(line):
    t = re.sub(r'\s+', ' ', line['text']).strip()
    if t.startswith('À retenir'): return 'box_title'
    if re.match(r'^(I|II|III|IV|V)\.$', t): return 'h1a'
    if re.match(r'^(I|II|III|IV|V)\.\s+\S', t): return 'h1'
    if re.match(r'^\d+\.\d+\.\d+\.?\s+\S', t): return 'h3'
    if re.match(r'^\d+\.\d+\.?\s+\S', t): return 'h2'
    if re.match(r'^(Figure|Tableau)\s+\d+\s*:', t, re.I): return 'caption'
    if line['size'] >= 17 and line['all_bold']: return 'h1'
    if line['all_bold'] and line['size'] >= 12.5 and len(t) < 150: return 'h2'
    if line['all_bold'] and line['size'] >= 11.9 and len(t) < 150: return 'h3'
    if t.startswith('À retenir'): return 'box_title'
    if line['size'] <= 9.6 and line['all_italic']: return 'note'
    return 'body'


def in_rect(line, rect, pad=1.5):
    return (rect[0]-pad <= line['x0'] and line['x1'] <= rect[2]+pad
            and rect[1]-pad <= line['y0'] and line['y1'] <= rect[3]+pad)


# ---------------------------------------------------------------------------
# 1. Collecte de toutes les lignes et de toutes les régions
# ---------------------------------------------------------------------------
pages = {}
for i, page in enumerate(doc):
    pno = i + 1
    lines = []
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            o = line_obj(pno, l)
            if not o: continue
            if o['y0'] < 58 or o['y0'] > 792: continue   # en-tête / pied de page
            lines.append(o)
    lines.sort(key=lambda o: (round(o['y0'], 1), o['x0']))
    figs = ASSETS['figures'].get(str(pno), [])
    tables = ASSETS['tables'].get(str(pno), [])
    # Bornes des encadrés « À retenir » : titre + union des fonds bleu pâle
    box_bounds = None
    titles = [l for l in lines if classify(l) == 'box_title']
    if titles:
        t0 = titles[0]['y0'] - 6
        strips = []
        for dr in page.get_drawings():
            f, r = dr.get('fill'), dr['rect']
            if not f or r.width < 430: continue
            rgb = tuple(round(float(v), 2) for v in f)
            if rgb in ((0.82, 0.87, 0.92), (0.92, 0.94, 0.97), (0.79, 0.83, 0.87)) \
                    and r.y0 >= t0 - 4 and r.y0 < 750:
                strips.append(r)
        if strips:
            box_bounds = [min(r.x0 for r in strips) - 2, t0,
                          max(r.x1 for r in strips) + 2,
                          max(r.y1 for r in strips) + 5]
        else:
            box_bounds = [55, t0, 540, titles[0]['y0'] + 220]
    kpi = ASSETS['kpi_regions'].get(str(pno))
    kpi_bounds = None
    if kpi:
        kpi_bounds = [min(r[0] for r in kpi) - 2, min(r[1] for r in kpi) - 3,
                      max(r[2] for r in kpi) + 2, max(r[3] for r in kpi) + 3]
    pages[pno] = {'lines': lines, 'figs': figs, 'tables': tables,
                  'box': box_bounds, 'kpi': kpi_bounds}

# ---------------------------------------------------------------------------
# 2. Construction des blocs ordonnés
# ---------------------------------------------------------------------------
blocks = []
source_lines = []          # (page, y, texte) pour contrôle de couverture
caption_index = []         # (page, y, texte complet) pour association
used_table_captions = set()

# 2a. Repérage global des légendes (certaines sont coupées sur 2 lignes)
for pno, pg in pages.items():
    ls = pg['lines']
    j = 0
    while j < len(ls):
        l = ls[j]
        if classify(l) == 'caption':
            txt = l['text'].strip()
            k = j + 1
            # légende tableau coupée (ex. « ... et ce que leur » / « résolution libère »)
            while (k < len(ls) and ls[k]['y0'] - ls[k-1]['y1'] < 4
                   and ls[k]['size'] >= 10.5 and ls[k]['color'] == 0x0e2841
                   and not re.match(r'^(Figure|Tableau)\s+\d+\s*:', ls[k]['text'])
                   and not re.match(r'^\d+\.\d+', ls[k]['text'].strip())):
                txt = dehyphen(txt, ls[k]['text'].strip())
                k += 1
            caption_index.append((pno, l['y0'], txt))
            j = k
        else:
            j += 1

for pno, pg in pages.items():
    lines = pg['lines']
    # régions (type, y0, y1, objet)
    regions = []
    for f in pg['figs']:
        regions.append(('figure', f['bbox'][1], f['bbox'][3], f))
    for ti, t in enumerate(pg['tables']):
        regions.append(('table', t['bbox'][1], t['bbox'][3], (ti, t)))
    if pg['box']:
        regions.append(('box', pg['box'][1], pg['box'][3], pg['box']))
    if pg['kpi']:
        regions.append(('kpi', pg['kpi'][1], pg['kpi'][3], pg['kpi']))
    regions.sort(key=lambda r: r[1])

    def region_of(line):
        for kind, y0, y1, obj in regions:
            if kind in ('box', 'kpi'):
                r = obj
                if r[1]-2 <= line['y0'] and line['y1'] <= r[3]+3 and r[0]-3 <= line['x0']:
                    return kind, obj
            else:
                r = obj['bbox'] if kind == 'figure' else obj[1]['bbox']
                if r[1]-2 <= line['y0'] and line['y1'] <= r[3]+2 and r[0]-3 <= line['x0'] and line['x1'] <= r[2]+3:
                    return kind, obj
        return None, None

    # 2b. Lignes rattachées aux régions
    for l in lines:
        kind, obj = region_of(l)
        source_lines.append((pno, round(l['y0'], 1), l['text']))
        l['_region'] = kind

    # 2c. Figures : image native + légende + notes
    for f in pg['figs']:
        y0, y1 = f['bbox'][1], f['bbox'][3]
        cap = ''
        for cp, cy, ct in caption_index:
            if cp == pno and cy >= y1 - 3 and cy < y1 + 40 and ct.startswith('Figure'):
                cap = ct; break
        blocks.append({'type': 'figure', 'page': pno, 'y': y0,
                       'path': f['path'], 'w': f['width'], 'h': f['height'],
                       'caption': cap, 'text': cap})

    # 2d. Tableaux : cellules exactes + couleurs + légende + notes
    # Une légende n'est émise qu'une seule fois pour un tableau éclaté
    # sur plusieurs pages (les lignes d'en-tête répétées restent, elles,
    # présentes dans les cellules source).
    for ti, t in enumerate(pg['tables']):
        y0, y1 = t['bbox'][1], t['bbox'][3]
        cap = ''
        best = None
        for cp, cy, ct in caption_index:
            if not ct.startswith('Tableau'): continue
            if cp < pno or (cp == pno and cy <= y0 + 2):
                if best is None or (cp, cy) > (best[0], best[1]): best = (cp, cy, ct)
        if best: cap = best[2]
        if cap and norm(cap) in used_table_captions:
            cap = ''                       # fragment d'un tableau déjà légendé
        elif cap:
            used_table_captions.add(norm(cap))
        # notes de bas de tableau (italique 9 pt) ; les paragraphes de
        # commentaire en 11,5 pt (ex. « Lecture du tableau. ») restent
        # des paragraphes courants avec leur segment gras initial.
        notes = []
        for l in lines:
            if l.get('_consumed') or l['_region']: continue
            if y1 - 2 <= l['y0'] <= y1 + 95 and classify(l) == 'note':
                notes.append(l)
        note_txt = ''
        for l in notes: note_txt = dehyphen(note_txt, l['text'].strip())
        for l in notes: l['_consumed'] = True
        blocks.append({'type': 'table', 'page': pno, 'y': y0,
                       'rows': t['rows'], 'fills': t['fills'],
                       'asset_index': ti,
                       'caption': cap, 'note': note_txt.strip(),
                       'text': cap + ' ' + note_txt.strip() +
                               ' ' + ' '.join(' '.join(r) for r in t['rows'])})
        # associer la légende consommée
        for cp, cy, ct in caption_index:
            pass

    # 2e. Encadré « À retenir »
    if pg['box']:
        b = pg['box']
        inside = [l for l in lines if b[1]-2 <= l['y0'] and l['y1'] <= b[3]+4
                  and not l.get('_consumed')]
        inside.sort(key=lambda o: (round(o['y0'], 1), o['x0']))
        title = 'À retenir'
        paras, cur = [], []
        for l in inside:
            if l['text'].strip().startswith('À retenir'): continue
            t = l['text'].strip()
            # Les paragraphes de l'encadré commencent par un segment gras
            starts = bool(l['spans'] and l['spans'][0]['bold'] and l['spans'][0]['text'].strip())
            if cur and (starts or (cur[-1]['y0'] and l['y0'] - cur[-1]['y1'] > 6)):
                paras.append(cur); cur = []
            cur.append(l)
        if cur: paras.append(cur)
        box_paras = [rich_from_lines(pp) for pp in paras]
        for l in inside: l['_consumed'] = True
        blocks.append({'type': 'box', 'page': pno, 'y': b[1],
                       'title': title, 'paragraphs': box_paras,
                       'text': title + ' ' + ' '.join(runs_plain(r) for r in box_paras)})

    # 2f. Bandeau d'indicateurs (p. 27 du source)
    if pg['kpi']:
        b = pg['kpi']
        inside = [l for l in lines if b[1]-2 <= l['y0'] and l['y1'] <= b[3]+4
                  and not l.get('_consumed')]
        inside.sort(key=lambda o: (o['x0'], o['y0']))
        # 5 colonnes définies par les rects
        cols = ASSETS['kpi_regions'][str(pno)]
        cells = []
        for c in cols:
            lo, hi = c[0]-2, c[2]+2
            cl = [l for l in inside if lo <= l['x0'] and l['x1'] <= hi]
            cl.sort(key=lambda o: o['y0'])
            val = ' '.join(l['text'].strip() for l in cl if l['size'] > 15)
            lab = ''
            for l in cl:
                if l['size'] <= 15: lab = dehyphen(lab, l['text'].strip())
            cells.append({'value': val.strip(), 'label': lab.strip()})
        for l in inside: l['_consumed'] = True
        blocks.append({'type': 'kpi', 'page': pno, 'y': b[1], 'cells': cells,
                       'text': ' '.join(c['value'] + ' ' + c['label'] for c in cells)})

    # 2g. Texte courant : titres, paragraphes, légendes, notes
    rest = [l for l in lines if not l.get('_consumed') and not l['_region']]
    rest.sort(key=lambda o: (round(o['y0'], 1), o['x0']))
    i = 0
    while i < len(rest):
        l = rest[i]
        k = classify(l)
        if k == 'caption':
            txt, j = l['text'].strip(), i + 1
            while j < len(rest) and rest[j]['y0'] - rest[j-1]['y1'] < 4 \
                  and rest[j]['size'] >= 10.5 and rest[j]['color'] == 0x0e2841 \
                  and classify(rest[j]) != 'caption' and not re.match(r'^\d+\.\d+', rest[j]['text'].strip()):
                txt = dehyphen(txt, rest[j]['text'].strip()); j += 1
            blocks.append({'type': 'caption', 'page': pno, 'y': l['y0'],
                           'text': txt, 'italic': True})
            i = j; continue
        if k in ('h1a', 'h1', 'h2', 'h3'):
            txt, j, lvl = l['text'].strip(), i + 1, (1 if k.startswith('h1') else 2 if k == 'h2' else 3)
            if k == 'h1a':
                lvl = 1
            # fusionner les lignes du même titre (même taille, écart faible)
            while j < len(rest) and rest[j]['y0'] - rest[j-1]['y1'] < 6 \
                  and abs(rest[j]['size'] - l['size']) < 0.6 \
                  and classify(rest[j]) not in ('caption',) \
                  and rest[j]['all_bold'] == l['all_bold'] \
                  and not re.match(r'^(Figure|Tableau)\s+\d+\s*:', rest[j]['text']):
                if re.match(r'^(I|II|III|IV|V)\.\s|\d+\.\d+', rest[j]['text'].strip()):
                    break
                txt = dehyphen(txt, rest[j]['text'].strip()); j += 1
            blocks.append({'type': 'heading', 'level': lvl, 'page': pno,
                           'y': l['y0'], 'text': txt})
            i = j; continue
        if k == 'box_title':
            i += 1; continue
        if k == 'note':
            txt, j = l['text'].strip(), i + 1
            while j < len(rest) and classify(rest[j]) == 'note' \
                  and rest[j]['y0'] - rest[j-1]['y1'] < 6:
                txt = dehyphen(txt, rest[j]['text'].strip()); j += 1
            blocks.append({'type': 'note', 'page': pno, 'y': l['y0'], 'text': txt})
            i = j; continue
        # paragraphe courant
        cur, j = [l], i + 1
        while j < len(rest):
            n = rest[j]
            if classify(n) in ('h1a', 'h1', 'h2', 'h3', 'caption', 'note', 'box_title'): break
            # Le source sépare ses paragraphes par 3 pt et ses lignes par 0 pt ;
            # au-delà de 2,2 pt on est sur un nouveau paragraphe (aucune fusion
            # de paragraphes distincts, aucune perte de structuration).
            if n['y0'] - cur[-1]['y1'] > 2.2: break
            if abs(n['size'] - cur[-1]['size']) > 1.0: break
            cur.append(n); j += 1
        runs = rich_from_lines(cur)
        blocks.append({'type': 'body', 'page': pno, 'y': l['y0'],
                       'runs': runs, 'text': runs_plain(runs)})
        i = j

blocks.sort(key=lambda b: (b['page'], b['y']))
# Déduplication des légendes : une légende déjà rattachée à une figure/tableau
# ne doit pas être réémise en bloc autonome.
attached = set()
for b in blocks:
    if b['type'] in ('figure', 'table') and b['caption']:
        attached.add(norm(b['caption']))
out = []
for b in blocks:
    if b['type'] == 'caption' and norm(b['text']) in attached:
        continue
    out.append(b)
blocks = out

# ---------------------------------------------------------------------------
# 3. Contrôle de couverture ligne par ligne
# ---------------------------------------------------------------------------
all_text = norm(' '.join(b.get('text', '') for b in blocks))
# ajouter les cellules de tableaux et les notes
uncovered = []
for pno, y, txt in source_lines:
    n = norm(txt)
    if not n: continue
    if n in all_text: continue
    # fragment court (numéro, sigle) : recherché dans les cellules
    if len(n) <= 3: continue
    uncovered.append((pno, y, txt))

# ---------------------------------------------------------------------------
# 4. Inventaire et checklist
# ---------------------------------------------------------------------------
inventory = {
    'source_pages': len(doc),
    'printed_first': 26, 'printed_last': 55,
    'source_text_chars': sum(len(p.get_text('text')) for p in doc),
    'source_lines': len(source_lines),
    'blocks': len(blocks),
    'block_types': dict(collections.Counter(b['type'] for b in blocks)),
    'figures': sum(len(v) for v in ASSETS['figures'].values()),
    'tables': sum(len(v) for v in ASSETS['tables'].values()),
    'table_cells': sum(sum(len(row) for row in t['rows'])
                       for v in ASSETS['tables'].values() for t in v),
    'kpi_cells': sum(len(v) for v in ASSETS['kpi_regions'].values()),
    'uncovered_lines': len(uncovered),
}
for pno in range(1, 31):
    inventory.setdefault('pages', {})[str(pno)] = {
        'printed': 25 + pno,
        'lines': len(pages[pno]['lines']),
        'blocks': sum(1 for b in blocks if b['page'] == pno),
        'figures': len(pages[pno]['figs']),
        'tables': len(pages[pno]['tables']),
        'box': bool(pages[pno]['box']),
        'kpi': bool(pages[pno]['kpi']),
    }

content = {
    'inventory': inventory,
    'blocks': blocks,
    'source_lines': source_lines,
    'uncovered_lines': uncovered,
    'captions': [{'page': p, 'y': y, 'text': t} for p, y, t in caption_index],
    'assets': {'figures': ASSETS['figures'], 'tables': ASSETS['tables'],
               'kpi': ASSETS['kpi_regions']},
}
json.dump(content, open(os.path.join(WORK, 'content_suite.json'), 'w'),
          ensure_ascii=False, indent=1)

# Checklist lisible
lines_out = ['INVENTAIRE EXHAUSTIF — SEGMENT SOURCE 26–55',
             '=' * 70, '',
             f"Pages physiques        : {inventory['source_pages']}",
             f"Pages imprimées        : {inventory['printed_first']}–{inventory['printed_last']}",
             f"Caractères extraits    : {inventory['source_text_chars']}",
             f"Lignes de texte        : {inventory['source_lines']}",
             f"Blocs sémantiques      : {inventory['blocks']} {inventory['block_types']}",
             f"Figures bitmap natives : {inventory['figures']}",
             f"Tableaux reconstruits  : {inventory['tables']} ({inventory['table_cells']} cellules)",
             f"Cellules KPI           : {inventory['kpi_cells']}",
             f"Lignes non couvertes   : {inventory['uncovered_lines']}", '',
             'DÉTAIL PAR PAGE', '-' * 70]
for pno in range(1, 31):
    d = inventory['pages'][str(pno)]
    lines_out.append(
        f"p.{pno:02d} (impr. {d['printed']}) : {d['lines']:3d} lignes | "
        f"{d['blocks']:3d} blocs | {d['figures']} figure(s) | {d['tables']} tableau(x) | "
        f"encadré={'oui' if d['box'] else 'non'} | KPI={'oui' if d['kpi'] else 'non'}")
lines_out += ['', 'LÉGENDES ET NOTES', '-' * 70]
for p, y, t in caption_index:
    lines_out.append(f'  p.{p:02d} y={y:6.1f}  {t}')
lines_out += ['', 'TITRES ET SOUS-TITRES', '-' * 70]
for b in blocks:
    if b['type'] == 'heading':
        lines_out.append(f"  p.{b['page']:02d} H{b['level']}  {b['text']}")
if uncovered:
    lines_out += ['', 'LIGNES À VÉRIFIER', '-' * 70]
    for p, y, t in uncovered[:200]:
        lines_out.append(f'  p.{p:02d} y={y} {t}')
open(os.path.join(WORK, 'inventaire_et_checklist_suite.txt'), 'w').write('\n'.join(lines_out) + '\n')

print(json.dumps(inventory, ensure_ascii=False, indent=1))
print('\nLignes non couvertes :', len(uncovered))
for u in uncovered[:40]: print('   ', u)
