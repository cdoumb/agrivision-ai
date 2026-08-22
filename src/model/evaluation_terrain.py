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

Le modèle évalué est celui que charge src/model/inference.py, donc le v2 par
défaut. Pour mesurer le v1, pointer AGRIVISION_MODELE dessus :

    AGRIVISION_MODELE=models/mobilenetv2_v1.keras python src/model/evaluation_terrain.py

Les chiffres de studio auxquels le terrain est comparé sont lus dans la fiche du
modèle chargé, dans reports/. Ils ne sont pas codés en dur : comparer le terrain
d'une version au studio d'une autre produirait un tableau faux sans que rien ne
le signale.

Usage :
    python src/model/evaluation_terrain.py

Produit dans reports/, suffixé par la version (v1, v2) :
    robustesse_terrain_<v>.json   les chiffres
    robustesse_terrain_<v>.png    comparaison studio / terrain par classe
    robustesse_confusion_<v>.png  matrice de confusion sur images de terrain
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

def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte)
                   if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# Référence studio
# ---------------------------------------------------------------------------
# Les chiffres de studio étaient autrefois recopiés en dur ici, ceux du v1. Le
# jour où le service est passé au v2, ce script a continué de comparer le
# terrain du v2 au studio du v1 : un tableau faux, sans le moindre message
# d'erreur. Ils sont désormais lus dans la fiche du modèle réellement chargé, et
# le script refuse de tourner si cette fiche est absente.

def _cle_version(version):
    """« mobilenetv2-v2.0 » donne « v2 », clé utilisée dans les fiches."""
    fin = version.rsplit("-", 1)[-1]
    return fin.split(".")[0]


def _extraire_studio(fiche, cle, indice_par_libelle):
    """
    Résultats de studio d'une fiche, quel que soit son format.

    Le v1 les range sous `resultats_test`, le v2 sous
    `resultats.studio_PlantVillage_test`. Renvoie (exactitude, {indice: f1}) ;
    le détail par classe peut être vide, il n'est pas présent dans toutes les
    fiches.
    """
    def indice_de(libelle):
        return indice_par_libelle.get(sans_accents(libelle).strip().lower())

    resultats_v1 = fiche.get("resultats_test")
    if resultats_v1:
        detail = resultats_v1.get("f1_par_classe", {})
        f1 = {indice_de(l): v for l, v in detail.items() if indice_de(l) is not None}
        return resultats_v1.get("exactitude"), f1

    resultats = fiche.get("resultats", {})
    studio = resultats.get("studio_PlantVillage_test", {}).get(cle, {})
    detail = resultats.get("f1_studio_par_classe", {})
    f1 = {indice_de(l): v[cle] for l, v in detail.items()
          if indice_de(l) is not None and cle in v}
    return studio.get("exactitude"), f1


