"""
Generateur du notebook d'amelioration de la robustesse (Binome B).

Produit : notebooks/02_amelioration_robustesse.ipynb

Le modele v1, entraine uniquement sur PlantVillage (studio), tombe de 96,6 %
a 35,7 % sur des photographies de terrain. Ce notebook produit un modele v2
qui corrige cela sur deux fronts : des images de terrain a l'entrainement, et
cinq corrections dans le code d'entrainement lui-meme.

Regenerer avec :
    python notebooks/build_notebook_v2.py
"""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SORTIE = RACINE / "02_amelioration_robustesse.ipynb"


def md(texte):
    return {"cell_type": "markdown", "metadata": {},
            "source": texte.strip("\n").splitlines(keepends=True)}


def code(texte):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": texte.strip("\n").splitlines(keepends=True)}


CELLULES = []

# ---------------------------------------------------------------------------
CELLULES.append(md("""
# AgriVision-AI - Amelioration de la robustesse (modele v2)

**Lot B (Faustin).** Le modele v1 atteint 96,64 % sur le jeu de test PlantVillage
mais seulement **35,7 %** sur PlantDoc, un corpus de photographies prises au champ.
Pire : sa confiance reste a 80,9 % alors qu'il se trompe deux fois sur trois, et il
ne reconnait aucune des 63 tomates saines de terrain.

Ce notebook produit un modele v2. Il ne remplace pas le v1 : les deux sont conserves
et compares sur les memes jeux de test.

## Ce qui change

**Cote donnees.** PlantWild est ajoute a l'entrainement : 18 542 photographies prises
en conditions reelles, dont les 10 classes du projet. PlantVillage est conserve : le
modele doit rester bon en studio aussi.

**Cote code, cinq corrections.**

| # | Correction | Ce que ca vise |
|---|---|---|
| 1 | Augmentation etendue (teinte, saturation, occlusions, flou) | le modele ne dependait que de conditions de studio |
| 2 | Degel de 80 couches au lieu de 40 | les couches de texture restaient figees sur ImageNet |
| 3 | Lissage des etiquettes | la surconfiance a 80,9 % malgre les erreurs |
| 4 | Melange d'images (mixup) | la generalisation hors du domaine d'entrainement |
| 5 | Pooling moyenne **et** maximum | une petite lesion sur 2 cases de la grille 7x7 etait noyee dans la moyenne des 49 |

## Le protocole d'evaluation

C'est le point sur lequel il ne faut pas tricher.

| Jeu | Role | Vu a l'entrainement |
|---|---|---|
| PlantVillage train/val | entrainement | oui |
| PlantWild train/val | entrainement | oui |
| **PlantVillage test** | verifie qu'on n'a rien casse en studio | non |
| **PlantDoc (942 images)** | **juge de la robustesse reelle** | **jamais** |

PlantDoc n'entre a aucun moment dans l'entrainement. C'est un corpus d'une autre
origine que PlantWild, ce qui rend la comparaison v1 / v2 honnete : les deux modeles
sont juges sur exactement les memes images inconnues.

Duree indicative : 20 a 30 min de telechargement, 40 a 60 min d'entrainement sur GPU T4.
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 1. GPU et environnement
"""))

CELLULES.append(code("""
import sys
import tensorflow as tf

print("Python     :", sys.version.split()[0])
print("TensorFlow :", tf.__version__)

gpus = tf.config.list_physical_devices("GPU")
if gpus:
    print("GPU        :", gpus[0].name)
    !nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else:
    print()
    print("!!! AUCUN GPU !!!  Execution > Modifier le type d'execution > GPU, puis relancer.")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 2. Drive et dossiers de travail

Le modele v1 doit se trouver dans `MyDrive/AgriVision-AI/models/` : il sert de point
de depart a l'entrainement et de terme de comparaison.
"""))

