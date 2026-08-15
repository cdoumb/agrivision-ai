"""
Service d'inférence AgriVision-AI (Binôme A).

Phase 0 (squelette) : /health et /classes fonctionnent déjà.
/predict renvoie une réponse factice tant que le modèle (Binôme B)
n'est pas livré — respecte déjà le format défini dans contrat_interface.md
pour que l'application puisse se développer contre ce mock.
"""
import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException

ROOT = Path(__file__).resolve().parents[2]
CLASSES_PATH = ROOT / "classes.json"
MODEL_VERSION = "mock-0.0"  # sera remplacé par la vraie version au jalon J14

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo, cf. contrat d'interface
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}

app = FastAPI(title="AgriVision-AI — Service d'inférence")


def load_classes():
    with open(CLASSES_PATH, encoding="utf-8") as f:
        return json.load(f)["classes"]


@app.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.get("/classes")
def classes():
    return load_classes()


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Format non supporté : JPEG ou PNG uniquement.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo).")

    # TODO (après J14) : redimensionner en 224x224, normaliser, appeler le
    # modèle réel, générer la vraie carte Grad-CAM.
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
