# Robustesse : ce que le modèle vaut hors du studio

<!--
    Chapitre de Faustin. Premier jet. C'est le chapitre central du rapport.
    Sources : reports/robustesse_terrain_v1.json, produit par
    src/model/evaluation_terrain.py, et les figures qui l'accompagnent.
-->

Le chapitre précédent s'achève sur une question restée ouverte : un modèle qui atteint
96,64 pour cent sur des photographies de studio a-t-il appris la maladie, ou les
conditions de prise de vue ? Ce chapitre y répond par la mesure, et la réponse est
sévère.

## Le protocole : un corpus jamais vu, dans d'autres conditions

Le guide de projet prévoyait à l'origine de fabriquer un jeu de test dégradé
artificiellement, en appliquant du flou, du bruit et des changements de luminosité aux
images de PlantVillage. Cette solution a été écartée au profit d'une mesure plus
exigeante, et le choix mérite d'être assumé explicitement : une image de studio floutée
reste une image de studio. Elle ne dit rien du feuillage encombré, de la lumière
naturelle ou de la feuille encore attachée à sa tige.

L'évaluation s'appuie donc sur **PlantDoc**, un corpus public de photographies prises en
conditions réelles. Après mise en correspondance de ses catégories avec les nôtres,
942 images exploitables ont été retenues, réparties sur neuf de nos dix classes. La
classe « Maïs - Sain » est absente de PlantDoc et n'a donc pas pu être évaluée au champ.

Trois propriétés de ce protocole en font une mesure honnête.

1. **Aucune image de PlantDoc n'a servi à l'entraînement**, d'aucune version du modèle.
   Le corpus est resté strictement à part, du premier jour jusqu'à la mesure.
2. **La mesure passe par le service d'inférence lui-même**, `src/model/inference.py`,
   et non par un code d'évaluation séparé. Le chiffre obtenu est donc celui qu'obtient
   réellement un utilisateur qui envoie une photo, prétraitement compris.
3. **Le résultat de studio auquel il est comparé est lu dans la fiche du modèle
   chargé**, et non écrit en dur dans le script. Comparer par erreur le terrain d'une
   version au studio d'une autre était un piège réel, et il a été refermé
   volontairement.

Ce troisième point mérite une phrase de plus, car il a failli produire un tableau faux.
Le script d'évaluation portait initialement les chiffres de studio de la version 1 en
constantes. Le service, lui, a par la suite basculé sur la version 2 sans que le script
en soit informé. Une exécution de routine aurait alors comparé le terrain de la
version 2 au studio de la version 1, et rien dans la sortie ne l'aurait signalé. Le
script lit désormais la fiche du modèle effectivement chargé, et refuse de s'exécuter si
elle est introuvable.

## Le résultat

| Mesure | Studio (PlantVillage) | Terrain (PlantDoc) |
|---|---|---|
| Exactitude | 96,64 % | **35,67 %** |
| F1 macro, 9 classes comparables | 0,9520 | **0,2908** |
| Confiance moyenne du modèle | non mesurée | 80,9 % |
| Images évaluées | 2 056 | 942 |

Tableau: Modèle v1, studio contre terrain. Le F1 macro est calculé sur les neuf classes présentes des deux côtés.

L'exactitude passe de 96,64 à 35,67 pour cent. Le modèle qui se trompait une fois sur
trente en studio se trompe désormais deux fois sur trois.

![Comparaison du F1 par classe entre studio et terrain, modèle v1.](reports/robustesse_terrain_v1.png)

Le F1 macro chute plus durement encore, de 0,9520 à 0,2908, ce qui indique que
l'effondrement n'est pas réparti uniformément : certaines classes ne survivent pas du
tout au changement de conditions.

| Classe | F1 studio | F1 terrain | Images terrain |
|---|---|---|---|
| Tomate - Saine | 0,986 | **0,000** | 63 |
| Tomate - Mildiou tardif | 0,965 | 0,471 | 111 |
| Tomate - Tache bactérienne | 0,972 | **0,044** | 110 |
| Tomate - Septoriose | 0,957 | 0,459 | 151 |
| Maïs - Rouille commune | 0,997 | 0,321 | 116 |
| Maïs - Helminthosporiose | 0,899 | 0,436 | 191 |
| Maïs - Cercosporiose | 0,825 | 0,344 | 68 |
| Poivron - Sain | 0,989 | 0,231 | 61 |
| Poivron - Tache bactérienne | 0,980 | 0,311 | 71 |

Tableau: Effondrement du F1 classe par classe, modèle v1.

Deux lignes sont particulièrement parlantes. La tomate saine obtient un F1 de **0,000**
au champ, contre 0,986 en studio : sur les 63 photographies de feuilles de tomate saines
prises au champ, le modèle n'en a pas identifié une seule correctement. La tache
bactérienne de la tomate tombe à 0,044, ce qui revient au même constat.

Ces deux classes ont un point commun. En studio, une feuille saine est un objet très
reconnaissable : un limbe régulier, uniformément vert, détaché, sur fond gris. Au champ,
une feuille saine ressemble à du feuillage, avec des reflets, des ombres portées, de la
poussière et des morsures d'insectes qui ne sont pas des maladies. Le modèle n'a jamais
appris à quoi ressemble une plante en bonne santé dans son milieu.