CELLULES.append(code("""
from pathlib import Path
from google.colab import drive

drive.mount("/content/drive")

DOSSIER_TRAVAIL = Path("/content/drive/MyDrive/AgriVision-AI")
DOSSIER_MODELES = DOSSIER_TRAVAIL / "models"
DOSSIER_RAPPORTS = DOSSIER_TRAVAIL / "reports"
for d in (DOSSIER_MODELES, DOSSIER_RAPPORTS):
    d.mkdir(parents=True, exist_ok=True)

DONNEES = Path("/content/data")
DONNEES.mkdir(parents=True, exist_ok=True)

CHEMIN_V1 = DOSSIER_MODELES / "mobilenetv2_v1.keras"
CHEMIN_V2 = DOSSIER_MODELES / "mobilenetv2_v2.keras"

print("Modele v1 present :", CHEMIN_V1.exists())
if not CHEMIN_V1.exists():
    print("  -> deposer mobilenetv2_v1.keras dans", DOSSIER_MODELES)
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 3. Les trois corpus

- **PlantVillage** (Kaggle, studio) : deja utilise pour le v1, on reprend le meme
  decoupage via le manifeste du lot A ;
- **PlantWild** (Hugging Face, terrain) : nouveau, 2,5 Go ;
- **PlantDoc** (GitHub, terrain) : uniquement pour juger, jamais pour entrainer.

PlantWild est distribue sous licence CC BY-NC-ND 4.0 : usage non commercial, ce qui
couvre un projet academique. A citer dans le rapport.
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
# PlantWild : une archive unique de 2,5 Go, pas de telechargement partiel possible.
ARCHIVE_PW = DONNEES / "plantwild.zip"
RACINE_PW = DONNEES / "plantwild"
URL_PW = "https://huggingface.co/datasets/uqtwei2/PlantWild/resolve/main/plantwild.zip"

if not RACINE_PW.exists():
    if not ARCHIVE_PW.exists():
        !wget -q --show-progress -O {str(ARCHIVE_PW)} {URL_PW}
    RACINE_PW.mkdir(parents=True, exist_ok=True)
    print("Decompression de 2,5 Go, comptez quelques minutes...")
    !unzip -q -o {str(ARCHIVE_PW)} -d {str(RACINE_PW)}

# La structure interne de l'archive n'est pas documentee : on la decouvre.
dossiers_images = sorted({p.parent for p in RACINE_PW.rglob("*.jpg")} |
                         {p.parent for p in RACINE_PW.rglob("*.JPG")} |
                         {p.parent for p in RACINE_PW.rglob("*.png")})
print(len(dossiers_images), "dossiers contenant des images")
print()
for d in dossiers_images[:8]:
    print("  ", d.relative_to(RACINE_PW), "->", len(list(d.glob("*"))), "fichiers")
"""))

CELLULES.append(code("""
# PlantDoc : le juge. Telecharge maintenant pour verifier qu'il est disponible,
# mais utilise uniquement a l'evaluation.
RACINE_PD = DONNEES / "plantdoc"
if not RACINE_PD.exists():
    !git clone --depth 1 -q https://github.com/pratikkayal/PlantDoc-Dataset.git {str(RACINE_PD)}

print("PlantDoc :", "ok" if (RACINE_PD / "train").exists() else "ECHEC du telechargement")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 4. Les 10 classes dans les trois corpus

Chaque corpus nomme les maladies a sa facon. La correspondance est ecrite
explicitement plutot que devinee, et verifiee par comptage : un dossier absent ou
vide se voit immediatement.

L'indice de chaque classe est fige par `classes.json` et par le contrat d'interface.
Il ne doit jamais changer, l'API renvoie ce nombre.
"""))

