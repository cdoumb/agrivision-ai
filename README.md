# AgriVision-AI

Plateforme d'aide au diagnostic des maladies des cultures par vision par ordinateur.
Projet ESMT Dakar — Cycle Ingénierie des Données et IA — 11 au 30 août 2026.

- Cheick Oumar Doumbia — Binôme A (données & service)
- Faustin Félicien Pikbougoum — Binôme B (modèle & application)

À partir de la photo d'une feuille, la plateforme identifie l'une des 10 classes
du contrat, indique son niveau de certitude, montre les zones de l'image qui ont
emporté la décision, et propose une conduite à tenir.

## Résultats du modèle

MobileNetV2 pré-entraîné sur ImageNet, transfert d'apprentissage puis fine-tuning.

| | |
|---|---|
| Exactitude sur le jeu de test | **96,64 %** (2 056 images jamais vues) |
| F1 macro | **0,9566** |
| Découpage train / val / test | 9 597 / 2 058 / 2 056 |
| Version du modèle | `mobilenetv2-v1.0` |

Les deux classes les plus difficiles sont la cercosporiose du maïs (F1 0,825) et
l'helminthosporiose du maïs (F1 0,899). Elles se confondent l'une avec l'autre :
les deux maladies produisent des lésions allongées gris-brun que l'œil humain
distingue mal sur photo. Toutes les autres classes dépassent 0,95.

L'application traite ce cas explicitement. Quand l'écart entre les deux premières
hypothèses est trop faible pour trancher, elle le signale et présente les deux
fiches côte à côte plutôt que d'imposer une réponse.

## Démarrage rapide

```bash
git clone https://github.com/cdoumb/agrivision-ai.git
cd agrivision-ai
# déposer le modèle dans models/ (voir section suivante)
docker compose up --build
```

- Service d'inférence : http://localhost:8000/docs
- Application : http://localhost:8501

Le premier démarrage prend quelques minutes, TensorFlow étant volumineux à
installer. L'application attend automatiquement que le service ait fini de
charger le modèle.

## Récupérer les données et le modèle

**Modèle entraîné** — `mobilenetv2_v1.keras`, 23 Mo, non versionné (Git n'est pas
fait pour les fichiers binaires lourds) :

> https://drive.google.com/drive/folders/19gji6dIzjMUoqy0ImYFwKCNAHGvcAER7?usp=sharing

Télécharger le fichier et le placer dans `models/` à la racine du dépôt. Le dossier
contient également `model_card.json`, qui détaille les résultats par classe et le
prétraitement attendu.

**Corpus** — PlantVillage, version *color*, hébergé sur Kaggle. Voir
`src/data/download.py`. Les images ne sont pas versionnées non plus : elles se
retéléchargent, et le découpage est reproductible à l'identique grâce à
`reports/split_manifest.csv`.

## Lancer sans Docker

Utile pour développer, ou lorsque la virtualisation n'est pas disponible sur la
machine. Deux terminaux :

```bash
# terminal 1 — service d'inférence
pip install -r src/api/requirements.txt
cd src/api && uvicorn main:app --port 8000

# terminal 2 — application
pip install -r src/app/requirements.txt
streamlit run src/app/main.py
```

Les deux jeux de dépendances ne cohabitent pas dans un même environnement :
Streamlit et TensorFlow exigent des versions incompatibles de `protobuf`. En
Docker le problème ne se pose pas, les conteneurs étant séparés. En local,
prévoir deux environnements virtuels, ou installer les versions épinglées dans
l'ordre indiqué ci-dessus.

## Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

28 tests : 8 sur la validation du service, 20 sur le module d'inférence. Ceux qui
nécessitent le fichier `.keras` s'ignorent automatiquement lorsqu'il est absent,
afin que la suite reste exécutable sur une machine sans le modèle.

## Réentraîner le modèle

`notebooks/01_entrainement_mobilenetv2.ipynb`, à ouvrir dans Google Colab avec un
GPU. Le notebook relit `reports/split_manifest.csv` au lieu de recalculer un
découpage, ce qui garantit que tout nouveau modèle reste comparable au précédent.

Il vérifie aussi, avant d'entraîner, que le nombre d'images de chaque classe
correspond au rapport de découpage, et affiche le taux de correspondance avec le
manifeste. Un corpus qui aurait changé se détecte donc en deux minutes plutôt
qu'après l'entraînement.

Le notebook est produit par `notebooks/build_notebook.py`, le format `.ipynb`
étant du JSON difficile à relire dans un diff.

## Structure du dépôt

| Dossier | Contenu | Responsable |
|---|---|---|
| `data/` | Images (non versionné) | A |
| `notebooks/` | Carnets Colab | Les deux |
| `src/data/` | Téléchargement, split, prétraitement, augmentation | A |
| `src/api/` | Service d'inférence FastAPI | A |
| `src/model/` | Inférence, Grad-CAM | B |
| `src/app/` | Application Streamlit | B |
| `models/` | Modèle entraîné (non versionné) | B |
| `reports/` | Statistiques, découpage, matrice de confusion, courbes | Les deux |
| `docs/` | Schéma d'architecture, doc API, rapport | Les deux |

## Documents clés

- [`contrat_interface.md`](./contrat_interface.md) — format image, API, classes (gelé au 14/08)
- [`classes.json`](./classes.json) — liste ordonnée des 10 classes, source unique
- [`docs/api.md`](./docs/api.md) — documentation du service
- `reports/model_card.json` — fiche du modèle (sur le Drive)

## Limites connues

Le corpus PlantVillage est constitué de photos prises en studio, feuille détachée
sur fond uni. Les performances annoncées valent dans ces conditions et ne
préjugent pas du comportement sur des photos prises au champ, avec un feuillage
dense, des ombres portées et un éclairage variable.

Les cartes Grad-CAM produites se posent bien sur les lésions et non sur le fond,
ce qui écarte l'hypothèse d'un modèle ayant appris le décor plutôt que la maladie.
Cette vérification reste néanmoins interne au corpus.

Toute image n'appartenant pas aux 10 classes est rapprochée de force de l'une
d'entre elles : le modèle répartit toujours 100 % de certitude entre les classes
qu'il connaît. Une feuille de manioc ou une photo de chaussure produira donc un
diagnostic, dépourvu de sens.

Les recommandations de `src/app/recommandations.json` orientent une observation de
terrain. Elles ne remplacent pas le diagnostic d'un conseiller agricole ou d'un
service de protection des végétaux, seuls habilités à préconiser un traitement.
