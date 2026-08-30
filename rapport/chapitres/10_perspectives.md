# Perspectives

## Ce qui répondrait à la limite principale

La limite centrale du chapitre 9 est la performance au champ. Les pistes qui
suivent sont classées par rapport attendu, la première étant de loin la plus
déterminante.

Collecter des images de terrain locales est la seule piste qui s'attaque à la
cause du problème et non à ses symptômes. Cela suppose des photographies prises
dans des exploitations sénégalaises, sur les trois cultures du périmètre,
étiquetées par un conseiller agricole plutôt que reprises d'un corpus public.
Nous ne disposons pas d'élément permettant de justifier un volume précis à
viser ; cette piste reste donc décrite qualitativement.

Corriger les étiquettes du corpus de test est une seconde piste, plus rapide à
mettre en œuvre. Le chapitre 8 établit qu'au moins une étiquette de PlantDoc
est fausse. Une relecture systématique de ce corpus donnerait une mesure plus
juste de ce que vaut réellement le modèle au champ, sans qu'il soit nécessaire
de réentraîner quoi que ce soit.

Élargir le périmètre à d'autres cultures est une troisième piste, à envisager
une fois les deux précédentes engagées, en commençant par les cultures qui
comptent localement et qui sont absentes des dix classes actuelles.

## Le refus de répondre

La limite d'usage la plus gênante, décrite au chapitre 9, est qu'une feuille
inconnue du modèle reçoit tout de même un diagnostic. Cela tient à la
conception même de la tête de classification, décrite au chapitre 4 : la
couche de sortie en softmax répartit toujours cent pour cent de certitude
entre les dix classes connues, y compris devant une photographie de manioc ou
une image sans rapport avec une feuille.

Un mécanisme de rejet, capable de répondre qu'une image n'appartient à aucune
classe connue plutôt que de forcer un choix parmi les dix, répondrait
directement à cette limite. Cela demande un travail spécifique, et pas
seulement un seuil de confiance plus élevé : un modèle surconfiant reste
surconfiant devant une image aberrante, un simple relèvement du seuil ne
suffit pas à corriger ce comportement.

## TensorFlow Lite, option non retenue

La conversion du modèle vers TensorFlow Lite figurait parmi les options du
sujet initial. Elle apporterait un diagnostic possible sans connexion réseau,
directement sur le téléphone, ce qui correspond exactement au contexte d'usage
décrit au chapitre 1.

Cette conversion n'a pas été engagée au cours des 30 jours du projet : la
priorité est allée à la mesure de la robustesse au champ et à la construction
de la version 2 du modèle, qui ont révélé un problème plus fondamental qu'un
problème de déploiement. Il s'agit d'un choix assumé, pas d'un oubli.

Cette voie reste ouverte pour la suite. Le choix de MobileNetV2, justifié au
chapitre 4, a précisément été fait en gardant cette possibilité praticable,
contrairement à ce qu'aurait donné une architecture plus lourde comme ResNet50.

## Couche météorologique, option non retenue

Le principe consisterait à croiser le diagnostic du modèle avec les conditions
locales, plusieurs des maladies du périmètre étant favorisées par l'humidité
et la chaleur.

Cette piste a été écartée parce qu'elle suppose un modèle déjà fiable au
champ. Ajouter une source de données supplémentaire à un diagnostic qui n'est
juste qu'une fois sur deux au champ n'améliorerait pas la décision de
l'utilisateur, cela la compliquerait sans en améliorer la fiabilité. C'est une
piste à envisager pour une suite du projet, une fois la limite principale
traitée.

## Ce que le projet retient

L'apport principal de ce projet n'est pas le modèle en lui-même, c'est la
mesure qui en révèle les limites. Une plateforme livrée sur la seule foi des
96,64 pour cent obtenus en studio aurait produit des diagnostics faux avec
assurance, sans que personne ne dispose du moyen de s'en rendre compte.
