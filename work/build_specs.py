import fitz, json, re, collections, os
from fontTools.ttLib import TTFont

SRC = 'Rapport_Diagnostic_Operationnel_Rapide_ESS_EpiC_RDC_FHI360_ICHESS_Rapport_final_version_propre_05-11-26.pdf'
REF = 'Md_ref.pdf'
c = json.load(open('work/content.json'))
src = fitz.open(SRC); ref = fitz.open(REF)

NAVY = '#131D44'; CREAM = '#FFFBF7'; DOTTED = '#CED6F8'; GREY = '#6B707D'
RULE = '#D9D9D9'; YELLOW = '#FFDE59'; PERIWINKLE = '#8DA1FF'; MIDBLUE = '#5166B7'
RED = '#FF3131'; GREEN = '#00BF63'

# ---------------------------------------------------------------------------
# Page-by-page analysis of the design reference
# ---------------------------------------------------------------------------
def rgb(v):
    return f'#{int(v[0]*255):02X}{int(v[1]*255):02X}{int(v[2]*255):02X}'

def style_stats(page):
    counts = collections.Counter(); colors = collections.Counter(); sizes = collections.Counter()
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            for s in l['spans']:
                if not s['text'].strip(): continue
                counts[s['font']] += len(s['text'])
                colors[s['color']] += len(s['text'])
                sizes[round(s['size'],1)] += len(s['text'])
    fills = collections.Counter(); strokes = collections.Counter(); widths = collections.Counter()
    for d in page.get_drawings():
        if d.get('fill'): fills[rgb(d['fill'])] += 1
        if d.get('color'): strokes[rgb(d['color'])] += 1
        w = d.get('width') or 0
        widths[round(w,1)] += 1
    return counts, colors, sizes, fills, strokes, widths

qualitative = {
 1:"Préface recomposée : en-tête courant espacé, filet gris, titre navy, paragraphes justifiés, signature centrée en gras navy et sous-titre gris.",
 2:"Remerciements : même grille, même hiérarchie, signature centrée.",
 3:"Table des matières, première partie : titres gras, points de conduite bleu pâle, numéros navy alignés à droite, hiérarchie romaine / décimale.",
 4:"Table des matières, deuxième partie : suites des chapitres, bibliographie et annexes.",
 5:"Liste des figures et tableaux : deux sous-titres navy, filet navy sous chacun, points de conduite bleu pâle.",
 6:"Suite de la liste des tableaux et ouverture des tableaux d'annexes.",
 7:"Suite des tableaux d'annexes ; conserve l'artefact « Erreur ! Signet non défini. » et les numéros de page accolés.",
 8:"Fin des tableaux d'annexes (A64, p.151).",
 9:"Abréviations et acronymes : barre d'en-tête navy, lignes alternées crème, colonnes sans filets verticaux.",
 10:"Deuxième page des abréviations : répétition de l'en-tête de tableau, numérotation de page espacée.",
 11:"Gabarit générique : bande navy supérieure, grand titre centré, filet bas, coordonnées espacées. Aucun texte à reprendre.",
 12:"Page de résultats générique : donuts navy/jaune, grands chiffres, texte de remplissage. Couleurs et formes à titre d'inspiration uniquement.",
 13:"Cartes arrondies à contour noir, barres de progression navy/pervenche, typographie display.",
 14:"Diagramme en aires navy/bleu, axes gris, étiquettes en gras.",
 15:"Variante de mise en page avec cartes et pictogrammes.",
 16:"Variante de tableau de bord, même palette.",
 17:"Cartes arrondies, barres de progression et graphique en aires : style graphique secondaire.",
 18:"Grille de cartes et de pourcentages.",
 19:"Graphiques circulaires et indicateurs.",
 20:"Page de synthèse colorée, bandeaux et pictogrammes.",
 21:"Page de clôture du gabarit, bande navy et filet bas.",
}

