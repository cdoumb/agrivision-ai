"""
Generateur du notebook d'entrainement AgriVision-AI (Binome B).

Produit : notebooks/01_entrainement_mobilenetv2.ipynb

Pourquoi un generateur plutot qu'un .ipynb ecrit a la main : le format
.ipynb est du JSON, penible a relire et a versionner dans Git. Ici le
contenu des cellules est du texte lisible, et on regenere le notebook
avec :

    python notebooks/build_notebook.py
"""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SORTIE = RACINE / "01_entrainement_mobilenetv2.ipynb"


def md(texte):
    return {"cell_type": "markdown", "metadata": {}, "source": texte.strip("\n").splitlines(keepends=True)}


def code(texte):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": texte.strip("\n").splitlines(keepends=True),
    }


CELLULES = []

# --------------------------------------------------------------------------
CELLULES.append(md("""
# AgriVision-AI - Entrainement du modele de reference

**Lot B (Faustin)** - classification de 10 classes de feuilles (tomate, mais, poivron)
avec MobileNetV2 en transfert d'apprentissage puis fine-tuning.

Le decoupage train / validation / test n'est **pas recalcule ici** : il est relu depuis
`reports/split_manifest.csv` produit par le lot A, pour que les deux binomes evaluent
sur exactement le meme jeu de test.

## Avant de lancer

1. Menu `Execution` > `Modifier le type d'execution` > accelerateur materiel : **GPU (T4)**
2. Avoir sous la main son fichier `kaggle.json` (voir cellule 3)
3. Executer les cellules dans l'ordre, de haut en bas

Duree indicative sur GPU T4 : environ 15 min de telechargement + 25 a 40 min d'entrainement.
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 1. Verification du GPU

Sans GPU l'entrainement passe de ~30 minutes a plusieurs heures. Si la cellule
affiche un avertissement, changer le type d'execution puis **relancer depuis le debut**.
"""))

CELLULES.append(code("""
import sys
import tensorflow as tf

print("Python         :", sys.version.split()[0])
print("TensorFlow     :", tf.__version__)

gpus = tf.config.list_physical_devices("GPU")
if gpus:
    print("GPU detecte    :", gpus[0].name)
    !nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else:
    print()
    print("!!! AUCUN GPU DETECTE !!!")
    print("Execution > Modifier le type d'execution > GPU, puis relancer ce notebook.")
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 2. Montage du Google Drive

Colab efface tout quand la session se ferme ou expire (90 minutes d'inactivite,
12 heures maximum). On ecrit donc le modele et les resultats directement sur le
Drive : si la session saute en cours de route, le travail deja fait est conserve.

Une fenetre d'autorisation Google va s'ouvrir, il faut l'accepter.
"""))

CELLULES.append(code("""
from pathlib import Path
from google.colab import drive

drive.mount("/content/drive")

# Tout ce qui doit survivre a la session va la-dedans
DOSSIER_TRAVAIL = Path("/content/drive/MyDrive/AgriVision-AI")
DOSSIER_MODELES = DOSSIER_TRAVAIL / "models"
DOSSIER_RAPPORTS = DOSSIER_TRAVAIL / "reports"

for d in (DOSSIER_MODELES, DOSSIER_RAPPORTS):
    d.mkdir(parents=True, exist_ok=True)

# Les images, elles, restent sur le disque local de Colab : elles se
# retelechargent vite et les lire depuis le Drive serait beaucoup plus lent.
DOSSIER_DONNEES = Path("/content/data")
DOSSIER_DONNEES.mkdir(parents=True, exist_ok=True)

print("Modeles et rapports :", DOSSIER_TRAVAIL)
print("Images (temporaire) :", DOSSIER_DONNEES)
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 3. Telechargement de PlantVillage depuis Kaggle

**Comment obtenir `kaggle.json`** (a faire une seule fois) :

1. Se connecter sur [kaggle.com](https://www.kaggle.com)
2. Cliquer sur sa photo de profil en haut a droite > `Settings`
3. Section **API** > bouton `Create New Token`
4. Un fichier `kaggle.json` se telecharge, c'est celui-la qu'il faut deposer ci-dessous

Ce fichier contient une cle personnelle : ne jamais le commiter sur GitHub
(il est deja dans le `.gitignore` du depot).
"""))

