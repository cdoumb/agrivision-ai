# Choix techniques

Le contrat d'interface fixe au chapitre 3 dit ce que chaque brique doit produire, sans
dire comment. Ce chapitre justifie les moyens retenus, et signale a chaque fois ce qui a
ete ecarte et pourquoi.

## Le modele : MobileNetV2 et transfert d'apprentissage

### Pourquoi ne pas entrainer un reseau de zero

Un reseau de convolution entraine depuis une initialisation aleatoire demande un corpus
de plusieurs centaines de milliers d'images pour apprendre seul les representations
visuelles elementaires que sont les contours, les textures et les motifs. Notre corpus en
compte 13 725. Entrainer de zero dans ces conditions produit un modele qui apprend par
coeur son jeu d'entrainement.

Le transfert d'apprentissage resout ce probleme en partant d'un reseau deja entraine sur
ImageNet, un corpus de plus d'un million d'images. Les couches basses de ce reseau savent
deja detecter des contours et des textures, ce qui est exactement ce dont la
reconnaissance d'une lesion foliaire a besoin. Seules les couches hautes, specialisees
dans les mille categories d'ImageNet, doivent etre reapprises.

### Pourquoi MobileNetV2

Trois architectures pre-entrainees etaient candidates : ResNet50, EfficientNetB0 et
MobileNetV2. Le choix s'est porte sur la troisieme pour des raisons de contexte
d'utilisation plutot que de performance brute.

| Critere | Ce qu'il implique ici |
|---|---|
| Taille du modele | 26 Mo une fois entraine, contre une centaine pour ResNet50 |
| Temps d'inference | Une fraction de seconde par image sur un processeur ordinaire, sans carte graphique |
| Conception d'origine | Pense pour le mobile, donc pour des ressources contraintes |
| Voie d'evolution | Convertible en TensorFlow Lite pour une execution sur telephone |

Tableau: Criteres ayant conduit au choix de MobileNetV2.

Le dernier critere merite d'etre precise, car il n'a pas ete suivi d'effet. La conversion
en TensorFlow Lite figurait parmi les options du projet, et elle a ete abandonnee faute
de temps. Le choix de MobileNetV2 garde neanmoins cette voie ouverte, ce qui n'aurait pas
ete le cas avec une architecture plus lourde. Le chapitre 10 y revient.

Le contexte vise, une exploitation agricole senegalaise avec une connexion incertaine et
un materiel modeste, rendait cette famille d'architectures plus pertinente qu'un reseau
plus precis mais plus exigeant. L'ecart de performance entre ces architectures sur une
tache a dix classes bien separees reste par ailleurs faible, et les 96,64 pour cent
obtenus au chapitre 5 le confirment.

### La tete de classification

Le corps de MobileNetV2 est conserve tel quel. Seule la tete, c'est-a-dire les dernieres
couches qui produisent la decision, a ete remplacee.

| Couche | Role |
|---|---|
| `GlobalAveragePooling2D` | Resume chaque carte de caracteristiques en un seul nombre |
| `Dropout(0.3)` | Eteint 30 pour cent des neurones au hasard, contre le surapprentissage |
| `Dense(10, softmax)` | Produit les dix scores de sortie, dont la somme vaut 1 |

Tableau: Tete de classification ajoutee au corps pre-entraine, version 1.

La sortie en `softmax` a une consequence directe sur l'usage, signalee au chapitre 9 :
les dix scores somment toujours a 1, y compris devant une image qui n'appartient a aucune
des dix classes. Le modele ne dispose d'aucun moyen de repondre qu'il ne sait pas.

### L'entrainement en deux phases

L'entrainement se deroule en deux temps, avec des taux d'apprentissage tres differents.

1. **Transfert.** Le corps du reseau est entierement gele, seule la tete apprend, avec un
   taux d'apprentissage de 1 pour 1 000 sur dix epoques au maximum. Un corps non gele
   des le depart verrait ses poids detruits par les gradients desordonnes d'une tete
   encore aleatoire.
2. **Affinage.** Les quarante dernieres couches sont degelees et reapprises avec un taux
   d'apprentissage cent fois plus faible, 1 pour 100 000, sur quinze epoques au maximum.
   L'objectif est de specialiser les representations de haut niveau sur les feuilles,
   sans effacer ce que le reseau sait deja.

Les couches de normalisation par lot restent gelees dans les deux phases, y compris parmi
les couches degelees. Elles portent des statistiques calculees sur ImageNet, sur plus
d'un million d'images ; les reestimer sur des lots de 32 images produirait des
statistiques bien plus bruitees.

Deux mecanismes automatiques encadrent l'entrainement : l'arret anticipe, qui interrompt
l'apprentissage lorsque l'exactitude de validation cesse de progresser, et la reduction
du taux d'apprentissage sur plateau. Ils evitent l'un et l'autre de choisir un nombre
d'epoques au juge.

### Le desequilibre des classes

Le corpus presente un rapport de 4,15 entre sa classe la plus fournie et la moins
fournie. Sans correction, le modele a interet a privilegier les classes nombreuses. Une
ponderation inversement proportionnelle a l'effectif de chaque classe est donc appliquee
a la fonction de perte : une erreur sur une classe rare coute plus cher qu'une erreur sur
une classe frequente.