Ce constat mène à une lecture plus dérangeante de l'excellent résultat du chapitre 5. Si
le modèle reconnaissait la maladie, ses performances baisseraient au champ à mesure que
la photographie devient difficile, mais elles baisseraient à peu près uniformément. Or
l'effondrement est très inégal : certaines classes conservent près de la moitié de leur
F1 quand d'autres tombent à zéro. Cette inégalité indique que le modèle ne s'appuyait
pas sur les mêmes indices selon les classes. Pour les maladies produisant des lésions
franches et contrastées, il avait bien appris quelque chose de la lésion, et il en
retrouve une partie au champ. Pour les feuilles saines, il n'avait appris qu'un décor,
et le décor a disparu.

Autrement dit, les 96,64 pour cent du chapitre 5 ne mesuraient pas une seule chose. Ils
agrégeaient des classes réellement apprises et des classes reconnues par leur contexte
de prise de vue, sans qu'aucun chiffre de ce chapitre ne permette de séparer les deux.
C'est le corpus de terrain qui rend cette séparation visible, et c'est la raison pour
laquelle il ne pouvait pas être remplacé par des images de studio dégradées
artificiellement : une image de studio floutée conserve son fond uni, donc conserve
exactement l'indice que le modèle avait appris à tort.

## Le point le plus grave : la confiance

L'effondrement de l'exactitude n'est pas, en soi, le résultat le plus préoccupant. Un
outil qui se trompe souvent mais qui le signale reste utilisable. Le problème est
ailleurs.

> ATTENTION: Sur les images de terrain, la confiance moyenne du modèle v1 reste de 80,9 pour cent, alors que son exactitude est de 35,67 pour cent. Le modèle se trompe deux fois sur trois, et l'annonce avec le même aplomb que lorsqu'il a raison.

C'est un défaut plus dangereux que l'erreur elle-même. Un agriculteur qui reçoit un
diagnostic affiché à 80 pour cent de certitude n'a aucune raison de le mettre en doute.
La mesure détaillée au chapitre 7 chiffre exactement le nombre de diagnostics faux
annoncés sans le moindre avertissement : ils sont 403 sur 942.

Cette surconfiance a une explication technique. Un réseau entraîné par entropie croisée
sur des étiquettes franches est poussé à produire des probabilités proches de 1 pour la
classe retenue. Rien dans cet entraînement ne lui apprend à réserver son jugement devant
une image qui ne ressemble à rien de ce qu'il connaît. La version 2 corrige précisément
ce point, et c'est l'objet du chapitre suivant.

![Matrice de confusion du modèle v1 sur les 942 images de terrain.|14.5](reports/robustesse_confusion_v1.png)

## Une précision sur les chiffres, et pourquoi elle compte

Le notebook d'entraînement annonce 36,27 pour cent d'exactitude au champ pour cette même
version, là où le service en mesure 35,67. L'écart de six dixièmes de point n'est pas une
erreur de l'un ou de l'autre : les deux chaînes ne redimensionnent pas les images de la
même façon. Le notebook utilise la fonction de redimensionnement de TensorFlow, le
service utilise la bibliothèque Pillow, et les deux méthodes ne produisent pas
exactement la même image de 224 pixels de côté.

L'écart moyen entre les deux versions d'une même image atteint 3,65 niveaux sur 255 pour
les images de terrain, contre 1,61 niveau seulement pour les images de studio. Cela
suffit à faire basculer la décision sur cinq ou six photographies de terrain sur 942, et
explique aussi pourquoi les chiffres de studio, eux, concordent au centième près entre
les deux chaînes.

La règle retenue pour tout le rapport découle de cette observation. Les chiffres du
service sont ceux qui décrivent l'expérience réelle d'un utilisateur, et ce sont eux qui
sont cités dès qu'il s'agit de dire ce que vaut la plateforme. Les chiffres du notebook
restent la référence pour comparer les deux versions entre elles, puisqu'elles y passent
toutes deux par la chaîne de mesure identique.

## Ce que ce chapitre établit

> RETENIR: Un modèle entraîné sur un corpus de laboratoire apprend une part des conditions de prise de vue en même temps que la maladie. Mesurer sa performance sur le jeu de test issu du même corpus ne détecte pas ce défaut, puisque ce jeu partage les mêmes conditions. Seule une source de données indépendante le révèle.

Ce constat n'est pas un échec du projet, c'est son principal apport. Une plateforme
livrée sur la foi des 96,64 pour cent de studio aurait produit des diagnostics faux avec
assurance, en situation réelle, sans que personne ne dispose du moyen de s'en rendre
compte. La chute est désagréable à lire dans un rapport, mais elle est mesurée, et une
faiblesse mesurée peut être corrigée, ou à défaut signalée à l'utilisateur.

Les deux chapitres suivants font l'un et l'autre : le chapitre 7 corrige ce qui peut
l'être, le chapitre 8 vérifie sur quels indices le modèle s'appuie réellement.