CELLULES.append(code("""
import os
from google.colab import files

!pip install -q kaggle

if not Path("/root/.kaggle/kaggle.json").exists():
    print("Deposer le fichier kaggle.json :")
    files.upload()
    os.makedirs("/root/.kaggle", exist_ok=True)
    !mv -f kaggle.json /root/.kaggle/kaggle.json
    !chmod 600 /root/.kaggle/kaggle.json

print("Jeton Kaggle en place.")
"""))

CELLULES.append(code("""
# PlantVillage, version "color" (les images d'origine, ni segmentees ni augmentees).
# C'est bien cette version qu'a utilisee le lot A : ses totaux bruts par classe
# correspondent exactement a ceux de ce jeu de donnees.
ARCHIVE = DOSSIER_DONNEES / "plantvillage-dataset.zip"

if not (DOSSIER_DONNEES / "plantvillage dataset").exists():
    !kaggle datasets download -d abdallahalidev/plantvillage-dataset -p {str(DOSSIER_DONNEES)} --force
    print("Decompression en cours (quelques minutes)...")
    !unzip -q -o {str(ARCHIVE)} -d {str(DOSSIER_DONNEES)}
    print("Termine.")
else:
    print("Jeu de donnees deja present, telechargement saute.")

RACINE_COLOR = DOSSIER_DONNEES / "plantvillage dataset" / "color"
print()
print("Racine des images :", RACINE_COLOR)
print("Dossiers trouves  :", len(list(RACINE_COLOR.iterdir())))
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 4. Selection des 10 classes du projet

PlantVillage contient 38 classes. On ne garde que les 10 du contrat d'interface,
dans l'ordre fige par `classes.json` (l'indice de chaque classe est definitif :
c'est lui que l'API renvoie dans `class_index`).

La correspondance entre les noms francais du projet et les noms de dossiers
anglais du jeu de donnees est ecrite explicitement ci-dessous, et **verifiee**
en comparant le nombre d'images trouvees au rapport du lot A. Si un dossier a
ete renomme dans une version ulterieure du jeu de donnees, la cellule le signale
au lieu d'entrainer silencieusement sur les mauvaises images.
"""))

