# Résultats de la première version en conditions de studio

<!--
    Chapitre de Faustin. Premier jet.
    Toutes les valeurs viennent de reports/model_card.json et de
    reports/metriques_par_classe.csv, produits par le notebook
    01_entrainement_mobilenetv2.ipynb. Aucun chiffre n'est saisi de mémoire.
-->

La première version du modèle, `mobilenetv2-v1.0`, a été entraînée le 17 août 2026 sur
le seul corpus PlantVillage. Ce chapitre rend compte de ce qu'elle vaut sur le jeu de
test issu de ce même corpus, c'est-à-dire dans les conditions exactes où elle a appris.
Le chapitre 6 mesure ensuite ce qu'elle vaut ailleurs, et l'écart entre les deux est le
résultat central du projet.

## Le jeu de test et sa constitution

Le découpage vient de `reports/split_manifest.csv`, produit par le binôme A et figé une
fois pour toutes. Il répartit les 13 725 images du corpus en 9 597 images
d'entraînement, 2 058 de validation et 2 056 de test, selon des proportions de 70, 15 et
15 pour cent, avec une graine aléatoire fixée à 42.

Deux précautions décrites au chapitre 2 méritent d'être rappelées ici, parce qu'elles
conditionnent la lecture des chiffres qui suivent. Les doublons exacts ont été retirés,
et les groupes d'images quasi identiques ont été maintenus dans une seule et même
partie du découpage. Sans cela, une image du jeu de test aurait pu avoir sa jumelle
dans le jeu d'entraînement, et le modèle aurait été noté sur des images qu'il avait déjà
vues. Le chiffre d'exactitude aurait été plus flatteur, et faux.

## Résultats d'ensemble

Sur les 2 056 images de test, le modèle atteint une exactitude de **96,64 pour cent**,
pour une perte de 0,089 et un F1 macro de 0,9566.

| Mesure | Valeur |
|---|---|
| Exactitude | 96,64 % |
| Perte (entropie croisée) | 0,089 |
| F1 macro, 10 classes | 0,9566 |
| F1 pondéré | 0,9665 |
| Images de test | 2 056 |

Tableau: Résultats de `mobilenetv2-v1.0` sur le jeu de test PlantVillage.

L'écart entre F1 macro et F1 pondéré, 0,9566 contre 0,9665, mesure exactement le poids
du déséquilibre entre classes. La moyenne macro traite les dix classes à égalité, la
moyenne pondérée donne plus de poids aux classes nombreuses. La seconde étant la plus
élevée, ce sont bien les classes les moins fournies qui tirent le résultat vers le bas.
C'est le comportement attendu, et la suite le confirme classe par classe.

![Évolution de l'exactitude et de la perte au fil des époques, transfert d'apprentissage puis affinage.](reports/courbes_apprentissage.png)

Les courbes d'apprentissage montrent les deux phases distinctes de l'entraînement. La
première gèle entièrement le corps de MobileNetV2 et n'entraîne que la tête de
classification. La seconde, l'affinage, dégèle les quarante dernières couches avec un
taux d'apprentissage réduit. Le décrochage visible entre les deux phases correspond à ce
changement de régime.

## Résultats par classe

| Classe | Précision | Rappel | F1 | Images de test |
|---|---|---|---|---|
| Tomate - Saine | 0,971 | 1,000 | 0,986 | 238 |
| Tomate - Mildiou tardif | 0,968 | 0,961 | 0,965 | 285 |
| Tomate - Tache bactérienne | 0,981 | 0,962 | 0,972 | 319 |
| Tomate - Septoriose | 0,955 | 0,958 | 0,957 | 265 |
| Maïs - Sain | 0,994 | 1,000 | 0,997 | 174 |
| Maïs - Rouille commune | 0,994 | 1,000 | 0,997 | 179 |
| Maïs - Helminthosporiose | 0,928 | 0,872 | 0,899 | 148 |
| Maïs - Cercosporiose | 0,795 | 0,857 | 0,825 | 77 |
| Poivron - Sain | 0,991 | 0,986 | 0,989 | 222 |
| Poivron - Tache bactérienne | 0,974 | 0,987 | 0,980 | 149 |

Tableau: Précision, rappel et F1 par classe, jeu de test PlantVillage, modèle v1.

Huit classes sur dix dépassent 0,95 de F1. Deux seulement décrochent, et ce sont les
deux mêmes maladies : l'helminthosporiose du maïs à 0,899 et la cercosporiose du maïs à
0,825.

![Matrice de confusion du modèle v1 sur le jeu de test PlantVillage.](reports/matrice_confusion.png)

## Où le modèle se trompe, et pourquoi

Le détail des deux classes faibles est instructif, parce qu'il ne se lit pas dans
l'exactitude globale.

La cercosporiose obtient une précision de 0,795 pour un rappel de 0,857. Autrement dit,
le modèle la retrouve correctement dans la plupart des cas, mais il l'annonce aussi
quand elle n'y est pas. Sur ses 77 images de test, environ 66 sont correctement
identifiées, et une quinzaine d'images d'autres classes lui sont attribuées à tort.

L'helminthosporiose présente le profil inverse : une précision élevée de 0,928 pour un
rappel de 0,872. Sur ses 148 images, une vingtaine échappent au modèle.

Ces deux déséquilibres sont symétriques, et l'hypothèse la plus économique est qu'ils se
répondent : les helminthosporioses manquées deviennent des cercosporioses annoncées à
tort. La matrice de confusion permet de le vérifier directement, et c'est bien ce
qu'elle montre. Cette confusion n'a rien d'aberrant sur le plan agronomique : les deux
maladies produisent sur la feuille de maïs des lésions allongées de couleur brun clair,
que le stade d'évolution rend parfois difficiles à distinguer à l'oeil nu.

Deux facteurs aggravent le phénomène. La cercosporiose est la classe la moins fournie du
corpus, avec 513 images au total contre 2 127 pour la plus fournie, soit un rapport de
4,15 entre les deux extrêmes. Et un jeu de test de 77 images seulement donne une marge
d'erreur large : quelques images de plus ou de moins déplacent le F1 de plusieurs
points.

> RETENIR: Un modèle qui atteint 96,64 pour cent en moyenne se trompe encore une fois sur cinq sur sa classe la plus faible. La moyenne masque la faiblesse ; seul le détail par classe la rend visible.

## Ce que ce chiffre prouve, et ce qu'il ne prouve pas

Il faut être clair sur la portée de ces 96,64 pour cent, car c'est précisément le genre
de chiffre qu'un rapport peut mettre en avant sans le mériter.

Ce résultat établit une chose, et une seule : sur des images produites dans les mêmes
conditions que celles de l'entraînement, feuille détachée, posée à plat sur un fond uni,
éclairage constant, le modèle sépare correctement les dix classes. C'est nécessaire, et
c'est loin d'être suffisant.

Il n'établit en revanche rien du tout sur le comportement du modèle face à une
photographie prise au champ, avec un feuillage encombré, une lumière rasante et une
feuille encore attachée à la plante. PlantVillage est un corpus de laboratoire, et un
modèle entraîné dessus apprend inévitablement une part des conditions de prise de vue en
même temps que la maladie. Quelle part, exactement, aucun chiffre de ce chapitre ne le
dit.

C'est cette question que le chapitre suivant instruit, avec un corpus que le modèle n'a
jamais vu et qui n'a rien de commun avec un studio.
