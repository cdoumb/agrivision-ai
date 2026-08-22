# Lecture des cartes Grad-CAM

Planche : `gradcam_exemples_mobilenetv2-v2.0.png`
Sélection : `gradcam_selection_mobilenetv2-v2.0.json`
Modèle : `mobilenetv2-v2.0`, 56 images examinées (20 de studio, 36 de terrain)

Les quatre cas ne sont pas choisis à la main. `src/model/planche_gradcam.py` les
retient selon des critères explicites, dont celui de l'erreur la plus assurée,
pour éviter de ne montrer que des réussites. Les commentaires ci-dessous sont
écrits après lecture des cartes.

Rappel de lecture : la couleur n'indique pas la zone analysée, mais ce qui a
pesé dans la décision. Toute la feuille est examinée. Le rouge a emporté le
diagnostic, le bleu n'a pratiquement pas compté.

## 1. Diagnostic juste en studio

`data/echantillon/Tomate__Saine_2.jpg`, tomate saine, diagnostiquée saine à 96 %.

La chaleur épouse le limbe et s'arrête à ses bords. Le fond gris granuleux reste
entièrement bleu.

C'est le résultat qu'on attend, et il répond à une objection prévisible. Une
feuille saine ne présente aucune lésion à désigner : le modèle ne peut s'appuyer
que sur la régularité de la texture et sur la silhouette. Le fait que le fond ne
compte pour rien écarte l'hypothèse d'un modèle qui aurait appris à reconnaître
le décor de studio de PlantVillage plutôt que la plante.

## 2. Diagnostic juste au champ

`data/plantdoc_images/Bell_pepper leaf/test_10148582-green-leaf-of-pepper.jpg`,
poivron sain, diagnostiqué sain à 85 %.

La zone décisive couvre le centre du limbe, les nervures principales comprises.

Ce cas appelle toutefois une réserve utile au rapport. L'image vient bien de
PlantDoc, notre corpus de terrain, mais elle est photographiée sur fond blanc
uni, feuille détachée, et porte le filigrane d'une banque d'images. PlantDoc
n'est donc pas homogène : une partie de ses images se rapproche des conditions
de studio. La chute mesurée entre studio et terrain est réelle, mais le corpus
qui la mesure mélange des conditions de prise de vue variées.

## 3. Erreur affirmée sans avertissement

`data/plantdoc_images/Tomato Septoria leaf spot/train_3893.jpg`, étiquetée
septoriose de la tomate, diagnostiquée tache bactérienne du poivron à 88 %.

C'est le cas le plus instructif de la planche, pour deux raisons.

D'abord, la carte montre que le modèle a regardé les bonnes zones. Le rouge se
pose sur les taches nécrotiques cerclées du limbe, pas sur le fond violet ni sur
un artefact de la photo. L'erreur ne vient donc pas d'un indice parasite, mais
d'une confusion entre deux maladies dont les symptômes se ressemblent : petites
taches brunes cerclées de jaune dans les deux cas.

Ensuite, et c'est le point important, l'image porte en bas un bandeau tiré de la
base EPPO qui nomme l'agent responsable : *Xanthomonas vesicatoria*. Cette
bactérie est l'agent de la **tache bactérienne**, pas de la septoriose, qui est
causée par le champignon *Septoria lycopersici*. Autrement dit, l'étiquette de
PlantDoc est très probablement fausse, et le modèle a raison sur la maladie. Il
ne se trompe que sur la culture, en annonçant le poivron plutôt que la tomate,
confusion d'autant plus compréhensible que cette bactérie attaque les deux.

Cela a une conséquence directe sur nos chiffres : une part des erreurs comptées
sur PlantDoc sont des erreurs d'étiquetage du corpus, et non du modèle. Les
49,47 % d'exactitude mesurés au champ sous-estiment donc la performance réelle,
dans une proportion que nous n'avons pas quantifiée.

Ce cas illustre aussi l'usage que le guide de projet assigne à Grad-CAM au
chapitre 2.6 : un outil de diagnostic pour nous, et pas seulement une
justification pour le jury. Ici, il n'a pas révélé un défaut du modèle mais un
défaut des données.

## 4. Le modèle prévient, et il a pourtant raison

`data/plantdoc_images/Tomato leaf late blight/train_IMG_5813.jpg`, mildiou
tardif de la tomate, diagnostiqué mildiou tardif à 19 %.

La chaleur se concentre exactement sur la grande lésion nécrotique, en ignorant
le feuillage voisin et le tuteur en bois. Le modèle regarde ce qu'il faut, et il
conclut juste. Mais il ne l'affirme qu'à 19 %, très en dessous du seuil de 60 %,
et l'application afficherait donc un avertissement.

Ce cas dit ce qu'un avertissement signifie, et ce qu'il ne signifie pas. Il ne
veut pas dire que le diagnostic est faux, mais que le modèle n'en est pas sûr.
Le lissage des étiquettes employé pour entraîner le v2 abaisse volontairement
les probabilités, y compris quand la réponse est bonne. C'est le prix payé pour
que les diagnostics faux cessent d'être annoncés avec assurance, et c'est
exactement le compromis recherché : mieux vaut douter à tort que se tromper
avec aplomb.

## Ce que la planche établit

Les cartes se posent sur les lésions et sur le limbe, jamais sur le fond, y
compris quand le diagnostic est faux. L'hypothèse d'un modèle ayant appris les
conditions de prise de vue plutôt que la maladie est donc écartée sur ces
exemples. Les erreurs observées viennent de ressemblances réelles entre
symptômes, et au moins une d'entre elles vient d'une étiquette erronée du corpus
de test.
