# AgriVision-AI

Plateforme d'aide au diagnostic des maladies des cultures par vision par ordinateur.
Projet ESMT Dakar — Cycle Ingénierie des Données et IA — 30 juillet au 30 août 2026.

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
| Exactitude | 94,36 % | 49,47 % |
| F1 macro, 9 classes comparables | 0,9306 | 0,4976 |

« Maïs - Sain » est absent de PlantDoc, le F1 macro est donc calculé sur les
9 classes présentes des deux côtés. Sur les 10 classes, il vaut 0,9373 en studio.

Ces chiffres sont ceux mesurés **par le service lui-même**, c'est-à-dire ceux
qu'obtient un utilisateur qui envoie une photo. Source :
`reports/robustesse_terrain_v2.json`, reproductible par
`python src/model/evaluation_terrain.py`.

Le notebook d'entraînement annonce des valeurs proches mais pas identiques,
48,99 % au champ par exemple. L'écart n'est pas une erreur : le notebook
redimensionne les images avec `tf.image.resize`, le service avec Pillow, et les
deux méthodes ne produisent pas exactement la même image de 224 pixels. Mesuré
sur les images de terrain, l'écart moyen entre les deux atteint 3,65 niveaux sur
255, ce qui fait basculer la décision pour cinq ou six photographies sur 942.
Les chiffres de studio, où la réduction est bien plus faible, concordent au
centième près. Les valeurs du notebook restent la référence pour comparer v1 et
v2 entre eux, puisque les deux modèles y passent par la même chaîne.

Le jeu de terrain, 942 photographies prises au champ, n'a jamais servi à
l'entraînement d'aucune version. C'est le seul juge honnête de ce que vaut le
modèle en conditions réelles.

L'écart entre les deux colonnes est le résultat le plus important du projet.
PlantVillage est photographié en studio, feuille détachée sur fond uni : un
modèle qui n'a vu que cela apprend autant les conditions de prise de vue que la
maladie. Le chapitre « robustesse » du rapport détaille la mesure.

### Ce qu'a apporté la version 2

La première version, entraînée sur le seul PlantVillage, atteignait 96,64 % en
studio mais 35,67 % au champ, et surtout restait aussi confiante quand elle se
trompait (77,3 %) que lorsqu'elle avait raison (84,4 %).

Sur les 942 photographies de terrain, en comptant ce que voit réellement
l'utilisateur. Ces quatre lignes viennent du notebook, qui mesure les deux
modèles par la même chaîne :

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

La version servie est celle désignée par `AGRIVISION_MODELE` dans
`docker-compose.yml`, `mobilenetv2_v2.keras` par défaut. Pour rejouer la
comparaison du rapport, y remplacer `v2` par `v1` et relancer. Le seuil
d'avertissement de l'application étant calibré sur le v2, un service lancé sur
le v1 affirme davantage de diagnostics faux que les 403 mesurés à 70 %.

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

La v2 ajoute PlantWild, hébergé sur Hugging Face et distribué sous licence
**CC BY-NC-ND 4.0** : usage non commercial, sans œuvre dérivée, attribution
obligatoire. Le projet est un travail académique sans exploitation commerciale.
Le modèle v2 ne peut donc pas être diffusé à des fins commerciales, et la
question de savoir si un modèle entraîné constitue une œuvre dérivée au sens de
la clause ND n'est pas tranchée : toute réutilisation hors du cadre académique
demande de revenir à la licence. La citation complète figure au chapitre
« données » du rapport.

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

30 tests : 8 sur la validation du service, 22 sur le module d'inférence. Ceux qui
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
| `reports/` | Statistiques du corpus, découpage, mesures de robustesse | Les deux |
| `docs/` | Schéma d'architecture, doc API, notice de l'application | Les deux |
| `rapport/` | Rapport de projet, un chapitre Markdown par fichier | Les deux |

## Documents clés

- [`contrat_interface.md`](./contrat_interface.md) — format image, API, classes (gelé au 14/08)
- [`classes.json`](./classes.json) — liste ordonnée des 10 classes, source unique
- [`docs/api.md`](./docs/api.md) — documentation du service
- [`docs/notice_application.md`](./docs/notice_application.md) — notice d'utilisation de l'application
- [`docs/architecture.png`](./docs/architecture.png) — schéma d'architecture annoté, six couches et frontière A/B
- [`reports/model_card.json`](./reports/model_card.json) et [`model_card_v2.json`](./reports/model_card_v2.json) — fiches des deux modèles, résultats par classe et prétraitement attendu
- [`rapport/README.md`](./rapport/README.md) — mode d'emploi du rapport : qui écrit quoi, syntaxe, génération
- [`reports/gradcam_commentaires.md`](./reports/gradcam_commentaires.md) — quatre cartes Grad-CAM analysées
- `reports/robustesse_terrain_v1.json`, `_v2.json` — mesures sur les 942 images de terrain

## Limites connues

**Au champ, le modèle se trompe une fois sur deux.** C'est mesuré, pas supposé :
49,47 % d'exactitude sur 942 photographies de terrain, contre 94,36 % en studio.
L'application est conçue autour de cette limite, en signalant explicitement les
diagnostics incertains plutôt qu'en affichant un chiffre rassurant.

Ce chiffre sous-estime toutefois le modèle, dans une proportion que nous n'avons
pas quantifiée : PlantDoc contient des étiquettes erronées. Un cas est documenté
dans [`reports/gradcam_commentaires.md`](./reports/gradcam_commentaires.md), où
une image rangée en septoriose porte une mention de la base EPPO désignant
*Xanthomonas vesicatoria*, agent de la tache bactérienne. Le diagnostic compté
comme faux était le bon.

L'entraînement repose majoritairement sur PlantVillage, photographié en studio,
feuille détachée sur fond uni. PlantWild apporte des images de terrain, mais en
bien moindre quantité. Un modèle entraîné dans ces conditions apprend en partie
la prise de vue et non la seule maladie.

Les cartes Grad-CAM se posent sur les lésions et non sur le fond, ce qui écarte
l'hypothèse d'un modèle ayant appris le décor. Cette vérification reste toutefois
faite sur les corpus disponibles. Quatre cas sont analysés dans
[`reports/gradcam_commentaires.md`](./reports/gradcam_commentaires.md), dont une
erreur affirmée à 88 % où la carte montre que le modèle visait bien les lésions.

Le jeu de test de terrain provient d'une source unique, PlantDoc. D'autres
conditions de prise de vue donneraient d'autres chiffres. La classe
« Maïs - Sain » y est absente et n'a donc pas pu être évaluée au champ. Le corpus
n'est pas homogène non plus : certaines de ses images sont photographiées sur
fond uni, feuille détachée, dans des conditions proches du studio.

Toute image n'appartenant pas aux 10 classes est rapprochée de force de l'une
d'entre elles : le modèle répartit toujours 100 % de certitude entre les classes
qu'il connaît. Une feuille de manioc ou une photo de chaussure produira donc un
diagnostic, dépourvu de sens.

Les recommandations de `src/app/recommandations.json` orientent une observation de
terrain. Elles ne remplacent pas le diagnostic d'un conseiller agricole ou d'un
service de protection des végétaux, seuls habilités à préconiser un traitement.
