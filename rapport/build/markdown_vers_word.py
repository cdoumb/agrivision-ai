# -*- coding: utf-8 -*-
"""
=============================================================================
 markdown_vers_word.py  -  Traduit un chapitre Markdown en objets Word
-----------------------------------------------------------------------------
 POURQUOI CE FICHIER EXISTE

 Le rapport se redige en Markdown, un fichier par chapitre, pour trois
 raisons : personne n'a besoin d'ecrire du Python, Git suit qui a ecrit quoi
 ligne a ligne, et deux personnes peuvent travailler en meme temps sans
 conflit. Ce module fait le pont entre ce texte et le generateur Word.

 Il ne comprend qu'un Markdown volontairement restreint, decrit dans
 rapport/README.md. Tout ce qui n'est pas reconnu est traite comme du
 paragraphe ordinaire, jamais silencieusement supprime.

 SYNTAXE RECONNUE

     # Titre                    titre du chapitre (une seule fois, en tete)
     ## Sous-titre              section
     ### Sous-sous-titre        sous-section
     texte                      paragraphe
     - element                  puce
     1. element                 liste numerotee
     > RETENIR: texte           encadre a retenir
     > ATTENTION: texte         encadre de vigilance
     > A REDIGER: texte         encadre signalant un trou a combler
     > texte                    encadre neutre
     | a | b |                  tableau, avec sa ligne de separation
     Tableau: legende           legende du tableau qui precede
     ![legende](reports/x.png)  figure, chemin relatif a la racine du depot
     ![legende|12](chemin)      figure de 12 cm de large
     <!-- note -->              commentaire, absent du document final

 Dans le texte : **gras**, *italique*, `chasse fixe`.
=============================================================================
"""

import re
from pathlib import Path

import mise_en_page as mep

RACINE_DEPOT = Path(__file__).resolve().parents[2]

# Largeur par defaut d'une figure. Volontairement inferieure a la largeur
# utile de la page : les matrices de confusion et les diagrammes en barres
# restent lisibles a cette taille, et le rapport doit tenir dans les 30 pages
# demandees. Une figure qui a besoin de plus se declare au cas par cas :
#     ![legende|15](reports/x.png)
LARGEUR_FIGURE_CM = 11.5

# Etiquettes d'encadre reconnues en tete de citation.
ETIQUETTES = {
    "RETENIR": "À RETENIR",
    "A RETENIR": "À RETENIR",
    "ATTENTION": "ATTENTION",
    "A REDIGER": "À RÉDIGER",
    "SOURCE": "SOURCE",
}

# --- expressions regulieres du parseur ---------------------------------------

RE_TITRE = re.compile(r"^(#{1,4})\s+(.*)$")
RE_PUCE = re.compile(r"^[-*]\s+(.*)$")
RE_NUMERO = re.compile(r"^(\d+)\.\s+(.*)$")
RE_CITATION = re.compile(r"^>\s?(.*)$")
RE_TABLEAU = re.compile(r"^\|(.+)\|\s*$")
RE_SEPARATEUR = re.compile(r"^\|[\s:|-]+\|\s*$")
RE_LEGENDE_TABLEAU = re.compile(r"^Tableau\s*:\s*(.*)$", re.IGNORECASE)
RE_FIGURE = re.compile(r"^!\[([^\]|]*)(?:\|([\d.]+))?\]\(([^)]+)\)\s*$")
RE_COMMENTAIRE = re.compile(r"<!--.*?-->", re.DOTALL)

# --- morceaux en ligne (gras, italique, chasse fixe) -------------------------

RE_MORCEAU = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^*]+\*)")


def morceaux(texte):
    """
    Decoupe une ligne en morceaux exploitables par mise_en_page.riche().

    Renvoie [(texte, options)]. Le balisage lui-meme est retire : ce sont les
    options qui portent la mise en forme, pas les asterisques.
    """
    sortie = []
    for fragment in RE_MORCEAU.split(texte):
        if not fragment:
            continue
        if fragment.startswith("**") and fragment.endswith("**") and len(fragment) > 4:
            sortie.append((fragment[2:-2], {"gras": True}))
        elif fragment.startswith("`") and fragment.endswith("`") and len(fragment) > 2:
            sortie.append((fragment[1:-1],
                           {"police": mep.MONO, "taille": 10}))
        elif fragment.startswith("*") and fragment.endswith("*") and len(fragment) > 2:
            sortie.append((fragment[1:-1], {"italique": True}))
        else:
            sortie.append((fragment, {}))
    return sortie or [(texte, {})]


def _sans_balise(texte):
    """Texte debarrasse de son balisage, pour les cas qui n'acceptent pas de runs."""
    return re.sub(r"\*\*|`|\*", "", texte)


# =============================================================================
#  Analyse du fichier : liste de blocs
# =============================================================================