with open('work/analyse_design_page_par_page.txt','w') as f:
    f.write('ANALYSE PAGE PAR PAGE DU MODÈLE DE DESIGN — Md_ref.pdf\n')
    f.write('Interprétation de la consigne utilisateur :\n')
    f.write('- Pages 1 à 10 : source exclusive de la mise en page, des marges, de la hiérarchie et des tailles de police.\n')
    f.write('- Pages 11 à 21 : source d’inspiration pour les couleurs, le style graphique et les accents décoratifs,\n')
    f.write('  sans reprise d’un seul mot de leur texte et sans modifier la hiérarchie typographique retenue.\n')
    f.write('- Le modèle est exclusivement une référence visuelle ; tout le contenu rédactionnel vient du DOCUMENT 1.\n\n')
    for n in range(1,22):
        p = ref[n-1]
        counts, colors, sizes, fills, strokes, widths = style_stats(p)
        f.write(f'=== PAGE {n:02d} ===\n')
        f.write(f'Dimensions : {p.rect.width:.2f} × {p.rect.height:.2f} pt\n')
        f.write('Polices dominantes : ' + ', '.join(f'{k} ({v} car.)' for k,v in counts.most_common(4)) + '\n')
        f.write('Tailles dominantes : ' + ', '.join(f'{k} pt ({v} car.)' for k,v in sizes.most_common(5)) + '\n')
        f.write('Couleurs de texte : ' + ', '.join(f'#{v:06X} ({n} car.)' for v,n in colors.most_common(5)) + '\n')
        f.write('Fonds : ' + ', '.join(f'{k} ({v})' for k,v in fills.most_common(5)) + '\n')
        f.write('Filets : ' + ', '.join(f'{k} ({v})' for k,v in strokes.most_common(5)) + '\n')
        f.write('Épaisseurs : ' + ', '.join(f'{k} pt ({v})' for k,v in widths.most_common(5)) + '\n')
        f.write('Lecture : ' + qualitative.get(n,'Gabarit générique.') + '\n\n')

# ---------------------------------------------------------------------------
# Design specification
# ---------------------------------------------------------------------------
with open('work/specification_design.txt','w') as f:
    f.write('SPÉCIFICATION DE DESIGN — APPLICATION DE Md_ref.pdf AU DOCUMENT 1\n')
    f.write('=================================================================\n\n')
    f.write('1. Périmètre et règle d’exclusivité\n')
    f.write('   - Md_ref.pdf est le fichier confirmé comme modèle de design unique.\n')
    f.write('   - Pages 1–10 : mise en page, marges, hiérarchie, tailles de police, en-têtes, pieds de page.\n')
    f.write('   - Pages 11–21 : inspiration uniquement pour la palette et les accents graphiques.\n')
    f.write('   - Aucune phrase, aucun titre, aucun chiffre du modèle n’est transféré.\n')
    f.write('   - Le contenu rédactionnel provient exclusivement du PDF source de 25 pages.\n\n')
    f.write('2. Format et grille\n')
    f.write('   - A4 : 595,28 × 841,89 pt.\n')
    f.write('   - Marges gauche/droite : 59,5 pt. Marge haute : 62 pt. Marge basse : 60 pt.\n')
    f.write('   - Largeur utile : 476,3 pt.\n')
    f.write('   - En-tête courant à 35,6–42,8 pt : « I C H E S S , L L C » à gauche, rubrique à droite.\n')
    f.write('   - Filet gris #D9D9D9 sous l’en-tête, y = 48,5 pt, épaisseur 0,7 pt.\n')
    f.write('   - Pied de page : numéro à deux chiffres espacés, centré, navy, 8,2 pt.\n')
    f.write('   - Couverture : pas d’en-tête ni de pied de page ; bande navy et accents jaune/pervenche inspirés des pp.11–21.\n\n')
    f.write('3. Palette exacte relevée\n')
    f.write(f'   - Navy dominant        : {NAVY}  (0.075, 0.114, 0.267)\n')
    f.write(f'   - Gris typographique   : {GREY}   (0.420, 0.439, 0.490)\n')
    f.write(f'   - Gris de filet        : {RULE}   (0.851, 0.851, 0.851)\n')
    f.write(f'   - Bleu pâle conducteur : {DOTTED} (0.808, 0.839, 0.973)\n')
    f.write(f'   - Crème lignes paires  : {CREAM} (1.000, 0.984, 0.969)\n')
    f.write(f'   - Jaune accent         : {YELLOW} (1.000, 0.871, 0.349)\n')
    f.write(f'   - Pervenche accent     : {PERIWINKLE} (0.553, 0.631, 1.000)\n')
    f.write(f'   - Bleu moyen accent    : {MIDBLUE} (0.318, 0.400, 0.718)\n')
    f.write(f'   - Rouge / vert accent  : {RED} / {GREEN}\n')
    f.write('   - Texte courant : noir #000000 ; blanc #FFFFFF sur navy.\n\n')
    f.write('4. Typographie\n')
    f.write('   - Famille : Glacial Indifference (Regular et Bold), extraite de Md_ref.pdf et complétée par les TTF complets.\n')
    f.write('   - Corps : 9,9 pt, interligne 14,0 pt, justifié.\n')
    f.write('   - Titre de rubrique H1 : 12,2 pt gras navy, espacement de 0,6 pt, précédé d’un filet navy 0,9 pt.\n')
    f.write('   - Titre H2 : 10,4 pt gras navy.\n')
    f.write('   - Titre H3 : 9,9 pt gras navy.\n')
    f.write('   - Toc/listes : 9,4–10,4 pt ; numéros 10,6 pt gras navy.\n')
    f.write('   - En-tête courant : 7,2 pt espacé, gris/navy.\n')
    f.write('   - Pied de page : 8,2 pt gras navy espacé.\n')
    f.write('   - Légendes de tableaux : 9,0 pt italiques navy, alignées à gauche.\n')
    f.write('   - Césure automatique : désactivée globalement et par paragraphe.\n')
    f.write('   - Espaces insécables : appliqués aux sigles, dates et noms d’organismes composés.\n')
    f.write('   - Glyphes absents de Glacial (≤, ≥, «, », •) : repli DejaVu Sans, uniquement pour ces glyphes.\n\n')
    f.write('5. Tables et listes\n')
    f.write('   - En-tête de tableau : bande navy #131D44, texte blanc gras 8,0–8,4 pt, hauteur 25 pt.\n')
    f.write('   - Lignes : alternance blanc / crème #FFFBF7, filets horizontaux bleu pâle #CED6F8, 0,4 pt.\n')
    f.write('   - Pas de filets verticaux ; cellules justifiées à gauche, en-têtes répétés à chaque page.\n')
    f.write('   - Points de conduite : #CED6F8, 0,9 pt, espacement régulier.\n')
    f.write('   - Largeurs de colonnes proportionnées au contenu, sans déformation des valeurs.\n\n')
    f.write('6. Éléments inspirés des pages 11–21\n')
    f.write('   - Bande navy supérieure de couverture.\n')
    f.write('   - Minces accents jaune et pervenche sur la couverture et les séparateurs de chapitre.\n')
    f.write('   - Filets de section navy/pervenche, sans cartes arrondies ni graphiques inventés.\n')
    f.write('   - Aucun donut, aucune barre de progression et aucune courbe n’est créé : le document source de 25 pages n’en contient pas.\n\n')
    f.write('7. Règles d’adaptation autorisées\n')
    f.write('   1) espacement ; 2) dimensions des blocs ; 3) marges dans les limites du modèle ;\n')
    f.write('   4) légère réduction typographique ; 5) réduction proportionnelle des visuels ; 6) ajout de pages.\n')
    f.write('   Aucune suppression de contenu, aucune valeur modifiée, aucun titre inventé.\n')