CELLULES.append(code("""
# indice -> (libelle du projet, nom du dossier PlantVillage, nom dans le manifeste, total attendu)
CLASSES = [
    (0, "Tomate - Saine",              "Tomato___healthy",                                   "Tomate_Saine",              1591),
    (1, "Tomate - Mildiou tardif",     "Tomato___Late_blight",                               "Tomate_Mildiou_tardif",     1909),
    (2, "Tomate - Tache bacterienne",  "Tomato___Bacterial_spot",                            "Tomate_Tache_bacterienne",  2127),
    (3, "Tomate - Septoriose",         "Tomato___Septoria_leaf_spot",                        "Tomate_Septoriose",         1771),
    (4, "Mais - Sain",                 "Corn_(maize)___healthy",                             "Mais_Sain",                 1162),
    (5, "Mais - Rouille commune",      "Corn_(maize)___Common_rust_",                        "Mais_Rouille_commune",      1192),
    (6, "Mais - Helminthosporiose",    "Corn_(maize)___Northern_Leaf_Blight",                "Mais_Helminthosporiose",     985),
    (7, "Mais - Cercosporiose",        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "Mais_Cercosporiose",         513),
    (8, "Poivron - Sain",              "Pepper,_bell___healthy",                             "Poivron_Sain",              1478),
    (9, "Poivron - Tache bacterienne", "Pepper,_bell___Bacterial_spot",                      "Poivron_Tache_bacterienne",  997),
]

NB_CLASSES = len(CLASSES)
LIBELLES = [libelle for _, libelle, _, _, _ in CLASSES]
INDICE_PAR_MANIFESTE = {manif: indice for indice, _, _, manif, _ in CLASSES}

anomalies = []
print(f"{'Classe du projet':<32} {'trouvees':>9} {'attendues':>10}   etat")
print("-" * 70)
for indice, libelle, dossier, manif, attendu in CLASSES:
    chemin = RACINE_COLOR / dossier
    if not chemin.exists():
        anomalies.append(f"Dossier introuvable : {dossier}")
        print(f"{libelle:<32} {'--':>9} {attendu:>10}   DOSSIER ABSENT")
        continue
    n = sum(1 for p in chemin.iterdir() if p.is_file())
    etat = "ok" if n == attendu else f"ECART de {n - attendu:+d}"
    if n != attendu:
        anomalies.append(f"{dossier} : {n} images au lieu de {attendu}")
    print(f"{libelle:<32} {n:>9} {attendu:>10}   {etat}")

print()
if anomalies:
    print("ANOMALIES DETECTEES :")
    for a in anomalies:
        print("  -", a)
    print()
    print("Ne pas continuer sans comprendre l'ecart : le decoupage du lot A")
    print("ne correspondrait plus aux images reellement utilisees ici.")
else:
    print("Les 10 dossiers correspondent exactement au rapport du lot A.")
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 5. Reconstruction du decoupage du lot A

C'est le point delicat. Le manifeste du lot A liste, pour chacune des 13 711
images retenues, la classe et le sous-ensemble (train, val ou test) auquel elle
appartient. En le relisant, on obtient **exactement le meme decoupage** que lui,
sans avoir besoin de son code de pretraitement.

Deux details a gerer :

- ses noms de fichiers portent un prefixe numerique (`00225_...`) ajoute lors de
  sa copie locale ; on le retire pour retrouver le nom d'origine ;
- il a supprime 14 doublons exacts, qui sont donc simplement absents du manifeste.

La cellule affiche le **taux de correspondance**. S'il n'est pas de 100 %, le
probleme apparait ici et pas trois heures plus tard au moment de l'evaluation.
"""))

CELLULES.append(code("""
import re
import shutil
import subprocess
import urllib.request

import pandas as pd

# Le manifeste vit dans le depot GitHub du projet. On le recupere avec trois
# voies de repli : les adresses reseau de Colab sont partagees entre des
# milliers d'utilisateurs et raw.githubusercontent.com renvoie regulierement
# une erreur 429 (quota de telechargements epuise) qui n'a rien a voir avec
# le projet.
CHEMIN_MANIFESTE = DOSSIER_DONNEES / "split_manifest.csv"
DEPOT = Path("/content/agrivision-ai")
URL_RAW = ("https://raw.githubusercontent.com/cdoumb/agrivision-ai/"
           "main/reports/split_manifest.csv")

# Voie 1 : git clone, dont le quota GitHub est distinct de celui de raw
if not CHEMIN_MANIFESTE.exists():
    try:
        if not DEPOT.exists():
            subprocess.run(["git", "clone", "--depth", "1",
                            "https://github.com/cdoumb/agrivision-ai.git",
                            str(DEPOT)], check=True)
        shutil.copy(DEPOT / "reports" / "split_manifest.csv", CHEMIN_MANIFESTE)
        print("Manifeste recupere via git clone.")
    except Exception as erreur:
        print("Echec du git clone :", erreur)

# Voie 2 : telechargement direct, si le quota s'est libere entre-temps
if not CHEMIN_MANIFESTE.exists():
    try:
        urllib.request.urlretrieve(URL_RAW, CHEMIN_MANIFESTE)
        print("Manifeste recupere via telechargement direct.")
    except Exception as erreur:
        print("Echec du telechargement direct :", erreur)

# Voie 3 : depot manuel du fichier depuis le PC
if not CHEMIN_MANIFESTE.exists():
    print("Deposer le fichier reports/split_manifest.csv depuis le PC :")
    from google.colab import files
    files.upload()
    shutil.move("split_manifest.csv", str(CHEMIN_MANIFESTE))

manifeste = pd.read_csv(CHEMIN_MANIFESTE)
print("Lignes lues :", len(manifeste))
print()
print(manifeste.groupby(["split"]).size().to_string())
"""))