def blocs(source):
    """
    Transforme le texte source en une suite de blocs typés.

    Un bloc est un tuple (nature, charge). Cette etape separe l'analyse du
    texte de sa mise en forme, ce qui rend chacune des deux lisible seule.
    """
    source = RE_COMMENTAIRE.sub("", source)
    lignes = source.splitlines()
    resultat = []
    paragraphe = []
    tableau = []

    def vider_paragraphe():
        if paragraphe:
            resultat.append(("paragraphe", " ".join(paragraphe)))
            paragraphe.clear()

    def vider_tableau():
        if tableau:
            resultat.append(("tableau", list(tableau)))
            tableau.clear()

    for brute in lignes:
        ligne = brute.rstrip()

        if RE_TABLEAU.match(ligne):
            vider_paragraphe()
            if not RE_SEPARATEUR.match(ligne):
                tableau.append([c.strip() for c in ligne.strip().strip("|").split("|")])
            continue
        vider_tableau()

        if not ligne.strip():
            vider_paragraphe()
            continue

        correspondance = RE_LEGENDE_TABLEAU.match(ligne)
        if correspondance:
            vider_paragraphe()
            resultat.append(("legende_tableau", correspondance.group(1).strip()))
            continue

        correspondance = RE_FIGURE.match(ligne)
        if correspondance:
            vider_paragraphe()
            legende, largeur, chemin = correspondance.groups()
            resultat.append(("figure", (legende.strip(), largeur, chemin.strip())))
            continue

        correspondance = RE_TITRE.match(ligne)
        if correspondance:
            vider_paragraphe()
            resultat.append((f"titre{len(correspondance.group(1))}",
                             correspondance.group(2).strip()))
            continue

        correspondance = RE_CITATION.match(ligne)
        if correspondance:
            vider_paragraphe()
            resultat.append(("citation", correspondance.group(1).strip()))
            continue

        correspondance = RE_NUMERO.match(ligne)
        if correspondance:
            vider_paragraphe()
            resultat.append(("numero", (int(correspondance.group(1)),
                                        correspondance.group(2).strip())))
            continue

        correspondance = RE_PUCE.match(ligne)
        if correspondance:
            vider_paragraphe()
            resultat.append(("puce", correspondance.group(1).strip()))
            continue

        paragraphe.append(ligne.strip())

    vider_paragraphe()
    vider_tableau()
    return resultat


# =============================================================================
#  Rendu des blocs dans le document
# =============================================================================

def _rendre_citation(doc, texte):
    for cle, etiquette in ETIQUETTES.items():
        prefixe = f"{cle}:"
        if texte.upper().startswith(prefixe):
            mep.encadre(doc, etiquette, _sans_balise(texte[len(prefixe):].strip()))
            return
    mep.encadre(doc, "", _sans_balise(texte))


def _rendre_figure(doc, legende, largeur, chemin, journal):
    fichier = (RACINE_DEPOT / chemin).resolve()
    if not fichier.is_file():
        journal.append(f"figure introuvable : {chemin}")
        mep.encadre(doc, "FIGURE MANQUANTE", f"{chemin} ({legende})")
        return
    mep.figure(doc, fichier.name, legende,
               largeur_cm=float(largeur) if largeur else LARGEUR_FIGURE_CM,
               dossier=fichier.parent)


def _rendre_tableau(doc, lignes, legende):
    if not lignes:
        return
    entetes, corps = lignes[0], lignes[1:]
    mep.tableau(doc, entetes, corps, legende=legende or None)


def rendre(doc, blocs_analyses, journal):
    """
    Ecrit les blocs dans le document.

    La legende d'un tableau est ecrite APRES le tableau dans le fichier source,
    alors que mise_en_page.tableau() la demande AVANT de le construire. Le
    tableau est donc mis de cote jusqu'a ce qu'on sache s'il porte une legende.
    """
    tableau_en_attente = None

    def poser_tableau(legende=""):
        nonlocal tableau_en_attente
        if tableau_en_attente is not None:
            _rendre_tableau(doc, tableau_en_attente, legende)
            tableau_en_attente = None

    for nature, charge in blocs_analyses:
        if nature == "tableau":
            poser_tableau()
            tableau_en_attente = charge
            continue
        if nature == "legende_tableau":
            poser_tableau(charge)
            continue
        poser_tableau()

        if nature == "titre1":
            continue                       # deja pose par build_rapport
        if nature == "titre2":
            mep.titre2(doc, _sans_balise(charge))
        elif nature == "titre3":
            mep.titre3(doc, _sans_balise(charge))
        elif nature == "titre4":
            mep.intertitre(doc, _sans_balise(charge))
        elif nature == "paragraphe":
            mep.riche(doc, morceaux(charge))
        elif nature == "puce":
            mep.puce(doc, _sans_balise(charge))
        elif nature == "numero":
            indice, texte = charge
            mep.numero(doc, indice, _sans_balise(texte))
        elif nature == "citation":
            _rendre_citation(doc, charge)
        elif nature == "figure":
            _rendre_figure(doc, *charge, journal=journal)

    poser_tableau()


# =============================================================================
#  Point d'entree
# =============================================================================

def titre_du_chapitre(source):
    """Premiere ligne commencant par un seul diese."""
    for ligne in source.splitlines():
        correspondance = RE_TITRE.match(ligne.rstrip())
        if correspondance and len(correspondance.group(1)) == 1:
            return correspondance.group(2).strip()
    return "Chapitre sans titre"


def ajouter_chapitre(doc, chemin, numero_chapitre, journal):
    """Ouvre le chapitre puis y deverse le contenu du fichier Markdown."""
    source = Path(chemin).read_text(encoding="utf-8")
    mep.chapitre(doc, numero_chapitre, titre_du_chapitre(source))
    rendre(doc, blocs(source), journal)
