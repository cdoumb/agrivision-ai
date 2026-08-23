# Choix techniques

<!--
    CHAPITRE PARTAGÉ.
    4.1 : Faustin, rédigé.
    4.2 : Cheick, squelette à remplir.
    Merci de ne pas toucher à la partie de l'autre, pour que Git montre
    clairement qui a écrit quoi.
-->

Le contrat d'interface fixé au chapitre 3 dit ce que chaque brique doit produire, sans
dire comment. Ce chapitre justifie les moyens retenus, et signale à chaque fois ce qui a
été écarté et pourquoi.

## Le modèle : MobileNetV2 et transfert d'apprentissage

### Pourquoi ne pas entraîner un réseau de zéro

Un réseau de convolution entraîné depuis une initialisation aléatoire demande un corpus
de plusieurs centaines de milliers d'images pour apprendre seul les représentations
visuelles élémentaires que sont les contours, les textures et les motifs. Notre corpus en
compte 13 725. Entraîner de zéro dans ces conditions produit un modèle qui apprend par
coeur son jeu d'entraînement.

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

<!--
    CHEICK : cette section est à toi. Environ 1,5 page.
    Suggestion de découpage ci-dessous, à modifier librement.
    Pense à justifier les choix ÉCARTÉS autant que ceux retenus : c'est ce qui
    distingue un chapitre de choix techniques d'une simple description.
-->

> A REDIGER: Section 4.2, à rédiger par Cheick. Les points à couvrir sont listés ci-dessous.

### Pourquoi FastAPI

- Ce qui a été comparé, et pourquoi FastAPI plutôt que Flask ou Django
- La validation des entrées et la documentation automatique de l'interface
- Le chargement du modèle une seule fois au démarrage plutôt qu'à chaque appel

### Pourquoi Streamlit pour l'application

- Ce que Streamlit apporte face à une interface écrite en HTML et JavaScript
- Ce que ce choix coûte en contrepartie
- La séparation entre l'application et le service, et pourquoi elle n'est pas négociable

### La conteneurisation

- Pourquoi deux conteneurs séparés plutôt qu'un seul
- Le conflit de versions entre Streamlit et TensorFlow sur la bibliothèque `protobuf`,
  qui rend cette séparation nécessaire et non seulement élégante
- Le rôle de la variable d'environnement qui désigne le modèle servi
- Ce que la reprise de contact automatique entre l'application et le service apporte au
  premier démarrage

### Les tests

- Ce que couvrent les 30 tests, et ce qu'ils ne couvrent pas
- Pourquoi les tests dépendant du fichier du modèle s'ignorent au lieu d'échouer