CELLULES.append(code("""
PREFIXE_NUMERIQUE = re.compile(r"^\\d+_")


def nom_origine(nom_fichier):
    \"\"\"Retire le prefixe numerique ajoute par le lot A (00225_xxx.JPG -> xxx.JPG).\"\"\"
    return PREFIXE_NUMERIQUE.sub("", nom_fichier)


# Index des fichiers reellement presents, par classe du manifeste
fichiers_disponibles = {}
for _, _, dossier, manif, _ in CLASSES:
    fichiers_disponibles[manif] = {p.name: p for p in (RACINE_COLOR / dossier).iterdir() if p.is_file()}

chemins = {"train": [], "val": [], "test": []}
etiquettes = {"train": [], "val": [], "test": []}
introuvables = []

# name=None : on recoit des tuples bruts, car la colonne s'appelle "class",
# un mot reserve de Python que pandas renommerait automatiquement.
for manif, split, nom_fichier, _source in manifeste.itertuples(index=False, name=None):
    nom = nom_origine(nom_fichier)
    disponible = fichiers_disponibles.get(manif, {})
    if nom in disponible:
        chemins[split].append(str(disponible[nom]))
        etiquettes[split].append(INDICE_PAR_MANIFESTE[manif])
    else:
        introuvables.append((manif, split, nom))

total_attendu = len(manifeste)
total_retrouve = sum(len(v) for v in chemins.values())
taux = 100.0 * total_retrouve / total_attendu

print(f"Images du manifeste retrouvees : {total_retrouve} / {total_attendu}  ({taux:.2f} %)")
print()
for split in ("train", "val", "test"):
    print(f"  {split:<6} : {len(chemins[split]):>6} images")

print()
if taux == 100.0:
    print("Correspondance parfaite : on entraine sur exactement le decoupage du lot A.")
else:
    print(f"ATTENTION : {len(introuvables)} images du manifeste sont introuvables.")
    print("Premiers cas :")
    for cas in introuvables[:10]:
        print("  -", cas)
    print()
    print("En dessous de 99 %, prevenir le binome avant de continuer : le jeu de")
    print("test ne serait plus identique au sien et les chiffres ne seraient pas comparables.")
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 6. Construction des jeux de donnees

On transforme les listes de chemins en flux d'images pretes pour le reseau.

Le pretraitement applique ici est **exactement celui que devra appliquer l'API**
au moment de la prediction, sinon le modele recevra en production des images qui
ne ressemblent pas a celles vues a l'entrainement :

1. redimensionnement en 224 x 224 pixels
2. normalisation `preprocess_input` de MobileNetV2, qui ramene les valeurs de
   `[0, 255]` vers `[-1, 1]`

L'augmentation (retournements, rotations, zooms, variations de luminosite et de
contraste) n'est appliquee **qu'au jeu d'entrainement**. Elle fabrique des
variantes des images pour forcer le reseau a reconnaitre une maladie meme si la
photo est prise de travers ou mal eclairee. L'appliquer a la validation ou au
test fausserait la mesure.
"""))

CELLULES.append(code("""
import tensorflow as tf

TAILLE = 224
TAILLE_LOT = 32
AUTOTUNE = tf.data.AUTOTUNE


def charger_image(chemin, etiquette):
    octets = tf.io.read_file(chemin)
    image = tf.io.decode_jpeg(octets, channels=3)
    image = tf.image.resize(image, (TAILLE, TAILLE))
    return image, etiquette


def construire_jeu(split, melanger):
    jeu = tf.data.Dataset.from_tensor_slices((chemins[split], etiquettes[split]))
    if melanger:
        jeu = jeu.shuffle(buffer_size=len(chemins[split]), seed=42, reshuffle_each_iteration=True)
    jeu = jeu.map(charger_image, num_parallel_calls=AUTOTUNE)
    jeu = jeu.batch(TAILLE_LOT).prefetch(AUTOTUNE)
    return jeu


jeu_train = construire_jeu("train", melanger=True)
jeu_val = construire_jeu("val", melanger=False)
jeu_test = construire_jeu("test", melanger=False)

for lot_images, lot_etiquettes in jeu_train.take(1):
    print("Forme d'un lot d'images    :", lot_images.shape)
    print("Forme des etiquettes       :", lot_etiquettes.shape)
    print("Valeurs brutes (min, max)  :", float(tf.reduce_min(lot_images)), float(tf.reduce_max(lot_images)))
"""))

