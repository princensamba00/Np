#!/usr/bin/env python3
import re
"""Extraction sans perte des éléments graphiques et tabulaires du segment 26-55.

- Figures bitmap : image native extraite du PDF (aucune modification de pixels).
- Tableaux vectoriels : cellules exactes (mots assignés au centre de chaque cellule)
  + couleur de fond de chaque cellule (information de classification vert/jaune/rouge).
- Encadrés « À retenir » et bandeaux d'indicateurs : bornes + texte natif.
"""
import json, os, io, collections
import pymupdf as fitz
from PIL import Image

ROOT = '/home/user/Np'
WORK = os.path.join(ROOT, 'work')
ASSETS = os.path.join(WORK, 'assets')
os.makedirs(ASSETS, exist_ok=True)
DOC = fitz.open(os.path.join(WORK, 'candidates', 'source_suite.pdf'))

# Couleurs de fond source -> couleurs de la charte (sémantique conservée)
FILL_MAP = {
    (0.79, 0.83, 0.87): '#DCE3EC',   # lignes alternées bleu-gris
    (0.96, 0.97, 0.98): '#F4F8FC',   # lignes claires
    (0.98, 0.88, 0.88): '#FBE3E3',   # rouge pâle
    (0.97, 0.82, 0.82): '#F7D3D3',   # rouge pâle foncé
    (0.89, 0.96, 0.91): '#DCEFE1',   # vert pâle
    (0.83, 0.93, 0.86): '#D3ECD9',   # vert pâle
    (1.0, 0.96, 0.8):   '#FFF2CC',   # jaune pâle
    (0.99, 0.93, 0.71): '#FCEBC0',   # jaune pâle
    (0.04, 0.16, 0.28): '#131D44',   # en-tête navy
    (0.06, 0.21, 0.36): '#1B3559',
    (0.08, 0.29, 0.43): '#24496E',
    (0.12, 0.31, 0.47): '#1F4E79',
    (0.92, 0.94, 0.97): '#EAF0F7',
    (0.82, 0.87, 0.92): '#D1DEEF',
    (1.0, 1.0, 1.0):    '#FFFFFF',
}


def nearest_fill(rgb):
    if rgb is None: return None
    key = tuple(round(float(v), 2) for v in rgb)
    if key in FILL_MAP: return FILL_MAP[key]
    best, bd = None, 9e9
    for k, v in FILL_MAP.items():
        d = sum((a-b)**2 for a, b in zip(key, k))
        if d < bd: best, bd = v, d
    return best


def fill_of_cells(page, cells):
    """Couleur dominante des rectangles de fond contenus dans chaque cellule."""
    drawings = page.get_drawings()
    rects = []
    for dr in drawings:
        f = dr.get('fill')
        if not f: continue
        r = dr['rect']
        if r.width < 3 or r.height < 2: continue
        rects.append((r, nearest_fill(f)))
    out = []
    for c in cells:
        if c is None:
            out.append(None); continue
        cr = fitz.Rect(c)
        votes = collections.Counter()
        for r, col in rects:
            # centre du rectangle dans la cellule
            cx, cy = (r.x0+r.x1)/2, (r.y0+r.y1)/2
            if cr.x0-0.6 <= cx <= cr.x1+0.6 and cr.y0-0.6 <= cy <= cr.y1+0.6:
                if r.width >= cr.width*0.55 and r.height >= cr.height*0.45:
                    votes[col] += 1
        out.append(votes.most_common(1)[0][0] if votes else None)
    return out


def cell_text(page, rect):
    """Texte exact de la cellule : get_text(clip=...) préserve tous les espaces."""
    txt = page.get_text('text', clip=rect)
    parts = [l.strip() for l in txt.splitlines() if l.strip()]
    out = ''
    for part in parts:
        if not out:
            out = part
        elif out[-1:] in ('-', '–', '‑') and part[:1].islower():
            out += part            # césure de fin de ligne du document source
        else:
            out += ' ' + part
    return re.sub(r'\s+', ' ', out).strip()


