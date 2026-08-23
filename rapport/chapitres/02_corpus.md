# Le corpus : constitution, nettoyage et découpage

<!--
    CHEICK : chapitre à toi. Environ 4 pages, c'est le plus long des tiens.
    Les tableaux de chiffres sont déjà remplis d'après reports/split_report.md
    et reports/corpus_stats.md : ils sont justes, ne les ressaisis pas, il ne
    reste qu'à écrire le texte autour.
    La déduplication par hash perceptif est le point fort du chapitre : c'est
    une précaution que le sujet ne demandait pas.
-->

> A REDIGER: Chapitre 2, à rédiger par Cheick. Les tableaux sont déjà renseignés à partir des fichiers du dépôt ; il reste le texte.

## PlantVillage : origine et nature

Points à couvrir :

- Origine du corpus, conditions de production des images, feuille détachée sur fond uni.
- Pourquoi ce corpus a été retenu malgré son caractère de laboratoire : c'est le seul
  disponible en quantité suffisante et correctement étiqueté.
- Signaler dès ici que cette nature de studio est la cause de ce que mesure le
  chapitre 6. Le lecteur doit être prévenu avant de lire les 96,64 pour cent du
  chapitre 5.

## Les dix classes retenues

| Culture | États reconnus |
|---|---|
| Tomate | Saine, Mildiou tardif, Tache bactérienne, Septoriose |
| Maïs | Sain, Rouille commune, Helminthosporiose, Cercosporiose |
| Poivron | Sain, Tache bactérienne |

Tableau: Les dix classes du contrat d'interface, gelées au 14 août 2026.

- Expliquer le critère de sélection de ces dix classes parmi les 38 de PlantVillage.
- Rappeler que `classes.json` est la source unique de vérité pour l'ordre des classes, et
  pourquoi un ordre stable est indispensable entre l'entraînement et le service.

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

- Le rapport de déséquilibre atteint 4,15 entre la classe la plus fournie et la moins
  fournie.
- Expliquer ce qu'un tel déséquilibre produit si rien n'est fait, et renvoyer à la
  pondération de la fonction de perte décrite au chapitre 4.
- Le lien avec le chapitre 5 est direct : la cercosporiose, classe la moins fournie, est
  aussi celle qui obtient le plus faible F1.

## Le contrôle d'intégrité

- Toutes les images font 256 pixels de côté, aucun fichier corrompu n'a été détecté sur
  les 13 725.
- Décrire ce que le script vérifie et pourquoi ce contrôle vient avant tout le reste.

## La déduplication, et le piège qu'elle referme

<!--
    C'est le passage le plus important du chapitre. Prends le temps de
    l'expliquer : un lecteur qui n'a jamais entendu parler de fuite de données
    doit comprendre pourquoi cette précaution change la validité de tous les
    chiffres du rapport.
-->

Points à couvrir :

- **Doublons exacts**, détectés par empreinte MD5 : 14 groupes au total, 8 sur le mildiou
  tardif de la tomate et 6 sur la tomate saine. Ils sont retirés.
- **Quasi-doublons**, détectés par hash perceptif : ce sont des images visuellement
  presque identiques mais dont les fichiers diffèrent, par exemple la même feuille
  photographiée deux fois de suite. Expliquer le principe du hash perceptif en une ou
  deux phrases accessibles.
- **La règle appliquée** : les images d'un même groupe de quasi-doublons sont placées
  dans la même partie du découpage, jamais réparties entre entraînement et test.
- **Pourquoi c'est décisif** : sans cette règle, une image du jeu de test aurait sa
  jumelle dans le jeu d'entraînement. Le modèle serait noté sur des images qu'il a déjà
  vues, et le chiffre d'exactitude serait à la fois plus flatteur et faux. Cette
  précaution ne figurait pas dans le sujet.

| Classe | Doublons exacts | Groupes de quasi-doublons |
|---|---|---|
| Tomate - Saine | 6 | 20 |
| Tomate - Mildiou tardif | 8 | 11 |
| Tomate - Tache bactérienne | 0 | 13 |
| Poivron - Sain | 0 | 4 |
| Maïs - Sain | 0 | 1 |
| Les cinq autres classes | 0 | 0 |

Tableau: Doublons détectés, en nombre de groupes. Source : reports/corpus_stats.md.

## Le découpage

| Partie | Images | Proportion |
|---|---|---|
| Entraînement | 9 597 | 70 % |
| Validation | 2 058 | 15 % |
| Test | 2 056 | 15 % |

Tableau: Découpage du corpus. Graine aléatoire fixée à 42. Source : reports/split_report.md.

- Le découpage est **stratifié** : chaque classe conserve ses proportions dans les trois
  parties.
- Il est consigné image par image dans `reports/split_manifest.csv`, versionné dans le
  dépôt.
- Expliquer pourquoi ce manifeste est relu par les notebooks au lieu d'être recalculé :
  tout modèle entraîné plus tard reste ainsi comparable aux précédents. Sans lui, la
  comparaison entre les versions 1 et 2 du chapitre 7 n'aurait aucune valeur.

## PlantWild, ajouté pour la version 2

- Origine, nature des images, volume retenu : 1 765 images de terrain.
- Ce que cet ajout apporte, mesuré au chapitre 7.
- **La licence CC BY-NC-ND 4.0**, à citer intégralement ici : usage non commercial, sans
  oeuvre dérivée, attribution obligatoire. La réserve sur la portée de la clause ND est
  développée au chapitre 9, il suffit d'y renvoyer.

## PlantDoc, réservé à l'évaluation

- Origine, 942 images exploitables après mise en correspondance des catégories.
- **Ce corpus n'a jamais servi à l'entraînement**, d'aucune version. C'est ce qui fait la
  valeur des mesures du chapitre 6, et cela doit être écrit explicitement ici.
- La classe « Maïs - Sain » y est absente.
- Signaler que le corpus n'est pas homogène, certaines de ses images étant prises sur
  fond uni : le chapitre 8 en donne un exemple.

<!--
    SOURCES DISPONIBLES DANS LE DÉPÔT
    - reports/corpus_stats.md, reports/split_report.md
    - reports/split_manifest.csv, le découpage image par image
    - src/data/download.py, split.py, preprocessing.py
    - le guide de projet, chapitre 3
-->
