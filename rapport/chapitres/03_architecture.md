# Architecture et contrat d'interface

## Vue d'ensemble

![Architecture de la plateforme, six couches et frontiere entre les deux perimetres.](docs/architecture.png)

La plateforme est organisee en six couches, qui correspondent chacune a une
etape du cycle de vie d'une photographie de feuille, depuis sa capture jusqu'a
l'affichage d'une recommandation. Trois de ces couches relevent du perimetre A :
la constitution du corpus, le pretraitement, et le service d'inference qui
heberge le modele. Les trois autres relevent du perimetre B : l'entrainement du
modele, la generation des cartes d'interpretabilite, et l'application qui
restitue le diagnostic.

Le plus lisible pour presenter cette architecture est de suivre une
photographie de bout en bout, plutot que de decrire chaque couche isolement.
Un utilisateur prend une photographie avec son telephone et la soumet dans
l'application. L'application transmet cette image, sans la modifier, au
service d'inference. Le service verifie le format et la taille du fichier, le
redimensionne a 224 sur 224 pixels, le normalise, puis le fait passer par le
modele charge en memoire. Le modele produit dix scores, un par classe. Le
service determine la classe de plus haut score, calcule la carte Grad-CAM
correspondante, et renvoie l'ensemble sous forme d'une reponse structuree.
L'application recoit cette reponse et l'affiche : diagnostic, niveau de
confiance, carte visuelle, et recommandation associee.

La frontiere entre le perimetre A et le perimetre B a ete placee a cet endroit
precis, entre le service d'inference et l'application, parce que c'est la
seule frontiere qui permet a chaque binome de travailler sur une brique
testable independamment : le service peut etre valide en lui envoyant des
images de test sans aucune interface, et l'application peut etre developpee
contre une reponse simulee sans que le modele soit termine.

## La separation entre l'application et le service

L'application ne charge jamais le modele elle-meme ; elle se contente
d'appeler le service par le reseau, sur les points d'acces decrits plus bas.

Cette separation permet trois choses distinctes : changer de version du
modele sans toucher a l'application, remplacer ou faire evoluer l'interface
sans toucher au modele, et tester les deux composantes separement. Elle a un
cout en retour : chaque diagnostic suppose desormais un appel reseau entre les
deux conteneurs, avec une gestion des pannes a prevoir, et un etat a afficher
dans l'application lorsque le service ne repond pas encore ou plus.

## Le contrat d'interface

Le contrat d'interface est le document qui a permis aux deux binomes de
travailler en parallele sans se bloquer l'un l'autre. Il a ete gele le
14 aout 2026 et n'a pas bouge depuis.

| Element | Valeur retenue |
|---|---|
| Formats d'image acceptes | JPEG ou PNG, trois canaux |
| Taille maximale du fichier | 5 Mo |
| Dimension attendue par le modele | 224 sur 224 pixels |
| Qui redimensionne | Le service, jamais l'application |
| Source de verite des classes | `classes.json`, jamais recopie en dur |

Tableau: Principales clauses du contrat d'interface.

| Methode | Route | Role |
|---|---|---|
| POST | `/predict` | Recoit l'image, renvoie le diagnostic complet |
| GET | `/health` | Etat du service et version du modele charge |
| GET | `/classes` | Liste ordonnee des dix classes |

Tableau: Points d'acces du service d'inference.

La reponse de `/predict` contient la classe retenue et son indice, le niveau
de confiance associe, les trois premieres hypotheses avec leur propre score,
la carte Grad-CAM encodee, et la version du modele ayant produit la reponse.

La clause qui confie tout le redimensionnement au service, et jamais a
l'application, garantit qu'une seule chaine de pretraitement existe pour une
photographie donnee. Le chapitre 6 montre precisement ce qui arrive quand deux
chaines de redimensionnement coexistent malgre tout, entre un notebook et le
service : les deux methodes utilisees, `tf.image.resize` d'un cote et Pillow de
l'autre, ne produisent pas exactement la meme image de 224 pixels, et cet ecart
suffit a faire basculer certains diagnostics.

L'ordre des dix classes est, de la meme maniere, un point de contrat et non un
detail d'implementation. Si le service et le modele ne s'accordaient pas sur
cet ordre, un indice decale transformerait silencieusement chaque diagnostic
en un autre, sans qu'aucune erreur ne se declenche : le systeme continuerait a
repondre, mais avec des libelles faux.

Le gel du contrat a permis concretement au binome B de developper l'application
contre un service simule respectant le meme format de reponse, pendant que le
binome A finalisait le service reel. Les deux composantes ont ainsi progresse
en parallele plutot que l'une apres l'autre.

## Ce que le service annonce sur lui-meme

La route `/health` renvoie la version du modele reellement charge en memoire,
deduite du nom du fichier charge, et non une valeur ecrite en dur dans le code.
Ce detail compte : un service qui annoncerait une version tout en en servant
une autre rendrait toute mesure de performance ininterpretable, puisqu'on ne
saurait plus quel modele est realise. Ce cas s'est presente en cours de projet
et a ete corrige ; le chapitre 6 le raconte du point de vue de l'evaluation
qu'il a fallu reprendre.