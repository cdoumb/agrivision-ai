"""
Generateur du notebook de complement d'evaluation (Binome B).

Produit : notebooks/03_complement_studio_v2.ipynb

POURQUOI CE NOTEBOOK EXISTE

model_card_v2.json donne, pour le studio, l'exactitude et le F1 macro, et rien
de plus. Le detail classe par classe n'y figure que pour le terrain. Or le
rapport compare studio et terrain classe par classe : sans le F1 studio par
classe du v2, cette comparaison ne peut se tracer que pour le v1.

Ce notebook comble ce trou, et rien d'autre. Il ne reentraine aucun modele : il
recharge le v1 et le v2 depuis le Drive et les evalue sur le jeu de test studio,
reconstruit a l'identique depuis le manifeste de decoupage du lot A. PlantWild
n'est pas telecharge, il ne sert qu'a l'entrainement.

Duree indicative : 10 a 20 minutes, dominees par le telechargement de
PlantVillage. Un GPU accelere l'inference mais n'est pas indispensable.

Regenerer avec :
    python notebooks/build_notebook_complement.py
"""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SORTIE = RACINE / "03_complement_studio_v2.ipynb"


def md(texte):
    return {"cell_type": "markdown", "metadata": {},
            "source": texte.strip("\n").splitlines(keepends=True)}


def code(texte):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": texte.strip("\n").splitlines(keepends=True)}


CELLULES = []

# ---------------------------------------------------------------------------
CELLULES.append(md("""
# AgriVision-AI - Complement d'evaluation studio (v1 et v2)

**Lot B (Faustin).** Ce notebook ne produit aucun modele. Il repond a un manque
precis : `model_card_v2.json` ne contient pas le F1 studio **par classe** du v2,
alors que le rapport en a besoin pour comparer studio et terrain classe par
classe.

## Ce qu'il fait

1. recharge le v1 et le v2 depuis le Drive, sans les modifier ;
2. reconstruit le jeu de test studio a l'identique, depuis le manifeste du lot A ;
3. calcule le F1 par classe des deux modeles sur ce jeu ;
4. verifie que les exactitudes retrouvees correspondent a celles deja publiees ;
5. ajoute le resultat dans `model_card_v2.json`, sans rien ecraser d'autre.

## Ce qu'il ne fait pas

Aucun entrainement, aucun telechargement de PlantWild (2,5 Go inutiles ici),
aucune modification des fichiers `.keras`.

Le point 4 est le garde-fou : si les exactitudes retrouvees ne correspondent pas
a 96,64 % et 94,36 %, c'est que le jeu de test reconstruit n'est pas celui
d'origine, et le resultat par classe ne doit alors pas etre publie.
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 1. Drive et chemins

Les deux modeles doivent se trouver dans `MyDrive/AgriVision-AI/models/`.
"""))

CELLULES.append(code("""
from pathlib import Path
from google.colab import drive

drive.mount("/content/drive")

DOSSIER_TRAVAIL = Path("/content/drive/MyDrive/AgriVision-AI")
DOSSIER_MODELES = DOSSIER_TRAVAIL / "models"
DOSSIER_RAPPORTS = DOSSIER_TRAVAIL / "reports"
DOSSIER_RAPPORTS.mkdir(parents=True, exist_ok=True)

DONNEES = Path("/content/data")
DONNEES.mkdir(parents=True, exist_ok=True)

CHEMIN_V1 = DOSSIER_MODELES / "mobilenetv2_v1.keras"
CHEMIN_V2 = DOSSIER_MODELES / "mobilenetv2_v2.keras"
CHEMIN_FICHE_V2 = DOSSIER_RAPPORTS / "model_card_v2.json"

for chemin in (CHEMIN_V1, CHEMIN_V2, CHEMIN_FICHE_V2):
    print(f"{'ok  ' if chemin.exists() else 'MANQUE'}  {chemin}")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 2. PlantVillage

Seul corpus necessaire ici. Le decoupage n'est pas recalcule : il est relu depuis
le manifeste du lot A, ce qui garantit que le jeu de test est exactement celui
sur lequel les chiffres publies ont ete obtenus.
"""))

CELLULES.append(code("""
import os

!pip install -q kaggle

if not Path("/root/.kaggle/kaggle.json").exists():
    from google.colab import files
    print("Deposer kaggle.json :")
    files.upload()
    os.makedirs("/root/.kaggle", exist_ok=True)
    !mv -f kaggle.json /root/.kaggle/kaggle.json
    !chmod 600 /root/.kaggle/kaggle.json

RACINE_PV = DONNEES / "plantvillage dataset" / "color"

if not RACINE_PV.exists():
    !kaggle datasets download -d abdallahalidev/plantvillage-dataset -p {str(DONNEES)} --force
    !unzip -q -o {str(DONNEES / 'plantvillage-dataset.zip')} -d {str(DONNEES)}

print("PlantVillage :", len(list(RACINE_PV.iterdir())), "dossiers")
"""))

