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
Version en service : `mobilenetv2-v2.0`, entraînée sur PlantVillage (studio) et
PlantWild (terrain).

| | studio (PlantVillage) | terrain (PlantDoc) |
|---|---|---|
| Exactitude | 94,36 % | 48,99 % |
| F1 macro | 0,9373 | 0,4520 |

Le jeu de terrain, 942 photographies prises au champ, n'a jamais servi à
l'entraînement d'aucune version. C'est le seul juge honnête de ce que vaut le
modèle en conditions réelles.

L'écart entre les deux colonnes est le résultat le plus important du projet.
PlantVillage est photographié en studio, feuille détachée sur fond uni : un
modèle qui n'a vu que cela apprend autant les conditions de prise de vue que la
maladie. Le chapitre « robustesse » du rapport détaille la mesure.

### Ce qu'a apporté la version 2

La première version, entraînée sur le seul PlantVillage, atteignait 96,64 % en
studio mais 36,27 % au champ, et surtout restait aussi confiante quand elle se
trompait que lorsqu'elle avait raison.

Sur les 942 photographies de terrain, en comptant ce que voit réellement
l'utilisateur :

| | v1 | v2 |
|---|---|---|
| Diagnostics affirmés sans avertissement | 672 | 220 |
| — dont corrects | 269 | 159 |
| **Fiabilité quand l'application affirme** | **40,0 %** | **72,3 %** |
| **Diagnostics faux affirmés sans avertissement** | **403** | **61** |

La v2 se prononce moins souvent, mais elle a raison bien plus souvent quand elle
le fait, et le nombre de diagnostics faux annoncés avec assurance est divisé par
près de sept. Pour un outil d'aide à la décision agricole, un modèle qui sait
douter vaut mieux qu'un modèle qui a un peu plus souvent raison.

Le seuil d'avertissement de l'application a été réglé en conséquence, à 60 %
au lieu de 70 % : la v2 produit des probabilités plus basses, ayant été entraînée
avec un lissage des étiquettes.

Les deux modèles sont conservés. `notebooks/02_amelioration_robustesse.ipynb`
produit la v2 et compare les deux sur les mêmes jeux.

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

**Modèle entraîné** — `mobilenetv2_v2.keras`, 26 Mo, non versionné (Git n'est pas
fait pour les fichiers binaires lourds). La v1 est conservée à côté, pour la
comparaison du rapport :

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

**Au champ, le modèle se trompe une fois sur deux.** C'est mesuré, pas supposé :
48,99 % d'exactitude sur 942 photographies de terrain, contre 94,36 % en studio.
L'application est conçue autour de cette limite, en signalant explicitement les
diagnostics incertains plutôt qu'en affichant un chiffre rassurant.

L'entraînement repose majoritairement sur PlantVillage, photographié en studio,
feuille détachée sur fond uni. PlantWild apporte des images de terrain, mais en
bien moindre quantité. Un modèle entraîné dans ces conditions apprend en partie
la prise de vue et non la seule maladie.

Les cartes Grad-CAM se posent sur les lésions et non sur le fond, ce qui écarte
l'hypothèse d'un modèle ayant appris le décor. Cette vérification reste toutefois
faite sur les corpus disponibles.

Le jeu de test de terrain provient d'une source unique, PlantDoc. D'autres
conditions de prise de vue donneraient d'autres chiffres. La classe
« Maïs - Sain » y est absente et n'a donc pas pu être évaluée au champ.

Toute image n'appartenant pas aux 10 classes est rapprochée de force de l'une
d'entre elles : le modèle répartit toujours 100 % de certitude entre les classes
qu'il connaît. Une feuille de manioc ou une photo de chaussure produira donc un
diagnostic, dépourvu de sens.

Les recommandations de `src/app/recommandations.json` orientent une observation de
terrain. Elles ne remplacent pas le diagnostic d'un conseiller agricole ou d'un
service de protection des végétaux, seuls habilités à préconiser un traitement.
