"""
Mesure de robustesse sur images de terrain (Binôme B).

Répond à l'exigence non fonctionnelle de la fiche de projet : « le modèle est
évalué sur des images non vues, idéalement de terrain, pas uniquement sur le
jeu public ».

Le modèle a été entraîné sur PlantVillage, dont les photographies sont prises
en studio : feuille détachée, fond uniforme, éclairage maîtrisé. Rien ne
garantit qu'il ait appris la maladie plutôt que ces conditions de prise de vue.
Ce script le confronte à PlantDoc, un corpus de photographies prises au champ,
sans réentraîner quoi que ce soit.

Usage :
    python src/model/evaluation_terrain.py

Produit dans reports/ :
    robustesse_terrain.json   les chiffres
    robustesse_terrain.png    comparaison studio / terrain par classe
    confusion_terrain.png     matrice de confusion sur images de terrain
"""
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

RACINE_MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE_MODULE.parent))

from model import inference  # noqa: E402

RACINE_DEPOT = RACINE_MODULE.parents[1]
DOSSIER_PLANTDOC = RACINE_DEPOT / "data" / "plantdoc_images"
DOSSIER_RAPPORTS = RACINE_DEPOT / "reports"

# Correspondance entre les classes du projet et celles de PlantDoc.
#
# « Maïs - Sain » (indice 4) est absent de PlantDoc : le corpus ne contient
# aucune feuille de maïs saine. Cette classe ne peut donc pas être mesurée, et
# le modèle peut la prédire à tort sans qu'aucune image ne le contredise. La
# limite est signalée dans le rapport produit.
#
# « Bell_pepper leaf spot » n'est pas explicitement déclaré bactérien par
# PlantDoc. La correspondance avec « Poivron - Tache bactérienne » est une
# approximation assumée.
CORRESPONDANCE = {
    0: "Tomato leaf",
    1: "Tomato leaf late blight",
    2: "Tomato leaf bacterial spot",
    3: "Tomato Septoria leaf spot",
    5: "Corn rust leaf",
    6: "Corn leaf blight",
    7: "Corn Gray leaf spot",
    8: "Bell_pepper leaf",
    9: "Bell_pepper leaf spot",
}

CLASSE_NON_COUVERTE = 4

# Résultats sur le jeu de test PlantVillage, pour la comparaison.
# Source : reports/model_card.json produit par le notebook d'entraînement.
F1_STUDIO = {
    0: 0.9855, 1: 0.9648, 2: 0.9715, 3: 0.9567, 4: 0.9971,
    5: 0.9972, 6: 0.8990, 7: 0.8250, 8: 0.9887, 9: 0.9800,
}
EXACTITUDE_STUDIO = 0.9664


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte)
                   if unicodedata.category(c) != "Mn")


