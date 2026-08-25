# Perspectives

## Ce qui repondrait a la limite principale

La limite centrale du chapitre 9 est la performance au champ. Les pistes qui
suivent sont classees par rapport attendu, la premiere etant de loin la plus
determinante.

Collecter des images de terrain locales est la seule piste qui s'attaque a la
cause du probleme et non a ses symptomes. Cela suppose des photographies prises
dans des exploitations senegalaises, sur les trois cultures du perimetre,
etiquetees par un conseiller agricole plutot que reprises d'un corpus public.
Nous ne disposons pas d'element permettant de justifier un volume precis a
viser ; cette piste reste donc decrite qualitativement.

Corriger les etiquettes du corpus de test est une seconde piste, plus rapide a
mettre en oeuvre. Le chapitre 8 etablit qu'au moins une etiquette de PlantDoc
est fausse. Une relecture systematique de ce corpus donnerait une mesure plus
juste de ce que vaut reellement le modele au champ, sans qu'il soit necessaire
de reentrainer quoi que ce soit.

Elargir le perimetre a d'autres cultures est une troisieme piste, a envisager
une fois les deux precedentes engagees, en commencant par les cultures qui
comptent localement et qui sont absentes des dix classes actuelles.

## Le refus de repondre

La limite d'usage la plus genante, decrite au chapitre 9, est qu'une feuille
inconnue du modele recoit tout de meme un diagnostic. Cela tient a la
conception meme de la tete de classification, decrite au chapitre 4 : la
couche de sortie en softmax repartit toujours cent pour cent de certitude
entre les dix classes connues, y compris devant une photographie de manioc ou
une image sans rapport avec une feuille.

Un mecanisme de rejet, capable de repondre qu'une image n'appartient a aucune
classe connue plutot que de forcer un choix parmi les dix, repondrait
directement a cette limite. Cela demande un travail specifique, et pas
seulement un seuil de confiance plus eleve : un modele surconfiant reste
surconfiant devant une image aberrante, un simple relevement du seuil ne
suffit pas a corriger ce comportement.

## TensorFlow Lite, option non retenue

La conversion du modele vers TensorFlow Lite figurait parmi les options du
sujet initial. Elle apporterait un diagnostic possible sans connexion reseau,
directement sur le telephone, ce qui correspond exactement au contexte d'usage
decrit au chapitre 1.

Cette conversion n'a pas ete engagee au cours des 30 jours du projet : la
priorite est allee a la mesure de la robustesse au champ et a la construction
de la version 2 du modele, qui ont revele un probleme plus fondamental qu'un
probleme de deploiement. Il s'agit d'un choix assume, pas d'un oubli.

Cette voie reste ouverte pour la suite. Le choix de MobileNetV2, justifie au
chapitre 4, a precisement ete fait en gardant cette possibilite praticable,
contrairement a ce qu'aurait donne une architecture plus lourde comme ResNet50.

## Couche meteorologique, option non retenue

Le principe consisterait a croiser le diagnostic du modele avec les conditions
locales, plusieurs des maladies du perimetre etant favorisees par l'humidite
et la chaleur.

Cette piste a ete ecartee parce qu'elle suppose un modele deja fiable au
champ. Ajouter une source de donnees supplementaire a un diagnostic qui n'est
juste qu'une fois sur deux au champ n'ameliorerait pas la decision de
l'utilisateur, elle la compliquerait sans en ameliorer la fiabilite. C'est une
piste a envisager pour une suite du projet, une fois la limite principale
traitee.

## Ce que le projet retient

L'apport principal de ce projet n'est pas le modele en lui-meme, c'est la
mesure qui en revele les limites. Une plateforme livree sur la seule foi des
96,64 pour cent obtenus en studio aurait produit des diagnostics faux avec
assurance, sans que personne ne dispose du moyen de s'en rendre compte.