CELLULES.append(code("""
import shutil
import subprocess
import urllib.request

import pandas as pd

CHEMIN_MANIFESTE = DONNEES / "split_manifest.csv"
DEPOT_PROJET = Path("/content/agrivision-ai")
URL_RAW = ("https://raw.githubusercontent.com/cdoumb/agrivision-ai/"
           "main/reports/split_manifest.csv")

if not CHEMIN_MANIFESTE.exists():
    try:
        if not DEPOT_PROJET.exists():
            subprocess.run(["git", "clone", "--depth", "1",
                            "https://github.com/cdoumb/agrivision-ai.git",
                            str(DEPOT_PROJET)], check=True)
        shutil.copy(DEPOT_PROJET / "reports" / "split_manifest.csv", CHEMIN_MANIFESTE)
        print("Manifeste recupere via git clone.")
    except Exception as erreur:
        print("Echec du git clone :", erreur)

if not CHEMIN_MANIFESTE.exists():
    try:
        urllib.request.urlretrieve(URL_RAW, CHEMIN_MANIFESTE)
        print("Manifeste recupere via telechargement direct.")
    except Exception as erreur:
        print("Echec du telechargement direct :", erreur)

if not CHEMIN_MANIFESTE.exists():
    print("Deposer reports/split_manifest.csv a la main :")
    from google.colab import files
    files.upload()
    shutil.move("split_manifest.csv", str(CHEMIN_MANIFESTE))

manifeste = pd.read_csv(CHEMIN_MANIFESTE)
print(len(manifeste), "lignes")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 3. Reconstruction du jeu de test studio

La correspondance entre les classes du projet et les dossiers PlantVillage est
reprise telle quelle du notebook 02. Elle ne doit surtout pas etre modifiee :
c'est elle qui donne un sens aux indices du modele.
"""))

CELLULES.append(code("""
import re

# indice -> (libelle projet, dossier PlantVillage)
CLASSES = [
    (0, "Tomate - Saine",              "Tomato___healthy"),
    (1, "Tomate - Mildiou tardif",     "Tomato___Late_blight"),
    (2, "Tomate - Tache bacterienne",  "Tomato___Bacterial_spot"),
    (3, "Tomate - Septoriose",         "Tomato___Septoria_leaf_spot"),
    (4, "Mais - Sain",                 "Corn_(maize)___healthy"),
    (5, "Mais - Rouille commune",      "Corn_(maize)___Common_rust_"),
    (6, "Mais - Helminthosporiose",    "Corn_(maize)___Northern_Leaf_Blight"),
    (7, "Mais - Cercosporiose",        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"),
    (8, "Poivron - Sain",              "Pepper,_bell___healthy"),
    (9, "Poivron - Tache bacterienne", "Pepper,_bell___Bacterial_spot"),
]

NB_CLASSES = len(CLASSES)
LIBELLES = [c[1] for c in CLASSES]

NOM_MANIFESTE = {
    0: "Tomate_Saine", 1: "Tomate_Mildiou_tardif", 2: "Tomate_Tache_bacterienne",
    3: "Tomate_Septoriose", 4: "Mais_Sain", 5: "Mais_Rouille_commune",
    6: "Mais_Helminthosporiose", 7: "Mais_Cercosporiose",
    8: "Poivron_Sain", 9: "Poivron_Tache_bacterienne",
}
INDICE_MANIFESTE = {v: k for k, v in NOM_MANIFESTE.items()}
PREFIXE = re.compile(r"^\\d+_")

disponibles = {}
for indice, _libelle, dossier in CLASSES:
    chemin = RACINE_PV / dossier
    if not chemin.exists():
        raise SystemExit(f"Dossier PlantVillage introuvable : {chemin}")
    disponibles[indice] = {p.name: p for p in chemin.iterdir() if p.is_file()}

chemins_test, etiquettes_test = [], []
absents = 0
for classe, split, nom_fichier, _src in manifeste.itertuples(index=False, name=None):
    if split != "test":
        continue
    indice = INDICE_MANIFESTE[classe]
    chemin = disponibles[indice].get(PREFIXE.sub("", nom_fichier))
    if chemin is None:
        absents += 1
        continue
    chemins_test.append(str(chemin))
    etiquettes_test.append(indice)

attendus = int((manifeste["split"] == "test").sum())
taux = 100 * len(chemins_test) / attendus
print(f"Jeu de test studio reconstruit : {len(chemins_test)} / {attendus} images "
      f"({taux:.1f} %), {absents} introuvables")
if taux < 99:
    print("  ATTENTION : reconstruction incomplete, ne pas publier le resultat.")
"""))

