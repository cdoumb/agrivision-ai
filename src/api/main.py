"""
Service d'inférence AgriVision-AI.

Squelette et validation : Binôme A.
Branchement du modèle réel : Binôme B, le 17 août 2026.

/predict valide réellement l'image reçue (pas seulement l'en-tête
Content-Type, qui peut être faux) puis délègue le diagnostic au module
src/model/inference.py. Tout ce qui touche au réseau de neurones vit
là-bas : ce fichier ne s'occupe que du transport HTTP.
"""
import io
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent

# Rend src/model/inference.py importable aussi bien en local (le module est
# alors dans src/, un cran au-dessus) que dans le conteneur (où le Dockerfile
# copie le code dans /app/model/, déjà sur le chemin d'import).
sys.path.insert(0, str(ROOT.parent))

from model import inference  # noqa: E402


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
MODEL_VERSION = inference.VERSION_MODELE

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo, cf. contrat d'interface
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Charge le modèle au démarrage plutôt qu'à la première requête, qui
    attendrait sinon une dizaine de secondes.

    Un modèle absent n'empêche pas le service de démarrer : /health le signale
    et /predict répond 503. Sans ça, un conteneur mal configuré redémarrerait
    en boucle sans qu'on sache pourquoi.
    """
    try:
        inference.charger()
        print(f"Modèle chargé : {inference.CHEMIN_MODELE}")
    except FileNotFoundError as erreur:
        print(f"AVERTISSEMENT — service démarré sans modèle.\n{erreur}")
    yield


app = FastAPI(
    title="AgriVision-AI — Service d'inférence",
    description="Diagnostic de maladies des cultures à partir d'une photo de feuille. "
                 "Voir contrat_interface.md à la racine du dépôt pour le détail du contrat.",
    version=MODEL_VERSION,
    lifespan=lifespan,
)


def load_classes():
    with open(CLASSES_PATH, encoding="utf-8") as f:
        return json.load(f)["classes"]


@app.get("/health", summary="État du service")
def health():
    """
    Vérifie que le service répond et indique la version du modèle chargé.

    `model_loaded` distingue deux situations que le seul « status: ok »
    confondait : le service répond mais ne sait pas encore diagnostiquer,
    et le service est pleinement opérationnel.
    """
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "model_loaded": inference.est_charge(),
    }


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

    # 4. Diagnostic. Le redimensionnement en 224x224 et la normalisation ont
    # lieu dans le module d'inférence, donc côté service comme l'impose la
    # section 2 du contrat, jamais côté application.
    try:
        return inference.diagnostiquer(contents)
    except FileNotFoundError:
        # Modèle absent : on le dit franchement plutôt que de renvoyer un
        # diagnostic factice qu'un client prendrait pour argent comptant.
        raise HTTPException(
            status_code=503,
            detail="Service indisponible : le modèle n'est pas chargé. "
                   "Voir les journaux du service au démarrage.",
        )
    except Exception as erreur:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur pendant le diagnostic : {type(erreur).__name__}",
        )
