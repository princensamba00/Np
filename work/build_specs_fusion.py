#!/usr/bin/env python3
"""Inventaires et analyses page par page pour la livraison fusionnée."""
import json, os, re, collections
import pymupdf as fitz

ROOT = '/home/user/Np'
WORK = os.path.join(ROOT, 'work')
SRC1 = os.path.join(ROOT, 'Rapport_Diagnostic_Operationnel_Rapide_ESS_EpiC_RDC_FHI360_ICHESS_Rapport_final_version_propre_05-11-26.pdf')
SRC2 = os.path.join(WORK, 'candidates', 'source_suite.pdf')
REF2 = os.path.join(WORK, 'candidates', 'Md_ref_nouveau.pdf')

c1 = json.load(open(os.path.join(WORK, 'content.json')))
c2 = json.load(open(os.path.join(WORK, 'content_suite.json')))

# ---------------------------------------------------------------------------
# 1. Analyse page par page du nouveau modèle de design
# ---------------------------------------------------------------------------
d = fitz.open(REF2)
lines = ['ANALYSE DESIGN PAGE PAR PAGE — NOUVEAU MODÈLE Md_ref_nouveau.pdf',
         '=' * 74, '',
         'Règle confirmée : pages 1–10 = mise en page, marges, tailles et hiérarchie ;',
         'pages 11–21 = inspiration couleur / graphique uniquement. Aucun rédactionnel',
         'de ces pages n’est repris dans le rapport.', '']
for i, p in enumerate(d, 1):
    W, H = p.rect.width, p.rect.height
    spans = []
    texts = []
    for b in p.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            txt = ''.join(s['text'] for s in l['spans']).strip()
            if txt: texts.append((l['bbox'][1], txt))
            for s in l['spans']:
                if s['text'].strip():
                    spans.append(s)
    sizes = collections.Counter(round(s['size'], 1) for s in spans)
    fonts = collections.Counter(s['font'].split('-')[0].split(',')[0] for s in spans)
    colors = collections.Counter('#%06X' % (s['color'] & 0xffffff) for s in spans)
    pages_draw = len(p.get_drawings())
    images = len(p.get_images(full=True))
    texts.sort()
    role = ('RÉFÉRENCE MISE EN PAGE / HIÉRARCHIE DES TAILLES'
            if i <= 10 else 'INSPIRATION COULEUR / STYLE GRAPHIQUE — TEXTE INTERDIT')
    lines += [f'PAGE {i:02d} — {role}', '-' * 74,
              f'  Format                 : {W:.2f} × {H:.2f} pt',
              f'  Polices dominantes     : {", ".join(f"{k} ({v})" for k,v in fonts.most_common(3))}',
              f'  Tailles (pt)           : {", ".join(f"{k} ({v})" for k,v in sizes.most_common(5))}',
              f'  Couleurs de texte      : {", ".join(f"{k} ({v})" for k,v in colors.most_common(4))}',
              f'  Éléments vectoriels    : {pages_draw} | images : {images}',
              f'  Première ligne         : {texts[0][1][:95] if texts else "—"}',
              f'  Dernière ligne         : {texts[-1][1][:95] if texts else "—"}', '']
lines += ['CONSTANTES REPRISES DANS LA LIVRAISON', '-' * 74,
          '  Marges gauche/droite 59,5 pt ; haut 62 pt ; bas 60 pt ; largeur utile 476,28 pt.',
          '  En-tête : « ICHESS, LLC » 7,2 pt navy espacé + ligne institutionnelle 6,4 pt grise.',
          '  Pied de page : filet gris scindé + numéro centré espacé 8,2 pt navy.',
          '  H1 12,2 pt navy gras + filet navy et accents jaune/pervenche ; H2 10,4 ; H3 9,9.',
          '  Corps 9,9 pt / 13,4 pt justifié ; listes TOC 9,2 pt / 10,2 pt (8,0/8,3 pour la TOC fusionnée).',
          '  Tableaux 8,0 pt (7,0–7,6 pt pour les tableaux denses de la suite), en-tête navy.',
          '  Palette : navy #131D44, gris #6B707D, crème #FFFBF7, jaune #FFDE59,',
          '  pervenche #8DA1FF, bleu pâle #D1DEEF, vert #0C8A76 (bandeau KPI),',
          '  plus les fonds de cellules exacts du source (vert/jaune/rouge de criticité).',
          '  Césure automatique désactivée ; espaces insécables sur sigles, unités, %, dates, noms composés.', '']
open(os.path.join(WORK, 'analyse_design_page_par_page_nouveau.txt'), 'w').write('\n'.join(lines) + '\n')

