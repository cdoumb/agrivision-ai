# Le corpus : constitution, nettoyage et découpage

## PlantVillage : origine et nature

Le corpus s'appuie sur PlantVillage, un corpus de référence de photographies de
feuilles, largement utilisé dans les travaux de classification de maladies des
plantes. Les images y sont produites en conditions de studio : une feuille
détachée, photographiée seule sur un fond uni.

Ce caractère de laboratoire n'est pas idéal, mais PlantVillage reste le corpus
retenu parce qu'il est le seul disponible en quantité suffisante et
correctement étiqueté pour les dix classes visées par le projet. Il faut le
dire dès ce chapitre : cette nature de studio est directement la cause de ce
que mesure le chapitre 6, qui compare les performances du modèle en studio et
sur des photographies de terrain. Le lecteur doit garder ce point en tête avant
de lire les 96,64 pour cent obtenus en studio au chapitre 5 : ce chiffre mesure
une performance sur des images qui ressemblent toutes à celles d'entraînement,
pas une performance au champ.

## Les dix classes retenues

| Culture | États reconnus |
|---|---|
| Tomate | Saine, Mildiou tardif, Tache bactérienne, Septoriose |
| Maïs | Sain, Rouille commune, Helminthosporiose, Cercosporiose |
| Poivron | Sain, Tache bactérienne |

Tableau: Les dix classes du contrat d'interface, gelées au 14 août 2026.

Ces dix classes ont été choisies parmi les 38 que compte PlantVillage, sur le
critère d'un périmètre maîtrisable pour un projet de 30 jours : trois cultures
courantes, et pour chacune un état sain plus les maladies les plus
représentées. Le fichier `classes.json` est la source unique de vérité pour
l'ordre de ces classes. Un ordre stable entre l'entraînement et le service
n'est pas un détail : c'est cet ordre qui permet au service de traduire
correctement l'indice renvoyé par le modèle en un libellé de maladie, et le
chapitre 3 revient sur les conséquences d'un décalage à ce niveau.

## Répartition et déséquilibre

| Classe | Images |
|---|---|
| Tomate - Tache bactérienne | 2 127 |
| Tomate - Mildiou tardif | 1 909 |
| Tomate - Septoriose | 1 771 |
| Tomate - Saine | 1 591 |
| Poivron - Sain | 1 478 |
| Maïs - Rouille commune | 1 192 |
| Maïs - Sain | 1 162 |
| Poivron - Tache bactérienne | 997 |
| Maïs - Helminthosporiose | 985 |
| Maïs - Cercosporiose | 513 |

Tableau: Effectif par classe, 13 725 images au total. Source : reports/corpus_stats.md.

Le rapport de déséquilibre atteint 4,15 entre la classe la plus fournie, la
tache bactérienne de la tomate, et la moins fournie, la cercosporiose du maïs.
Laissé tel quel, ce déséquilibre pousserait le modèle à privilégier les classes
nombreuses au détriment des classes rares : une erreur sur une classe peu
représentée compte moins dans la fonction de perte globale, donc le modèle n'a
pas de raison forte de l'éviter. Le chapitre 4 décrit la pondération appliquée
à la fonction de perte pour corriger ce biais. Le lien avec le chapitre 5 est
direct : la cercosporiose, classe la moins fournie, y obtient aussi le plus
faible F1.

## Le contrôle d'intégrité

Toutes les images du corpus font 256 pixels de côté, et aucun fichier corrompu
n'a été détecté sur les 13 725. Ce contrôle vérifie systématiquement la
lisibilité et les dimensions de chaque fichier avant toute autre étape : une
image corrompue ou mal dimensionnée qui passerait ce contrôle romprait
silencieusement le prétraitement en aval, potentiellement bien plus tard dans
la chaîne, à un endroit où l'erreur serait plus difficile à rattacher à sa
cause.

## La déduplication, et le piège qu'elle referme

Deux types de doublons ont été recherchés dans le corpus.

Les doublons exacts sont détectés par empreinte MD5 : deux fichiers produisent
la même empreinte s'ils sont, au bit près, identiques. Quatorze groupes de ce
type ont été trouvés, dont huit sur le mildiou tardif de la tomate et six sur
la tomate saine. Ils ont été retirés du corpus.

