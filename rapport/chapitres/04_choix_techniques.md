# Choix techniques

Le contrat d'interface fixé au chapitre 3 dit ce que chaque brique doit produire, sans
dire comment. Ce chapitre justifie les moyens retenus, et signale à chaque fois ce qui a
été écarté et pourquoi.

## Le modèle : MobileNetV2 et transfert d'apprentissage

### Pourquoi ne pas entraîner un réseau de zéro

Un réseau de convolution entraîné depuis une initialisation aléatoire demande un corpus
de plusieurs centaines de milliers d'images pour apprendre seul les représentations
visuelles élémentaires que sont les contours, les textures et les motifs. Notre corpus en
compte 13 725. Entraîner de zéro dans ces conditions produit un modèle qui apprend par
cœur son jeu d'entraînement.

Le transfert d'apprentissage résout ce problème en partant d'un réseau déjà entraîné sur
ImageNet, un corpus de plus d'un million d'images. Les couches basses de ce réseau savent
déjà détecter des contours et des textures, ce qui est exactement ce dont la
reconnaissance d'une lésion foliaire a besoin. Seules les couches hautes, spécialisées
dans les mille catégories d'ImageNet, doivent être réapprises.

### Pourquoi MobileNetV2

Trois architectures pré-entraînées étaient candidates : ResNet50, EfficientNetB0 et
MobileNetV2. Le choix s'est porté sur la troisième pour des raisons de contexte
d'utilisation plutôt que de performance brute.

| Critère | Ce qu'il implique ici |
|---|---|
| Taille du modèle | 26 Mo une fois entraîné, contre une centaine pour ResNet50 |
| Temps d'inférence | Une fraction de seconde par image sur un processeur ordinaire, sans carte graphique |
| Conception d'origine | Pensé pour le mobile, donc pour des ressources contraintes |
| Voie d'évolution | Convertible en TensorFlow Lite pour une exécution sur téléphone |

Tableau: Critères ayant conduit au choix de MobileNetV2.

Le dernier critère mérite d'être précisé, car il n'a pas été suivi d'effet. La conversion
en TensorFlow Lite figurait parmi les options du projet, et elle a été abandonnée faute
de temps. Le choix de MobileNetV2 garde néanmoins cette voie ouverte, ce qui n'aurait pas
été le cas avec une architecture plus lourde. Le chapitre 10 y revient.

Le contexte visé, une exploitation agricole sénégalaise avec une connexion incertaine et
un matériel modeste, rendait cette famille d'architectures plus pertinente qu'un réseau
plus précis mais plus exigeant. L'écart de performance entre ces architectures sur une
tâche à dix classes bien séparées reste par ailleurs faible, et les 96,64 pour cent
obtenus au chapitre 5 le confirment.

Il faut ajouter que ce raisonnement, tel qu'il a été tenu au moment du choix, portait
sur le mauvais problème. Il compare des architectures sur le critère de leur exactitude
en studio, alors que le chapitre 6 établit que le facteur limitant n'est pas
l'architecture mais la nature du corpus d'entraînement. Un ResNet50 entraîné sur les
mêmes images de studio se serait effondré au champ de la même manière, et probablement
dans les mêmes proportions. Le choix de MobileNetV2 reste justifié par le contexte de
déploiement, qui est un argument solide ; il ne l'est pas par un gain de performance,
qui n'existe pas ici. La distinction compte, parce qu'elle indique où il aurait fallu
investir l'effort : dans les données plutôt que dans le modèle.

### La tête de classification

Le corps de MobileNetV2 est conservé tel quel. Seule la tête, c'est-à-dire les dernières
couches qui produisent la décision, a été remplacée.

| Couche | Rôle |
|---|---|
| `GlobalAveragePooling2D` | Résume chaque carte de caractéristiques en un seul nombre |
| `Dropout(0.3)` | Éteint 30 pour cent des neurones au hasard, contre le surapprentissage |
| `Dense(10, softmax)` | Produit les dix scores de sortie, dont la somme vaut 1 |

Tableau: Tête de classification ajoutée au corps pré-entraîné, version 1.

