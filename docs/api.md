# Service d'inférence — documentation

Le service expose une documentation interactive auto-générée par FastAPI,
disponible dès qu'il tourne : **http://localhost:8000/docs**

## Endpoints

### `GET /health`
Vérifie que le service répond.
```json
{ "status": "ok", "model_version": "mock-0.0" }
```

### `GET /classes`
Renvoie les 10 classes dans leur ordre figé (source : `classes.json`).
```json
[
  { "index": 0, "culture": "Tomate", "etat": "Saine" },
  ...
]
```

### `POST /predict`
Reçoit une image en `multipart/form-data`, champ `file`.

**Contraintes** (cf. `contrat_interface.md`) :
- Format JPEG ou PNG uniquement
- 5 Mo maximum
- Le fichier doit être une image réellement décodable (pas seulement porter
  la bonne extension ou le bon Content-Type déclaré)

**Exemple d'appel (curl) :**
```bash
curl -X POST http://localhost:8000/predict \
  -F "file=@feuille.jpg;type=image/jpeg"
```

**Réponse (200) :**
```json
{
  "predicted_class": "Tomate - Mildiou tardif",
  "class_index": 1,
  "confidence": 0.94,
  "top3": [...],
  "gradcam_base64": null,
  "model_version": "mock-0.0"
}
```

**Erreurs possibles (400) :** format non supporté, fichier vide, fichier
trop volumineux, image illisible/corrompue.

## Statut actuel
Le modèle réel n'est pas encore intégré : `/predict` renvoie une réponse
mock (toujours la première classe, confiance factice) mais respecte déjà
exactement le format attendu, pour que le Binôme B puisse développer
l'application contre ce service dès maintenant.

## Lancer le service

**Sans Docker :**
```bash
pip install -r src/api/requirements.txt
uvicorn src.api.main:app --reload --app-dir .
```

**Avec Docker (service + app ensemble) :**
```bash
docker compose up --build
```

## Tests
```bash
pip install -r tests/requirements.txt
pytest tests/test_api.py -v
```
