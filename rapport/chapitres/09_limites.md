# Limites connues

<!--
    Chapitre de Faustin. Premier jet.
    Sources : les blocs "limites" de reports/robustesse_terrain_v2.json et
    reports/model_card_v2.json, la section "Limites connues" du README, et les
    constats des chapitres 6 à 8.
    Cheick : le chapitre 10 s'accroche directement ici.
-->

Ce chapitre rassemble ce que la plateforme ne fait pas, ne mesure pas, ou fait moins bien
qu'il n'y paraît. Il est écrit avant les perspectives, parce que les secondes répondent
aux premières.

## La limite principale : au champ, le modèle se trompe une fois sur deux

C'est mesuré et non supposé : 49,47 pour cent d'exactitude sur 942 photographies de
terrain, contre 94,36 pour cent sur des photographies de studio, pour la version en
service. L'application est conçue autour de cette limite, en signalant explicitement les
diagnostics incertains plutôt qu'en affichant un chiffre rassurant.

Ce chiffre appelle deux corrections en sens inverse, et il est plus honnête de les
donner toutes les deux.

Il **sous-estime** le modèle, dans une proportion non quantifiée, parce que PlantDoc
contient des étiquettes erronées. Un cas est documenté au chapitre 8, où une image rangée
en septoriose porte une mention de la base EPPO désignant l'agent de la tache
bactérienne. Le diagnostic compté comme faux était le bon.

Il **surestime** aussi le modèle sur un autre plan, parce que PlantDoc n'est pas
homogène. Une partie de ses images est photographiée sur fond uni, feuille détachée, dans
des conditions proches du studio, comme le montre le deuxième cas du chapitre 8. La
performance sur des photographies réellement prises dans un champ dense est donc
probablement inférieure aux 49,47 pour cent affichés.

Aucune de ces deux corrections n'a été chiffrée. Les additionner ou les compenser
mentalement n'aurait aucun fondement.

## Limites du corpus d'entraînement

L'entraînement repose majoritairement sur PlantVillage, photographié en studio, feuille
détachée sur fond uni. PlantWild apporte des images de terrain, mais en bien moindre
quantité : 1 765 images contre 9 597. Un modèle entraîné dans ces conditions apprend en
partie la prise de vue et non la seule maladie.

Le corpus est par ailleurs déséquilibré, dans un rapport de 4,15 entre la classe la plus
fournie, la tache bactérienne de la tomate avec 2 127 images, et la moins fournie, la
cercosporiose du maïs avec 513. C'est cette dernière qui obtient le plus faible F1 en
studio, à 0,825, et le rapprochement n'a rien d'accidentel.

Enfin, les dix classes ne couvrent que trois cultures, tomate, maïs et poivron. Ce
périmètre a été gelé au 14 août dans le contrat d'interface, et il ne représente qu'une
petite partie des cultures pratiquées au Sénégal.

## Limites du protocole d'évaluation

Le jeu de test de terrain provient d'une **source unique**, PlantDoc. D'autres conditions
de prise de vue, un autre appareil, un autre climat donneraient d'autres chiffres. Rien
ne garantit que les 49,47 pour cent se retrouveraient sur des photographies prises dans
une exploitation sénégalaise.

La classe « Maïs - Sain » est absente de PlantDoc. Elle n'a donc pas pu être évaluée au
champ, et le modèle peut la prédire à tort sans qu'aucune image ne vienne le contredire.
Tous les F1 macro de terrain sont pour cette raison calculés sur neuf classes.

La correspondance entre la catégorie « Bell pepper leaf spot » de PlantDoc et notre
classe « Poivron - Tache bactérienne » est une approximation : PlantDoc ne précise pas
l'agent responsable de la tache observée.

Les classes les moins fournies du jeu de terrain, autour de soixante images, ont une
marge d'erreur large. Un écart de quelques points sur ces classes n'est pas
interprétable.

## Limites de reproductibilité

Le seuil d'avertissement de 60 pour cent a été retenu après comparaison de plusieurs
valeurs, mais ce balayage n'apparaît pas dans le dépôt : seule la valeur finale y figure.
Le choix n'est donc pas reproductible en l'état à partir d'un simple clone. Ce point est
développé au chapitre 7.

Les deux chaînes de mesure, celle du notebook et celle du service, ne donnent pas
exactement les mêmes chiffres, pour une raison de redimensionnement d'image détaillée au
chapitre 6. L'écart est faible, moins d'un point, mais il impose de préciser la source de
chaque chiffre cité, ce que ce rapport fait systématiquement.

Enfin, ni les images ni les modèles entraînés ne sont versionnés dans le dépôt, Git
n'étant pas adapté aux fichiers binaires lourds. Le corpus se retélécharge et le
découpage est reproductible à l'identique grâce au manifeste, mais les fichiers `.keras`
dépendent d'un partage externe.

## Limites de l'usage

Toute image n'appartenant pas aux dix classes est rapprochée de force de l'une d'entre
elles. Le modèle répartit toujours 100 pour cent de certitude entre les classes qu'il
connaît : une feuille de manioc, une feuille d'arachide ou une photographie de chaussure
produira donc un diagnostic, dépourvu de sens. L'application ne sait pas répondre qu'elle
ne connaît pas cette plante.

Le modèle ne mesure ni la gravité de l'atteinte ni son stade d'évolution. Il attribue une
classe, rien de plus.

Les recommandations affichées orientent une observation de terrain. Elles ne remplacent
pas le diagnostic d'un conseiller agricole ou d'un service de protection des végétaux,
seuls habilités à préconiser un traitement. Aucune prescription phytosanitaire ne figure
dans l'application, et c'est un choix de périmètre assumé.

## Limite juridique

PlantWild est distribué sous licence Creative Commons **CC BY-NC-ND 4.0** : usage non
commercial, sans oeuvre dérivée, attribution obligatoire. Le projet est un travail
académique sans exploitation commerciale, ce qui satisfait la clause NC.

La clause ND soulève en revanche une question non tranchée : un modèle entraîné sur ces
images constitue-t-il une oeuvre dérivée au sens de la licence ? Le droit d'auteur
n'apporte pas de réponse établie sur ce point. Par prudence, le modèle v2 ne peut pas
être diffusé à des fins commerciales, et toute réutilisation hors du cadre académique
demande de revenir à la licence.

> ATTENTION: Cette limite ne concerne que la version 2. La version 1, entraînée sur le seul PlantVillage, n'est pas affectée par la licence de PlantWild.
