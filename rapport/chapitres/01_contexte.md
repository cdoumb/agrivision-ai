# Contexte et problematique

## Le probleme agricole

Les cultures vivrieres et de rente en Afrique de l'Ouest subissent des pertes
considerables faute de diagnostic precoce des maladies foliaires. Un producteur
eloigne d'un service phytosanitaire ne dispose generalement d'aucun moyen simple
d'identifier une maladie a ses premiers symptomes, alors que la precocite du
diagnostic conditionne directement l'efficacite du traitement et la limitation
de la propagation.

Deux constats renforcent ce probleme sans qu'il soit possible de les chiffrer a
partir des sources dont nous disposons : le delai entre l'apparition des
symptomes et un diagnostic par un conseiller agricole peut etre long lorsque ce
conseiller n'est pas facilement accessible, et le nombre de conseillers
disponibles rapporte au nombre d'exploitations reste, dans beaucoup de regions
d'Afrique de l'Ouest, limite. Nous ne disposons pas de chiffre verifiable pour
ces deux points dans les sources du depot ; nous les mentionnons donc comme
elements de contexte qualitatifs, pas comme donnees mesurees.

## Pourquoi la vision par ordinateur

Le telephone equipe d'un appareil photo est deja present dans une grande partie
des exploitations, ce qui n'est le cas d'aucun autre instrument de diagnostic
specialise. C'est ce constat qui rend la vision par ordinateur pertinente pour
ce contexte precis : elle s'appuie sur un materiel deja possede, plutot que sur
un equipement a acquerir.

Un modele de vision entraine pour cette tache sait attribuer une classe a une
photographie de feuille, avec un niveau de confiance associe. Il ne sait pas, et
ne pretend pas savoir, mesurer la gravite d'une infection, prescrire un
traitement, ou remplacer le jugement d'un conseiller agricole. Cette limite est
posee des ce premier chapitre parce qu'elle encadre tout le reste du projet ; le
chapitre 9 y revient en detail, a la lumiere des mesures effectuees.

## Ce que le projet a construit

AgriVision-AI est une plateforme qui recoit la photographie d'une feuille,
attribue un diagnostic parmi dix classes de maladies, indique un niveau de
confiance, montre par une carte visuelle les zones de l'image qui ont motive la
decision, et propose une conduite a tenir.

Les dix classes retenues couvrent trois cultures : la tomate, le mais et le
poivron. Ce perimetre, precise au chapitre 2, a ete gele le 14 aout 2026 dans le
contrat d'interface qui separe les deux composantes du projet, et n'a plus
bouge depuis.

## La question a laquelle le rapport repond

Un modele qui obtient un excellent resultat sur un jeu de test de laboratoire
est-il pour autant utilisable au champ ? Ce rapport repond non, le mesure, et en
tire les consequences sur la conception de l'application. Cette question
traverse l'ensemble du document : les chapitres 5 et 6 la mesurent, le
chapitre 7 montre ce qui a ete fait pour y repondre, et le chapitre 9 en tire
les limites qui subsistent.

## Organisation du rapport

Le chapitre 2 decrit le corpus et son decoupage. Le chapitre 3 presente
l'architecture de la plateforme et le contrat qui separe les deux binomes. Le
chapitre 4 justifie les choix techniques, du modele au deploiement. Les
chapitres 5 a 7 mesurent les performances du modele, en studio puis au champ, et
presentent la version 2 construite pour repondre a cet ecart. Le chapitre 8
explique les decisions du modele par l'interpretabilite. Le chapitre 9 dresse
les limites connues, et le chapitre 10 propose des pistes pour y repondre.

Le projet est mene par un binome de deux etudiants. Cheick Oumar Doumbia,
binome A, est responsable du corpus, du pretraitement et du service
d'inference ; Faustin Felicien Pikbougoum, binome B, est responsable de
l'entrainement du modele, de l'evaluation, de l'interpretabilite et de
l'application. Cette repartition se retrouve dans l'attribution des chapitres :
les chapitres 1 a 3, la section 4.2 et le chapitre 10 sont rediges par Cheick,
les chapitres 5 a 9 et la section 4.1 par Faustin.