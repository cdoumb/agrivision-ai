# -*- coding: utf-8 -*-
"""
=============================================================================
 build_rapport.py  -  Genere le rapport de projet au format Word
-----------------------------------------------------------------------------
 Produit :  rapport/AgriVision-AI_Rapport.docx

 ORGANISATION DES FICHIERS
       chapitres/NN_nom.md      le texte, un fichier par chapitre
       build/mise_en_page.py    les briques de mise en forme, aucun texte
       build/markdown_vers_word.py   traduit le Markdown en objets Word
       build/controle_style.py  refuse les caracteres et tournures interdits
       build/build_rapport.py   ce fichier : assemble le tout

 UTILISATION
       python rapport/build/build_rapport.py

 Le numero de chapitre vient du nom du fichier : 05_resultats_studio.md
 devient le chapitre 5. Pour ajouter, retirer ou reordonner un chapitre, il
 suffit de renommer des fichiers, sans toucher a une ligne de code.

 Dependance : python-docx
=============================================================================
"""

import re
import sys
from pathlib import Path

DOSSIER_BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER_BUILD))

import controle_style                                            # noqa: E402
import markdown_vers_word as mdw                                 # noqa: E402
from mise_en_page import (CPT, nouveau_document, page_de_garde,   # noqa: E402
                          para, puce, sommaire, titre1)

DOSSIER_RAPPORT = DOSSIER_BUILD.parent
DOSSIER_CHAPITRES = DOSSIER_RAPPORT / "chapitres"

# =============================================================================
#  Ce qui figure sur la page de garde
# =============================================================================

META = {
    "etablissement": "École Supérieure Multinationale des Télécommunications",
    "filiere": "Cycle d'ingénierie, Ingénierie des Données et Intelligence Artificielle",
    "matiere": "Projet de stage, année académique 2025-2026",
    "nature": "RAPPORT DE PROJET",
    "titre": "AgriVision-AI",
    "sous_titre": "Diagnostic des maladies des cultures par vision par ordinateur, "
                  "et mesure honnête de ce qu'un tel modèle vaut au champ",
    "auteurs": [
        "DOUMBIA Cheick Oumar",
        "PIKBOUGOUM Faustin Félicien",
    ],
    "encadrant": "Prof. Boudal NIANG",
    "date": "Remis le 30 août 2026",
}

NOM_FICHIER = "AgriVision-AI_Rapport.docx"
TITRE_PIED = "AgriVision-AI    |    Rapport de projet"

RE_NOM_CHAPITRE = re.compile(r"^(\d+)_")


# =============================================================================
#  Assemblage
# =============================================================================

def chapitres():
    """Chapitres tries par leur numero, lu dans le nom du fichier."""
    trouves = []
    for chemin in sorted(DOSSIER_CHAPITRES.glob("*.md")):
        correspondance = RE_NOM_CHAPITRE.match(chemin.name)
        if correspondance:
            trouves.append((int(correspondance.group(1)), chemin))
    return sorted(trouves)


def table_des_illustrations(doc):
    """
    Liste des figures et des tableaux, dressee a partir des compteurs.

    Elle se construit apres coup : les compteurs ne sont remplis qu'une fois
    tous les chapitres ecrits.
    """
    if not CPT.index_figures and not CPT.index_tableaux:
        return

    titre1(doc, "Table des figures et des tableaux")

    if CPT.index_figures:
        para(doc, "Figures", taille=11, gras=True, apres=4)
        for numero, legende in CPT.index_figures:
            puce(doc, f"Figure {numero}. {legende}")

    if CPT.index_tableaux:
        para(doc, "Tableaux", taille=11, gras=True, avant=12, apres=4)
        for numero, legende in CPT.index_tableaux:
            puce(doc, f"Tableau {numero}. {legende}")


def construire(journal):
    doc = nouveau_document(TITRE_PIED)

    page_de_garde(doc, META["etablissement"], META["filiere"], META["matiere"],
                  META["nature"], META["titre"], META["sous_titre"],
                  META["auteurs"], META["encadrant"], META["date"])
    sommaire(doc)

    for numero, chemin in chapitres():
        mdw.ajouter_chapitre(doc, chemin, numero, journal)

    table_des_illustrations(doc)
    return doc


def verifier_chapitres():
    """Refuse de generer un document troue plutot que de le tronquer en silence."""
    trouves = chapitres()
    if not trouves:
        print(f"  aucun chapitre dans {DOSSIER_CHAPITRES}")
        return False

    numeros = [numero for numero, _ in trouves]
    manquants = [n for n in range(1, max(numeros) + 1) if n not in numeros]
    if manquants:
        print(f"  chapitres manquants dans la numerotation : {manquants}")
        return False

    doublons = {n for n in numeros if numeros.count(n) > 1}
    if doublons:
        print(f"  numeros de chapitre en double : {sorted(doublons)}")
        return False
    return True


def main():
    print("Generation du rapport AgriVision-AI")

    if controle_style.main() != 0:
        print("\n  Generation annulee : corriger le style d'abord.")
        return 1

    if not verifier_chapitres():
        return 1

    journal = []
    doc = construire(journal)

    sortie = DOSSIER_RAPPORT / NOM_FICHIER
    doc.save(sortie)

    print(f"  {len(chapitres())} chapitre(s)")
    print(f"  {CPT.figure} figure(s) numerotee(s)")
    print(f"  {CPT.tableau} tableau(x) numerote(s)")
    if journal:
        print(f"  {len(journal)} avertissement(s) :")
        for message in journal:
            print(f"     {message}")
    print(f"  ecrit : {sortie}")
    print("\n  Ouvrir le fichier dans Word, puis Ctrl+A et F9")
    print("  pour renseigner le sommaire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
