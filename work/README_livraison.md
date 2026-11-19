# Livraison — rapport de diagnostic opérationnel rapide

## Fichiers
- `Rapport_Diagnostic_Operationnel_Rapide_ESS_EpiC_RDC_FHI360_ICHESS_Md_ref_25pages.docx` — DOCX modifiable, styles Hiérarchie 1/2/3, TOC automatique.
- `Rapport_Diagnostic_Operationnel_Rapide_ESS_EpiC_RDC_FHI360_ICHESS_Md_ref_25pages.pdf` — PDF d'impression, 24 pages, polices incorporées.

## Portée
L'utilisateur a confirmé que le PDF de 25 pages est la portée actuelle et fournira les autres pages d'un document initial de 150/151 pages ultérieurement. Les deux livrables contiennent donc **100 % du contenu disponible** : couverture, préface, remerciements, table des matières source (54 entrées), listes de 21 figures / 37 tableaux / 64 tableaux d'annexes, 72 lignes d'abréviations, 8 tableaux complets, résumé exécutif, introduction et approche méthodologique jusqu'à « 2.10. Limites méthodologiques ». Les références de la TOC aux pages 26–151 sont conservées telles quelles ; aucune page absente n'a été inventée.

## Design
`Md_ref.pdf` a été confirmé comme modèle. Pages 1–10 : mise en page, marges, tailles et hiérarchie. Pages 11–21 : inspiration pour la palette et les accents graphiques (bande navy, jaune, pervenche), sans reprise de texte ni création de graphiques inexistants dans la source.

## Contrôle
Voir `work/qc_report.txt`, `work/specification_design.txt`, `work/analyse_design_page_par_page.txt`, `work/inventaire_et_checklist.txt` et les rendus `work/renders/final_p*.png`.

## Prochaine étape
Quand les pages restantes seront fournies, elles seront ajoutées au même pipeline (`work/content.json` + `work/layout_engine.py`) sans refonte de l'identité visuelle, et la TOC automatique sera mise à jour.