CELLULES.append(code("""
import re

# indice -> (libelle projet, dossier PlantVillage, classe PlantWild, classe PlantDoc)
CLASSES = [
    (0, "Tomate - Saine",              "Tomato___healthy",
        "tomato leaf",                 "Tomato leaf"),
    (1, "Tomate - Mildiou tardif",     "Tomato___Late_blight",
        "tomato late blight",          "Tomato leaf late blight"),
    (2, "Tomate - Tache bacterienne",  "Tomato___Bacterial_spot",
        "tomato bacterial leaf spot",  "Tomato leaf bacterial spot"),
    (3, "Tomate - Septoriose",         "Tomato___Septoria_leaf_spot",
        "tomato septoria leaf spot",   "Tomato Septoria leaf spot"),
    (4, "Mais - Sain",                 "Corn_(maize)___healthy",
        "corn leaf",                   None),
    (5, "Mais - Rouille commune",      "Corn_(maize)___Common_rust_",
        "corn rust",                   "Corn rust leaf"),
    (6, "Mais - Helminthosporiose",    "Corn_(maize)___Northern_Leaf_Blight",
        "corn northern leaf blight",   "Corn leaf blight"),
    (7, "Mais - Cercosporiose",        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
        "corn gray leaf spot",         "Corn Gray leaf spot"),
    (8, "Poivron - Sain",              "Pepper,_bell___healthy",
        "bell pepper leaf",            "Bell_pepper leaf"),
    (9, "Poivron - Tache bacterienne", "Pepper,_bell___Bacterial_spot",
        "bell pepper leaf spot",       "Bell_pepper leaf spot"),
]

NB_CLASSES = len(CLASSES)
LIBELLES = [c[1] for c in CLASSES]


def normaliser(nom):
    \"\"\"Ramene un nom de dossier a une forme comparable.\"\"\"
    nom = re.sub(r"[_\\-]+", " ", str(nom).lower())
    return re.sub(r"\\s+", " ", nom).strip()


# Index des dossiers PlantWild, par nom normalise
index_pw = {}
for d in dossiers_images:
    index_pw.setdefault(normaliser(d.name), []).append(d)

print(f"{'Classe':<32}{'PlantVillage':>13}{'PlantWild':>11}{'PlantDoc':>10}")
print("-" * 68)

dossiers_par_classe = {}
for indice, libelle, nom_pv, nom_pw, nom_pd in CLASSES:
    chemin_pv = RACINE_PV / nom_pv
    n_pv = len(list(chemin_pv.iterdir())) if chemin_pv.exists() else 0

    trouves_pw = index_pw.get(normaliser(nom_pw), [])
    n_pw = sum(len([f for f in d.iterdir() if f.is_file()]) for d in trouves_pw)

    n_pd = 0
    if nom_pd:
        for partie in ("train", "test"):
            d = RACINE_PD / partie / nom_pd
            if d.exists():
                n_pd += len([f for f in d.iterdir() if f.is_file()])

    dossiers_par_classe[indice] = {"pv": chemin_pv, "pw": trouves_pw}
    marque = "" if n_pw else "   <- CLASSE PLANTWILD INTROUVABLE"
    print(f"{libelle:<32}{n_pv:>13}{n_pw:>11}{n_pd if nom_pd else '-':>10}{marque}")

print()
introuvables = [LIBELLES[i] for i, _, _, nom_pw, _ in CLASSES
                if not index_pw.get(normaliser(nom_pw))]
if introuvables:
    print("A CORRIGER avant de continuer, classes PlantWild introuvables :")
    for nom in introuvables:
        print("   -", nom)
    print()
    print("Noms de dossiers PlantWild disponibles (extrait) :")
    for nom in sorted(index_pw)[:40]:
        print("   ", nom)
else:
    print("Les 10 classes sont presentes dans PlantVillage et PlantWild.")
    print("PlantDoc en couvre 9 : Mais - Sain y est absent.")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 5. Constitution des jeux

**PlantVillage** garde exactement le decoupage du lot A, relu depuis le manifeste.
C'est ce qui rend le test studio comparable entre v1 et v2.

**PlantWild** est decoupe ici, 80 % entrainement et 20 % validation, par classe et
avec une graine fixe pour etre reproductible. Aucune image de PlantWild ne va dans un
jeu de test : le juge sera PlantDoc, d'origine differente.
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

CELLULES.append(code("""
import numpy as np

PREFIXE = re.compile(r"^\\d+_")
NOM_MANIFESTE = {
    0: "Tomate_Saine", 1: "Tomate_Mildiou_tardif", 2: "Tomate_Tache_bacterienne",
    3: "Tomate_Septoriose", 4: "Mais_Sain", 5: "Mais_Rouille_commune",
    6: "Mais_Helminthosporiose", 7: "Mais_Cercosporiose",
    8: "Poivron_Sain", 9: "Poivron_Tache_bacterienne",
}
INDICE_MANIFESTE = {v: k for k, v in NOM_MANIFESTE.items()}

# --- PlantVillage, decoupage du lot A ---
disponibles = {indice: {p.name: p for p in d["pv"].iterdir() if p.is_file()}
               for indice, d in dossiers_par_classe.items()}

pv = {"train": ([], []), "val": ([], []), "test": ([], [])}
absents = 0
for classe, split, nom_fichier, _src in manifeste.itertuples(index=False, name=None):
    indice = INDICE_MANIFESTE[classe]
    nom = PREFIXE.sub("", nom_fichier)
    chemin = disponibles[indice].get(nom)
    if chemin is None:
        absents += 1
        continue
    pv[split][0].append(str(chemin))
    pv[split][1].append(indice)

taux = 100 * (len(manifeste) - absents) / len(manifeste)
print(f"PlantVillage  train {len(pv['train'][0]):>6}  val {len(pv['val'][0]):>5}  "
      f"test {len(pv['test'][0]):>5}   correspondance {taux:.1f} %")
if taux < 99:
    print("  ATTENTION : correspondance incomplete, verifier avant de continuer.")
"""))

CELLULES.append(code("""
# --- PlantWild, decoupage fait ici : 80 / 20 par classe ---
GRAINE = 42
generateur = np.random.default_rng(GRAINE)

pw = {"train": ([], []), "val": ([], [])}
print(f"{'Classe':<32}{'train':>8}{'val':>7}")
print("-" * 47)
for indice, _, _, _, _ in CLASSES:
    fichiers = []
    for d in dossiers_par_classe[indice]["pw"]:
        fichiers += [str(p) for p in sorted(d.iterdir())
                     if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    fichiers = sorted(set(fichiers))
    generateur.shuffle(fichiers)

    coupe = int(0.8 * len(fichiers))
    pw["train"][0].extend(fichiers[:coupe])
    pw["train"][1].extend([indice] * coupe)
    pw["val"][0].extend(fichiers[coupe:])
    pw["val"][1].extend([indice] * (len(fichiers) - coupe))
    print(f"{LIBELLES[indice]:<32}{coupe:>8}{len(fichiers) - coupe:>7}")

print("-" * 47)
print(f"{'PlantWild total':<32}{len(pw['train'][0]):>8}{len(pw['val'][0]):>7}")
"""))

CELLULES.append(code("""
# --- Fusion : le modele apprend les deux mondes ---
chemins = {
    "train": pv["train"][0] + pw["train"][0],
    "val":   pv["val"][0] + pw["val"][0],
    "test_studio": pv["test"][0],
}
etiquettes = {
    "train": pv["train"][1] + pw["train"][1],
    "val":   pv["val"][1] + pw["val"][1],
    "test_studio": pv["test"][1],
}

print(f"{'Jeu':<16}{'images':>9}   composition")
print("-" * 62)
print(f"{'entrainement':<16}{len(chemins['train']):>9}   "
      f"{len(pv['train'][0])} studio + {len(pw['train'][0])} terrain")
print(f"{'validation':<16}{len(chemins['val']):>9}   "
      f"{len(pv['val'][0])} studio + {len(pw['val'][0])} terrain")
print(f"{'test studio':<16}{len(chemins['test_studio']):>9}   PlantVillage, identique au v1")
print(f"{'test terrain':<16}{'942':>9}   PlantDoc, jamais vu par aucun modele")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 6. Correction 1 : une augmentation qui simule le terrain

L'augmentation du v1 se limitait a des retournements, rotations, zooms et variations
d'intensite. Elle ne produisait jamais ce qui distingue une photo de champ d'une photo
de studio.

Ce qui est ajoute :

- **teinte et saturation** : la lumiere de fin de journee verdit ou rougit une photo,
  l'ombre la bleuit. Le v1 n'avait jamais vu ca ;
- **occlusions** : au champ, une feuille en cache souvent une autre. On efface des
  rectangles au hasard pour que le modele n'ait pas besoin de voir la feuille entiere ;
- **flou** : les photos prises a main levee ne sont pas nettes ;
- **translations** : la feuille n'est pas toujours centree.

Les couches de Keras ne couvrant pas tout, teinte, saturation, flou et occlusions sont
ecrits a la main avec les operations de TensorFlow.
"""))

CELLULES.append(code("""
TAILLE = 224
TAILLE_LOT = 32
AUTOTUNE = tf.data.AUTOTUNE

augmentation_geometrique = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal_and_vertical", seed=GRAINE),
    tf.keras.layers.RandomRotation(0.25, fill_mode="reflect", seed=GRAINE),
    tf.keras.layers.RandomZoom(0.25, fill_mode="reflect", seed=GRAINE),
    tf.keras.layers.RandomTranslation(0.15, 0.15, fill_mode="reflect", seed=GRAINE),
], name="augmentation_geometrique")


def augmenter_couleur(image):
    \"\"\"Teinte, saturation, luminosite et contraste. Valeurs attendues en 0-255.\"\"\"
    image = tf.image.random_hue(image / 255.0, 0.08)
    image = tf.image.random_saturation(image, 0.6, 1.5)
    image = tf.image.random_brightness(image, 0.25)
    image = tf.image.random_contrast(image, 0.6, 1.5)
    return tf.clip_by_value(image, 0.0, 1.0) * 255.0


def flouter(image, probabilite=0.25):
    \"\"\"Flou moyen 3x3 applique une fois sur quatre, pour simuler le bougé.\"\"\"
    def appliquer():
        noyau = tf.ones((3, 3, 3, 1), dtype=image.dtype) / 9.0
        return tf.nn.depthwise_conv2d(image[None], noyau, [1, 1, 1, 1], "SAME")[0]
    return tf.cond(tf.random.uniform([]) < probabilite, appliquer, lambda: image)


def occulter(image, probabilite=0.35, proportion=0.25):
    \"\"\"
    Efface un rectangle au hasard (technique dite « random erasing »).

    Force le modele a decider a partir d'une feuille partiellement masquee, situation
    banale au champ et absente de PlantVillage.
    \"\"\"
    def appliquer():
        hauteur = tf.random.uniform([], 0.1, proportion)
        largeur = tf.random.uniform([], 0.1, proportion)
        dh = tf.cast(hauteur * TAILLE, tf.int32)
        dl = tf.cast(largeur * TAILLE, tf.int32)
        y = tf.random.uniform([], 0, TAILLE - dh, dtype=tf.int32)
        x = tf.random.uniform([], 0, TAILLE - dl, dtype=tf.int32)

        lignes = tf.range(TAILLE)[:, None]
        colonnes = tf.range(TAILLE)[None, :]
        dedans = (lignes >= y) & (lignes < y + dh) & (colonnes >= x) & (colonnes < x + dl)
        masque = tf.cast(~dedans, image.dtype)[..., None]
        gris = tf.ones_like(image) * 127.0
        return image * masque + gris * (1.0 - masque)
    return tf.cond(tf.random.uniform([]) < probabilite, appliquer, lambda: image)


def augmenter(image):
    image = augmenter_couleur(image)
    image = flouter(image)
    image = occulter(image)
    return image
"""))

CELLULES.append(code("""
def charger(chemin, etiquette, poids):
    octets = tf.io.read_file(chemin)
    image = tf.io.decode_image(octets, channels=3, expand_animations=False)
    image = tf.image.resize(image, (TAILLE, TAILLE))
    image.set_shape([TAILLE, TAILLE, 3])
    return image, etiquette, poids


def construire(split, entrainement, poids_classes=None):
    listes = chemins[split], etiquettes[split]
    poids = [poids_classes[e] if poids_classes else 1.0 for e in listes[1]]

    jeu = tf.data.Dataset.from_tensor_slices(
        (listes[0], tf.one_hot(listes[1], NB_CLASSES), poids))
    if entrainement:
        jeu = jeu.shuffle(len(listes[0]), seed=GRAINE, reshuffle_each_iteration=True)
    jeu = jeu.map(charger, num_parallel_calls=AUTOTUNE)
    if entrainement:
        jeu = jeu.map(lambda i, e, p: (augmenter(i), e, p), num_parallel_calls=AUTOTUNE)
    jeu = jeu.batch(TAILLE_LOT)
    if entrainement:
        jeu = jeu.map(lambda i, e, p: (augmentation_geometrique(i, training=True), e, p),
                      num_parallel_calls=AUTOTUNE)
    return jeu.prefetch(AUTOTUNE)
"""))

CELLULES.append(code("""
# Ponderation des classes : le desequilibre change avec l'ajout de PlantWild
comptes = np.bincount(etiquettes["train"], minlength=NB_CLASSES)
total = comptes.sum()
poids_classes = {i: float(total / (NB_CLASSES * max(comptes[i], 1))) for i in range(NB_CLASSES)}

print(f"{'Classe':<32}{'train':>8}{'poids':>9}")
print("-" * 49)
for i, libelle in enumerate(LIBELLES):
    print(f"{libelle:<32}{comptes[i]:>8}{poids_classes[i]:>9.3f}")

jeu_train = construire("train", entrainement=True, poids_classes=poids_classes)
jeu_val = construire("val", entrainement=False)
jeu_test_studio = construire("test_studio", entrainement=False)
"""))

CELLULES.append(code("""
# Verification visuelle : douze variantes augmentees. Elles doivent etre nettement
# plus variees que celles du notebook v1, sinon l'augmentation ne sert a rien.
import matplotlib.pyplot as plt

lot_images, lot_etiquettes, _ = next(iter(jeu_train))
plt.figure(figsize=(13, 7))
for i in range(12):
    plt.subplot(3, 4, i + 1)
    plt.imshow(tf.cast(tf.clip_by_value(lot_images[i], 0, 255), tf.uint8))
    plt.title(LIBELLES[int(tf.argmax(lot_etiquettes[i]))], fontsize=8)
    plt.axis("off")
plt.tight_layout()
plt.show()
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 7. Correction 4 : le melange d'images

Le mixup fabrique des images intermediaires en superposant deux photos, et melange
leurs etiquettes dans la meme proportion : 70 % de mildiou et 30 % de septoriose
donnent une image a 70/30 et une etiquette a 70/30.

L'interet ici est double. Le modele apprend a repondre de facon graduee au lieu de
trancher brutalement, ce qui attenue directement la surconfiance mesuree sur le v1.
Et il ne peut plus se reposer sur un fond propre, puisque les fonds se melangent eux
aussi.

Le melange s'applique **uniquement a l'entrainement**, jamais a la validation ni au test.
"""))

CELLULES.append(code("""
MIXUP_ACTIF = True
MIXUP_ALPHA = 0.2   # plus la valeur est haute, plus les melanges sont marques


def melanger(images, etiquettes_lot, poids):
    \"\"\"Superpose le lot avec une version permutee de lui-meme.\"\"\"
    taille = tf.shape(images)[0]
    lam = tf.random.uniform([], 0.0, 1.0)
    lam = tf.maximum(lam, 1.0 - lam)      # garde l'image dominante identifiable
    ordre = tf.random.shuffle(tf.range(taille))

    images_melangees = lam * images + (1 - lam) * tf.gather(images, ordre)
    etiquettes_melangees = lam * etiquettes_lot + (1 - lam) * tf.gather(etiquettes_lot, ordre)
    poids_melanges = lam * poids + (1 - lam) * tf.gather(poids, ordre)
    return images_melangees, etiquettes_melangees, poids_melanges


if MIXUP_ACTIF:
    jeu_train = jeu_train.map(melanger, num_parallel_calls=AUTOTUNE).prefetch(AUTOTUNE)
    print("Melange d'images actif, alpha =", MIXUP_ALPHA)
else:
    print("Melange d'images desactive")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 8. Correction 5 : le modele, avec pooling moyenne et maximum

Le v1 resumait les 49 cases de la grille 7x7 par leur **moyenne**. Une lesion occupant
deux cases voyait donc son signal divise par vingt-cinq, noye dans les quarante-sept
cases de feuille saine. C'est mauvais precisement pour les maladies a petites taches,
septoriose ou tache bacterienne debutantes.

Le v2 concatene la **moyenne** et le **maximum**. Le maximum retient la case la plus
alarmante quelle que soit sa taille ; la moyenne conserve la vision d'ensemble. Le
vecteur passe de 1 280 a 2 560 valeurs, ce qui reste negligeable en taille.

Le reste ne change pas : meme MobileNetV2, memes 10 sorties, meme normalisation
integree, meme format de reponse. Le contrat d'interface est intact et l'API du lot A
fonctionnera sans modification.
"""))

CELLULES.append(code("""
base = tf.keras.applications.MobileNetV2(
    input_shape=(TAILLE, TAILLE, 3), include_top=False, weights="imagenet")
base.trainable = False

entree = tf.keras.Input(shape=(TAILLE, TAILLE, 3), name="image_entree")
x = tf.keras.applications.mobilenet_v2.preprocess_input(entree)
x = base(x, training=False)

moyenne = tf.keras.layers.GlobalAveragePooling2D(name="moyenne_globale")(x)
maximum = tf.keras.layers.GlobalMaxPooling2D(name="maximum_global")(x)
x = tf.keras.layers.Concatenate(name="moyenne_et_maximum")([moyenne, maximum])

x = tf.keras.layers.Dropout(0.4, name="dropout")(x)
sortie = tf.keras.layers.Dense(NB_CLASSES, activation="softmax", name="predictions")(x)

modele = tf.keras.Model(entree, sortie, name="agrivision_mobilenetv2_v2")

# Correction 3 : lissage des etiquettes. Au lieu d'exiger 1,0 pour la bonne classe,
# on vise 0,9 et on repartit le reste. Le modele cesse d'apprendre a etre categorique,
# ce qui est exactement le defaut mesure sur le v1 (80,9 % de confiance a tort).
perte = tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)