CELLULES.append(code("""
import numpy as np
import tensorflow as tf

TAILLE = 224
TAILLE_LOT = 32
AUTOTUNE = tf.data.AUTOTUNE


def charger(chemin, etiquette):
    octets = tf.io.read_file(chemin)
    image = tf.io.decode_image(octets, channels=3, expand_animations=False)
    image = tf.image.resize(image, (TAILLE, TAILLE))
    image.set_shape([TAILLE, TAILLE, 3])
    return image, etiquette


# Aucune augmentation, aucun melange : c'est un jeu d'evaluation.
jeu_test_studio = (tf.data.Dataset
                   .from_tensor_slices((chemins_test, tf.one_hot(etiquettes_test, NB_CLASSES)))
                   .map(charger, num_parallel_calls=AUTOTUNE)
                   .batch(TAILLE_LOT)
                   .prefetch(AUTOTUNE))

verites = np.array(etiquettes_test)
print("Jeu pret :", len(chemins_test), "images en", -(-len(chemins_test) // TAILLE_LOT), "lots")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 4. Evaluation des deux modeles

Le controle d'integrite se joue ici. Les exactitudes retrouvees doivent
correspondre a celles publiees : **96,64 %** pour le v1 et **94,36 %** pour le v2.
Un ecart superieur a un demi-point signale que le jeu reconstruit n'est pas le
bon, et le resultat par classe ne doit alors pas etre publie.
"""))

CELLULES.append(code("""
from sklearn.metrics import f1_score

EXACTITUDES_PUBLIEES = {"v1": 0.9664, "v2": 0.9436}
TOLERANCE = 0.005

modeles = {
    "v1": tf.keras.models.load_model(CHEMIN_V1),
    "v2": tf.keras.models.load_model(CHEMIN_V2),
}

resultats = {}
for nom, modele in modeles.items():
    probabilites = modele.predict(jeu_test_studio, verbose=0)
    predictions = probabilites.argmax(axis=1)
    resultats[nom] = {
        "exactitude": float((predictions == verites).mean()),
        "f1_macro": float(f1_score(verites, predictions, average="macro", zero_division=0)),
        "f1_par_classe": f1_score(verites, predictions, average=None, zero_division=0),
    }

print(f"{'':<12}{'retrouve':>12}{'publie':>10}{'ecart':>10}")
print("-" * 44)
conforme = True
for nom, resultat in resultats.items():
    publiee = EXACTITUDES_PUBLIEES[nom]
    ecart = resultat["exactitude"] - publiee
    if abs(ecart) > TOLERANCE:
        conforme = False
    print(f"{nom:<12}{resultat['exactitude']:>11.2%}{publiee:>10.2%}{ecart:>+10.2%}")

print()
print("Controle d'integrite : conforme." if conforme else
      "Controle d'integrite : ECHEC. Ne pas publier, le jeu de test n'est pas le bon.")
"""))

CELLULES.append(code("""
print(f"{'Classe':<32}{'v1':>9}{'v2':>9}{'gain':>9}")
print("-" * 59)
for indice, libelle in enumerate(LIBELLES):
    f1_v1 = resultats["v1"]["f1_par_classe"][indice]
    f1_v2 = resultats["v2"]["f1_par_classe"][indice]
    print(f"{libelle:<32}{f1_v1:>9.4f}{f1_v2:>9.4f}{f1_v2 - f1_v1:>+9.4f}")

print("-" * 59)
print(f"{'F1 macro':<32}{resultats['v1']['f1_macro']:>9.4f}"
      f"{resultats['v2']['f1_macro']:>9.4f}"
      f"{resultats['v2']['f1_macro'] - resultats['v1']['f1_macro']:>+9.4f}")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 5. Mise a jour de la fiche du modele

La cle `f1_studio_par_classe` est ajoutee dans `resultats`, a cote de
`f1_terrain_par_classe` qui existe deja. Rien d'autre n'est touche, et la fiche
n'est ecrite que si le controle d'integrite est passe.
"""))

CELLULES.append(code("""
import json

if not conforme:
    raise SystemExit("Controle d'integrite en echec : la fiche n'est pas modifiee.")

with open(CHEMIN_FICHE_V2, encoding="utf-8") as f:
    fiche = json.load(f)

fiche["resultats"]["f1_studio_par_classe"] = {
    libelle: {
        "v1": round(float(resultats["v1"]["f1_par_classe"][indice]), 4),
        "v2": round(float(resultats["v2"]["f1_par_classe"][indice]), 4),
    }
    for indice, libelle in enumerate(LIBELLES)
}

with open(CHEMIN_FICHE_V2, "w", encoding="utf-8") as f:
    json.dump(fiche, f, ensure_ascii=False, indent=2)

print("Fiche mise a jour :", CHEMIN_FICHE_V2)
print()
print(json.dumps(fiche["resultats"]["f1_studio_par_classe"], ensure_ascii=False, indent=2))
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 6. Et ensuite

Recuperer `model_card_v2.json` depuis le Drive et le redeposer dans `reports/`
du depot, en remplacement de la version actuelle. La comparaison studio contre
terrain par classe devient alors tracable pour les deux modeles.
"""))


notebook = {
    "cells": CELLULES,
    "metadata": {
        "colab": {"provenance": [], "gpuType": "T4"},
        "accelerator": "GPU",
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

SORTIE.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook genere : {SORTIE}")