def extract_table(page, table):
    rows, fills = [], []
    # Largeurs de colonnes natives : elles préservent les proportions du
    # tableau source (notamment les colonnes étroites de pourcentages).
    src_widths = []
    for c in table.rows[0].cells:
        src_widths.append(round(c[2]-c[0], 1) if c else 0.0)
    if not any(src_widths):
        src_widths = [round((table.bbox[2]-table.bbox[0])/table.col_count, 1)] * table.col_count
    for ri in range(table.row_count):
        cells = table.rows[ri].cells
        row = []
        for c in cells:
            if c is None:
                row.append(''); continue
            cr = fitz.Rect(c)
            # Marge latérale seulement : agrandir verticalement ferait entrer
            # l'ascendante de la ligne suivante (ex. le « f » de « Difficultés »
            # capté dans « Saturation de l'hôpital de référence f »).
            cr.x0 -= 0.4; cr.x1 += 0.4
            cr.y0 += 0.8; cr.y1 -= 0.8
            row.append(cell_text(page, cr))
        rows.append(row)
        fills.append(fill_of_cells(page, cells))
    return {'rows': rows, 'fills': fills, 'col_widths': src_widths,
            'bbox': [round(v, 1) for v in table.bbox],
            'n_rows': table.row_count, 'n_cols': table.col_count}


def main():
    out = {'figures': {}, 'tables': {}, 'kpi_regions': {}, 'box_regions': {}}
    for i, page in enumerate(DOC):
        pno = i + 1
        # --- figures bitmap natives ---
        for im in page.get_images(full=True):
            xref = im[0]
            for r in page.get_image_rects(xref):
                if r.width < 100 or r.height < 40: continue
                info = DOC.extract_image(xref)
                raw = info['image']
                try:
                    img = Image.open(io.BytesIO(raw)).convert('RGB')
                except Exception:
                    continue
                fn = os.path.join(ASSETS, f'suite_fig_p{pno:02d}_x{xref}.png')
                img.save(fn, 'PNG')
                out['figures'].setdefault(str(pno), []).append({
                    'path': f'work/assets/suite_fig_p{pno:02d}_x{xref}.png',
                    'width': img.width, 'height': img.height,
                    'bbox': [round(v, 1) for v in r], 'xref': xref,
                })
        # --- tableaux vectoriels ---
        try:
            found = page.find_tables(strategy='lines_strict')
        except Exception:
            found = []
        tabs = []
        for t in found.tables:
            if t.row_count < 2 or t.col_count < 2: continue
            tabs.append(extract_table(page, t))
        if tabs:
            out['tables'][str(pno)] = tabs
        # --- encadrés « À retenir » (fond bleu clair de grande hauteur) ---
        boxes = []
        for dr in page.get_drawings():
            f = dr.get('fill'); r = dr['rect']
            if not f: continue
            if r.width > 430 and r.height > 55 and r.y0 < 700:
                rgb = tuple(round(float(v), 2) for v in f)
                if rgb in ((0.82, 0.87, 0.92), (0.92, 0.94, 0.97), (0.79, 0.83, 0.87)):
                    boxes.append([round(v, 1) for v in r])
        if boxes:
            # garder le plus grand par page (les autres sont des sous-rectangles)
            boxes.sort(key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
            out['box_regions'][str(pno)] = boxes[0]
        # --- bandeaux KPI (rects navy/teal en bas de page) ---
        kpis = []
        for dr in page.get_drawings():
            f = dr.get('fill'); r = dr['rect']
            if not f: continue
            rgb = tuple(round(float(v), 2) for v in f)
            if r.width > 70 and 50 < r.height < 90 and r.y0 > 690 and rgb[2] > rgb[0]:
                kpis.append([round(v, 1) for v in r])
        if kpis:
            kpis.sort(key=lambda b: b[0])
            # déduire les sous-rectangles
            uniq = []
            for b in kpis:
                if not uniq or abs(b[0]-uniq[-1][0]) > 5: uniq.append(b)
            out['kpi_regions'][str(pno)] = uniq
    json.dump(out, open(os.path.join(WORK, 'suite_assets.json'), 'w'),
              ensure_ascii=False, indent=1)
    print('figures:', sum(len(v) for v in out['figures'].values()),
          'pages avec tableaux:', len(out['tables']),
          'total tableaux:', sum(len(v) for v in out['tables'].values()))
    print('encadrés:', out['box_regions'])
    print('bandeaux KPI:', {k: len(v) for k, v in out['kpi_regions'].items()})
    for k, v in out['tables'].items():
        print('  p%s:' % k, [(t['n_rows'], t['n_cols']) for t in v])


if __name__ == '__main__':
    main()
