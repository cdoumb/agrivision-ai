# -*- coding: utf-8 -*-
"""
=============================================================================
 controle_style.py  -  Refuse les caracteres et les tournures interdits
-----------------------------------------------------------------------------
 POURQUOI CE SCRIPT EXISTE

 Le rapport doit rester sobre et lisible : pas de tiret cadratin, pas de
 fleche, pas d'emoji, aucun symbole decoratif. Il doit aussi ne pas se lire
 comme une sortie de generateur automatique : certaines tournures sont donc
 bannies, et le script les refuse avant que le document ne soit produit.

 Il scanne les chapitres Markdown de rapport/chapitres/ et signale chaque
 infraction avec son fichier et sa ligne. C'est la meme regle pour les deux
 membres du binome, appliquee par une machine plutot que par un relecteur.

 Version derivee de build/controle_style.py, qui lisait des fichiers Python.
 Ici la source est du Markdown : plus besoin d'arbre syntaxique, tout le
 fichier est du texte destine a etre imprime.

 UTILISATION
       python rapport/build/controle_style.py

 Code de retour 0 si tout va bien, 1 sinon. build_rapport.py l'appelle avant
 de generer quoi que ce soit.
=============================================================================
"""

import re
import sys
import unicodedata
from pathlib import Path

DOSSIER_CHAPITRES = Path(__file__).resolve().parent.parent / "chapitres"

# -----------------------------------------------------------------------------
#  Caracteres autorises
# -----------------------------------------------------------------------------
# Lettres francaises accentuees, chiffres, ponctuation ordinaire, guillemets
# francais, et rien d'autre. Tout le reste est refuse par defaut, ce qui evite
# d'avoir a lister tous les symboles indesirables un par un.

AUTORISES = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "àâäçéèêëîïôöùûüÿœæ"
    "ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ"
    " .,;:!?'\"()[]{}/\\-_+=*%&#@$<>|~^`\n\t"
    "«»°"
)

# Caracteres explicitement nommes, pour produire un message clair.
NOMMES = {
    "—": "tiret cadratin",
    "–": "tiret demi-cadratin",
    "…": "points de suspension",
    "→": "fleche vers la droite",
    "←": "fleche vers la gauche",
    "↔": "fleche double",
    "‘": "apostrophe typographique ouvrante",
    "’": "apostrophe typographique fermante",
    "“": "guillemet anglais ouvrant",
    "”": "guillemet anglais fermant",
    "•": "puce",
    "·": "point median",
    "✓": "coche",
    "✗": "croix",
}

# -----------------------------------------------------------------------------
#  Tournures qui trahissent une redaction automatique
# -----------------------------------------------------------------------------

TOURNURES = [
    (r"il est important de noter", "tournure creuse"),
    (r"il convient de noter", "tournure creuse"),
    (r"dans cette section, nous allons", "annonce inutile"),
    (r"dans ce chapitre, nous allons", "annonce inutile"),
    (r"nous allons voir", "annonce inutile"),
    (r"en conclusion, nous pouvons dire", "conclusion redondante"),
    (r"il est essentiel de", "tournure creuse"),
    (r"joue un role (crucial|clef|cle)", "cliche"),
    (r"au coeur de", "cliche"),
    (r"force est de constater", "cliche"),
    (r"\bplongeons\b", "cliche"),
    (r"\bexplorons\b", "cliche"),
    (r"n'hesitez pas a", "tournure de chatbot"),
    (r"en resume,", "annonce inutile"),
    (r"il s'agit d'un element (cle|essentiel)", "tournure creuse"),
    (r"revolutionn", "emphase publicitaire"),
]


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower())
                   if unicodedata.category(c) != "Mn")


def controler(fichiers):
    infractions = []

    for chemin in fichiers:
        for numero, ligne in enumerate(
                chemin.read_text(encoding="utf-8").splitlines(), start=1):

            for caractere in ligne:
                if caractere in AUTORISES:
                    continue
                nom = NOMMES.get(caractere)
                if nom is None:
                    try:
                        nom = unicodedata.name(caractere).lower()
                    except ValueError:
                        nom = "caractere non imprimable"
                # On affiche le code du caractere et non le caractere lui-meme :
                # la console Windows ne sait pas toujours l'imprimer.
                infractions.append(
                    (chemin.name, numero,
                     f"caractere interdit U+{ord(caractere):04X} ({nom})"))

            plat = sans_accents(ligne)
            for motif, raison in TOURNURES:
                if re.search(motif, plat):
                    infractions.append(
                        (chemin.name, numero, f"tournure interdite ({raison})"))

    return infractions


def chapitres():
    """
    Les fichiers de chapitre, a l'exclusion des fichiers temporaires de Word.

    Ouvrir un .md dans Word depose a cote de lui un fichier « ~$nom.md » qui
    n'est pas du texte UTF-8. Sans ce filtre, il fait echouer la generation
    avec une erreur d'encodage incomprehensible.
    """
    return sorted(c for c in DOSSIER_CHAPITRES.glob("*.md")
                  if not c.name.startswith("~$"))


def main():
    fichiers = chapitres()
    if not fichiers:
        print(f"  aucun chapitre trouve dans {DOSSIER_CHAPITRES}")
        return 1

    uniques = sorted(set(controler(fichiers)))

    if not uniques:
        print(f"  controle de style : {len(fichiers)} chapitres, aucun probleme")
        return 0

    print(f"  controle de style : {len(uniques)} probleme(s)")
    for fichier, ligne, message in uniques:
        print(f"     {fichier}:{ligne}  {message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