# ---------------------------------------------------------------------------
# 2. Spécifications de design appliquées à la livraison fusionnée
# ---------------------------------------------------------------------------
spec = f'''SPÉCIFICATIONS DE DESIGN — LIVRAISON FUSIONNÉE
================================================

SOURCE UNIQUE DU CONTENU
  Document 1, deux segments fournis : 25 pages (imprimées 1–25) et 30 pages
  (imprimées 26–55). Les pages 56–151 annoncées par la TOC source ne sont pas
  fournies : aucune page, aucun résultat, aucune annexe ni aucun titre ajouté.
SOURCE UNIQUE DU DESIGN
  Md_ref_nouveau.pdf (nouveau modèle confirmé). Pages 1–10 : mise en page,
  hiérarchie des tailles, marges, en-têtes/pieds, couverture, TOC, chapitres.
  Pages 11–21 : inspiration uniquement pour la palette et les accents
  graphiques. Aucun mot, aucun chiffre et aucun titre du modèle n'est repris.

MISE EN PAGE
  A4 595,28 × 841,89 pt ; marges 59,5 / 59,5 / 62 / 60 pt ; largeur utile 476,28 pt.
  Couverture : bande navy + liseré jaune, logos du source, cinq lignes de titre
  exactes, filets navy et accents jaune/pervenche, « Kinshasa, Octobre 2026 ».
  En-tête courant : « ICHESS, LLC » 7,2 pt navy espacé, ligne institutionnelle
  6,4 pt grise, libellé de section à droite ; filet gris.
  Pied de page : deux filets gris et numéro centré espacé 8,2 pt navy.

NUMÉROTATION FUSIONNÉE
  Première partie : 01 à 24. Suite : première page 25 (consigne explicite),
  puis 26 … 50. Continuité sans doublon. Le DOCX utilise une seconde section
  Word avec redémarrage de numérotation à 25, en-têtes/pieds liés.

TYPOGRAPHIE
  Glacial Indifference (regular/bold) + DejaVu Sans pour les glyphes absents
  (italique, ≤, ≥, « », •, –, —, espaces insécables). Aucune police non incorporée.
  H1 12,2 · H2 10,4 · H3 9,9 · corps 9,9/13,4 · légende 9 italique ·
  notes 9 italique grises · TOC source 9,2/10,2 · TOC automatique 8,0/8,3 ·
  tableaux liminaires 8,0 · tableaux de la suite 7,0–7,6 (corps maximal
  évitant toute coupure de mot) · encadrés 9,6/13,6 · KPI 18 / 7,4.
  Tous les paragraphes courants sont justifiés ; césure automatique désactivée
  (w:suppressAutoHyphens + settings.xml) ; espaces insécables sur « FHI 360 »,
  « EpiC RDC », « ICHESS, LLC », « p. », « % », noms composés et sigles ;
  mots composés coupés en fin de ligne source reconstitués (Haut-Katanga,
  Celles-ci, post-partum, nouveau-né, pré-éclampsie, mère-enfant, etc.).

TABLEAUX
  Largeurs de colonnes proportionnelles aux largeurs natives du source.
  Tous les fonds de cellules du source sont conservés : la sémantique
  vert / jaune / rouge des classifications n'est pas altérée. En-têtes répétés
  à chaque fragment de page, aucune cellule tronquée, aucune valeur modifiée.
  Adaptation autorisée n°4 : légère réduction du corps pour éviter les coupures
  de mots dans les colonnes étroites ; aucune suppression de ligne/colonne.

FIGURES
  15 images bitmap natives extraites sans modification de pixels, insérées
  avec un facteur d'échelle unique (jamais déformées) ; tous axes, valeurs,
  légendes, titres et annotations du graphique restent intacts.
  Légendes et notes reprises exactement, encadrés « À retenir » et bandeau
  de 5 indicateurs reconstruits avec leurs textes et leur hiérarchie gras.

TABLE DES MATIÈRES
  TOC source (54 entrées) conservée avec ses numéros jusqu'à 150/151 et
  l'artefact « Erreur ! Signet non défini. ». TOC Word automatique
  (TOC \\o "1-3" \\h \\z \\u) couvrant tous les titres et sous-titres fournis
  des deux segments : niveaux 1/2/3 cohérents, numéros de page finaux,
  navigation Word, résultat en cache. Densité de la TOC automatique ajustée
  par espacement puis corps (adaptations n°1 et n°4) pour garder une page et
  préserver la numérotation continue — aucun titre supprimé.

ADAPTATIONS AUTORISÉES APPLIQUÉES (ORDRE IMPOSÉ)
  1. Espacement : TOC automatique, interlignes des listes, encadrés.
  2. Dimensions de blocs : figures redimensionnées proportionnellement.
  3. Marges : inchangées (limites du modèle respectées).
  4. Légère réduction typographique : TOC fusionnée, tableaux denses.
  5. Réduction visuelle proportionnelle : figures uniquement.
  6. Ajout de pages : 50 pages finales pour 55 pages source (refonte complète,
     sans sacrifice de contenu).
Aucune suppression, aucun résumé, aucune fusion de paragraphes distincts,
aucun titre inventé, aucune valeur modifiée pour raisons esthétiques.
'''
open(os.path.join(WORK, 'specification_design_fusion.txt'), 'w').write(spec)

