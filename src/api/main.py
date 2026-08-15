"""
Service d'inférence AgriVision-AI (Binôme A).

/health et /classes sont opérationnels. /predict valide réellement
l'image reçue (pas seulement l'en-tête Content-Type, qui peut être faux)
et renvoie une réponse factice tant que le modèle (Binôme B) n'est pas
livré — au format défini dans contrat_interface.md, pour que
l'application puisse déjà se développer contre ce mock.
"""
import io
import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent


def _find_classes_json(start: Path) -> Path:
    """
    Cherche classes.json en remontant depuis le dossier du script.
    Fonctionne à la fois en local (src/api/main.py -> remonte à la racine
    du dépôt) et dans le conteneur Docker (classes.json copié au même
    niveau que main.py, cf. src/api/Dockerfile).
    """
    for candidate_dir in [start, *start.parents]:
        candidate = candidate_dir / "classes.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"classes.json introuvable en remontant depuis {start}")


CLASSES_PATH = _find_classes_json(ROOT)
MODEL_VERSION = "mock-0.0"  # sera remplacé par la vraie version au jalon J14

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo, cf. contrat d'interface
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}

app = FastAPI(
    title="AgriVision-AI — Service d'inférence",
    description="Diagnostic de maladies des cultures à partir d'une photo de feuille. "
                 "Voir contrat_interface.md à la racine du dépôt pour le détail du contrat.",
    version=MODEL_VERSION,
)


def load_classes():
    with open(CLASSES_PATH, encoding="utf-8") as f:
        return json.load(f)["classes"]


@app.get("/health", summary="État du service")
def health():
    """Vérifie que le service répond et indique la version du modèle chargé."""
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.get("/classes", summary="Liste ordonnée des classes")
def classes():
    """Renvoie les 10 classes dans leur ordre figé (source unique : classes.json)."""
    return load_classes()


@app.post("/predict", summary="Diagnostic à partir d'une photo de feuille")
async def predict(file: UploadFile = File(..., description="Image JPEG ou PNG, 5 Mo max")):
    """
    Reçoit une image, la valide (type déclaré, taille, lisibilité réelle),
    et renvoie le diagnostic au format défini par le contrat d'interface.
    """
    # 1. Type déclaré par le client
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté ({file.content_type}). JPEG ou PNG uniquement.",
        )

    # 2. Taille
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(contents) / 1024 / 1024:.1f} Mo, max 5 Mo).",
        )

    # 3. Lisibilité réelle — le Content-Type déclaré peut mentir ou être absent,
    # donc on vérifie que le contenu est vraiment une image décodable.
    try:
        with Image.open(io.BytesIO(contents)) as img:
            img.verify()
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Fichier illisible : ce n'est pas une image valide.")
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur lors de la lecture de l'image.")

    # TODO (après J14) : redimensionner en 224x224, normaliser, appeler le
    # modèle réel (src/model/), générer la vraie carte Grad-CAM.
    all_classes = load_classes()
    top = all_classes[0]
    return {
        "predicted_class": f"{top['culture']} - {top['etat']}",
        "class_index": top["index"],
        "confidence": 0.42,
        "top3": [
            {"class_index": c["index"], "label": f"{c['culture']} - {c['etat']}", "score": 0.0}
            for c in all_classes[:3]
        ],
        "gradcam_base64": None,
        "model_version": MODEL_VERSION,
    }