Les quasi-doublons sont plus difficiles à détecter, et plus gênants s'ils
passent inaperçus. Ce sont des images visuellement presque identiques mais dont
les fichiers diffèrent, par exemple la même feuille photographiée deux fois de
suite avec un léger changement de cadrage ou de luminosité. Ils sont repérés
par hash perceptif : contrairement au hash exact, ce hash produit des valeurs
proches pour des images qui se ressemblent visuellement, même si leurs octets
diffèrent.

| Classe | Doublons exacts | Groupes de quasi-doublons |
|---|---|---|
| Tomate - Saine | 6 | 20 |
| Tomate - Mildiou tardif | 8 | 11 |
| Tomate - Tache bactérienne | 0 | 13 |
| Poivron - Sain | 0 | 4 |
| Maïs - Sain | 0 | 1 |
| Les cinq autres classes | 0 | 0 |

Tableau: Doublons détectés, en nombre de groupes. Source : reports/corpus_stats.md.

La règle appliquée est la suivante : toutes les images d'un même groupe de
quasi-doublons sont placées dans la même partie du découpage, entraînement,
validation ou test, jamais réparties entre plusieurs. Cette précaution décide
de la validité de tous les chiffres du rapport. Sans elle, une image du jeu de
test pourrait avoir sa quasi-jumelle dans le jeu d'entraînement : le modèle
serait alors en partie noté sur des images qu'il a déjà vues sous une forme
très proche, et le chiffre d'exactitude obtenu serait à la fois plus flatteur
et faux. Cette précaution ne figurait pas dans le sujet du projet ; elle a été
ajoutée parce que la fuite de données est l'un des pièges les plus courants et
les plus discrets d'un projet de classification d'images.

## Le découpage

| Partie | Images | Proportion |
|---|---|---|
| Entraînement | 9 597 | 70 % |
| Validation | 2 058 | 15 % |
| Test | 2 056 | 15 % |

Tableau: Découpage du corpus. Graine aléatoire fixée à 42. Source : reports/split_report.md.

Le découpage est stratifié : chaque classe conserve, dans chacune des trois
parties, une proportion proche de celle qu'elle occupe dans le corpus entier.
Il est consigné image par image dans `reports/split_manifest.csv`, versé dans
le dépôt. Ce manifeste est relu par les notebooks d'entraînement plutôt que
recalculé à chaque fois, pour une raison précise : tout nouveau modèle entraîné
plus tard reste ainsi comparé sur exactement le même jeu de test que les
précédents. Sans ce manifeste fixe, la comparaison entre les versions 1 et 2 du
modèle, faite au chapitre 7, n'aurait aucune valeur : un écart de performance
pourrait alors venir d'un découpage différent plutôt que d'une amélioration
réelle du modèle.

## PlantWild, ajouté pour la version 2

PlantWild est un corpus d'images de terrain, ajouté lors de la construction de
la version 2 du modèle, pour un volume de 1 765 images. Ce que cet ajout
apporte concrètement est mesuré au chapitre 7.

PlantWild est distribué sous licence CC BY-NC-ND 4.0 : usage non commercial,
sans œuvre dérivée, attribution obligatoire. Le projet, un travail académique
sans exploitation commerciale, respecte la première condition. La question de
savoir si un modèle entraîné à partir de ces images constitue une œuvre
dérivée au sens de la clause ND n'est pas tranchée ; le chapitre 9 développe
cette réserve.

## PlantDoc, réservé à l'évaluation

PlantDoc apporte 942 images exploitables, après mise en correspondance de ses
catégories avec les dix classes du projet. Ce corpus n'a jamais servi à
l'entraînement d'aucune version du modèle, ni la v1 ni la v2. C'est précisément
ce qui donne leur valeur aux mesures du chapitre 6 : PlantDoc est le seul jeu
sur lequel le modèle est évalué sans jamais l'avoir vu, même indirectement.

La classe Maïs - Sain est absente de PlantDoc, elle n'a donc pas pu être
évaluée. Le corpus n'est pas non plus parfaitement homogène : certaines
de ses images sont prises sur fond uni, feuille détachée, dans des conditions
proches de celles du studio ; le chapitre 8 en donne un exemple concret.
