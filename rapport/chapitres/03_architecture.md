# Architecture et contrat d'interface

## Vue d'ensemble

![Architecture de la plateforme, six couches et frontière entre les deux périmètres.](docs/architecture.png)

La plateforme est organisée en six couches, qui correspondent chacune à une
étape du cycle de vie d'une photographie de feuille, depuis sa capture jusqu'à
l'affichage d'une recommandation. Trois de ces couches relèvent du périmètre A :
la constitution du corpus, le prétraitement, et le service d'inférence qui
héberge le modèle. Les trois autres relèvent du périmètre B : l'entraînement du
modèle, la génération des cartes d'interprétabilité, et l'application qui
restitue le diagnostic.

Le plus lisible pour présenter cette architecture est de suivre une
photographie de bout en bout, plutôt que de décrire chaque couche isolément.
Un utilisateur prend une photographie avec son téléphone et la soumet dans
l'application. L'application transmet cette image, sans la modifier, au
service d'inférence. Le service vérifie le format et la taille du fichier, le
redimensionne à 224 sur 224 pixels, le normalise, puis le fait passer par le
modèle chargé en mémoire. Le modèle produit dix scores, un par classe. Le
service détermine la classe de plus haut score, calcule la carte Grad-CAM
correspondante, et renvoie l'ensemble sous forme d'une réponse structurée.
L'application reçoit cette réponse et l'affiche : diagnostic, niveau de
confiance, carte visuelle, et recommandation associée.

La frontière entre le périmètre A et le périmètre B a été placée à cet endroit
précis, entre le service d'inférence et l'application, parce que c'est la
seule frontière qui permet à chaque binôme de travailler sur une brique
testable indépendamment : le service peut être validé en lui envoyant des
images de test sans aucune interface, et l'application peut être développée
contre une réponse simulée sans que le modèle soit terminé.

## La séparation entre l'application et le service

L'application ne charge jamais le modèle elle-même ; elle se contente
d'appeler le service par le réseau, sur les points d'accès décrits plus bas.

Cette séparation permet trois choses distinctes : changer de version du
modèle sans toucher à l'application, remplacer ou faire évoluer l'interface
sans toucher au modèle, et tester les deux composantes séparément. Elle a un
coût en retour : chaque diagnostic suppose désormais un appel réseau entre les
deux conteneurs, avec une gestion des pannes à prévoir, et un état à afficher
dans l'application lorsque le service ne répond pas encore ou plus.

## Le contrat d'interface

Le contrat d'interface est le document qui a permis aux deux binômes de
travailler en parallèle sans se bloquer l'un l'autre. Il a été gelé le
14 août 2026 et n'a pas bougé depuis.

| Élément | Valeur retenue |
|---|---|
| Formats d'image acceptés | JPEG ou PNG, trois canaux |
| Taille maximale du fichier | 5 Mo |
| Dimension attendue par le modèle | 224 sur 224 pixels |
| Qui redimensionne | Le service, jamais l'application |
| Source de vérité des classes | `classes.json`, jamais recopié en dur |

Tableau: Principales clauses du contrat d'interface.

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/predict` | Reçoit l'image, renvoie le diagnostic complet |
| GET | `/health` | État du service et version du modèle chargé |
| GET | `/classes` | Liste ordonnée des dix classes |

Tableau: Points d'accès du service d'inférence.

La réponse de `/predict` contient la classe retenue et son indice, le niveau
de confiance associé, les trois premières hypothèses avec leur propre score,
la carte Grad-CAM encodée, et la version du modèle ayant produit la réponse.

La clause qui confie tout le redimensionnement au service, et jamais à
l'application, garantit qu'une seule chaîne de prétraitement existe pour une
photographie donnée. Le chapitre 6 montre précisément ce qui arrive quand deux
chaînes de redimensionnement coexistent malgré tout, entre un notebook et le
service : les deux méthodes utilisées, `tf.image.resize` d'un côté et Pillow de
l'autre, ne produisent pas exactement la même image de 224 pixels, et cet écart
suffit à faire basculer certains diagnostics.

L'ordre des dix classes est, de la même manière, un point de contrat et non un
détail d'implémentation. Si le service et le modèle ne s'accordaient pas sur
cet ordre, un indice décalé transformerait silencieusement chaque diagnostic
en un autre, sans qu'aucune erreur ne se déclenche : le système continuerait à
répondre, mais avec des libellés faux.

Le gel du contrat a permis concrètement au binôme B de développer l'application
contre un service simulé respectant le même format de réponse, pendant que le
binôme A finalisait le service réel. Les deux composantes ont ainsi progressé
en parallèle plutôt que l'une après l'autre.

## Ce que le service annonce sur lui-même

La route `/health` renvoie la version du modèle réellement chargé en mémoire,
déduite du nom du fichier chargé, et non une valeur écrite en dur dans le code.
Ce détail compte : un service qui annoncerait une version tout en en servant
une autre rendrait toute mesure de performance ininterprétable, puisqu'on ne
saurait plus quel modèle est utilisé. Ce cas s'est présenté en cours de projet
et a été corrigé ; le chapitre 6 le raconte du point de vue de l'évaluation
qu'il a fallu reprendre.
