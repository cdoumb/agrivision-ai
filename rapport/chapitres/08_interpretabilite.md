# Interprétabilité : sur quoi le modèle s'appuie réellement

<!--
    Chapitre de Faustin. Premier jet.
    Sources : reports/gradcam_commentaires.md, rédigé à la main après lecture
    de la planche, et reports/gradcam_selection_mobilenetv2-v2.0.json produit
    par src/model/planche_gradcam.py.
-->

Les deux chapitres précédents mesurent ce que le modèle réussit et ce qu'il rate. Ils ne
disent pas sur quoi il s'appuie pour décider. C'est une question distincte, et elle est
loin d'être théorique : un modèle entraîné majoritairement sur des images de studio
pourrait très bien avoir appris à reconnaître le fond gris de PlantVillage plutôt que les
lésions sur la feuille. Rien dans une matrice de confusion ne permettrait de le voir.

La méthode Grad-CAM répond à cette question. Elle remonte les gradients de la classe
retenue jusqu'à la dernière couche de convolution du réseau, ici la couche `out_relu`, et
produit une carte de chaleur indiquant quelles régions de l'image ont pesé dans la
décision.

> ATTENTION: La couleur n'indique pas la zone que le modèle a examinée. Toute l'image est examinée, sans exception. Elle indique ce qui a pesé dans la décision : le rouge a emporté le diagnostic, le bleu n'a pratiquement pas compté. Une lésion située ailleurs ne serait pas ignorée, elle deviendrait simplement la zone rouge à son tour.

## Comment les quatre cas ont été choisis

Le guide de projet insiste sur un point : des cartes affichées sans lecture ne
démontrent rien. Encore faut-il que les cas montrés n'aient pas été choisis pour
flatter le modèle.

Le script `src/model/planche_gradcam.py` ne retient donc aucun cas à la main. Il
diagnostique un lot de 56 images, 20 de studio et 36 de terrain tirées avec une graine
fixe, puis sélectionne quatre situations selon des critères écrits d'avance :

- le diagnostic juste le plus assuré en conditions de studio ;
- le diagnostic juste le plus assuré en conditions de terrain ;
- **l'erreur affirmée avec le plus d'assurance**, c'est-à-dire le pire cas possible du
  point de vue de l'utilisateur ;
- le cas où le modèle est le moins sûr de lui, sous le seuil d'avertissement de
  60 pour cent.

Le troisième critère est celui qui rend la planche honnête : il garantit qu'un échec
figure sur la planche, et pas n'importe lequel, le plus embarrassant.

![Les quatre cartes Grad-CAM retenues, modèle v2. À gauche la photographie, à droite la carte de chaleur.|9.5](reports/gradcam_exemples_mobilenetv2-v2.0.png)

## Cas 1 : diagnostic juste en studio

Une feuille de tomate saine, diagnostiquée saine à 96 pour cent. La chaleur épouse le
limbe et s'arrête à ses bords. Le fond gris granuleux reste entièrement bleu.

C'est le résultat attendu, et il répond à une objection prévisible. Une feuille saine ne
présente aucune lésion à désigner : le modèle ne peut s'appuyer que sur la régularité de
la texture et sur la silhouette. Le fait que le fond ne compte pour rien écarte
l'hypothèse d'un modèle qui aurait appris à reconnaître le décor de studio plutôt que la
plante.

## Cas 2 : diagnostic juste au champ

Une feuille de poivron saine issue de PlantDoc, diagnostiquée saine à 85 pour cent. La
zone décisive couvre le centre du limbe, nervures principales comprises.

Ce cas appelle une réserve utile. L'image vient bien du corpus de terrain, mais elle est
photographiée sur fond blanc uni, feuille détachée, et porte le filigrane d'une banque
d'images. **PlantDoc n'est donc pas homogène** : une partie de ses images se rapproche
des conditions de studio. La chute mesurée au chapitre 6 est réelle, mais le corpus qui
la mesure mélange des conditions de prise de vue variées, et cette limite doit être
gardée à l'esprit.

## Cas 3 : l'erreur affirmée, et ce qu'elle a révélé

Une image de PlantDoc étiquetée septoriose de la tomate, diagnostiquée tache bactérienne
du poivron à 88 pour cent. C'est le cas le plus instructif de la planche, pour deux
raisons.

D'abord, la carte montre que le modèle a regardé les bonnes zones. Le rouge se pose sur
les taches nécrotiques cerclées du limbe, pas sur le fond ni sur un artefact de la
photographie. L'erreur ne vient donc pas d'un indice parasite, mais d'une confusion entre
deux maladies dont les symptômes se ressemblent : petites taches brunes cerclées de jaune
dans les deux cas.

Ensuite, et c'est le point important, l'image porte en bas un bandeau tiré de la base
EPPO qui nomme l'agent responsable : *Xanthomonas vesicatoria*. Cette bactérie est
l'agent de la **tache bactérienne**, pas de la septoriose, laquelle est causée par le
champignon *Septoria lycopersici*. Autrement dit, l'étiquette de PlantDoc est très
probablement fausse, et le modèle a raison sur la maladie. Il ne se trompe que sur la
culture, en annonçant le poivron plutôt que la tomate, confusion d'autant plus
compréhensible que cette bactérie attaque les deux.

> RETENIR: Une part des erreurs comptées sur PlantDoc sont des erreurs d'étiquetage du corpus, et non du modèle. Les 49,47 pour cent d'exactitude mesurés au champ sous-estiment donc la performance réelle, dans une proportion que nous n'avons pas quantifiée.

Ce cas illustre l'usage que le guide de projet assigne à l'interprétabilité : un outil de
diagnostic pour l'équipe, et pas seulement une justification destinée au jury. Ici, il
n'a pas révélé un défaut du modèle mais un défaut des données. Il éclaire aussi le seul
recul observé au chapitre 7, celui de la classe septoriose, dont une partie des images de
test est peut-être mal étiquetée.

## Cas 4 : le modèle prévient, et il a pourtant raison

Une feuille de tomate atteinte de mildiou tardif, diagnostiquée mildiou tardif à
19 pour cent. La chaleur se concentre exactement sur la grande lésion nécrotique, en
ignorant le feuillage voisin et le tuteur en bois. Le modèle regarde ce qu'il faut, et il
conclut juste. Mais il ne l'affirme qu'à 19 pour cent, très en dessous du seuil de
60 pour cent, et l'application afficherait donc un avertissement.

Ce cas dit ce qu'un avertissement signifie, et ce qu'il ne signifie pas. Il ne veut pas
dire que le diagnostic est faux, mais que le modèle n'en est pas sûr. Le lissage des
étiquettes employé pour la version 2 abaisse volontairement les probabilités, y compris
quand la réponse est bonne. C'est le prix payé pour que les diagnostics faux cessent
d'être annoncés avec assurance, et c'est exactement le compromis recherché au chapitre 7.

## Ce que la planche établit

Sur ces quatre exemples, les cartes se posent sur les lésions et sur le limbe, jamais sur
le fond, y compris quand le diagnostic est faux. L'hypothèse d'un modèle ayant appris les
conditions de prise de vue plutôt que la maladie est donc écartée pour ces cas.

Cette vérification a une portée limitée, et il serait malhonnête de la présenter
autrement : quatre images ne constituent pas une preuve statistique, et la sélection
porte sur un tirage de 56 images. Elle établit néanmoins que les erreurs observées
viennent de ressemblances réelles entre symptômes, et non d'un raccourci appris sur le
décor. Elle a par ailleurs mis au jour un défaut du corpus de test que trois chapitres de
mesures n'avaient pas détecté.
