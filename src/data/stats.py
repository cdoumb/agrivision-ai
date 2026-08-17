"""
Statistiques du corpus AgriVision-AI (Binôme A).

Calcule, pour chaque classe présente dans data/raw/ :
  - le nombre d'images
  - les dimensions rencontrées (pour repérer les images atypiques)
  - les doublons exacts (même contenu binaire, piège classique de PlantVillage)
  - les doublons quasi-identiques (même image, ré-encodée différemment),
    détectés par hash perceptif

Produit un rapport texte dans reports/corpus_stats.md et repère les
classes déséquilibrées (utile pour l'étape de rééquilibrage à venir).

Usage :
  python src/data/stats.py
"""
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
REPORT_PATH = ROOT / "reports" / "corpus_stats.md"


def md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze_class(class_dir: Path):
    images = [p for p in class_dir.iterdir() if p.is_file()]
    dims = Counter()
    exact_hashes = defaultdict(list)
    perceptual_hashes = defaultdict(list)
    corrupt = []

    for img_path in images:
        try:
            with Image.open(img_path) as im:
                dims[im.size] += 1
                if HAS_IMAGEHASH:
                    perceptual_hashes[str(imagehash.average_hash(im))].append(img_path.name)
        except Exception as e:
            corrupt.append((img_path.name, str(e)))
            continue

        exact_hashes[md5_of_file(img_path)].append(img_path.name)

    exact_dupes = {h: files for h, files in exact_hashes.items() if len(files) > 1}
    perceptual_dupes = {h: files for h, files in perceptual_hashes.items() if len(files) > 1}

    return {
        "count": len(images),
        "dims": dims,
        "exact_dupes": exact_dupes,
        "perceptual_dupes": perceptual_dupes,
        "corrupt": corrupt,
    }


def main():
    if not DATA_RAW.exists():
        print(f"{DATA_RAW} n'existe pas encore — lance d'abord src/data/download.py")
        return

    class_dirs = sorted([d for d in DATA_RAW.iterdir() if d.is_dir()])
    if not class_dirs:
        print(f"Aucune classe trouvée dans {DATA_RAW}")
        return

    results = {}
    for class_dir in class_dirs:
        print(f"Analyse de {class_dir.name} ...")
        results[class_dir.name] = analyze_class(class_dir)

    counts = {name: r["count"] for name, r in results.items()}
    total = sum(counts.values())
    max_count = max(counts.values())
    min_count = min(counts.values())
    imbalance_ratio = max_count / min_count if min_count > 0 else float("inf")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Statistiques du corpus — AgriVision-AI\n",
        f"Total images analysées : **{total}**\n",
        f"Ratio de déséquilibre max/min : **{imbalance_ratio:.2f}**"
        + (" ⚠️ à corriger avant l'entraînement" if imbalance_ratio > 2 else " (acceptable)") + "\n",
        "## Images par classe\n",
        "| Classe | Images | Dimensions dominantes | Doublons exacts | Quasi-doublons | Fichiers corrompus |",
        "|---|---|---|---|---|---|",
    ]

    for name, r in results.items():
        top_dim = r["dims"].most_common(1)
        top_dim_str = f"{top_dim[0][0]} ({top_dim[0][1]}x)" if top_dim else "—"
        lines.append(
            f"| {name} | {r['count']} | {top_dim_str} | "
            f"{len(r['exact_dupes'])} groupes | "
            f"{len(r['perceptual_dupes']) if HAS_IMAGEHASH else 'non calculé'} groupes | "
            f"{len(r['corrupt'])} |"
        )

    lines.append("\n## Détail des doublons exacts\n")
    any_exact = False
    for name, r in results.items():
        if r["exact_dupes"]:
            any_exact = True
            lines.append(f"### {name}")
            for h, files in r["exact_dupes"].items():
                lines.append(f"- `{h[:10]}...` : {', '.join(files)}")
    if not any_exact:
        lines.append("Aucun doublon exact détecté.")

    if not HAS_IMAGEHASH:
        lines.append(
            "\n> Détection des quasi-doublons désactivée : "
            "installe `imagehash` (`pip install imagehash`) pour l'activer."
        )

    if any(r["corrupt"] for r in results.values()):
        lines.append("\n## Fichiers corrompus / illisibles\n")
        for name, r in results.items():
            for fname, err in r["corrupt"]:
                lines.append(f"- {name}/{fname} : {err}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapport écrit dans {REPORT_PATH}")
    print(f"Total : {total} images | déséquilibre max/min : {imbalance_ratio:.2f}")


if __name__ == "__main__":
    main()
