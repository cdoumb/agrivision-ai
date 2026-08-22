# Service d'inférence, documentation

Le service expose une documentation interactive auto-générée par FastAPI,
disponible dès qu'il tourne : **http://localhost:8000/docs**

Le modèle réel est branché depuis le 17 août 2026. Le service charge son modèle au
démarrage, ce qui prend une dizaine de secondes, et non à la première requête.

La version servie dépend de `AGRIVISION_MODELE` dans `docker-compose.yml`,
`mobilenetv2_v2.keras` par défaut. Les exemples ci-dessous correspondent à cette version.

## Endpoints

### `GET /health`

Vérifie que le service répond et indique la version du modèle.

```json
{
  "status": "ok",
  "model_version": "mobilenetv2-v2.0",
  "model_loaded": true
}
```

`model_loaded` distingue deux situations que `status: ok` confondait : le service répond
mais ne sait pas encore diagnostiquer (modèle absent), et le service est pleinement
opérationnel. Un modèle absent n'empêche pas le démarrage, afin qu'un conteneur mal
configuré ne redémarre pas en boucle sans explication ; `/predict` répond alors 503.

### `GET /classes`

Renvoie les 10 classes dans leur ordre figé (source unique : `classes.json`).

```json
[
  { "index": 0, "culture": "Tomate", "etat": "Saine" },
  { "index": 1, "culture": "Tomate", "etat": "Mildiou tardif" },
  ...
]
```

### `POST /predict`

Reçoit une image en `multipart/form-data`, champ `file`.

**Contraintes** (cf. `contrat_interface.md`) :

- Format JPEG ou PNG uniquement
- 5 Mo maximum
- Le fichier doit être une image réellement décodable, pas seulement porter la bonne
  extension ou le bon `Content-Type` déclaré

Le redimensionnement en 224 x 224 et la normalisation ont lieu ici, côté service, jamais
côté application. C'est la section 2 du contrat d'interface, et c'est ce qui garantit que
l'image est préparée exactement comme à l'entraînement.

**Exemple d'appel :**

```bash
curl -X POST http://localhost:8000/predict \
  -F "file=@feuille.jpg;type=image/jpeg"
```

**Réponse (200) :**

```json
{
  "predicted_class": "Tomate - Mildiou tardif",
  "class_index": 1,
  "confidence": 0.7412,
  "top3": [
    { "class_index": 1, "label": "Tomate - Mildiou tardif", "score": 0.7412 },
    { "class_index": 3, "label": "Tomate - Septoriose",     "score": 0.1803 },
    { "class_index": 2, "label": "Tomate - Tache bactérienne", "score": 0.0421 }
  ],
  "gradcam_base64": "iVBORw0KGgoAAAANSUhEUg...",
  "model_version": "mobilenetv2-v2.0"
}
```

`confidence` et les scores de `top3` sont arrondis à quatre décimales.
`gradcam_base64` contient la carte de chaleur superposée à la photo, encodée en PNG
base64. Elle vaut `null` si la carte n'a pas pu être produite.

**Codes d'erreur :**

| Code | Cause |
|---|---|
| 400 | Format non supporté, fichier vide, fichier trop volumineux, image illisible ou corrompue |
| 503 | Le service fonctionne mais aucun modèle n'est chargé |
| 500 | Erreur inattendue pendant le diagnostic |

## Lancer le service

**Avec Docker, service et application ensemble :**

```bash
docker compose up --build
```

**Sans Docker :**

```bash
pip install -r src/api/requirements.txt
cd src/api && uvicorn main:app --port 8000
```

Streamlit et TensorFlow exigent des versions incompatibles de `protobuf` : en local,
prévoir deux environnements virtuels séparés pour le service et pour l'application. En
Docker la question ne se pose pas, les conteneurs étant distincts.

## Tests

```bash
pip install -r tests/requirements.txt
pytest tests/test_api.py -v
```

8 tests couvrent le service : `/health`, l'ordre des 10 classes, un diagnostic valide, et
cinq cas de refus (type déclaré non supporté, fichier vide, dépassement de taille, image
corrompue, et PNG valide déguisé sous un `Content-Type` mensonger).