modele.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
               loss=perte, metrics=["accuracy"])

print("Parametres entrainables, phase 1 :",
      f"{sum(int(tf.size(w)) for w in modele.trainable_weights):,}")
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 9. Phase 1 : la tete de classification

L'extracteur reste gele, on n'entraine que la couche de sortie. Rapide, et cela evite
de detruire le savoir pre-entraine avec des gradients desordonnes au demarrage.
"""))

CELLULES.append(code("""
rappels_1 = [
    tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3,
                                     restore_best_weights=True, verbose=1),
    tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.2,
                                         patience=2, min_lr=1e-6, verbose=1),
    tf.keras.callbacks.ModelCheckpoint(str(DOSSIER_MODELES / "v2_phase1.keras"),
                                       monitor="val_accuracy", save_best_only=True),
]

historique1 = modele.fit(jeu_train, validation_data=jeu_val, epochs=10,
                         callbacks=rappels_1, verbose=1)
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 10. Phase 2 : correction 2, un degel deux fois plus profond

Le v1 ne degelait que 40 couches sur 154, soit 26 %. Les couches basses, celles qui
encodent textures et couleurs elementaires, restaient figees sur ImageNet. Or c'est
exactement ce qui doit s'adapter quand on passe du studio au champ.

Le v2 en degele 80, soit 52 %. Les BatchNormalization restent gelees : les degeler
sur des lots de 32 images est une cause classique d'effondrement en fine-tuning.
"""))

CELLULES.append(code("""
NB_COUCHES_DEGELEES = 80