CELLULES.append(code("""
augmentation = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal_and_vertical", seed=42),
    tf.keras.layers.RandomRotation(0.2, seed=42),
    tf.keras.layers.RandomZoom(0.15, seed=42),
    tf.keras.layers.RandomBrightness(0.2, value_range=(0, 255), seed=42),
    tf.keras.layers.RandomContrast(0.2, seed=42),
], name="augmentation")

# Verification visuelle : une meme feuille, vue sous six variantes.
import matplotlib.pyplot as plt

lot_images, lot_etiquettes = next(iter(jeu_train))
image_test = lot_images[0]

plt.figure(figsize=(12, 5))
for i in range(6):
    variante = augmentation(tf.expand_dims(image_test, 0), training=True)[0]
    plt.subplot(2, 3, i + 1)
    plt.imshow(tf.cast(variante, tf.uint8))
    plt.axis("off")
plt.suptitle(f"Augmentation - {LIBELLES[int(lot_etiquettes[0])]}")
plt.tight_layout()
plt.show()
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 7. Ponderation des classes

Les classes sont desequilibrees : 513 images pour la cercosporiose du mais contre
2 127 pour la tache bacterienne de la tomate, soit un rapport de 1 a 4. Sans
correction, le reseau a interet a negliger les classes rares, ce qui donne une
bonne exactitude globale mais un mauvais diagnostic sur les maladies peu
representees.

On donne donc plus de poids aux erreurs commises sur les classes rares.
"""))

CELLULES.append(code("""
import numpy as np

comptes = np.bincount(etiquettes["train"], minlength=NB_CLASSES)
total = comptes.sum()
poids_classes = {i: total / (NB_CLASSES * comptes[i]) for i in range(NB_CLASSES)}

print(f"{'Classe':<32} {'train':>7} {'poids':>8}")
print("-" * 50)
for i, libelle in enumerate(LIBELLES):
    print(f"{libelle:<32} {comptes[i]:>7} {poids_classes[i]:>8.3f}")
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 8. Le modele

MobileNetV2 a deja ete entraine sur ImageNet, un jeu de 1,2 million de photos.
Il sait donc deja reconnaitre des formes, des textures, des bords. On reutilise
tout ce savoir et on ne lui apprend que la partie specifique a notre probleme :
distinguer nos 10 etats de feuilles.

Le modele complet, de haut en bas :

| Etage | Role |
|---|---|
| Entree 224x224x3 | l'image brute, valeurs de 0 a 255 |
| Augmentation | actif uniquement a l'entrainement |
| `preprocess_input` | ramene les valeurs vers [-1, 1] |
| MobileNetV2 gele | l'extracteur de caracteristiques pre-entraine |
| `GlobalAveragePooling2D` | resume chaque carte de caracteristiques en un nombre |
| `Dropout(0.3)` | eteint 30 % des neurones au hasard, contre le surapprentissage |
| `Dense(10, softmax)` | les 10 scores de sortie, qui somment a 1 |

Le pretraitement est **integre au modele**. C'est volontaire : l'API n'aura
qu'a envoyer une image redimensionnee en 224x224 avec ses valeurs de 0 a 255,
sans avoir a reproduire une normalisation qui pourrait diverger.
"""))

