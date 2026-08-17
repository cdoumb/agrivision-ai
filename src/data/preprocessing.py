"""
Prétraitement et augmentation — AgriVision-AI (Binôme A).

Fournit build_datasets(), qui construit trois tf.data.Dataset (train, val,
test) à partir de data/split/ :
  - redimensionnement à 224x224 (taille imposée par le contrat d'interface)
  - normalisation des pixels en [0, 1]
  - augmentation (rotation, symétrie, luminosité, contraste, léger bruit),
    appliquée UNIQUEMENT sur train, et seulement à la volée pendant
    l'entraînement — jamais de fichiers dupliqués écrits sur disque.

ATTENTION — ORDRE DES CLASSES
------------------------------
L'ordre alphabétique des dossiers (Mais_..., Poivron_..., Tomate_...) NE
correspond PAS à l'ordre des indices dans classes.json (Tomate = 0-3,
Maïs = 4-7, Poivron = 8-9). CLASS_FOLDER_ORDER ci-dessous force l'ordre
correct. Si une nouvelle classe est ajoutée un jour, il faut mettre à jour
CLASS_FOLDER_ORDER et classes.json EN MÊME TEMPS.

Utilisation par le Binôme B (dans le notebook Colab d'entraînement) :

    from src.data.preprocessing import build_datasets
    train_ds, val_ds, test_ds, class_names = build_datasets()
    model.fit(train_ds, validation_data=val_ds, epochs=...)

Test local, sans GPU, juste pour vérifier que les données se chargent :

    python src/data/preprocessing.py
"""
from pathlib import Path

import tensorflow as tf

ROOT = Path(__file__).resolve().parents[2]
DATA_SPLIT = ROOT / "data" / "split"
IMG_SIZE = (224, 224)   # cf. contrat_interface.md
BATCH_SIZE = 32
SEED = 42

# Doit rester synchronisé avec classes.json — voir avertissement ci-dessus.
CLASS_FOLDER_ORDER = [
    "Tomate_Saine",               # index 0
    "Tomate_Mildiou_tardif",      # index 1
    "Tomate_Tache_bacterienne",   # index 2
    "Tomate_Septoriose",          # index 3
    "Mais_Sain",                  # index 4
    "Mais_Rouille_commune",       # index 5
    "Mais_Helminthosporiose",     # index 6
    "Mais_Cercosporiose",         # index 7
    "Poivron_Sain",               # index 8
    "Poivron_Tache_bacterienne",  # index 9
]


def _check_folders_exist(split_name: str):
    split_dir = DATA_SPLIT / split_name
    missing = [c for c in CLASS_FOLDER_ORDER if not (split_dir / c).exists()]
    if missing:
        raise FileNotFoundError(
            f"Dossiers manquants dans {split_dir} : {missing}. "
            f"Lance src/data/split.py avant preprocessing.py."
        )


def _load_raw_dataset(split_name: str, shuffle: bool):
    _check_folders_exist(split_name)
    split_dir = DATA_SPLIT / split_name
    return tf.keras.utils.image_dataset_from_directory(
        split_dir,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=shuffle,
        seed=SEED,
        label_mode="categorical",
        class_names=CLASS_FOLDER_ORDER,  # force l'ordre — voir avertissement en tête de fichier
    )


def _normalize(image, label):
    return tf.cast(image, tf.float32) / 255.0, label


def build_augmentation_pipeline():
    """
    Augmentation volontairement agressive (cf. guide de projet, §4.2) pour
    compenser l'absence de photos de terrain : PlantVillage est un corpus
    de laboratoire (fond uni, éclairage stable), donc on habitue le modèle
    à des conditions dégradées dès l'entraînement.
    """
    return tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal_and_vertical"),
        tf.keras.layers.RandomRotation(0.15),
        tf.keras.layers.RandomBrightness(0.2),
        tf.keras.layers.RandomContrast(0.2),
        tf.keras.layers.GaussianNoise(0.03),
    ], name="augmentation")


def build_datasets():
    train_ds = _load_raw_dataset("train", shuffle=True)
    val_ds = _load_raw_dataset("val", shuffle=False)
    test_ds = _load_raw_dataset("test", shuffle=False)

    class_names = train_ds.class_names  # == CLASS_FOLDER_ORDER, dans cet ordre

    train_ds = train_ds.map(_normalize, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.map(_normalize, num_parallel_calls=tf.data.AUTOTUNE)
    test_ds = test_ds.map(_normalize, num_parallel_calls=tf.data.AUTOTUNE)

    augment = build_augmentation_pipeline()
    train_ds = train_ds.map(
        lambda x, y: (augment(x, training=True), y),
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(tf.data.AUTOTUNE)
    test_ds = test_ds.prefetch(tf.data.AUTOTUNE)

    return train_ds, val_ds, test_ds, class_names


def main():
    if not DATA_SPLIT.exists():
        print(f"{DATA_SPLIT} n'existe pas — lance d'abord src/data/split.py")
        return

    train_ds, val_ds, test_ds, class_names = build_datasets()
    print(f"Classes (dans l'ordre de classes.json) : {class_names}")
    assert list(class_names) == CLASS_FOLDER_ORDER, "Ordre des classes incohérent !"

    for name, ds in [("train", train_ds), ("val", val_ds), ("test", test_ds)]:
        n_batches = sum(1 for _ in ds)
        print(f"{name}: {n_batches} lots de taille ~{BATCH_SIZE}")

    print("\nOK — le pipeline est prêt à être importé dans le notebook Colab du Binôme B.")


if __name__ == "__main__":
    main()