def charger_reference_studio(version, libelles):
    """
    Cherche dans reports/ la fiche dont `model_version` vaut `version`.

    Renvoie (exactitude_studio, {indice: f1_studio}). Lève SystemExit si aucune
    fiche ne correspond : sans référence, la comparaison studio contre terrain
    n'a pas de sens et vaut mieux ne pas être produite du tout.
    """
    indice_par_libelle = {sans_accents(l).strip().lower(): i
                          for i, l in enumerate(libelles)}

    for chemin in sorted(DOSSIER_RAPPORTS.glob("*.json")):
        try:
            with open(chemin, encoding="utf-8") as f:
                fiche = json.load(f)
        except (ValueError, OSError):
            continue
        if not isinstance(fiche, dict) or fiche.get("model_version") != version:
            continue

        exactitude, f1 = _extraire_studio(fiche, _cle_version(version), indice_par_libelle)
        if exactitude is None:
            continue
        print(f"Référence de studio : {chemin.name} ({version})")
        if not f1:
            print("  le détail par classe manque dans cette fiche : la comparaison "
                  "par classe sera omise.")
        return float(exactitude), f1

    raise SystemExit(
        f"Aucune fiche de modèle pour « {version} » dans {DOSSIER_RAPPORTS}.\n"
        "Les résultats de studio y sont lus, ils ne sont plus codés en dur. "
        "Déposer le model_card correspondant avant de relancer."
    )


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

    version = inference.VERSION_MODELE
    exactitude_studio, f1_studio = charger_reference_studio(version, libelles)
    suffixe = _cle_version(version)

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

    # Le détail par classe n'existe que si la fiche du modèle le porte.
    comparables = [i for i in couvertes if i in f1_studio]
    f1_macro_studio = (float(np.mean([f1_studio[i] for i in comparables]))
                       if comparables else None)

    print()
    print("=" * 68)
    print(f"Modèle : {version}")
    print(f"{'':<32}{'studio':>12}{'terrain':>12}{'écart':>10}")
    print("-" * 68)
    print(f"{'Exactitude globale':<32}{exactitude_studio:>11.1%}{exactitude:>12.1%}"
          f"{exactitude - exactitude_studio:>+10.1%}")
    print()
    if comparables:
        for rang, indice in enumerate(couvertes):
            terrain = float(f1_par_classe[rang])
            if indice not in f1_studio:
                print(f"{libelles[indice]:<32}{'—':>11}{terrain:>12.3f}{'':>10}")
                continue
            studio = f1_studio[indice]
            print(f"{libelles[indice]:<32}{studio:>11.3f}{terrain:>12.3f}"
                  f"{terrain - studio:>+10.3f}")
        print("-" * 68)
        print(f"{'F1 macro (9 classes)':<32}{f1_macro_studio:>11.3f}{f1_macro:>12.3f}"
              f"{f1_macro - f1_macro_studio:>+10.3f}")
    else:
        for rang, indice in enumerate(couvertes):
            print(f"{libelles[indice]:<32}{'—':>11}{float(f1_par_classe[rang]):>12.3f}")
        print("-" * 68)
        print(f"{'F1 macro (9 classes)':<32}{'—':>11}{f1_macro:>12.3f}")
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

    # Comparaison studio / terrain. Sans détail de studio par classe, la figure
    # n'aurait qu'une série : on ne la produit pas, une comparaison à une seule
    # colonne induirait en erreur.
    positions = np.arange(len(couvertes))
    largeur = 0.38
    if comparables:
        figure, axe = plt.subplots(figsize=(11, 5.5))
        axe.bar(positions - largeur / 2, [f1_studio.get(i, 0.0) for i in couvertes], largeur,
                label="PlantVillage (studio)", color="#37474f")
        axe.bar(positions + largeur / 2, f1_par_classe, largeur,
                label="PlantDoc (terrain)", color="#c62828")
        axe.set_xticks(positions, [libelles[i] for i in couvertes], rotation=40, ha="right", fontsize=9)
        axe.set_ylabel("F1")
        axe.set_ylim(0, 1.05)
        axe.set_title(f"Généralisation du modèle {version} : "
                      "conditions de studio contre conditions de terrain")
        axe.legend()
        axe.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(DOSSIER_RAPPORTS / f"robustesse_terrain_{suffixe}.png",
                    dpi=150, bbox_inches="tight")
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
    axe.set_title(f"Images de terrain, modèle {version} — exactitude {exactitude:.1%}")
    for i in range(len(lignes_utiles)):
        for j in range(10):
            if matrice_reduite[i, j] > 0:
                axe.text(j, i, str(matrice_reduite[i, j]), ha="center", va="center", fontsize=7,
                         color="white" if normalisee[i, j] > 0.5 else "black")
    figure.colorbar(image, ax=axe, fraction=0.046)
    plt.tight_layout()
    # Préfixe « robustesse_ » pour toutes les sorties de ce script : le notebook
    # v2 produit de son côté un confusion_terrain_v2.png qui compare les deux
    # modèles, ce n'est pas la même figure et elle ne doit pas être écrasée.
    plt.savefig(DOSSIER_RAPPORTS / f"robustesse_confusion_{suffixe}.png",
                dpi=150, bbox_inches="tight")
    plt.close()

    # ------------------------------------------------------------------
    # Fichier de résultats
    # ------------------------------------------------------------------
    resultats = {
        "corpus_terrain": "PlantDoc (github.com/pratikkayal/PlantDoc-Dataset)",
        "modele": version,
        # Le notebook Colab mesure les mêmes images via tf.image.resize et
        # obtient des chiffres proches mais pas identiques, à un demi-point
        # près. Preciser la chaine evite de comparer deux mesures qui ne
        # passent pas par le meme pretraitement.
        "chaine_mesure": "service d'inférence (Pillow), src/model/inference.py",
        "images_evaluees": int(len(predictions)),
        "classes_couvertes": len(CORRESPONDANCE),
        "classe_non_couverte": libelles[CLASSE_NON_COUVERTE],
        "studio": {
            "exactitude": exactitude_studio,
            "f1_macro_9_classes": f1_macro_studio,
        },
        "terrain": {
            "exactitude": round(exactitude, 4),
            "f1_macro_9_classes": round(f1_macro, 4),
            "confiance_moyenne": round(float(confiances.mean()), 4),
        },
        "f1_par_classe": {
            libelles[indice]: {
                "studio": f1_studio.get(indice),
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

    with open(DOSSIER_RAPPORTS / f"robustesse_terrain_{suffixe}.json", "w",
              encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    ecrits = [f"robustesse_terrain_{suffixe}.json",
              f"robustesse_confusion_{suffixe}.png"]
    if comparables:
        ecrits.insert(1, f"robustesse_terrain_{suffixe}.png")

    print()
    print("Écrit dans reports/ : " + ", ".join(ecrits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