CELLULES.append(code("""
base = tf.keras.applications.MobileNetV2(
    input_shape=(TAILLE, TAILLE, 3),
    include_top=False,
    weights="imagenet",
)
base.trainable = False  # phase 1 : on gele tout l'extracteur

entree = tf.keras.Input(shape=(TAILLE, TAILLE, 3), name="image_entree")
x = augmentation(entree)
x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
x = base(x, training=False)          # training=False : les BatchNorm restent en mode inference
x = tf.keras.layers.GlobalAveragePooling2D(name="moyenne_globale")(x)
x = tf.keras.layers.Dropout(0.3, name="dropout")(x)
sortie = tf.keras.layers.Dense(NB_CLASSES, activation="softmax", name="predictions")(x)

modele = tf.keras.Model(entree, sortie, name="agrivision_mobilenetv2")

modele.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

modele.summary()
print()
print("Parametres entrainables en phase 1 :",
      f"{sum(int(tf.size(w)) for w in modele.trainable_weights):,}")
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 9. Phase 1 - transfert d'apprentissage

On n'entraine que la tete de classification, avec un taux d'apprentissage
normal. C'est rapide : moins de 13 000 parametres a ajuster sur les 2,3 millions
du reseau.

Trois garde-fous automatiques :

- **EarlyStopping** arrete l'entrainement si la validation ne progresse plus
  pendant 3 epoques, et restaure les meilleurs poids ;
- **ReduceLROnPlateau** divise le taux d'apprentissage par 5 quand ca stagne ;
- **ModelCheckpoint** ecrit le meilleur modele sur le Drive apres chaque epoque,
  donc une deconnexion de Colab ne fait pas tout perdre.
"""))

CELLULES.append(code("""
CHEMIN_PHASE1 = DOSSIER_MODELES / "mobilenetv2_phase1.keras"

rappels_phase1 = [
    tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3,
                                     restore_best_weights=True, verbose=1),
    tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.2,
                                         patience=2, min_lr=1e-6, verbose=1),
    tf.keras.callbacks.ModelCheckpoint(str(CHEMIN_PHASE1), monitor="val_accuracy",
                                       save_best_only=True, verbose=0),
]

historique1 = modele.fit(
    jeu_train,
    validation_data=jeu_val,
    epochs=10,
    class_weight=poids_classes,
    callbacks=rappels_phase1,
    verbose=1,
)
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 10. Phase 2 - fine-tuning

On degele les 40 dernieres couches de MobileNetV2 pour qu'elles se specialisent
sur les textures de feuilles malades, avec un taux d'apprentissage **cent fois
plus faible**. Un taux normal detruirait le savoir pre-entraine.

Les couches de `BatchNormalization` restent gelees : elles conservent les
statistiques calculees sur ImageNet. Les degeler sur des lots de 32 images est
une cause classique d'effondrement des performances en fine-tuning.
"""))

CELLULES.append(code("""
base.trainable = True

NB_COUCHES_DEGELEES = 40
for couche in base.layers[:-NB_COUCHES_DEGELEES]:
    couche.trainable = False

# Les BatchNorm restent en mode inference, meme parmi les couches degelees
for couche in base.layers:
    if isinstance(couche, tf.keras.layers.BatchNormalization):
        couche.trainable = False

modele.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

print("Parametres entrainables en phase 2 :",
      f"{sum(int(tf.size(w)) for w in modele.trainable_weights):,}")
"""))

CELLULES.append(code("""
CHEMIN_FINAL = DOSSIER_MODELES / "mobilenetv2_v1.keras"

rappels_phase2 = [
    tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=4,
                                     restore_best_weights=True, verbose=1),
    tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.2,
                                         patience=2, min_lr=1e-8, verbose=1),
    tf.keras.callbacks.ModelCheckpoint(str(CHEMIN_FINAL), monitor="val_accuracy",
                                       save_best_only=True, verbose=0),
]

historique2 = modele.fit(
    jeu_train,
    validation_data=jeu_val,
    epochs=15,
    class_weight=poids_classes,
    callbacks=rappels_phase2,
    verbose=1,
)
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 11. Courbes d'apprentissage

Ce qu'il faut lire sur ces courbes :

- les deux courbes montent ensemble et se rejoignent : bon signe ;
- l'entrainement monte mais la validation stagne ou redescend : surapprentissage,
  le reseau apprend par coeur au lieu de generaliser ;
- la marche visible au debut de la phase 2 est normale, elle correspond au
  changement de taux d'apprentissage.
"""))