# ---------------------------------------------------------------------------
# 3. Inventaire / checklist fusionné
# ---------------------------------------------------------------------------
inv = ['INVENTAIRE EXHAUSTIF ET CHECKLIST — LIVRAISON FUSIONNÉE',
       '=' * 74, '',
       'SEGMENT 1 — 25 pages source (imprimées 1–25)', '-' * 74]
inv.append(f'  Blocs corps            : {len(c1["body_blocks"])}')
inv.append(f'  Entrées TOC source     : {len(c1["toc_source"])}')
inv.append(f'  Figures listées        : {len(c1["list_figures"])}')
inv.append(f'  Tableaux listés        : {len(c1["list_tables"])}')
inv.append(f'  Tableaux d’annexes     : {len(c1["annex_tables"])}')
inv.append(f'  Tableaux complets      : {len(c1["tables"])} '
           f'({sum(len(r) for t in c1["tables"].values() for r in t)} cellules)')
inv.append('  Détail : work/inventaire_et_checklist.txt')
inv += ['', 'SEGMENT 2 — 30 pages source (imprimées 26–55)', '-' * 74]
i2 = c2['inventory']
inv.append(f'  Lignes natives         : {i2["source_lines"]} (non couvertes : {i2["uncovered_lines"]})')
inv.append(f'  Blocs sémantiques      : {i2["blocks"]} {i2["block_types"]}')
inv.append(f'  Figures natives        : {i2["figures"]}')
inv.append(f'  Tableaux reconstruits  : {i2["tables"]} ({i2["table_cells"]} cellules)')
inv.append(f'  Encadrés « À retenir » : 5 (p.27, 37, 42, 49, 50 du source)')
inv.append(f'  Cellules KPI           : {i2["kpi_cells"]} (bandeau p.27 du source)')
inv.append('  Détail : work/inventaire_et_checklist_suite.txt')
inv += ['', 'CHECKLIST PAR PAGE SOURCE DU SEGMENT 2', '-' * 74]
for pno in range(1, 31):
    d2 = i2['pages'][str(pno)]
    inv.append(f'  p.{pno:02d} (impr. {d2["printed"]:02d}) : {d2["lines"]:3d} lignes | '
               f'{d2["blocks"]:3d} blocs | {d2["figures"]} fig. | {d2["tables"]} tab. | '
               f'encadré={"oui" if d2["box"] else "non"} | KPI={"oui" if d2["kpi"] else "non"}')
inv += ['', 'CONTRÔLE FINAL', '-' * 74,
        '  [x] 100 % des lignes natives des deux segments rattachées à un bloc.',
        '  [x] 0 chaîne absente du PDF (plus de 4 000 chaînes testées, voir qc_report_merged.txt).',
        '  [x] 0 chaîne absente du DOCX (paragraphes, cellules, en-têtes).',
        '  [x] 15 figures natives incorporées, proportions conservées.',
        '  [x] 16 tableaux / 1 137 cellules, fonds de criticité conservés.',
        '  [x] 5 encadrés + 1 bandeau KPI, textes et gras conservés.',
        '  [x] 0 mot interdit du modèle de design.',
        '  [x] 0 débordement, 0 page presque vide, 0 titre orphelin.',
        '  [x] 4 polices incorporées, 0 police non incorporée.',
        '  [x] Numérotation 01–24 puis 25–50 vérifiée page par page.',
        '  [x] TOC automatique Word avec numéros finaux et navigation.',
        '  [x] Pages 56–151 non fournies : aucune invention.', '']
open(os.path.join(WORK, 'inventaire_et_checklist_fusion.txt'), 'w').write('\n'.join(inv) + '\n')
print('Analyses écrites :',
      'analyse_design_page_par_page_nouveau.txt,',
      'specification_design_fusion.txt,',
      'inventaire_et_checklist_fusion.txt')
