#!/usr/bin/env python3
"""Extraction exhaustive du segment source 26-55 et du nouveau modèle Md_ref.

Produit des transcripts texte / blocs / dictionnaires / styles / dessins / images
et des rendus PNG de toutes les pages. Aucune information n'est écartée :
les transcripts bruts servent de référence pour le contrôle intégral.
"""
import json
import os
import collections
import pymupdf as fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work")
RENDERS = os.path.join(WORK, "renders")
os.makedirs(RENDERS, exist_ok=True)

SRC = os.path.join(WORK, "candidates", "source_suite.pdf")
REF = os.path.join(WORK, "candidates", "Md_ref_nouveau.pdf")


def bytes_to_hex(o):
    if isinstance(o, bytes):
        return {"__hex__": o.hex()}
    if isinstance(o, dict):
        return {k: bytes_to_hex(v) for k, v in o.items()}
    if isinstance(o, list):
        return [bytes_to_hex(v) for v in o]
    return o


def dump_pages(doc, prefix, dpi=150, hi_dpi=200):
    text_lines = []
    block_lines = []
    dict_obj = {"pages": []}
    span_lines = []
    drawing_lines = []
    image_lines = []
    font_counter = collections.Counter()
    size_counter = collections.Counter()
    color_counter = collections.Counter()
    page_size_lines = []
    pixmaps = []

    for i, page in enumerate(doc):
        pno = i + 1
        rect = page.rect
        page_size_lines.append(f"page {pno:02d}: {rect.width:.4f} x {rect.height:.4f}")
        txt = page.get_text("text")
        text_lines.append(f"\n{'=' * 90}\nPAGE {pno:02d} — {len(txt)} CARACTÈRES\n{'=' * 90}\n{txt}")
        blocks = page.get_text("blocks", sort=False)
        block_lines.append(f"\n{'=' * 90}\nPAGE {pno:02d} — {len(blocks)} BLOCS (ordre natif)\n{'=' * 90}")
        for j, b in enumerate(blocks):
            x0, y0, x1, y1, content, bno, btype = b[:7]
            block_lines.append(
                f"[b{j:03d} no={bno} type={btype} bbox=({x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f})] "
                f"{content!r}"
            )
        d = page.get_text("dict")
        dict_obj["pages"].append(bytes_to_hex(d))
        span_lines.append(f"\n{'=' * 90}\nPAGE {pno:02d} — SPANS\n{'=' * 90}")
        for b in d.get("blocks", []):
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    f = s.get("font", "")
                    sz = round(float(s.get("size", 0)), 2)
                    col = int(s.get("color", 0)) & 0xFFFFFF
                    font_counter[f] += len(s.get("text", ""))
                    size_counter[sz] += len(s.get("text", ""))
                    color_counter[f"0x{col:06x}"] += len(s.get("text", ""))
                    span_lines.append(
                        f"y={s['bbox'][1]:7.2f} x={s['bbox'][0]:7.2f} "
                        f"size={sz:5.2f} color=0x{col:06x} flags={s.get('flags', 0):3d} "
                        f"font={f!r} | {s.get('text', '')!r}"
                    )
        drawings = page.get_drawings()
        drawing_lines.append(f"\nPAGE {pno:02d} — {len(drawings)} DESSINS")
        for j, dr in enumerate(drawings):
            drawing_lines.append(
                f"  d{j:03d} rect={tuple(round(v, 1) for v in dr.get('rect', ()))} "
                f"fill={dr.get('fill')} stroke={dr.get('color')} width={dr.get('width')} "
                f"items={len(dr.get('items', []))} close={dr.get('closePath')}"
            )
        imgs = page.get_images(full=True)
        image_lines.append(f"PAGE {pno:02d} — {len(imgs)} IMAGES")
        for im in imgs:
            xref, smask, w, h, bpc, cs, alt, name, filt = im[:9]
            image_lines.append(
                f"  xref={xref} smask={smask} {w}x{h} bpc={bpc} cs={cs} filter={filt} name={name}"
            )
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        pixmaps.append((pno, pix))

    with open(os.path.join(WORK, f"{prefix}_src_text.txt" if prefix == "suite" else f"{prefix}_text.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(text_lines))
    with open(os.path.join(WORK, f"{prefix}_blocks.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(block_lines))
    with open(os.path.join(WORK, f"{prefix}_dict.json"), "w", encoding="utf-8") as f:
        json.dump(dict_obj, f, ensure_ascii=False)
    with open(os.path.join(WORK, f"{prefix}_spans.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(span_lines))
    with open(os.path.join(WORK, f"{prefix}_drawings.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(drawing_lines))
    with open(os.path.join(WORK, f"{prefix}_images.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(image_lines))
    with open(os.path.join(WORK, f"{prefix}_stats.txt"), "w", encoding="utf-8") as f:
        f.write("DIMENSIONS\n" + "\n".join(page_size_lines) + "\n\nPOLICES (caractères)\n")
        for k, v in font_counter.most_common():
            f.write(f"{k}\t{v}\n")
        f.write("\nTAILLES (caractères)\n")
        for k, v in sorted(size_counter.items(), key=lambda kv: -kv[1]):
            f.write(f"{k}\t{v}\n")
        f.write("\nCOULEURS (caractères)\n")
        for k, v in color_counter.most_common(40):
            f.write(f"{k}\t{v}\n")
        f.write("\nDESSINS — remplissages\n")
        fills = collections.Counter()
        strokes = collections.Counter()
        for line in drawing_lines:
            if " fill=" in line:
                seg = line.split(" fill=")[1].split(" stroke=")[0]
                fills[seg] += 1
                st = line.split(" stroke=")[1].split(" width=")[0]
                strokes[st] += 1
        for k, v in fills.most_common(30):
            f.write(f"fill {k}\t{v}\n")
        f.write("\nDESSINS — traits\n")
        for k, v in strokes.most_common(30):
            f.write(f"stroke {k}\t{v}\n")

    # rendus
    for pno, pix in pixmaps:
        pix.save(os.path.join(RENDERS, f"{prefix}_p{pno:02d}.png"))
    # planche contact
    from PIL import Image, ImageOps, ImageDraw
    thumbs = []
    for pno, pix in pixmaps:
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        im.thumbnail((300, 424))
        canvas = Image.new("RGB", (320, 454), "white")
        canvas.paste(im, ((320 - im.width) // 2, 10))
        ImageDraw.Draw(canvas).text((10, 435), f"{prefix} p{pno:02d}", fill="black")
        thumbs.append(canvas)
    cols = 5
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 320, rows * 454), (235, 235, 235))
    for k, t in enumerate(thumbs):
        sheet.paste(t, ((k % cols) * 320, (k // cols) * 454))
    sheet.save(os.path.join(RENDERS, f"{prefix}_contact.png"))
    print(f"{prefix}: {len(pixmaps)} pages rendues, {len(span_lines)} lignes de spans, "
          f"{sum(font_counter.values())} caractères")
    return dict_obj


if __name__ == "__main__":
    src = fitz.open(SRC)
    ref = fitz.open(REF)
    print("source suite:", len(src), "pages | modèle:", len(ref), "pages")
    dump_pages(src, "suite", dpi=150)
    dump_pages(ref, "ref2", dpi=110)
    # rendus haute définition du source pour les graphiques
    for i, page in enumerate(src):
        pix = page.get_pixmap(dpi=220, alpha=False)
        pix.save(os.path.join(RENDERS, f"suite_hi_p{i+1:02d}.png"))
    print("rendus haute définition 220 dpi écrits")
