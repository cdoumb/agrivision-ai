# Le corpus : constitution, nettoyage et decoupage

## PlantVillage : origine et nature

Le corpus s'appuie sur PlantVillage, un corpus de reference de photographies de
feuilles, largement utilise dans les travaux de classification de maladies des
plantes. Les images y sont produites en conditions de studio : une feuille
detachee, photographiee seule sur un fond uni.

Ce caractere de laboratoire n'est pas ideal, mais PlantVillage reste le corpus
retenu parce qu'il est le seul disponible en quantite suffisante et
correctement etiquete pour les dix classes visees par le projet. Il faut le
dire des ce chapitre : cette nature de studio est directement la cause de ce
que mesure le chapitre 6, qui compare les performances du modele en studio et
sur des photographies de terrain. Le lecteur doit garder ce point en tete avant
de lire les 96,64 pour cent obtenus en studio au chapitre 5 : ce chiffre mesure
une performance sur des images qui ressemblent toutes a celles d'entrainement,
pas une performance au champ.

## Les dix classes retenues

| Culture | Etats reconnus |
|---|---|
| Tomate | Saine, Mildiou tardif, Tache bacterienne, Septoriose |
| Mais | Sain, Rouille commune, Helminthosporiose, Cercosporiose |
| Poivron | Sain, Tache bacterienne |

Tableau: Les dix classes du contrat d'interface, gelees au 14 aout 2026.

Ces dix classes ont ete choisies parmi les 38 que compte PlantVillage, sur le
critere d'un perimetre maitrisable pour un projet de 30 jours : trois cultures
courantes, et pour chacune un etat sain plus les maladies les plus
representees. Le fichier `classes.json` est la source unique de verite pour
l'ordre de ces classes. Un ordre stable entre l'entrainement et le service
n'est pas un detail : c'est cet ordre qui permet au service de traduire
correctement l'indice renvoye par le modele en un libelle de maladie, et le
chapitre 3 revient sur les consequences d'un decalage a ce niveau.

## Repartition et desequilibre

| Classe | Images |
|---|---|
| Tomate - Tache bacterienne | 2 127 |
| Tomate - Mildiou tardif | 1 909 |
| Tomate - Septoriose | 1 771 |
| Tomate - Saine | 1 591 |
| Poivron - Sain | 1 478 |
| Mais - Rouille commune | 1 192 |
| Mais - Sain | 1 162 |
| Poivron - Tache bacterienne | 997 |
| Mais - Helminthosporiose | 985 |
| Mais - Cercosporiose | 513 |

Tableau: Effectif par classe, 13 725 images au total. Source : reports/corpus_stats.md.

Le rapport de desequilibre atteint 4,15 entre la classe la plus fournie, la
tache bacterienne de la tomate, et la moins fournie, la cercosporiose du mais.
Laisse tel quel, ce desequilibre pousserait le modele a privilegier les classes
nombreuses au detriment des classes rares : une erreur sur une classe peu
representee compte moins dans la fonction de perte globale, donc le modele n'a
pas de raison forte de l'eviter. Le chapitre 4 decrit la ponderation appliquee
a la fonction de perte pour corriger ce biais. Le lien avec le chapitre 5 est
direct : la cercosporiose, classe la moins fournie, y obtient aussi le plus
faible F1.

## Le controle d'integrite

Toutes les images du corpus font 256 pixels de cote, et aucun fichier corrompu
n'a ete detecte sur les 13 725. Ce controle verifie systematiquement la
lisibilite et les dimensions de chaque fichier avant toute autre etape : une
image corrompue ou mal dimensionnee qui passerait ce controle romprait
silencieusement le pretraitement en aval, potentiellement bien plus tard dans
la chaine, a un endroit ou l'erreur serait plus difficile a rattacher a sa
cause.

## La deduplication, et le piege qu'elle referme

Deux types de doublons ont ete recherches dans le corpus.

Les doublons exacts sont detectes par empreinte MD5 : deux fichiers produisent
la meme empreinte s'ils sont, au bit pres, identiques. Quatorze groupes de ce
type ont ete trouves, dont huit sur le mildiou tardif de la tomate et six sur
la tomate saine. Ils ont ete retires du corpus.

