# -*- coding: utf-8 -*-
"""
=============================================================================
 build_chapitres.py  -  Un document Word mis en forme par chapitre
-----------------------------------------------------------------------------
 POURQUOI CE FICHIER EXISTE

 Les chapitres se redigent en Markdown, et c'est ce qui permet a Git de
 suivre qui a ecrit quoi ligne a ligne. Mais un fichier .md se lit mal :
 les asterisques, les barres de tableau et les liens d'images encombrent le
 texte, et rien n'y ressemble au document final.

 Ce script produit, a cote des sources, un document Word par chapitre, dans
 la mise en forme exacte du rapport : Calibri, memes titres, memes tableaux,
 memes figures. Il sert a relire un chapitre seul, ou a le faire relire par
 quelqu'un qui n'ouvrira jamais un fichier Markdown.

 Les .md restent la source. Ces documents sont regeneres, jamais edites :
 une correction faite dans le .docx serait perdue a la generation suivante.

 UTILISATION
       python rapport/build/build_chapitres.py

 Produit dans rapport/chapitres_word/ un fichier par chapitre.
 Le rapport complet, lui, se genere avec build_rapport.py.

 Dependance : python-docx
=============================================================================
"""

import sys
from pathlib import Path

DOSSIER_BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER_BUILD))

import build_rapport as br                                    # noqa: E402
import controle_style                                         # noqa: E402
import markdown_vers_word as mdw                              # noqa: E402
import mise_en_page as mep                                    # noqa: E402

DOSSIER_SORTIE = br.DOSSIER_RAPPORT / "chapitres_word"

# Qui signe quoi. La soutenance comporte une part individuelle : un relecteur
# doit savoir a qui adresser ses remarques sans ouvrir l'historique Git.
AUTEURS = {
    1: "Cheick Oumar Doumbia",
    2: "Cheick Oumar Doumbia",
    3: "Cheick Oumar Doumbia",
    4: "Section 4.1 Faustin Pikbougoum, section 4.2 Cheick Oumar Doumbia",
    5: "Faustin Félicien Pikbougoum",
    6: "Faustin Félicien Pikbougoum",
    7: "Faustin Félicien Pikbougoum",
    8: "Faustin Félicien Pikbougoum",
    9: "Faustin Félicien Pikbougoum",
    10: "Cheick Oumar Doumbia",
}


def construire_chapitre(numero, chemin, journal):
    """Un document autonome contenant le seul chapitre demande."""
    # Les compteurs sont partages par tout le module de mise en page. Sans
    # cette remise a zero, le chapitre 6 numeroterait sa premiere figure
    # « Figure 5 » parce que les chapitres precedents ont deja compte.
    mep.CPT.figure = 0
    mep.CPT.tableau = 0
    mep.CPT.index_figures.clear()
    mep.CPT.index_tableaux.clear()

    source = chemin.read_text(encoding="utf-8")
    titre = mdw.titre_du_chapitre(source)

    doc = mep.nouveau_document(
        f"{br.META['titre']}    |    Chapitre {numero}",
        auteur=AUTEURS.get(numero, ""),
        titre=f"{br.META['titre']} : chapitre {numero}, {titre}",
        sujet=br.META["sous_titre"])

    mep.para(doc, br.META["nature"].title(), taille=9, couleur=mep.GRIS_DOUX,
             align=None, apres=0)
    mep.para(doc, f"{br.META['titre']} : {br.META['sous_titre']}",
             taille=9, couleur=mep.GRIS_DOUX, align=None, avant=0, apres=2)
    mep.para(doc, f"Rédaction : {AUTEURS.get(numero, 'non attribué')}",
             taille=9, italique=True, couleur=mep.GRIS_DOUX, align=None,
             avant=0, apres=10)

    # saut=False : dans le rapport complet, un chapitre commence sur une page
    # neuve. Ici il est seul dans son document, un saut laisserait une page
    # blanche en tete.
    mep.chapitre(doc, numero, titre, saut=False)
    mdw.rendre(doc, mdw.blocs(source), journal)
    return doc, titre


def main():
    print("Generation des chapitres mis en forme")

    if controle_style.main() != 0:
        print("\n  Generation annulee : corriger le style d'abord.")
        return 1

    trouves = br.chapitres()
    if not trouves:
        print(f"  aucun chapitre dans {br.DOSSIER_CHAPITRES}")
        return 1

    DOSSIER_SORTIE.mkdir(exist_ok=True)
    journal, ecrits, bloques = [], 0, []

    for numero, chemin in trouves:
        doc, titre = construire_chapitre(numero, chemin, journal)
        sortie = DOSSIER_SORTIE / f"{chemin.stem}.docx"
        try:
            doc.save(sortie)
        except PermissionError:
            bloques.append(sortie.name)
            continue
        ecrits += 1
        print(f"  chapitre {numero:>2} : {sortie.name:<28} {titre}")

    if bloques:
        print(f"\n  {len(bloques)} fichier(s) ouverts dans Word, non ecrits :")
        for nom in bloques:
            print(f"     {nom}")
        print("  Fermer les documents, puis relancer.")

    if journal:
        print(f"\n  {len(journal)} avertissement(s) :")
        for message in sorted(set(journal)):
            print(f"     {message}")

    print(f"\n  {ecrits} document(s) ecrits dans {DOSSIER_SORTIE}")
    return 1 if bloques else 0


if __name__ == "__main__":
    raise SystemExit(main())
