# État des lieux — 19/11/2026

## Ce qui a été perdu lors de la réinitialisation du bac à sable

Le sandbox a été remis à l'état du commit `d6a735a` (livraison 50 pages).
Sont donc **détruits** (ils n'étaient pas versionnés) :

- `work/candidates/source_part3.pdf` — la source des pages imprimées 55–82 (28 p.) ;
- `work/extract_part3_assets.py`, `work/parse_part3.py`, `work/build_part3.py` ;
- `work/part3_assets.json` (19 tableaux + 6 figures), `work/content_part3.json` (118 blocs) ;
- `work/build_part3_layout.json` ;
- le PDF `..._Md_ref_fusion_complet.pdf` (**81 p.**, celui qui venait d'être corrigé) ;
- `work/renders/k_*.png`, `m_*.png`, `n_*.png` (contrôles visuels des pages 49–82).

## Ce qui est préservé

- `d6a735a` sur `origin/arena/ab65c571-np` : la livraison **50 pages** complète et conforme
  (`..._Md_ref_fusion.pdf` + `.docx`, `README_livraison_fusion.md`, `qc_report_merged.txt`).
- La source 25 pages `..._version_propre_05-11-26.pdf` (root) et la suite 26–55
  (`..._suite_26-55.pdf` + `work/candidates/source_suite.pdf`).
- `work/content.json`, `work/content_suite.json` et tout le moteur (layout, pdf, docx).

## Dernier état connu de la partie 3 (avant perte)

- 118 blocs, 0 ligne non couverte, 19 tableaux et 6 figures extraits.
- Dernier build : **81 p.**, numérotation 1…81 continue, paysage **71–73**
  (Tableau 30 complet en 3 pages après correctif de détection des filets).
- TOC régénérée : **100 entrées, 0 incohérence** (pages 5–6) + TOC source page 4.
- Signets : **101** (100 distincts), aucune cible invalide.
- Anomalies restantes au moment de la perte :
  1. Liste des figures/tableaux (pp. 7–8) : numéros de page codés en dur pour les
     tableaux 1–37 et figures 1–21, devenus faux après repagination ;
     le Tableau 29 affiche « Erreur ! Signet non défini. » (reproduit de la source).
  2. TOC source (p. 4) conserve les numéros de la version 151 pages : non
     corrigeable sans inventer, car elle décrit des sections (IV, V, annexes)
     dont le contenu n'a jamais été fourni.

## Pour reprendre

Il faut **re-fournir le PDF source des pages 55–82** (28 pages). Sans lui, la partie 3
ne peut pas être reconstruite : aucune page ne sera inventée.
