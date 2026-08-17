"""
Nettoyage + split train/val/test — AgriVision-AI (Binôme A).

Étapes, dans cet ordre, pour éviter toute fuite de données :
  1. Supprime les doublons EXACTS (même contenu binaire) — ne garde qu'un
     exemplaire par groupe.
  2. Regroupe les quasi-doublons (hash perceptif identique) : un groupe
     entier ira dans UN SEUL jeu (train, val ou test), jamais réparti.
  3. Split stratifié par classe : 70 % train / 15 % val / 15 % test,
     graine aléatoire fixée pour la reproductibilité.
  4. Copie les fichiers vers data/split/{train,val,test}/<classe>/ et
     écrit un manifeste CSV.

Se lance UNE FOIS que src/data/stats.py a tourné (pour identifier les
doublons) — en pratique ce script refait sa propre détection en interne.

Usage :
  python src/data/split.py
"""
import csv
import hashlib
import random
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_SPLIT = ROOT / "data" / "split"
REPORT_PATH = ROOT / "reports" / "split_report.md"
MANIFEST_PATH = ROOT / "reports" / "split_manifest.csv"

SEED = 42
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


def md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_duplicate_groups(image_paths):
    """
    Renvoie une liste de groupes (listes de chemins). Un groupe = images
    identiques ou quasi-identiques qui doivent rester ensemble dans le
    même split. Les images sans doublon forment un groupe à un seul élément.
    """
    exact_hash_to_paths = defaultdict(list)
    for p in image_paths:
        exact_hash_to_paths[md5_of_file(p)].append(p)

    # On garde un seul exemplaire par doublon exact (les autres sont
    # écartés du corpus, ce sont des copies inutiles).
    kept_paths = [paths[0] for paths in exact_hash_to_paths.values()]
    dropped_exact = sum(len(paths) - 1 for paths in exact_hash_to_paths.values())

    if not HAS_IMAGEHASH:
        return [[p] for p in kept_paths], dropped_exact, 0

    perceptual_to_paths = defaultdict(list)
    for p in kept_paths:
        try:
            with Image.open(p) as im:
                h = str(imagehash.average_hash(im))
            perceptual_to_paths[h].append(p)
        except Exception:
            perceptual_to_paths[f"__unreadable__{p}"].append(p)

    groups = list(perceptual_to_paths.values())
    merged_groups_count = sum(1 for g in groups if len(g) > 1)
    return groups, dropped_exact, merged_groups_count


def stratified_group_split(groups, seed):
    """
    Répartit des groupes (pas des images individuelles) entre
    train/val/test en respectant approximativement les ratios cibles,
    mesurés en nombre d'IMAGES (pas en nombre de groupes).
    """
    rng = random.Random(seed)
    groups = groups[:]
    rng.shuffle(groups)

    total_images = sum(len(g) for g in groups)
    targets = {k: v * total_images for k, v in RATIOS.items()}
    current = {k: 0 for k in RATIOS}
    assigned = {k: [] for k in RATIOS}

    for group in groups:
        # assigne au split le plus "en retard" par rapport à sa cible
        deficits = {k: targets[k] - current[k] for k in RATIOS}
        best_split = max(deficits, key=deficits.get)
        assigned[best_split].append(group)
        current[best_split] += len(group)

    return assigned


def main():
    if not DATA_RAW.exists():
        print(f"{DATA_RAW} n'existe pas — lance d'abord src/data/download.py")
        return

    if DATA_SPLIT.exists():
        print(f"{DATA_SPLIT} existe déjà — suppression avant reconstruction.")
        shutil.rmtree(DATA_SPLIT)

    class_dirs = sorted([d for d in DATA_RAW.iterdir() if d.is_dir()])
    manifest_rows = []
    report_lines = [
        "# Rapport de split — AgriVision-AI\n",
        f"Graine aléatoire : {SEED} | Ratios cibles : train {RATIOS['train']:.0%}, "
        f"val {RATIOS['val']:.0%}, test {RATIOS['test']:.0%}\n",
        "| Classe | Total brut | Doublons exacts retirés | Groupes quasi-dupliqués fusionnés | Train | Val | Test |",
        "|---|---|---|---|---|---|---|",
    ]

    for class_dir in class_dirs:
        class_name = class_dir.name
        image_paths = [p for p in class_dir.iterdir() if p.is_file()]
        groups, dropped_exact, merged_groups = build_duplicate_groups(image_paths)
        assigned = stratified_group_split(groups, seed=SEED)

        counts = {}
        for split_name, split_groups in assigned.items():
            split_dir = DATA_SPLIT / split_name / class_name
            split_dir.mkdir(parents=True, exist_ok=True)
            n = 0
            for group in split_groups:
                for img_path in group:
                    dest = split_dir / img_path.name
                    shutil.copy(img_path, dest)
                    manifest_rows.append({
                        "class": class_name,
                        "split": split_name,
                        "filename": img_path.name,
                        "source_path": str(img_path),
                    })
                    n += 1
            counts[split_name] = n

        report_lines.append(
            f"| {class_name} | {len(image_paths)} | {dropped_exact} | {merged_groups} | "
            f"{counts['train']} | {counts['val']} | {counts['test']} |"
        )
        print(f"{class_name}: train={counts['train']} val={counts['val']} test={counts['test']} "
              f"(doublons exacts retirés: {dropped_exact})")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HAS_IMAGEHASH:
        report_lines.append(
            "\n> Regroupement des quasi-doublons désactivé : "
            "installe `imagehash` pour une protection complète contre la fuite de données."
        )
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["class", "split", "filename", "source_path"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"\nRapport : {REPORT_PATH}")
    print(f"Manifeste : {MANIFEST_PATH}")
    print(f"Données splittées dans : {DATA_SPLIT}")


if __name__ == "__main__":
    main()
