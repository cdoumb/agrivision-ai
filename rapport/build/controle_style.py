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

# -----------------------------------------------------------------------------
#  Mots qui doivent porter leurs accents
# -----------------------------------------------------------------------------
# Cinq chapitres ont ete rediges sans un seul accent, et le defaut a traverse
# une relecture complete du document genere sans etre vu : rien ne le signale,
# le texte reste lisible. Ce controle le rend impossible a rater.
#
# La liste ne contient que des formes SANS homographe non accentue, pour
# qu'aucune correction ne depende du contexte. Sont donc volontairement
# absents : a/à, ou/où, des/dès, du/dû, sur/sûr, la/là, mais/maïs, ainsi que
# les participes passes homographes d'un present (compte/compté, reste/resté).
# Ceux-la se verifient a la lecture, pas a la machine.

ACCENTS_OBLIGATOIRES = [
    "problematique", "probleme", "problemes", "modele", "modeles", "donnee",
    "donnees", "resultat", "resultats", "perimetre", "perimetres", "deja",
    "etre", "meme", "memes", "tres", "apres", "premiere", "premieres",
    "derniere", "dernieres", "troisieme", "deuxieme", "quatrieme",
    "entrainement", "entrainer", "entraine", "entrainee", "entraines",
    "entrainees", "reentrainer", "deploiement", "inference", "interpretabilite",
    "evaluation", "evaluations", "evalue", "evaluee", "pretraitement",
    "decoupage", "desequilibre", "deduplication", "integrite", "verite",
    "etiquette", "etiquettes", "etiquete", "etiquetee", "etiquetees",
    "reference", "references", "representation", "representations",
    "caracteristiques", "categories", "parametres", "requete", "requetes",
    "reponse", "reponses", "acces", "critere", "criteres", "element",
    "elements", "etape", "etapes", "etat", "etats", "necessaire", "precis",
    "precise", "precisement", "precoce", "precocite", "efficacite",
    "specialise", "specialisee", "specialisees", "specifique", "systeme",
    "systematique", "systematiquement", "telephone", "materiel", "numerique",
    "generalement", "genere", "generee", "generation", "separation", "separe",
    "separee", "separees", "separement", "frontiere", "memoire", "chaine",
    "chaines", "controle", "controles", "developpe", "developpee",
    "developper", "developpement", "considerables", "consequence",
    "consequences", "conference", "difference", "differents", "differente",
    "differentes", "eleve", "elevee", "reseau", "reseaux", "zero",
    "detecter", "detecte", "detectes",
    "detectee", "detectees", "repondre", "repond", "repondrait", "presente",
    "detail", "details", "lumiere", "maniere", "matiere", "barriere",
    "presentee", "presentees", "operation", "operations", "securite",
    "qualite", "quantite", "validite", "fiabilite", "possibilite",
    "possibilites", "priorite", "propriete", "proprietes", "unite", "unites",
    "activite", "capacite", "densite", "humidite", "luminosite", "gravite",
    "senegalaise", "senegalaises", "academique", "theorique", "numero",
]


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower())
                   if unicodedata.category(c) != "Mn")


SANS_ACCENT = set(ACCENTS_OBLIGATOIRES)

# Trois sortes de texte ne sont pas de la prose et n'ont pas a etre accentuees :
# les commentaires, qui ne figurent pas dans le document final, le balisage de
# chasse fixe, et les noms de fichiers, de routes et de variables. Sans ce
# filtre, « src/model/evaluation_terrain.py » serait signale comme un accent
# manquant sur « evaluation ».
RE_COMMENTAIRE = re.compile(r"<!--.*?-->", re.DOTALL)
RE_CODE = re.compile(r"`[^`]*`")
RE_CHEMIN = re.compile(r"[A-Za-z0-9_.\-/]*[_./][A-Za-z0-9_.\-/]*")
RE_MOT = re.compile(r"[A-Za-zÀ-ÿ]+")


def _prose(texte):
    """
    Le texte destine a etre lu, commentaires et identifiants retires.

    Les zones neutralisees sont remplacees par des espaces de meme longueur,
    et non supprimees : la numerotation des lignes doit rester exacte pour
    que les messages d'erreur pointent au bon endroit.
    """
    def blanchir(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    for motif in (RE_COMMENTAIRE, RE_CODE, RE_CHEMIN):
        texte = motif.sub(blanchir, texte)
    return texte


def controler(fichiers):
    infractions = []

    for chemin in fichiers:
        source = chemin.read_text(encoding="utf-8")

        for numero, ligne in enumerate(_prose(source).splitlines(), start=1):
            for mot in RE_MOT.findall(ligne):
                if mot.lower() in SANS_ACCENT:
                    infractions.append(
                        (chemin.name, numero, f"accent manquant : {mot}"))

        for numero, ligne in enumerate(source.splitlines(), start=1):

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
