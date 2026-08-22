"""
Planche d'exemples Grad-CAM commentes (Binome B).

Repond au livrable 6.3 de la fiche de projet, « exemples d'interpretabilite
(cartes Grad-CAM commentees) ». Le guide de projet insiste sur le mot commente :
une carte affichee sans lecture ne demontre rien.

Ce script ne choisit pas les cas au hasard et ne prend pas les plus flatteurs.
Il diagnostique un lot d'images, puis retient quatre situations qui disent
chacune quelque chose de different :

    1. un diagnostic juste en studio, ou la zone chaude doit tomber sur les
       lesions ;
    2. un diagnostic juste au champ, cas beaucoup plus difficile ;
    3. une erreur affirmee avec assurance, le cas le plus instructif : c'est la
       qu'on voit sur quoi le modele s'est appuye pour se tromper ;
    4. un cas ou le modele previent, confiance sous le seuil de l'application.

Le commentaire de chaque vignette est ecrit a la main dans
reports/gradcam_commentaires.md, apres lecture de la planche. Un commentaire
genere automatiquement ne serait qu'une legende deguisee.

Usage :
    python src/model/planche_gradcam.py

Produit dans reports/ :
    gradcam_exemples_<version>.png   la planche
    gradcam_selection_<version>.json  les cas retenus et leurs chiffres
"""
import base64
import io
import json
import random
import sys
import unicodedata
from pathlib import Path

RACINE_MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE_MODULE.parent))

from model import inference  # noqa: E402
from model.evaluation_terrain import CORRESPONDANCE, sans_accents  # noqa: E402

RACINE_DEPOT = RACINE_MODULE.parents[1]
DOSSIER_ECHANTILLON = RACINE_DEPOT / "data" / "echantillon"
DOSSIER_PLANTDOC = RACINE_DEPOT / "data" / "plantdoc_images"
DOSSIER_RAPPORTS = RACINE_DEPOT / "reports"

# Seuil d'avertissement de l'application, cf. src/app/main.py.
SEUIL_CONFIANCE_FAIBLE = 0.60

# Nombre d'images de terrain tirees par classe. Le Grad-CAM coute une passe de
# gradients par image : on echantillonne au lieu de traiter les 942.
TIRAGE_PAR_CLASSE = 4
GRAINE = 42


def _cle(texte):
    return sans_accents(texte).strip().lower()


def indice_depuis_nom(nom_fichier, index_par_libelle):
    """
    « Mais__Cercosporiose_1.jpg » donne l'indice de « Mais - Cercosporiose ».

    Le nom de fichier porte la verite terrain : c'est ainsi que le lot A a
    depose l'echantillon.
    """
    tige = Path(nom_fichier).stem
    tige = tige.rsplit("_", 1)[0] if tige.rsplit("_", 1)[-1].isdigit() else tige
    return index_par_libelle.get(_cle(tige.replace("__", " - ").replace("_", " ")))


