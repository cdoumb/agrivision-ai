"""
Télécharge PlantVillage depuis Kaggle et n'extrait que les 10 classes
retenues (cf. classes.json) vers data/raw/<culture>_<etat>/.

Prérequis :
  - un compte Kaggle
  - le fichier kaggle.json (clé API) placé dans ~/.kaggle/kaggle.json
  - pip install kaggle

Usage :
  python src/data/download.py --subset  # 3 classes seulement (phase squelette)
  python src/data/download.py           # les 10 classes complètes (phase 1)
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
KAGGLE_DATASET = "abdallahalidev/plantvillage-dataset"

# Mapping entre nos libellés (classes.json) et les noms de dossiers
# tels qu'ils existent dans le dataset PlantVillage sur Kaggle.
# À ajuster une fois le dataset téléchargé et inspecté une première fois.
PLANTVILLAGE_FOLDER_MAP = {
    "Tomate_Saine":              "Tomato___healthy",
    "Tomate_Mildiou_tardif":     "Tomato___Late_blight",
    "Tomate_Tache_bacterienne":  "Tomato___Bacterial_spot",
    "Tomate_Septoriose":         "Tomato___Septoria_leaf_spot",
    "Mais_Sain":                 "Corn_(maize)___healthy",
    "Mais_Rouille_commune":      "Corn_(maize)___Common_rust_",
    "Mais_Helminthosporiose":    "Corn_(maize)___Northern_Leaf_Blight",
    "Mais_Cercosporiose":        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Poivron_Sain":              "Pepper,_bell___healthy",
    "Poivron_Tache_bacterienne": "Pepper,_bell___Bacterial_spot",
}

SUBSET_FOR_SKELETON = [
    "Tomate_Saine",
    "Tomate_Mildiou_tardif",
    "Mais_Sain",
]


def load_classes():
    with open(ROOT / "classes.json", encoding="utf-8") as f:
        return json.load(f)["classes"]


def download_dataset(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement de {KAGGLE_DATASET} vers {dest} ...")
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-p", str(dest), "--unzip"],
        check=True,
    )


def extract_classes(source_root: Path, subset_only: bool):
    keys = SUBSET_FOR_SKELETON if subset_only else list(PLANTVILLAGE_FOLDER_MAP.keys())
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    for key in keys:
        kaggle_folder_name = PLANTVILLAGE_FOLDER_MAP[key]
        # abdallahalidev/plantvillage-dataset contient 3 variantes par image :
        # color/, grayscale/, segmented/. On ne veut QUE la version couleur,
        # sinon le corpus mélange 3x la même image sous des formes différentes.
        candidates = [
            p for p in source_root.rglob(kaggle_folder_name)
            if "color" in [part.lower() for part in p.parts]
        ]
        if not candidates:
            print(f"[ATTENTION] Dossier introuvable pour {key} ({kaggle_folder_name}) — à vérifier manuellement.")
            continue

        dest_dir = DATA_RAW / key
        dest_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for src_folder in candidates:
            for img in src_folder.glob("*"):
                if img.is_file():
                    shutil.copy(img, dest_dir / f"{count:05d}_{img.name}")
                    count += 1
        print(f"{key}: {count} images copiées vers {dest_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", action="store_true", help="N'extraire que 3 classes (phase squelette)")
    parser.add_argument("--kaggle-dir", default=str(ROOT / "data" / "kaggle_download"))
    args = parser.parse_args()

    kaggle_dir = Path(args.kaggle_dir)
    if not kaggle_dir.exists() or not any(kaggle_dir.iterdir()):
        download_dataset(kaggle_dir)
    else:
        print(f"{kaggle_dir} existe déjà et n'est pas vide, téléchargement ignoré.")

    extract_classes(kaggle_dir, subset_only=args.subset)


if __name__ == "__main__":
    main()
