# AgriVision-AI

Plateforme d'aide au diagnostic des maladies des cultures par vision par ordinateur.
Projet ESMT Dakar — Cycle Ingénierie des Données et IA — 11 au 30 août 2026.

- Cheick Oumar Doumbia — Binôme A (données & service)
- Faustin Félicien Pikbougoum — Binôme B (modèle & application)

## Démarrage rapide

```bash
git clone <url-du-depot>
cd agrivision-ai
docker compose up --build
```

- Service d'inférence : http://localhost:8000/docs
- Application : http://localhost:8501

## Récupérer les données et le modèle
- Corpus : PlantVillage (Kaggle) — script `src/data/download.py` (à venir)
- Modèle entraîné : lien Google Drive à ajouter ici après l'entraînement

## Structure du dépôt
| Dossier | Contenu | Responsable |
|---|---|---|
| `data/` | Images (non versionné) | A |
| `notebooks/` | Carnets Colab | Les deux |
| `src/data/` | Téléchargement, split, prétraitement, augmentation | A |
| `src/api/` | Service d'inférence FastAPI | A |
| `src/model/` | Entraînement, évaluation, Grad-CAM | B |
| `src/app/` | Application Streamlit | B |
| `models/` | Modèle entraîné (non versionné) | B |
| `reports/` | Matrice de confusion, courbes, cartes | B |
| `docs/` | Schéma d'architecture, doc API, rapport | Les deux |

## Documents clés
- [`contrat_interface.md`](./contrat_interface.md) — format image, API, classes (gelé au 14/08)
- [`classes.json`](./classes.json) — liste ordonnée des 10 classes
