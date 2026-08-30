# Contexte et problématique

## Le problème agricole

Les cultures vivrières et de rente en Afrique de l'Ouest subissent des pertes
considérables faute de diagnostic précoce des maladies foliaires. Un producteur
éloigné d'un service phytosanitaire ne dispose généralement d'aucun moyen simple
d'identifier une maladie à ses premiers symptômes, alors que la précocité du
diagnostic conditionne directement l'efficacité du traitement et la limitation
de la propagation.

Deux constats renforcent ce problème sans qu'il soit possible de les chiffrer à
partir des sources dont nous disposons : le délai entre l'apparition des
symptômes et un diagnostic par un conseiller agricole peut être long lorsque ce
conseiller n'est pas facilement accessible, et le nombre de conseillers
disponibles rapporté au nombre d'exploitations reste, dans beaucoup de régions
d'Afrique de l'Ouest, limité. Nous ne disposons pas de chiffre vérifiable pour
ces deux points dans les sources du dépôt ; nous les mentionnons donc comme
éléments de contexte qualitatifs, pas comme données mesurées.

Ce refus d'avancer un chiffre demande à être justifié, car il serait facile d'en
citer un. Une maladie foliaire évolue sur quelques jours, et la fenêtre pendant
laquelle un traitement reste utile se referme vite. Un diagnostic qui arrive
après cette fenêtre ne coûte pas seulement la parcelle atteinte : il laisse le
temps à la maladie de gagner les rangs voisins, si bien que le retard se paie
deux fois. C'est ce mécanisme, et non un pourcentage de pertes, qui motive le
projet. Un chiffre de pertes cité sans source vérifiable donnerait au rapport
une apparence de rigueur qu'il n'aurait pas, et le chapitre 6 montre assez ce
que coûte une mesure prise pour argent comptant.

## Pourquoi la vision par ordinateur

Le téléphone équipé d'un appareil photo est déjà présent dans une grande partie
des exploitations, ce qui n'est le cas d'aucun autre instrument de diagnostic
spécialisé. C'est ce constat qui rend la vision par ordinateur pertinente pour
ce contexte précis : elle s'appuie sur un matériel déjà possédé, plutôt que sur
un équipement à acquérir.

Un modèle de vision entraîné pour cette tâche sait attribuer une classe à une
photographie de feuille, avec un niveau de confiance associé. Il ne sait pas, et
ne prétend pas savoir, mesurer la gravité d'une infection, prescrire un
traitement, ou remplacer le jugement d'un conseiller agricole. Cette limite est
posée dès ce premier chapitre parce qu'elle encadre tout le reste du projet ; le
chapitre 9 y revient en détail, à la lumière des mesures effectuées.

Le choix du support n'est pas neutre non plus. Un diagnostic qui suppose
d'envoyer un échantillon à un laboratoire suppose aussi un transport, un délai
et un coût, c'est-à-dire exactement les trois obstacles que le projet cherche à
lever. Une photographie prise sur place et analysée en quelques secondes
supprime les trois d'un coup, à condition que le traitement reste accessible
depuis un appareil ordinaire. Cette contrainte a orienté des décisions
techniques concrètes, décrites au chapitre 4 : le modèle retenu tient en
26 mégaoctets et répond en une fraction de seconde sur un processeur sans carte
graphique, là où une architecture plus précise aurait exigé un serveur dédié.
La performance brute n'a donc pas été le seul critère, et le chapitre 4 assume
ce compromis plutôt que de le taire.

## Ce que le projet a construit

AgriVision-AI est une plateforme qui reçoit la photographie d'une feuille,
attribue un diagnostic parmi dix classes de maladies, indique un niveau de
confiance, montre par une carte visuelle les zones de l'image qui ont motivé la
décision, et propose une conduite à tenir.

Les dix classes retenues couvrent trois cultures : la tomate, le maïs et le
poivron. Ce périmètre, précisé au chapitre 2, a été gelé le 14 août 2026 dans le
contrat d'interface qui sépare les deux composantes du projet, et n'a plus
bougé depuis.

## La question à laquelle le rapport répond

Un modèle qui obtient un excellent résultat sur un jeu de test de laboratoire
est-il pour autant utilisable au champ ? Ce rapport répond non, le mesure, et en
tire les conséquences sur la conception de l'application. Cette question
traverse l'ensemble du document : les chapitres 5 et 6 la mesurent, le
chapitre 7 montre ce qui a été fait pour y répondre, et le chapitre 9 en tire
les limites qui subsistent.

## Organisation du rapport

Le chapitre 2 décrit le corpus et son découpage. Le chapitre 3 présente
l'architecture de la plateforme et le contrat qui sépare les deux binômes. Le
chapitre 4 justifie les choix techniques, du modèle au déploiement. Les
chapitres 5 à 7 mesurent les performances du modèle, en studio puis au champ, et
présentent la version 2 construite pour répondre à cet écart. Le chapitre 8
explique les décisions du modèle par l'interprétabilité. Le chapitre 9 dresse
les limites connues, et le chapitre 10 propose des pistes pour y répondre.

Le projet est mené par un binôme de deux étudiants. Cheick Oumar Doumbia,
binôme A, est responsable du corpus, du prétraitement et du service
d'inférence ; Faustin Félicien Pikbougoum, binôme B, est responsable de
l'entraînement du modèle, de l'évaluation, de l'interprétabilité et de
l'application. Cette répartition se retrouve dans l'attribution des chapitres :
les chapitres 1 à 3, la section 4.2 et le chapitre 10 sont rédigés par Cheick,
les chapitres 5 à 9 et la section 4.1 par Faustin.