La sortie en `softmax` a une conséquence directe sur l'usage, signalée au chapitre 9 :
les dix scores somment toujours à 1, y compris devant une image qui n'appartient à aucune
des dix classes. Le modèle ne dispose d'aucun moyen de répondre qu'il ne sait pas.

### L'entraînement en deux phases

L'entraînement se déroule en deux temps, avec des taux d'apprentissage très différents.

1. **Transfert.** Le corps du réseau est entièrement gelé, seule la tête apprend, avec un
   taux d'apprentissage de 1 pour 1 000 sur dix époques au maximum. Un corps non gelé
   dès le départ verrait ses poids détruits par les gradients désordonnés d'une tête
   encore aléatoire.
2. **Affinage.** Les quarante dernières couches sont dégelées et réapprises avec un taux
   d'apprentissage cent fois plus faible, 1 pour 100 000, sur quinze époques au maximum.
   L'objectif est de spécialiser les représentations de haut niveau sur les feuilles,
   sans effacer ce que le réseau sait déjà.

Les couches de normalisation par lot restent gelées dans les deux phases, y compris parmi
les couches dégelées. Elles portent des statistiques calculées sur ImageNet, sur plus
d'un million d'images ; les réestimer sur des lots de 32 images produirait des
statistiques bien plus bruitées.

Deux mécanismes automatiques encadrent l'entraînement : l'arrêt anticipé, qui interrompt
l'apprentissage lorsque l'exactitude de validation cesse de progresser, et la réduction
du taux d'apprentissage sur plateau. Ils évitent l'un et l'autre de choisir un nombre
d'époques au jugé.

L'écart de facteur cent entre les deux taux d'apprentissage n'est pas un réglage
arbitraire, et c'est le point le moins intuitif de ce dispositif. Pendant la première
phase, la tête part de poids aléatoires : ses gradients sont grands et mal orientés, et
il faut qu'elle apprenne vite. Pendant la seconde, les couches dégelées portent des
représentations déjà correctes, acquises sur plus d'un million d'images ; le but n'est
plus de les apprendre mais de les déplacer légèrement vers le domaine des feuilles. Un
taux resté au niveau de la première phase effacerait en quelques lots ce qu'ImageNet a
mis des semaines à construire. C'est la raison pour laquelle l'ordre des deux phases
n'est pas interchangeable, et pourquoi dégeler le corps dès le départ, ce qui paraît
plus direct, produit en pratique un modèle nettement moins bon.

### Le déséquilibre des classes

Le corpus présente un rapport de 4,15 entre sa classe la plus fournie et la moins
fournie. Sans correction, le modèle a intérêt à privilégier les classes nombreuses. Une
pondération inversement proportionnelle à l'effectif de chaque classe est donc appliquée
à la fonction de perte : une erreur sur une classe rare coûte plus cher qu'une erreur sur
une classe fréquente.

### L'augmentation de données

Les images d'entraînement subissent des retournements horizontaux et verticaux, des
rotations, des zooms et des variations de luminosité et de contraste, tirés au hasard à
chaque époque. Le modèle ne voit donc jamais deux fois exactement la même image.

Cette augmentation est délibérément placée **à l'intérieur du modèle**, et non dans la
chaîne de chargement des données. Elle se désactive ainsi automatiquement en inférence,
sans qu'aucun code n'ait à y penser. Une augmentation restée active au moment du
diagnostic ferait varier le résultat d'un appel à l'autre sur la même photographie.

La version 2 étend nettement ce dispositif, avec des variations de teinte et de
saturation, des occlusions et du flou. Le chapitre 7 détaille ces ajouts et ce qu'ils ont
apporté.

### Grad-CAM plutôt que les alternatives

L'exigence d'interprétabilité pouvait être satisfaite par plusieurs méthodes. Grad-CAM a
été retenue parce qu'elle ne demande aucune modification du modèle, qu'elle s'exécute en
une seule passe de gradients, donc assez vite pour être calculée à chaque diagnostic, et
que son résultat, une carte de chaleur superposée à la photographie, se lit sans
formation particulière. Les méthodes à base de perturbations comme LIME auraient exigé
des centaines de passes par image, ce qui aurait fait passer le temps de réponse d'une
fraction de seconde à plusieurs dizaines de secondes, pour un diagnostic censé être
immédiat.