def rassembler_candidats(index_par_libelle):
    """Images de studio (toutes) et de terrain (un tirage par classe)."""
    candidats = []

    for chemin in sorted(DOSSIER_ECHANTILLON.glob("*.jpg")):
        indice = indice_depuis_nom(chemin.name, index_par_libelle)
        if indice is not None:
            candidats.append({"chemin": chemin, "verite": indice, "origine": "studio"})

    tirage = random.Random(GRAINE)
    for indice, nom_plantdoc in sorted(CORRESPONDANCE.items()):
        dossier = DOSSIER_PLANTDOC / nom_plantdoc
        if not dossier.exists():
            continue
        images = sorted(p for p in dossier.iterdir()
                        if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        for chemin in tirage.sample(images, min(TIRAGE_PAR_CLASSE, len(images))):
            candidats.append({"chemin": chemin, "verite": indice, "origine": "terrain"})

    return candidats


def diagnostiquer(candidats, libelles):
    """Diagnostic complet, Grad-CAM comprise, de chaque candidat."""
    resultats = []
    for numero, candidat in enumerate(candidats, start=1):
        try:
            sortie = inference.diagnostiquer(candidat["chemin"].read_bytes())
        except Exception as erreur:
            print(f"  ignoree ({type(erreur).__name__}) : {candidat['chemin'].name}")
            continue

        resultats.append({
            **candidat,
            "predit": sortie["class_index"],
            "confiance": sortie["confidence"],
            "gradcam": sortie["gradcam_base64"],
            "juste": sortie["class_index"] == candidat["verite"],
            "libelle_vrai": libelles[candidat["verite"]],
            "libelle_predit": sortie["predicted_class"],
        })
        if numero % 10 == 0:
            print(f"  {numero} / {len(candidats)} images traitées")
    return resultats


def choisir(resultats):
    """
    Retient les quatre cas de la planche.

    Chaque critere est explicite : on prend le plus representatif, pas le plus
    avantageux. Pour l'erreur, on cherche celle qui a ete affirmee avec le plus
    d'assurance, parce que c'est le defaut que le projet cherche a rendre
    visible.
    """
    def meilleur(candidats, cle, defaut=None):
        return max(candidats, key=cle) if candidats else defaut

    justes_studio = [r for r in resultats if r["juste"] and r["origine"] == "studio"]
    justes_terrain = [r for r in resultats if r["juste"] and r["origine"] == "terrain"]
    fausses = [r for r in resultats if not r["juste"]]
    fausses_affirmees = [r for r in fausses if r["confiance"] >= SEUIL_CONFIANCE_FAIBLE]
    prudents = [r for r in resultats if r["confiance"] < SEUIL_CONFIANCE_FAIBLE]

    choix = [
        ("Diagnostic juste, conditions de studio",
         meilleur(justes_studio, lambda r: r["confiance"])),
        ("Diagnostic juste, conditions de terrain",
         meilleur(justes_terrain, lambda r: r["confiance"])),
        ("Erreur affirmée sans avertissement",
         meilleur(fausses_affirmees or fausses, lambda r: r["confiance"])),
        ("Le modèle prévient : confiance sous 60 %",
         meilleur(prudents, lambda r: -r["confiance"])),
    ]
    return [(titre, cas) for titre, cas in choix if cas is not None]


def tracer(choix, version):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    figure, axes = plt.subplots(len(choix), 2, figsize=(8.5, 3.5 * len(choix)))
    if len(choix) == 1:
        axes = [axes]

    for rang, (titre, cas) in enumerate(choix):
        photo = Image.open(cas["chemin"]).convert("RGB")
        axes[rang][0].imshow(photo)
        axes[rang][0].set_title(
            f"{titre}\nvérité : {cas['libelle_vrai']}", fontsize=9, loc="left")

        if cas["gradcam"]:
            carte = Image.open(io.BytesIO(base64.b64decode(cas["gradcam"])))
            axes[rang][1].imshow(carte)
        marque = "" if cas["juste"] else "  (faux)"
        axes[rang][1].set_title(
            f"diagnostic : {cas['libelle_predit']}{marque}\n"
            f"confiance {cas['confiance']:.0%}", fontsize=9, loc="left")

        for axe in axes[rang]:
            axe.axis("off")

    figure.suptitle(f"Cartes Grad-CAM, modèle {version}", fontsize=12)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    sortie = DOSSIER_RAPPORTS / f"gradcam_exemples_{version}.png"
    plt.savefig(sortie, dpi=150, bbox_inches="tight")
    plt.close()
    return sortie


def main():
    if not DOSSIER_ECHANTILLON.exists():
        print(f"Échantillon introuvable : {DOSSIER_ECHANTILLON}")
        return 1

    classes = inference._charger_classes()
    libelles = [c["label"] for c in classes]
    index_par_libelle = {_cle(l): i for i, l in enumerate(libelles)}
    version = inference.VERSION_MODELE

    candidats = rassembler_candidats(index_par_libelle)
    print(f"{len(candidats)} images candidates "
          f"({sum(c['origine'] == 'studio' for c in candidats)} studio, "
          f"{sum(c['origine'] == 'terrain' for c in candidats)} terrain)")

    print("Diagnostic et cartes Grad-CAM...")
    resultats = diagnostiquer(candidats, libelles)
    if not resultats:
        print("Aucune image exploitable.")
        return 1

    choix = choisir(resultats)
    DOSSIER_RAPPORTS.mkdir(exist_ok=True)
    sortie = tracer(choix, version)

    selection = {
        "modele": version,
        "seuil_avertissement": SEUIL_CONFIANCE_FAIBLE,
        "images_examinees": len(resultats),
        "cas": [
            {
                "critere": titre,
                "image": str(cas["chemin"].relative_to(RACINE_DEPOT)).replace("\\", "/"),
                "origine": cas["origine"],
                "verite": cas["libelle_vrai"],
                "diagnostic": cas["libelle_predit"],
                "confiance": cas["confiance"],
                "juste": cas["juste"],
            }
            for titre, cas in choix
        ],
    }
    chemin_selection = DOSSIER_RAPPORTS / f"gradcam_selection_{version}.json"
    with open(chemin_selection, "w", encoding="utf-8") as f:
        json.dump(selection, f, ensure_ascii=False, indent=2)

    print()
    for titre, cas in choix:
        marque = "juste" if cas["juste"] else "FAUX"
        print(f"  {titre}")
        print(f"      {cas['chemin'].name}  ->  {cas['libelle_predit']} "
              f"({cas['confiance']:.0%}, {marque})")

    print()
    print(f"Écrit : {sortie.name}, {chemin_selection.name}")
    print("Les commentaires se rédigent à la main dans reports/gradcam_commentaires.md, "
          "après lecture de la planche.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