CELLULES.append(code("""
def concatener(cle):
    return historique1.history[cle] + historique2.history[cle]


epoques = range(1, len(concatener("accuracy")) + 1)
bascule = len(historique1.history["accuracy"])

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

axes[0].plot(epoques, concatener("accuracy"), label="entrainement")
axes[0].plot(epoques, concatener("val_accuracy"), label="validation")
axes[0].axvline(bascule + 0.5, color="grey", linestyle="--", linewidth=1)
axes[0].text(bascule + 0.7, axes[0].get_ylim()[0], " fine-tuning", fontsize=9, color="grey")
axes[0].set_title("Exactitude")
axes[0].set_xlabel("epoque")
axes[0].legend()
axes[0].grid(alpha=0.3)

axes[1].plot(epoques, concatener("loss"), label="entrainement")
axes[1].plot(epoques, concatener("val_loss"), label="validation")
axes[1].axvline(bascule + 0.5, color="grey", linestyle="--", linewidth=1)
axes[1].set_title("Fonction de cout")
axes[1].set_xlabel("epoque")
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(DOSSIER_RAPPORTS / "courbes_apprentissage.png", dpi=150, bbox_inches="tight")
plt.show()
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 12. Evaluation sur le jeu de test

Le jeu de test n'a jamais ete vu, ni pendant l'entrainement ni pour les
decisions d'arret. C'est le seul chiffre honnete a mettre dans le rapport.

L'exactitude globale ne suffit pas : elle peut cacher une classe systematiquement
ratee. On regarde donc aussi le **F1 par classe** et la **matrice de confusion**,
qui montre precisement quelles maladies le modele confond entre elles.
"""))

CELLULES.append(code("""
from sklearn.metrics import classification_report, confusion_matrix, f1_score

perte_test, exactitude_test = modele.evaluate(jeu_test, verbose=0)

probabilites = modele.predict(jeu_test, verbose=1)
predictions = probabilites.argmax(axis=1)
verite = np.array(etiquettes["test"])

f1_macro = f1_score(verite, predictions, average="macro")

print()
print(f"Exactitude sur le test : {exactitude_test:.4f}")
print(f"Perte sur le test      : {perte_test:.4f}")
print(f"F1 macro               : {f1_macro:.4f}")
print()
print(classification_report(verite, predictions, target_names=LIBELLES, digits=3))
"""))

CELLULES.append(code("""
matrice = confusion_matrix(verite, predictions)
matrice_norm = matrice.astype(float) / matrice.sum(axis=1, keepdims=True)

fig, ax = plt.subplots(figsize=(10, 8.5))
image = ax.imshow(matrice_norm, cmap="Greys", vmin=0, vmax=1)

ax.set_xticks(range(NB_CLASSES), LIBELLES, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(NB_CLASSES), LIBELLES, fontsize=9)
ax.set_xlabel("Classe predite")
ax.set_ylabel("Classe reelle")
ax.set_title(f"Matrice de confusion normalisee - exactitude {exactitude_test:.1%}")

for i in range(NB_CLASSES):
    for j in range(NB_CLASSES):
        if matrice[i, j] > 0:
            ax.text(j, i, f"{matrice[i, j]}", ha="center", va="center", fontsize=8,
                    color="white" if matrice_norm[i, j] > 0.5 else "black")

fig.colorbar(image, ax=ax, fraction=0.046, label="proportion de la classe reelle")
plt.tight_layout()
plt.savefig(DOSSIER_RAPPORTS / "matrice_confusion.png", dpi=150, bbox_inches="tight")
plt.show()

# Les confusions les plus frequentes, utiles pour la discussion du rapport
print()
print("Principales confusions :")
erreurs = [(matrice[i, j], LIBELLES[i], LIBELLES[j])
           for i in range(NB_CLASSES) for j in range(NB_CLASSES) if i != j and matrice[i, j] > 0]
for n, reelle, predite in sorted(erreurs, reverse=True)[:8]:
    print(f"  {n:>4} fois : {reelle}  pris pour  {predite}")
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 13. Sauvegarde et fiche du modele

On enregistre trois choses sur le Drive :

- le modele au format `.keras` ;
- un fichier `model_card.json` qui decrit precisement ce modele : version,
  pretraitement attendu, resultats, et **le nom de la derniere couche de
  convolution**, dont le Grad-CAM aura besoin ;
- les metriques par classe, pour le rapport.

Le champ `model_version` est celui que l'API renvoie dans chaque reponse,
conformement au contrat d'interface.
"""))