## Le service et le déploiement

### Pourquoi FastAPI

FastAPI a été retenu plutôt que Flask ou Django pour trois raisons directement liées au
rôle du service dans ce projet, celui d'exposer un modèle de classification derrière une
API simple.

FastAPI valide automatiquement les entrées d'une requête à partir de leur déclaration de
type, et rejette une requête mal formée avant même qu'elle n'atteigne le code de
prédiction. Flask ne fait rien de tel par défaut, cette validation devrait être écrite à
la main. FastAPI génère aussi automatiquement une documentation interactive de l'API,
accessible sur `/docs`, qui liste les points d'accès, leurs paramètres et le format
attendu des réponses ; cette documentation reste synchronisée avec le code puisqu'elle
est générée depuis lui, ce qui évite le risque, fréquent avec Django ou Flask, d'une
documentation écrite à part et qui dérive au fil des modifications.

Le modèle est chargé une seule fois, au démarrage du service, et non à chaque appel de
`/predict`. Charger un modèle de plusieurs dizaines de mégaoctets à chaque requête
ajouterait plusieurs secondes à chaque diagnostic, là où l'objectif est une réponse quasi
immédiate.

### Pourquoi Streamlit pour l'application

Streamlit permet de construire une interface web fonctionnelle en quelques dizaines de
lignes de Python, sans écrire de HTML, de CSS ou de JavaScript. Pour une application dont
le rôle se limite à soumettre une photographie et à afficher un diagnostic, cette
rapidité de développement a compté davantage que la finesse de personnalisation qu'une
interface écrite à la main aurait permise.

Ce choix a une contrepartie : l'apparence de l'application reste largement celle imposée
par Streamlit, avec des possibilités de personnalisation visuelle limitées comparé à une
interface construite composant par composant en HTML et JavaScript.

Quel que soit le choix retenu pour l'interface, la séparation entre l'application et le
service, décrite au chapitre 3, n'est pas négociable : l'application, quelle que soit sa
technologie, ne fait jamais que consommer l'API du service.

### La conteneurisation

L'application et le service tournent dans deux conteneurs Docker séparés, plutôt que
dans un seul. Cette séparation n'est pas seulement une question d'organisation :
Streamlit et TensorFlow exigent chacun une version différente et incompatible de la
bibliothèque `protobuf`. Les deux ne peuvent pas cohabiter dans un même environnement
Python. Deux conteneurs distincts résolvent ce conflit sans qu'il faille chercher un
compromis de version qui, de toute façon, n'existe pas.

Une variable d'environnement, `AGRIVISION_MODELE`, désigne dans `docker-compose.yml` le
modèle effectivement chargé par le service, `v2` par défaut. Rejouer la comparaison
entre les deux versions du modèle, présentée au chapitre 7, revient à remplacer cette
valeur par `v1` et à relancer les conteneurs, sans modifier une ligne de code.

Au premier démarrage, l'application attend automatiquement que le service ait terminé de
charger le modèle avant de lui adresser des requêtes. Sans cette reprise de contact
automatique, un utilisateur qui lancerait l'application juste après les conteneurs
risquerait une première erreur, le temps que TensorFlow finisse de s'installer et que le
modèle soit chargé en mémoire, ce qui prend plusieurs minutes au tout premier démarrage.

### Les tests

La suite de tests compte 30 tests au total : 8 portent sur la validation des entrées du
service, comme le format ou la taille d'une image reçue, et 22 portent sur le module
d'inférence lui-même.

Les tests qui nécessitent le fichier du modèle entraîné s'ignorent automatiquement
lorsque ce fichier est absent, plutôt que d'échouer. Le modèle n'étant pas versé dans le
dépôt Git en raison de sa taille, cette règle permet à la suite de tests de rester
exécutable sur une machine qui n'a pas encore téléchargé le modèle, en particulier en
intégration continue.
