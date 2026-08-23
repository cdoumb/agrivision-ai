# Perspectives

<!--
    CHEICK : chapitre à toi. Environ 1 page, c'est le plus court.
    Il s'accroche directement au chapitre 9 : chaque perspective doit répondre
    à une limite qui y est nommée, sinon elle n'a rien à faire ici.
    Attention au ton : ce sont des pistes, pas des promesses. Rien de ce qui
    suit n'a été engagé.
-->

> A REDIGER: Chapitre 10, à rédiger par Cheick. Le plan proposé figure ci-dessous.

## Ce qui répondrait à la limite principale

La limite centrale du chapitre 9 est la performance au champ. Les pistes qui suivent
sont classées par rapport attendu, la première étant de loin la plus déterminante.

- **Collecter des images de terrain locales.** C'est la seule piste qui s'attaque à la
  cause et non aux symptômes. Décrire ce que cela suppose : des photographies prises
  dans des exploitations sénégalaises, étiquetées par un conseiller agricole, sur les
  cultures du périmètre. Donner un ordre de grandeur du volume nécessaire si tu peux le
  justifier, sinon rester qualitatif.
- **Corriger les étiquettes du corpus de test.** Le chapitre 8 établit qu'au moins une
  étiquette de PlantDoc est fausse. Une relecture systématique donnerait une mesure plus
  juste de ce que vaut réellement le modèle, sans réentraîner quoi que ce soit.
- **Élargir le périmètre à d'autres cultures**, à commencer par celles qui comptent
  localement et qui sont absentes des dix classes actuelles.

## Le refus de répondre

La limite d'usage la plus gênante est qu'une feuille inconnue reçoit tout de même un
diagnostic. Piste à décrire : un mécanisme de rejet, capable de répondre que l'image
n'appartient à aucune classe connue, au lieu de répartir de force cent pour cent de
certitude entre dix possibilités.

Signaler que cela demande un travail spécifique, et pas seulement un seuil plus haut :
un modèle surconfiant reste surconfiant devant une image aberrante.

## TensorFlow Lite, option non retenue

<!--
    À traiter comme un choix assumé, pas comme un oubli. Le sujet le
    proposait en option, nous ne l'avons pas engagé faute de temps.
-->

Points à couvrir :

- Ce que la conversion apporterait : un diagnostic sans connexion, sur le téléphone
  directement, ce qui correspond au contexte d'usage décrit au chapitre 1.
- Pourquoi elle n'a pas été engagée : la priorité est allée à la mesure de robustesse et
  à la version 2, qui ont révélé un problème plus fondamental qu'un problème de
  déploiement.
- Pourquoi elle reste ouverte : le choix de MobileNetV2, justifié au chapitre 4, a été
  fait en gardant cette voie praticable.

## Couche météorologique, option non retenue

- Le principe : croiser le diagnostic avec les conditions locales, plusieurs des
  maladies du périmètre étant favorisées par l'humidité et la chaleur.
- Pourquoi elle a été écartée : elle suppose un modèle déjà fiable au champ. Ajouter une
  source de données à un diagnostic juste une fois sur deux n'améliorerait pas la
  décision, cela la compliquerait.
- C'est une piste pour une suite, une fois la limite principale traitée.

## Ce que le projet retient

<!--
    Deux ou trois phrases de clôture pour tout le rapport. Elles doivent
    porter sur la démarche, pas sur les chiffres, qui sont déjà donnés
    ailleurs. Le rapport se termine ici.
-->

Piste de formulation, à retravailler dans tes mots :

L'apport principal du projet n'est pas le modèle, c'est la mesure qui en révèle les
limites. Une plateforme livrée sur la foi des 96,64 pour cent de studio aurait produit
des diagnostics faux avec assurance, sans que personne ne dispose du moyen de s'en rendre
compte.
