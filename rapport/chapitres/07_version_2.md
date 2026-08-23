# La version 2 : apprendre à douter

<!--
    Chapitre de Faustin. Premier jet.
    Sources : reports/model_card_v2.json (chiffres du notebook, qui compare
    les deux versions par la même chaîne) et reports/robustesse_terrain_v2.json
    (chiffres du service). Les deux jeux sont distingués dans le texte.
-->

Le chapitre précédent laisse le projet devant un choix. La chute de performance au champ
tient à la nature du corpus d'entraînement, et aucun réglage ne la fera disparaître.
Restait à savoir ce qu'il était possible de récupérer, et surtout ce qu'il fallait viser.

La décision prise a orienté tout le reste : plutôt que de chercher quelques points
d'exactitude supplémentaires, la version 2 a été construite pour **cesser de se tromper
avec assurance**. Pour un outil d'aide à la décision agricole, un modèle qui sait douter
vaut mieux qu'un modèle qui a un peu plus souvent raison.

## Ce qui a changé

La version 2, `mobilenetv2-v2.0`, a été entraînée le 18 août 2026. Cinq modifications la
séparent de la précédente.

1. **Ajout d'images de terrain à l'entraînement.** Le corpus PlantWild apporte
   1 765 photographies prises en conditions réelles, aux côtés des 9 597 images de
   PlantVillage. Le modèle voit désormais des feuilles dans leur milieu, et non
   seulement sur fond uni.
2. **Augmentation de données étendue.** Aux transformations géométriques usuelles
   s'ajoutent des variations de teinte et de saturation, des occlusions partielles, du
   flou et des translations. L'objectif est de rendre le modèle indifférent aux
   conditions de prise de vue plutôt qu'à la seule orientation de la feuille.
3. **Affinage plus profond.** Quatre-vingts couches sur les 154 de MobileNetV2 sont
   dégelées, contre quarante pour la version 1. Le modèle peut donc réviser des
   représentations plus générales, et pas seulement les dernières couches spécialisées.
4. **Lissage des étiquettes à 0,1.** C'est la correction visant directement la
   surconfiance. Plutôt que d'apprendre au modèle qu'une image est une septoriose à
   100 pour cent, on lui apprend qu'elle l'est à 90 pour cent, le reste étant réparti
   sur les autres classes. Le modèle est ainsi dissuadé de produire des certitudes
   absolues.
5. **Mélange d'images et double agrégation.** La technique du mélange d'images, qui
   combine deux images et leurs étiquettes, complète le dispositif. La couche
   d'agrégation finale combine désormais moyenne et maximum, au lieu de la seule
   moyenne.

## Ce que cela coûte en studio

Le premier effet de ces changements est une baisse en conditions de studio, et il faut la
présenter avant les gains.

| Mesure | v1 | v2 |
|---|---|---|
| Exactitude studio | 96,64 % | 94,36 % |
| F1 macro studio, 10 classes | 0,9566 | 0,9373 |

Tableau: Coût de la version 2 sur le jeu de test PlantVillage.

Le modèle perd 2,28 points d'exactitude sur le corpus de laboratoire. Cette perte est
attendue et acceptée : un modèle contraint de généraliser à des conditions plus variées
exploite moins finement les régularités d'un studio. Elle serait inquiétante si elle
n'était pas compensée ailleurs.

## Ce que cela rapporte au champ

![Comparaison des deux versions sur les 942 images de terrain.](reports/comparaison_v1_v2_terrain.png)

| Mesure, corpus PlantDoc | v1 | v2 |
|---|---|---|
| Exactitude | 36,27 % | 48,99 % |
| F1 macro, 9 classes | 0,2671 | 0,4520 |
| Confiance moyenne quand le diagnostic est juste | 84,4 % | 50,9 % |
| Confiance moyenne quand le diagnostic est faux | 77,3 % | 40,3 % |

Tableau: Les deux versions mesurées par la chaîne du notebook, qui les traite à l'identique.

L'exactitude au champ progresse de près de treize points et le F1 macro passe de 0,2671
à 0,4520, soit un gain de près de 70 pour cent en valeur relative. Mais la ligne la plus
importante de ce tableau n'est pas l'exactitude.

En version 1, la confiance moyenne quand le modèle a raison était de 84,4 pour cent, et
de 77,3 pour cent quand il se trompait. Sept points d'écart seulement : la confiance
affichée ne permettait pratiquement pas de distinguer un bon diagnostic d'un mauvais. En
version 2, ces valeurs deviennent 50,9 et 40,3 pour cent, soit plus de dix points
d'écart, sur une échelle de valeurs globalement abaissée. La confiance affichée est
devenue un signal exploitable.