### L'augmentation de donnees

Les images d'entrainement subissent des retournements horizontaux et verticaux, des
rotations, des zooms et des variations de luminosite et de contraste, tires au hasard a
chaque epoque. Le modele ne voit donc jamais deux fois exactement la meme image.

Cette augmentation est deliberement placee **a l'interieur du modele**, et non dans la
chaine de chargement des donnees. Elle se desactive ainsi automatiquement en inference,
sans qu'aucun code n'ait a y penser. Une augmentation restee active au moment du
diagnostic ferait varier le resultat d'un appel a l'autre sur la meme photographie.

La version 2 etend nettement ce dispositif, avec des variations de teinte et de
saturation, des occlusions et du flou. Le chapitre 7 detaille ces ajouts et ce qu'ils ont
apporte.

### Grad-CAM plutot que les alternatives

L'exigence d'interpretabilite pouvait etre satisfaite par plusieurs methodes. Grad-CAM a
ete retenue parce qu'elle ne demande aucune modification du modele, qu'elle s'execute en
une seule passe de gradients, donc assez vite pour etre calculee a chaque diagnostic, et
que son resultat, une carte de chaleur superposee a la photographie, se lit sans
formation particuliere. Les methodes a base de perturbations comme LIME auraient exige
des centaines de passes par image, ce qui aurait fait passer le temps de reponse d'une
fraction de seconde a plusieurs dizaines de secondes, pour un diagnostic cense etre
immediat.

## Le service et le deploiement

### Pourquoi FastAPI

FastAPI a ete retenu plutot que Flask ou Django pour trois raisons directement liees au
role du service dans ce projet, celui d'exposer un modele de classification derriere une
API simple.

FastAPI valide automatiquement les entrees d'une requete a partir de leur declaration de
type, et rejette une requete mal formee avant meme qu'elle n'atteigne le code de
prediction. Flask ne fait rien de tel par defaut, cette validation devrait etre ecrite a
la main. FastAPI genere aussi automatiquement une documentation interactive de l'API,
accessible sur `/docs`, qui liste les points d'acces, leurs parametres et le format
attendu des reponses ; cette documentation reste synchronisee avec le code puisqu'elle
est generee depuis lui, ce qui evite le risque, frequent avec Django ou Flask, d'une
documentation ecrite a part et qui derive au fil des modifications.

Le modele est charge une seule fois, au demarrage du service, et non a chaque appel de
`/predict`. Charger un modele de plusieurs dizaines de megaoctets a chaque requete
ajouterait plusieurs secondes a chaque diagnostic, la ou l'objectif est une reponse quasi
immediate.

### Pourquoi Streamlit pour l'application

Streamlit permet de construire une interface web fonctionnelle en quelques dizaines de
lignes de Python, sans ecrire de HTML, de CSS ou de JavaScript. Pour une application dont
le role se limite a soumettre une photographie et a afficher un diagnostic, cette
rapidite de developpement a compte davantage que la finesse de personnalisation qu'une
interface ecrite a la main aurait permise.

Ce choix a une contrepartie : l'apparence de l'application reste largement celle imposee
par Streamlit, avec des possibilites de personnalisation visuelle limitees compare a une
interface construite composant par composant en HTML et JavaScript.

Quel que soit le choix retenu pour l'interface, la separation entre l'application et le
service, decrite au chapitre 3, n'est pas negociable : l'application, quelle que soit sa
technologie, ne fait jamais que consommer l'API du service.

### La conteneurisation

L'application et le service tournent dans deux conteneurs Docker separes, plutot que
dans un seul. Cette separation n'est pas seulement une question d'organisation :
Streamlit et TensorFlow exigent chacun une version differente et incompatible de la
bibliotheque `protobuf`. Les deux ne peuvent pas cohabiter dans un meme environnement
Python. Deux conteneurs distincts resolvent ce conflit sans qu'il faille chercher un
compromis de version qui, de toute facon, n'existe pas.

Une variable d'environnement, `AGRIVISION_MODELE`, designe dans `docker-compose.yml` le
modele effectivement charge par le service, `v2` par defaut. Rejouer la comparaison
entre les deux versions du modele, presentee au chapitre 7, revient a remplacer cette
valeur par `v1` et a relancer les conteneurs, sans modifier une ligne de code.

Au premier demarrage, l'application attend automatiquement que le service ait termine de
charger le modele avant de lui adresser des requetes. Sans cette reprise de contact
automatique, un utilisateur qui lancerait l'application juste apres les conteneurs
risquerait une premiere erreur, le temps que TensorFlow finisse de s'installer et que le
modele soit charge en memoire, ce qui prend plusieurs minutes au tout premier demarrage.

### Les tests

La suite de tests compte 30 tests au total : 8 portent sur la validation des entrees du
service, comme le format ou la taille d'une image recue, et 22 portent sur le module
d'inference lui-meme.

Les tests qui necessitent le fichier du modele entraine s'ignorent automatiquement
lorsque ce fichier est absent, plutot que d'echouer. Le modele n'etant pas verse dans le
depot Git en raison de sa taille, cette regle permet a la suite de tests de rester
executable sur une machine qui n'a pas encore telecharge le modele, en particulier en
integration continue.