base.trainable = True
for couche in base.layers[:-NB_COUCHES_DEGELEES]:
    couche.trainable = False
for couche in base.layers:
    if isinstance(couche, tf.keras.layers.BatchNormalization):
        couche.trainable = False

modele.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
               loss=perte, metrics=["accuracy"])

print(f"Couches degelees : {NB_COUCHES_DEGELEES} / {len(base.layers)} "
      f"({NB_COUCHES_DEGELEES / len(base.layers):.0%})")
print("Parametres entrainables, phase 2 :",
      f"{sum(int(tf.size(w)) for w in modele.trainable_weights):,}")
"""))

CELLULES.append(code("""
rappels_2 = [
    tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=5,
                                     restore_best_weights=True, verbose=1),
    tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.2,
                                         patience=2, min_lr=1e-8, verbose=1),
    tf.keras.callbacks.ModelCheckpoint(str(CHEMIN_V2), monitor="val_accuracy",
                                       save_best_only=True),
]

historique2 = modele.fit(jeu_train, validation_data=jeu_val, epochs=20,
                         callbacks=rappels_2, verbose=1)

modele.save(CHEMIN_V2)
print("Modele v2 enregistre :", CHEMIN_V2)
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 11. Le juge : PlantDoc, jamais vu

C'est ici que tout se joue. Les deux modeles sont evalues sur exactement les memes
942 images de terrain, qu'aucun des deux n'a rencontrees a l'entrainement.