CELLULES.append(code("""
import json

VERSION_MODELE = "mobilenetv2-v1.0"

modele.save(CHEMIN_FINAL)

# Le Grad-CAM a besoin de la derniere couche de convolution de l'extracteur.
# Pour MobileNetV2 c'est "out_relu" ; on le retrouve dynamiquement pour ne pas
# dependre d'un nom code en dur.
derniere_conv = next(c.name for c in reversed(base.layers)
                     if isinstance(c, (tf.keras.layers.Conv2D, tf.keras.layers.ReLU))
                     and len(c.output.shape) == 4)

fiche = {
    "model_version": VERSION_MODELE,
    "architecture": "MobileNetV2 (ImageNet) + tete dense 10 classes",
    "date_entrainement": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "entree": {
        "taille": [TAILLE, TAILLE, 3],
        "plage_valeurs": "0-255 (uint8 ou float) - la normalisation est integree au modele",
        "remarque": "Le service redimensionne en 224x224 puis passe l'image telle quelle.",
    },
    "couche_gradcam": derniere_conv,
    "classes": [{"index": i, "label": libelle} for i, libelle in enumerate(LIBELLES)],
    "decoupage": {
        "source": "reports/split_manifest.csv (lot A)",
        "train": len(chemins["train"]),
        "val": len(chemins["val"]),
        "test": len(chemins["test"]),
    },
    "resultats_test": {
        "exactitude": round(float(exactitude_test), 4),
        "perte": round(float(perte_test), 4),
        "f1_macro": round(float(f1_macro), 4),
        "f1_par_classe": {
            libelle: round(float(v), 4)
            for libelle, v in zip(LIBELLES, f1_score(verite, predictions, average=None))
        },
    },
}

with open(DOSSIER_RAPPORTS / "model_card.json", "w", encoding="utf-8") as f:
    json.dump(fiche, f, ensure_ascii=False, indent=2)

pd.DataFrame(classification_report(verite, predictions, target_names=LIBELLES,
                                   output_dict=True)).transpose().to_csv(
    DOSSIER_RAPPORTS / "metriques_par_classe.csv")

print("Modele        :", CHEMIN_FINAL)
print("Fiche modele  :", DOSSIER_RAPPORTS / "model_card.json")
print("Couche Grad-CAM retenue :", derniere_conv)
print()
print(json.dumps(fiche["resultats_test"], ensure_ascii=False, indent=2))
"""))

# --------------------------------------------------------------------------
CELLULES.append(md("""
## 14. Verification de rechargement

Dernier controle avant de livrer : on recharge le fichier sauvegarde depuis zero
et on verifie qu'il donne bien les memes predictions. C'est ce fichier-la qui
partira dans l'API, pas le modele encore en memoire.
"""))

CELLULES.append(code("""
modele_recharge = tf.keras.models.load_model(CHEMIN_FINAL)

lot_images, lot_etiquettes = next(iter(jeu_test))
avant = modele.predict(lot_images, verbose=0)
apres = modele_recharge.predict(lot_images, verbose=0)

ecart_max = float(np.abs(avant - apres).max())
print(f"Ecart maximal entre le modele en memoire et le modele recharge : {ecart_max:.2e}")
print("Rechargement conforme." if ecart_max < 1e-5 else "PROBLEME : le rechargement modifie les predictions.")

taille_mo = CHEMIN_FINAL.stat().st_size / 1024 / 1024
print(f"Taille du fichier modele : {taille_mo:.1f} Mo")
print()
print("Etape suivante : telecharger", CHEMIN_FINAL.name, "depuis le Drive")
print("et le placer dans src/model/ du depot (le .gitignore l'exclut de Git,")
print("il se transmet par Drive ou par une release GitHub).")
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