Les quasi-doublons sont plus difficiles a detecter, et plus genants s'ils
passent inapercus. Ce sont des images visuellement presque identiques mais dont
les fichiers different, par exemple la meme feuille photographiee deux fois de
suite avec un leger changement de cadrage ou de luminosite. Ils sont reperes
par hash perceptif : contrairement au hash exact, ce hash produit des valeurs
proches pour des images qui se ressemblent visuellement, meme si leurs octets
different.

| Classe | Doublons exacts | Groupes de quasi-doublons |
|---|---|---|
| Tomate - Saine | 6 | 20 |
| Tomate - Mildiou tardif | 8 | 11 |
| Tomate - Tache bacterienne | 0 | 13 |
| Poivron - Sain | 0 | 4 |
| Mais - Sain | 0 | 1 |
| Les cinq autres classes | 0 | 0 |

Tableau: Doublons detectes, en nombre de groupes. Source : reports/corpus_stats.md.

La regle appliquee est la suivante : toutes les images d'un meme groupe de
quasi-doublons sont placees dans la meme partie du decoupage, entrainement,
validation ou test, jamais reparties entre plusieurs. Cette precaution decide
de la validite de tous les chiffres du rapport. Sans elle, une image du jeu de
test pourrait avoir sa quasi-jumelle dans le jeu d'entrainement : le modele
serait alors en partie note sur des images qu'il a deja vues sous une forme
tres proche, et le chiffre d'exactitude obtenu serait a la fois plus flatteur
et faux. Cette precaution ne figurait pas dans le sujet du projet ; elle a ete
ajoutee parce que la fuite de donnees est l'un des pieges les plus courants et
les plus discrets d'un projet de classification d'images.

## Le decoupage

| Partie | Images | Proportion |
|---|---|---|
| Entrainement | 9 597 | 70 % |
| Validation | 2 058 | 15 % |
| Test | 2 056 | 15 % |

Tableau: Decoupage du corpus. Graine aleatoire fixee a 42. Source : reports/split_report.md.

Le decoupage est stratifie : chaque classe conserve, dans chacune des trois
parties, une proportion proche de celle qu'elle occupe dans le corpus entier.
Il est consigne image par image dans `reports/split_manifest.csv`, verse dans
le depot. Ce manifeste est relu par les notebooks d'entrainement plutot que
recalcule a chaque fois, pour une raison precise : tout nouveau modele entraine
plus tard reste ainsi compare sur exactement le meme jeu de test que les
precedents. Sans ce manifeste fixe, la comparaison entre les versions 1 et 2 du
modele, faite au chapitre 7, n'aurait aucune valeur : un ecart de performance
pourrait alors venir d'un decoupage different plutot que d'une amelioration
reelle du modele.

## PlantWild, ajoute pour la version 2

PlantWild est un corpus d'images de terrain, ajoute lors de la construction de
la version 2 du modele, pour un volume de 1 765 images. Ce que cet ajout
apporte concretement est mesure au chapitre 7.

PlantWild est distribue sous licence CC BY-NC-ND 4.0 : usage non commercial,
sans oeuvre derivee, attribution obligatoire. Le projet, un travail academique
sans exploitation commerciale, respecte la premiere condition. La question de
savoir si un modele entraine a partir de ces images constitue une oeuvre
derivee au sens de la clause ND n'est pas tranchee ; le chapitre 9 developpe
cette reserve.

## PlantDoc, reserve a l'evaluation

PlantDoc apporte 942 images exploitables, apres mise en correspondance de ses
categories avec les dix classes du projet. Ce corpus n'a jamais servi a
l'entrainement d'aucune version du modele, ni la v1 ni la v2. C'est precisement
ce qui donne leur valeur aux mesures du chapitre 6 : PlantDoc est le seul jeu
sur lequel le modele est evalue sans jamais l'avoir vu, meme indirectement.

La classe Mais - Sain est absente de PlantDoc, qui n'a donc pas pu etre evaluee
sur cette classe. Le corpus n'est pas non plus parfaitement homogene : certaines
de ses images sont prises sur fond uni, feuille detachee, dans des conditions
proches de celles du studio ; le chapitre 8 en donne un exemple concret.