Rappel du v1 : 35,7 % d'exactitude, 0,291 de F1 macro, et 80,9 % de confiance moyenne
malgre deux erreurs sur trois.
"""))

CELLULES.append(code("""
CORRESPONDANCE_PD = {i: nom for i, _, _, _, nom in CLASSES if nom}

chemins_pd, verites_pd = [], []
for indice, nom in sorted(CORRESPONDANCE_PD.items()):
    for partie in ("train", "test"):
        d = RACINE_PD / partie / nom
        if not d.exists():
            continue
        fichiers = [str(p) for p in sorted(d.iterdir())
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        chemins_pd += fichiers
        verites_pd += [indice] * len(fichiers)

verites_pd = np.array(verites_pd)
print(len(chemins_pd), "images de terrain sur", len(CORRESPONDANCE_PD), "classes")
print("Mais - Sain est absent de PlantDoc, la classe ne peut pas etre mesuree.")


def jeu_depuis(liste_chemins, liste_etiquettes):
    jeu = tf.data.Dataset.from_tensor_slices(
        (liste_chemins, tf.one_hot(liste_etiquettes, NB_CLASSES),
         [1.0] * len(liste_chemins)))
    return jeu.map(charger, num_parallel_calls=AUTOTUNE).batch(TAILLE_LOT).prefetch(AUTOTUNE)


jeu_terrain = jeu_depuis(chemins_pd, verites_pd)
"""))

CELLULES.append(code("""
from sklearn.metrics import confusion_matrix, f1_score


def evaluer(modele_teste, jeu, verites, nom):
    probabilites = modele_teste.predict(jeu, verbose=0)
    predictions = probabilites.argmax(axis=1)
    confiances = probabilites.max(axis=1)
    justes = predictions == verites

    resultat = {
        "nom": nom,
        "exactitude": float(justes.mean()),
        "f1_macro": float(f1_score(verites, predictions, average="macro", zero_division=0)),
        "confiance_moyenne": float(confiances.mean()),
        "confiance_si_juste": float(confiances[justes].mean()) if justes.any() else 0.0,
        "confiance_si_faux": float(confiances[~justes].mean()) if (~justes).any() else 0.0,
        "predictions": predictions,
    }
    return resultat


modele_v1 = tf.keras.models.load_model(CHEMIN_V1)
modele_v2 = tf.keras.models.load_model(CHEMIN_V2)

classes_pd = sorted(CORRESPONDANCE_PD)
terrain_v1 = evaluer(modele_v1, jeu_terrain, verites_pd, "v1")
terrain_v2 = evaluer(modele_v2, jeu_terrain, verites_pd, "v2")
studio_v1 = evaluer(modele_v1, jeu_test_studio, np.array(etiquettes["test_studio"]), "v1")
studio_v2 = evaluer(modele_v2, jeu_test_studio, np.array(etiquettes["test_studio"]), "v2")

print("=" * 72)
print(f"{'':<34}{'v1':>12}{'v2':>12}{'gain':>12}")
print("-" * 72)
for titre, a, b in [
    ("TERRAIN  exactitude", terrain_v1["exactitude"], terrain_v2["exactitude"]),
    ("TERRAIN  F1 macro", terrain_v1["f1_macro"], terrain_v2["f1_macro"]),
    ("TERRAIN  confiance si juste", terrain_v1["confiance_si_juste"], terrain_v2["confiance_si_juste"]),
    ("TERRAIN  confiance si faux", terrain_v1["confiance_si_faux"], terrain_v2["confiance_si_faux"]),
    ("STUDIO   exactitude", studio_v1["exactitude"], studio_v2["exactitude"]),
    ("STUDIO   F1 macro", studio_v1["f1_macro"], studio_v2["f1_macro"]),
]:
    print(f"{titre:<34}{a:>12.4f}{b:>12.4f}{b - a:>+12.4f}")
print("=" * 72)
print()
print("La confiance quand le modele se trompe doit BAISSER : c'est le signe qu'il")
print("sait desormais reconnaitre son incertitude, et que le garde-fou de")
print("l'application redevient utile.")
"""))

CELLULES.append(code("""
# F1 par classe, sur le terrain
f1_v1 = f1_score(verites_pd, terrain_v1["predictions"], labels=classes_pd,
                 average=None, zero_division=0)
f1_v2 = f1_score(verites_pd, terrain_v2["predictions"], labels=classes_pd,
                 average=None, zero_division=0)

print(f"{'Classe':<32}{'v1':>8}{'v2':>8}{'gain':>9}")
print("-" * 57)
for rang, indice in enumerate(classes_pd):
    print(f"{LIBELLES[indice]:<32}{f1_v1[rang]:>8.3f}{f1_v2[rang]:>8.3f}"
          f"{f1_v2[rang] - f1_v1[rang]:>+9.3f}")

positions = np.arange(len(classes_pd))
largeur = 0.38
figure, axe = plt.subplots(figsize=(11, 5.5))
axe.bar(positions - largeur / 2, f1_v1, largeur, label="v1 (studio seul)", color="#37474f")
axe.bar(positions + largeur / 2, f1_v2, largeur, label="v2 (studio + terrain)", color="#2e7d32")
axe.set_xticks(positions, [LIBELLES[i] for i in classes_pd], rotation=40, ha="right", fontsize=9)
axe.set_ylabel("F1 sur images de terrain")
axe.set_ylim(0, 1.05)
axe.set_title("Effet des corrections, mesure sur PlantDoc (jamais vu par les deux modeles)")
axe.legend()
axe.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(DOSSIER_RAPPORTS / "comparaison_v1_v2_terrain.png", dpi=150, bbox_inches="tight")
plt.show()
"""))

CELLULES.append(code("""
# Matrice de confusion du v2 sur le terrain, a comparer a celle du v1
matrice = confusion_matrix(verites_pd, terrain_v2["predictions"], labels=list(range(NB_CLASSES)))
lignes = [i for i in range(NB_CLASSES) if matrice[i].sum() > 0]
reduite = matrice[lignes]
normalisee = reduite / reduite.sum(axis=1, keepdims=True)

figure, axe = plt.subplots(figsize=(10, 7))
image = axe.imshow(normalisee, cmap="Greys", vmin=0, vmax=1)
axe.set_xticks(range(NB_CLASSES), LIBELLES, rotation=45, ha="right", fontsize=8)
axe.set_yticks(range(len(lignes)), [LIBELLES[i] for i in lignes], fontsize=8)
axe.set_xlabel("Classe predite")
axe.set_ylabel("Classe reelle")
axe.set_title(f"Modele v2 sur images de terrain - exactitude {terrain_v2['exactitude']:.1%}")
for i in range(len(lignes)):
    for j in range(NB_CLASSES):
        if reduite[i, j] > 0:
            axe.text(j, i, str(reduite[i, j]), ha="center", va="center", fontsize=7,
                     color="white" if normalisee[i, j] > 0.5 else "black")
figure.colorbar(image, ax=axe, fraction=0.046)
plt.tight_layout()
plt.savefig(DOSSIER_RAPPORTS / "confusion_terrain_v2.png", dpi=150, bbox_inches="tight")
plt.show()
"""))

# ---------------------------------------------------------------------------
CELLULES.append(md("""
## 12. Fiche du modele v2

Le v1 n'est pas ecrase : les deux fichiers coexistent sur le Drive, et la fiche du v2
consigne la comparaison. C'est cette comparaison, plus que le chiffre final, qui fera
le chapitre « resultats » du rapport.
"""))

CELLULES.append(code("""
import json

VERSION_V2 = "mobilenetv2-v2.0"

derniere_conv = next(c.name for c in reversed(base.layers)
                     if isinstance(c, (tf.keras.layers.Conv2D, tf.keras.layers.ReLU))
                     and len(c.output.shape) == 4)

fiche = {
    "model_version": VERSION_V2,
    "remplace": "mobilenetv2-v1.0 (conserve, non ecrase)",
    "architecture": "MobileNetV2 (ImageNet) + pooling moyenne et maximum + dense 10 classes",
    "date_entrainement": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "corpus_entrainement": {
        "PlantVillage (studio)": len(pv["train"][0]),
        "PlantWild (terrain, CC BY-NC-ND 4.0)": len(pw["train"][0]),
    },
    "corrections": [
        "augmentation etendue : teinte, saturation, occlusions, flou, translations",
        f"degel de {NB_COUCHES_DEGELEES} couches sur {len(base.layers)} au lieu de 40",
        "lissage des etiquettes a 0,1 contre la surconfiance",
        f"melange d'images (mixup) {'actif' if MIXUP_ACTIF else 'desactive'}",
        "pooling moyenne et maximum au lieu de la seule moyenne",
    ],
    "entree": {
        "taille": [TAILLE, TAILLE, 3],
        "plage_valeurs": "0-255, la normalisation est integree au modele",
    },
    "couche_gradcam": derniere_conv,
    "classes": [{"index": i, "label": l} for i, l in enumerate(LIBELLES)],
    "resultats": {
        "terrain_PlantDoc_942_images": {
            "v1": {k: round(terrain_v1[k], 4) for k in
                   ("exactitude", "f1_macro", "confiance_si_juste", "confiance_si_faux")},
            "v2": {k: round(terrain_v2[k], 4) for k in
                   ("exactitude", "f1_macro", "confiance_si_juste", "confiance_si_faux")},
        },
        "studio_PlantVillage_test": {
            "v1": {k: round(studio_v1[k], 4) for k in ("exactitude", "f1_macro")},
            "v2": {k: round(studio_v2[k], 4) for k in ("exactitude", "f1_macro")},
        },
        "f1_terrain_par_classe": {
            LIBELLES[indice]: {"v1": round(float(f1_v1[rang]), 4),
                               "v2": round(float(f1_v2[rang]), 4)}
            for rang, indice in enumerate(classes_pd)
        },
    },
    "limites": [
        "Mais - Sain est absent de PlantDoc : la classe n'est pas mesuree sur le terrain.",
        "PlantWild est sous licence CC BY-NC-ND 4.0, usage non commercial uniquement.",
        "Le test terrain vient d'un corpus unique : d'autres conditions de prise de "
        "vue donneraient d'autres chiffres.",
    ],
}

with open(DOSSIER_RAPPORTS / "model_card_v2.json", "w", encoding="utf-8") as f:
    json.dump(fiche, f, ensure_ascii=False, indent=2)

print(json.dumps(fiche["resultats"]["terrain_PlantDoc_942_images"], ensure_ascii=False, indent=2))
print()
print("Fiche ecrite :", DOSSIER_RAPPORTS / "model_card_v2.json")
print()
print("A rapatrier depuis le Drive :")
print("   models/mobilenetv2_v2.keras      -> models/ du depot")
print("   reports/model_card_v2.json       -> reports/")
print("   reports/comparaison_v1_v2_terrain.png et confusion_terrain_v2.png -> reports/")
"""))

CELLULES.append(code("""
# Controle final : le fichier recharge doit donner les memes predictions.
recharge = tf.keras.models.load_model(CHEMIN_V2)
lot_images, lot_etiquettes, _ = next(iter(jeu_test_studio))
ecart = float(np.abs(modele_v2.predict(lot_images, verbose=0)
                     - recharge.predict(lot_images, verbose=0)).max())
print(f"Ecart maximal apres rechargement : {ecart:.2e}")
print("Conforme." if ecart < 1e-5 else "PROBLEME : le rechargement modifie les predictions.")
print(f"Taille du fichier : {CHEMIN_V2.stat().st_size / 1024 / 1024:.1f} Mo")
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
print(f"{len(CELLULES)} cellules "
      f"({sum(1 for c in CELLULES if c['cell_type'] == 'code')} de code, "
      f"{sum(1 for c in CELLULES if c['cell_type'] == 'markdown')} de texte)")