## Le tableau qui compte : ce que voit l'utilisateur

Les mesures précédentes décrivent le modèle. Celle-ci décrit la plateforme, en ne
comptant que les diagnostics effectivement affichés sans avertissement, sur les
942 photographies de terrain.

| | v1 | v2 |
|---|---|---|
| Diagnostics affirmés sans avertissement | 672 | 220 |
| dont corrects | 269 | 159 |
| **Fiabilité quand l'application affirme** | **40,0 %** | **72,3 %** |
| **Diagnostics faux affirmés sans avertissement** | **403** | **61** |

Tableau: Comportement des deux versions du point de vue de l'utilisateur.

La lecture de ce tableau demande d'accepter une idée peu intuitive. La version 2 se
prononce trois fois moins souvent : 220 diagnostics affirmés contre 672. Elle produit
même moins de diagnostics justes en valeur absolue, 159 contre 269. À première vue, elle
fait moins bien.

Ce qui compte pourtant est la dernière ligne. Le nombre de diagnostics faux annoncés
sans le moindre signal passe de 403 à 61, soit une division par près de sept. Et quand
l'application affirme quelque chose, elle a raison dans 72,3 pour cent des cas au lieu de
40,0.

> RETENIR: Un outil qui se tait quand il ne sait pas est plus utile qu'un outil qui parle toujours. La version 1 affirmait 403 diagnostics faux avec assurance ; la version 2 en affirme 61. C'est le résultat que le projet retient.

## Le réglage du seuil d'avertissement

Le lissage des étiquettes abaisse mécaniquement toutes les probabilités produites par le
modèle, y compris quand la réponse est juste. Le seuil d'avertissement de l'application a
donc dû être réajusté : il est passé de 70 pour cent pour la version 1 à **60 pour cent**
pour la version 2. Sans cet ajustement, l'application aurait signalé comme douteux des
diagnostics parfaitement corrects, et l'avertissement aurait perdu son sens à force
d'apparaître.

Un point d'honnêteté est nécessaire ici, plutôt que d'attendre la question. Ce seuil a
été retenu après comparaison de plusieurs valeurs, mais **ce balayage n'apparaît nulle
part dans le code du dépôt** : seule la valeur finale y figure. Deux conséquences en
découlent, et elles doivent être écrites. D'abord, le choix n'est pas reproductible en
l'état à partir du seul dépôt. Ensuite, si la comparaison a été menée sur PlantDoc, alors
ce corpus a servi à régler un paramètre, et il n'est plus totalement vierge pour ce
réglage précis. Il le demeure pour tout le reste, puisqu'aucune de ses images n'a jamais
été vue en entraînement, mais la nuance méritait d'être posée.

## Où le gain se situe, classe par classe

| Classe | F1 terrain v1 | F1 terrain v2 |
|---|---|---|
| Tomate - Saine | 0,060 | 0,591 |
| Tomate - Mildiou tardif | 0,506 | 0,691 |
| Tomate - Tache bactérienne | 0,044 | 0,245 |
| Tomate - Septoriose | 0,471 | 0,403 |
| Maïs - Rouille commune | 0,241 | 0,607 |
| Maïs - Helminthosporiose | 0,432 | 0,522 |
| Maïs - Cercosporiose | 0,361 | 0,440 |
| Poivron - Sain | 0,211 | 0,564 |
| Poivron - Tache bactérienne | 0,345 | 0,457 |

Tableau: F1 par classe au champ, mesuré par le notebook sur les deux versions.

Le gain le plus spectaculaire concerne les deux classes de plantes saines, tomate et
poivron, qui passent respectivement de 0,060 à 0,591 et de 0,211 à 0,564. C'est
exactement ce que l'ajout de PlantWild pouvait apporter : le modèle a enfin vu à quoi
ressemble une plante en bonne santé dans son milieu naturel.

Une classe recule, la septoriose de la tomate, de 0,471 à 0,403. Le chapitre 8 apporte un
élément d'explication troublant sur cette classe précise, à partir de l'examen des cartes
d'interprétabilité.

![Matrice de confusion du modèle v2 sur les 942 images de terrain.](reports/confusion_terrain_v2.png)

## Les deux modèles sont conservés

La version 1 n'a pas été écrasée. Les deux fichiers coexistent, et la version servie est
désignée par une variable d'environnement dans `docker-compose.yml`. Remplacer `v2` par
`v1` et relancer suffit à rejouer la comparaison de ce chapitre sur la plateforme réelle,
sans réentraîner quoi que ce soit. Le service annonce d'ailleurs la version qu'il sert
réellement, déduite du nom du fichier chargé, ce qui rend impossible le cas d'un service
qui annoncerait une version en en servant une autre.