def rassembler_images():
    """
    Collecte les images de PlantDoc pour les 9 classes couvertes.

    Les dossiers train et test d'origine ont été fusionnés à l'extraction :
    on n'entraîne rien ici, et aucune de ces images n'a été vue par le modèle,
    qui n'a connu que PlantVillage. La distinction n'a donc pas de sens.
    """
    chemins, verites = [], []
    manquants = []

    for indice, nom_plantdoc in sorted(CORRESPONDANCE.items()):
        dossier = DOSSIER_PLANTDOC / nom_plantdoc
        if not dossier.exists():
            manquants.append(nom_plantdoc)
            continue
        trouves = [p for p in sorted(dossier.iterdir())
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        chemins += trouves
        verites += [indice] * len(trouves)

    return chemins, np.array(verites), manquants


def diagnostiquer_tout(chemins):
    """Fait passer chaque image dans le modèle, sans Grad-CAM (plus rapide)."""
    predictions, confiances, illisibles = [], [], []

    for numero, chemin in enumerate(chemins, start=1):
        try:
            resultat = inference.diagnostiquer(chemin.read_bytes(), avec_gradcam=False)
        except Exception as erreur:
            illisibles.append((chemin.name, type(erreur).__name__))
            predictions.append(-1)
            confiances.append(0.0)
            continue
        predictions.append(resultat["class_index"])
        confiances.append(resultat["confidence"])

        if numero % 100 == 0:
            print(f"  {numero} / {len(chemins)} images traitées")

    return np.array(predictions), np.array(confiances), illisibles


def main():
    if not DOSSIER_PLANTDOC.exists():
        print(f"Corpus PlantDoc introuvable : {DOSSIER_PLANTDOC}")
        print("git clone --depth 1 https://github.com/pratikkayal/PlantDoc-Dataset.git "
              f"{DOSSIER_PLANTDOC}")
        return 1

    classes = inference._charger_classes()
    libelles = [c["label"] for c in classes]

    print("Collecte des images de terrain...")
    chemins, verites, manquants = rassembler_images()
    if manquants:
        print("  dossiers absents :", ", ".join(manquants))
    print(f"  {len(chemins)} images sur {len(CORRESPONDANCE)} classes\n")

    if not chemins:
        print("Aucune image collectée, vérifier l'arborescence du corpus.")
        return 1

    print("Diagnostic en cours...")
    predictions, confiances, illisibles = diagnostiquer_tout(chemins)
    if illisibles:
        print(f"  {len(illisibles)} image(s) illisible(s), écartée(s)")

    valides = predictions >= 0
    predictions, verites, confiances = predictions[valides], verites[valides], confiances[valides]

    # ------------------------------------------------------------------
    # Chiffres
    # ------------------------------------------------------------------
    from sklearn.metrics import confusion_matrix, f1_score

    exactitude = float((predictions == verites).mean())
    couvertes = sorted(CORRESPONDANCE)
    f1_par_classe = f1_score(verites, predictions, labels=couvertes,
                             average=None, zero_division=0)
    f1_macro = float(np.mean(f1_par_classe))

    print()
    print("=" * 68)
    print(f"{'':<32}{'studio':>12}{'terrain':>12}{'écart':>10}")
    print("-" * 68)
    print(f"{'Exactitude globale':<32}{EXACTITUDE_STUDIO:>11.1%}{exactitude:>12.1%}"
          f"{exactitude - EXACTITUDE_STUDIO:>+10.1%}")
    print()
    for rang, indice in enumerate(couvertes):
        studio, terrain = F1_STUDIO[indice], float(f1_par_classe[rang])
        print(f"{libelles[indice]:<32}{studio:>11.3f}{terrain:>12.3f}{terrain - studio:>+10.3f}")
    print("-" * 68)
    print(f"{'F1 macro (9 classes)':<32}"
          f"{np.mean([F1_STUDIO[i] for i in couvertes]):>11.3f}{f1_macro:>12.3f}"
          f"{f1_macro - np.mean([F1_STUDIO[i] for i in couvertes]):>+10.3f}")
    print("=" * 68)

    print()
    print(f"Confiance moyenne sur images de terrain : {confiances.mean():.1%}")
    print(f"Confiance moyenne quand la réponse est juste : {confiances[predictions == verites].mean():.1%}")
    faux = predictions != verites
    if faux.any():
        print(f"Confiance moyenne quand la réponse est fausse : {confiances[faux].mean():.1%}")

    # Vers quoi le modèle dérive-t-il ?
    derives = Counter(int(p) for p in predictions[faux])
    print()
    print("Classes prédites à tort le plus souvent :")
    for indice, nombre in derives.most_common(5):
        marque = "  (classe absente du corpus terrain)" if indice == CLASSE_NON_COUVERTE else ""
        print(f"  {nombre:>4} fois  {libelles[indice]}{marque}")

    # ------------------------------------------------------------------
    # Figures
    # ------------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    DOSSIER_RAPPORTS.mkdir(exist_ok=True)

    # Comparaison studio / terrain
    positions = np.arange(len(couvertes))
    largeur = 0.38
    figure, axe = plt.subplots(figsize=(11, 5.5))
    axe.bar(positions - largeur / 2, [F1_STUDIO[i] for i in couvertes], largeur,
            label="PlantVillage (studio)", color="#37474f")
    axe.bar(positions + largeur / 2, f1_par_classe, largeur,
            label="PlantDoc (terrain)", color="#c62828")
    axe.set_xticks(positions, [libelles[i] for i in couvertes], rotation=40, ha="right", fontsize=9)
    axe.set_ylabel("F1")
    axe.set_ylim(0, 1.05)
    axe.set_title("Généralisation du modèle : conditions de studio contre conditions de terrain")
    axe.legend()
    axe.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(DOSSIER_RAPPORTS / "robustesse_terrain.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Matrice de confusion sur les 10 classes (le modèle peut prédire la 4)
    matrice = confusion_matrix(verites, predictions, labels=list(range(10)))
    lignes_utiles = [i for i in range(10) if matrice[i].sum() > 0]
    matrice_reduite = matrice[lignes_utiles]
    normalisee = matrice_reduite / matrice_reduite.sum(axis=1, keepdims=True)

    figure, axe = plt.subplots(figsize=(10, 7))
    image = axe.imshow(normalisee, cmap="Greys", vmin=0, vmax=1)
    axe.set_xticks(range(10), libelles, rotation=45, ha="right", fontsize=8)
    axe.set_yticks(range(len(lignes_utiles)), [libelles[i] for i in lignes_utiles], fontsize=8)
    axe.set_xlabel("Classe prédite")
    axe.set_ylabel("Classe réelle")
    axe.set_title(f"Images de terrain — exactitude {exactitude:.1%}")
    for i in range(len(lignes_utiles)):
        for j in range(10):
            if matrice_reduite[i, j] > 0:
                axe.text(j, i, str(matrice_reduite[i, j]), ha="center", va="center", fontsize=7,
                         color="white" if normalisee[i, j] > 0.5 else "black")
    figure.colorbar(image, ax=axe, fraction=0.046)
    plt.tight_layout()
    plt.savefig(DOSSIER_RAPPORTS / "confusion_terrain.png", dpi=150, bbox_inches="tight")
    plt.close()

    # ------------------------------------------------------------------
    # Fichier de résultats
    # ------------------------------------------------------------------
    resultats = {
        "corpus_terrain": "PlantDoc (github.com/pratikkayal/PlantDoc-Dataset)",
        "modele": inference.VERSION_MODELE,
        "images_evaluees": int(len(predictions)),
        "classes_couvertes": len(CORRESPONDANCE),
        "classe_non_couverte": libelles[CLASSE_NON_COUVERTE],
        "studio": {
            "exactitude": EXACTITUDE_STUDIO,
            "f1_macro_9_classes": float(np.mean([F1_STUDIO[i] for i in couvertes])),
        },
        "terrain": {
            "exactitude": round(exactitude, 4),
            "f1_macro_9_classes": round(f1_macro, 4),
            "confiance_moyenne": round(float(confiances.mean()), 4),
        },
        "f1_par_classe": {
            libelles[indice]: {
                "studio": F1_STUDIO[indice],
                "terrain": round(float(f1_par_classe[rang]), 4),
                "images_terrain": int((verites == indice).sum()),
            }
            for rang, indice in enumerate(couvertes)
        },
        "limites": [
            "Maïs - Sain est absent de PlantDoc : la classe ne peut pas être mesurée, "
            "et le modèle peut la prédire à tort sans qu'aucune image ne le contredise.",
            "La correspondance entre « Bell_pepper leaf spot » et « Poivron - Tache "
            "bactérienne » est une approximation : PlantDoc ne précise pas l'agent.",
            "Les classes comptant une soixantaine d'images ont une marge d'erreur large.",
        ],
    }

    with open(DOSSIER_RAPPORTS / "robustesse_terrain.json", "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    print()
    print("Écrit dans reports/ : robustesse_terrain.json, robustesse_terrain.png, "
          "confusion_terrain.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