# ---------------------------------------------------------------------------
# Exhaustive source inventory and checklist
# ---------------------------------------------------------------------------
with open('work/inventaire_et_checklist.txt','w') as f:
    f.write('INVENTAIRE EXHAUSTIF ET CHECKLIST DE CONTRÔLE — DOCUMENT 1\n')
    f.write('=========================================================\n')
    f.write('Portée confirmée par l’utilisateur : les 25 pages disponibles ; les pages suivantes seront fournies ultérieurement.\n')
    f.write('Le contrôle d’intégralité porte donc sur 100 % du contenu effectivement présent dans le PDF source.\n\n')
    inv = c['inventory']
    f.write(f'Pages source                         : {inv["source_pages"]}\n')
    f.write(f'Caractères de texte extraits         : {inv["source_text_chars"]}\n')
    f.write(f'Images de couverture                 : {inv["cover_images"]}\n')
    f.write(f'Entrées de table des matières        : {inv["toc_source_entries"]}\n')
    f.write(f'Entrées liste des figures            : {inv["figure_entries"]}\n')
    f.write(f'Entrées liste des tableaux           : {inv["table_entries"]}\n')
    f.write(f'Entrées tableaux d’annexes           : {inv["annex_table_entries"]}\n')
    f.write(f'Blocs sémantiques du corps           : {inv["body_blocks"]}\n')
    f.write(f'Types de blocs                       : {inv["body_block_types"]}\n\n')
    f.write('--- Par page source ---\n')
    page_notes = {
      1:'Couverture : titre en 5 lignes, date, logos USAID / EpiC / ICHESS.',
      2:'Préface : 7 paragraphes + signature en 2 lignes.',
      3:'Remerciements : 6 paragraphes + signature en 2 lignes.',
      4:'Table des matières, première page : 43 entrées.',
      5:'Table des matières, deuxième page : 11 entrées d’annexes.',
      6:'Liste des figures (21) et début liste des tableaux (1–20).',
      7:'Liste des tableaux (21–37) ; « Erreur ! Signet non défini. » ; tableaux A1–A26 ; numéros accolés.',
      8:'Tableaux d’annexes A27–A64 ; numéros accolés et retours à la ligne.',
      9:'Abréviations et acronymes, 42 lignes (Sigle / Signification).',
      10:'Abréviations et acronymes, 30 lignes, en-tête répété.',
      11:'Résumé exécutif, 1 titre + 4 sous-titres + 6 paragraphes.',
      12:'Résumé exécutif, 4 sous-titres + 5 paragraphes.',
      13:'Recommandations stratégiques, 1 sous-titre + paragraphes.',
      14:'I. Introduction + 1.1. Contexte et justification.',
      15:'1.2. Objectifs ; 1.2.1 ; 1.2.2 (5 puces) ; 1.2.3 ; Tableau 1.',
      16:'1.2.4 (6 puces) ; 1.3 ; 1.3.1 ; 1.3.2.',
      17:'II. Approche ; 2.1 ; 2.2 ; 2.2.1 ; Tableau 2 ; 2.2.2.',
      18:'2.3 ; 2.3.1 ; 2.3.2 ; 2.4 ; 2.4.1.',
      19:'2.4.2 ; 2.5 ; 2.6 ; 2.6.1.',
      20:'Tableau 3 (29 × 5) ; « Définitions et conventions de lecture ».',
      21:'Définitions ; 2.6.2. Algorithme de classification.',
      22:'Tableau 4 (9 × 3) ; suite de 2.6.2.',
      23:'Tableau 5 (13 × 5) ; suite.',
      24:'Tableau 6 (7 × 2) ; 2.7 ; 2.8.',
      25:'2.9. Considérations éthiques ; 2.10. Limites méthodologiques.',
    }
    for n in range(1,26):
        f.write(f'  [ ] p.{n:02d} | blocs PDF : {inv["source_page_blocks"][str(n)]:2d} | {page_notes.get(n,"")}\n')
    f.write('\n--- Couverture et pages liminaires : tous les éléments ---\n')
    f.write('  [ ] Titre couverture : ' + ' / '.join(c['cover']['title_lines']) + '\n')
    f.write('  [ ] Date couverture : ' + c['cover']['date'] + '\n')
    f.write('  [ ] Logos couverture : USAID, EpiC, ICHESS (3 images)\n')
    for key,v in c['front'].items():
        f.write(f'  [ ] {v["heading"]} : {len(v["paragraphs"])} paragraphes\n')
        for i,p in enumerate(v['paragraphs'],1): f.write(f'        {i:02d}. {p}\n')
        for s in v['signature']: f.write(f'        Signature : {s}\n')
    f.write('\n--- Table des matières source : 54 entrées, numéros conservés ---\n')
    for i,e in enumerate(c['toc_source'],1):
        f.write(f'  [ ] TOC {i:02d} | {e["text"]} | p. {e["page"]}\n')
    f.write('\n--- Liste des figures : 21 entrées ---\n')
    for i,e in enumerate(c['list_figures'],1):
        f.write(f'  [ ] FIG {i:02d} | {e["text"]} | p. {e["page"]}\n')
    f.write('\n--- Liste des tableaux : 37 entrées, artefact conservé ---\n')
    for i,e in enumerate(c['list_tables'],1):
        f.write(f'  [ ] TAB {i:02d} | {e["text"]} | {e["page"]}\n')
    f.write('\n--- Tableaux d’annexes : 64 entrées ---\n')
    for i,e in enumerate(c['annex_tables'],1):
        f.write(f'  [ ] ANX {i:02d} | {e["text"]} | p. {e["page"]}\n')
    f.write('\n--- Tableaux complets : toutes les cellules ---\n')
    for name,rows in c['tables'].items():
        f.write(f'  [ ] {name} : {len(rows)} lignes × {max(len(r) for r in rows)} colonnes\n')
        for ri,row in enumerate(rows):
            f.write(f'        L{ri:02d} | ' + ' | '.join(str(x) for x in row) + '\n')
    f.write('\n--- Corps du rapport : 141 blocs sémantiques ---\n')
    for i,b in enumerate(c['body_blocks'],1):
        tag = b['type'] + (str(b['level']) if b.get('level') else '')
        txt = b.get('text','') if 'text' in b else f'TABLE {b["table"]} — {b["caption"]}'
        f.write(f'  [ ] B{i:03d} | src p.{b["page"]:02d} | {tag:8s} | {txt}\n')
    f.write('\n--- Éléments techniques à vérifier ---\n')
    for item in [
        'Justification de tous les paragraphes de texte courant',
        'Césure automatique désactivée (document + paragraphes)',
        'Espaces insécables dans les sigles et noms composés',
        'Aucune coupure artificielle de nom propre / organisme / acronyme',
        'En-têtes de tableaux répétés à chaque page',
        'Aucune ligne, colonne, valeur ou note de tableau supprimée',
        'Aucun titre inventé ; hiérarchie H1/H2/H3 respectée',
        'Table des matières Word automatique et navigable',
        'Numéros de page du rendu final',
        'Contrôle visuel de toutes les pages rendues',
        'Absence de contenu rédactionnel de Md_ref.pdf',
        'Absence de page presque vide, de titre orphelin, de débordement',
        'Identité visuelle conforme à Md_ref.pdf',
    ]:
        f.write(f'  [ ] {item}\n')

print('wrote specification_design.txt, analyse_design_page_par_page.txt, inventaire_et_checklist.txt')
