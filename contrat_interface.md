# Contrat d'interface — AgriVision-AI

**Statut : GELÉ au 14 août 2026.** Toute modification doit être décidée à deux, par écrit, et ce fichier mis à jour dans la foulée.

## 1. Répartition
- **Binôme A (Cheick Oumar)** : corpus, prétraitement, service d'inférence, Docker.
- **Binôme B (Faustin)** : entraînement du modèle, évaluation, Grad-CAM, application.

## 2. Format de l'image en entrée
| Élément | Valeur |
|---|---|
| Formats acceptés | JPEG ou PNG, 3 canaux (RGB) |
| Taille max du fichier | 5 Mo |
| Dimension attendue par le modèle | 224 × 224 px |
| Qui redimensionne | **Le service (A), jamais l'application (B)** |

## 3. Points d'accès de l'API
| Méthode | Route | Rôle |
|---|---|---|
| POST | `/predict` | Reçoit l'image (form-data), renvoie le diagnostic |
| GET | `/health` | État du service |
| GET | `/classes` | Liste des classes (lue depuis `classes.json`, jamais recopiée en dur) |

## 4. Format de la réponse de `/predict` (JSON)
```json
{
  "predicted_class": "Tomate - Mildiou tardif",
  "class_index": 1,
  "confidence": 0.94,
  "top3": [
    { "class_index": 1, "label": "Tomate - Mildiou tardif", "score": 0.94 },
    { "class_index": 3, "label": "Tomate - Septoriose", "score": 0.04 },
    { "class_index": 0, "label": "Tomate - Saine", "score": 0.01 }
  ],
  "gradcam_base64": "iVBORw0KGgoAAAANSUhEUg...",
  "model_version": "mobilenetv2-v1.0"
}
```

## 5. Liste des classes
Source unique : [`classes.json`](./classes.json), 10 classes, indices 0 à 9, figés.

## 6. Conventions communes
- Le prétraitement (redimensionnement, normalisation) se fait **côté service**, jamais côté application.
- La version du modèle est renvoyée dans chaque réponse (`model_version`).
- L'application peut se développer contre un service simulé (mock) tant que le contrat est respecté.

## 7. Validation
- [ ] Confirmé par les deux étudiants
- [ ] Confirmé par Prof. Boudal NIANG (par écrit, ex. courriel)
