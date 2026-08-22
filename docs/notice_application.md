# Notice d'utilisation de l'application

Cette notice s'adresse à la personne qui utilise l'application pour diagnostiquer une
feuille, pas à celle qui l'installe. Pour l'installation et le démarrage, voir le
[README](../README.md).

## Ce que fait l'application, et ce qu'elle ne fait pas

À partir de la photo d'une feuille, l'application propose une maladie parmi dix classes
connues, indique son degré de certitude, montre les zones de l'image qui ont pesé dans la
décision, et affiche une conduite à tenir.

Elle **ne remplace pas** un conseiller agricole ni un service de protection des végétaux.
Elle ne mesure pas la gravité de l'atteinte ni son stade d'évolution, et ne prescrit aucun
produit phytosanitaire. Les recommandations affichées orientent une observation de
terrain, rien de plus.

## Les dix classes reconnues

| Culture | États reconnus |
|---|---|
| Tomate | Saine, Mildiou tardif, Tache bactérienne, Septoriose |
| Maïs | Sain, Rouille commune, Helminthosporiose, Cercosporiose |
| Poivron | Sain, Tache bactérienne |

Ces dix classes sont les seules que le modèle connaît. **Toute autre feuille sera
rapprochée de force de l'une d'entre elles.** Une feuille de manioc, une feuille d'arachide
ou même une photo de chaussure produiront un diagnostic, dépourvu de sens. L'application ne
sait pas dire « je ne connais pas cette plante ».

## Prendre une photo exploitable

C'est le point qui influence le plus le résultat. Le modèle a surtout appris sur des
photographies de studio, feuille détachée sur fond uni, et sa fiabilité chute nettement sur
des photos prises dans un couvert végétal encombré.

À faire :

- une seule feuille par photo, bien à plat
- de près, la feuille remplissant l'essentiel du cadre
- en lumière du jour, sans flash
- sur un fond uni, une planche ou un tissu par exemple

À éviter : les photos floues, les contre-jours, les feuilles encore mouillées, les prises
de vue lointaines et les photos où plusieurs feuilles se chevauchent.

Formats acceptés : JPEG ou PNG, 5 Mo au maximum. Une image d'un autre format ou trop
lourde sera refusée par le service avec un message explicite.

## Obtenir un diagnostic

1. Ouvrir l'application dans le navigateur, à l'adresse `http://localhost:8501`.
2. Vérifier dans la barre latérale que l'état du service est **Opérationnel**. S'il indique
   autre chose, voir la section « Messages d'erreur » plus bas.
3. Déposer la photo dans la zone « Déposer une photo de feuille ».
4. Vérifier l'aperçu, puis cliquer sur **Diagnostiquer**.

Le premier diagnostic après le démarrage peut prendre une dizaine de secondes, le temps que
le modèle se charge en mémoire. Les suivants sont quasi immédiats.

## Lire le résultat

### Le bandeau de diagnostic

Il annonce la maladie retenue et la confiance associée, en pourcentage. Un liseré coloré
rappelle la gravité de la maladie, du vert (aucune) au rouge (élevée).

**Un pourcentage élevé ne signifie pas que le diagnostic est juste.** Le modèle répartit
toujours 100 % de certitude entre les dix classes qu'il connaît, quoi qu'on lui montre. Un
score de 90 % indique seulement qu'il hésite peu, pas qu'il a raison.

### Les deux avertissements

L'application signale deux situations distinctes. Elles n'ont pas la même signification.

**« Diagnostic incertain »** apparaît quand les deux premières hypothèses sont séparées de
moins de 20 points, par exemple 52 % contre 48 %. Ce n'est pas un diagnostic, c'est une
hésitation entre deux maladies. L'application affiche alors les deux fiches côte à côte,
dans deux onglets, pour que vous puissiez trancher vous-même en comparant les symptômes
décrits à ce que vous observez sur la plante.

**« Confiance limitée »** apparaît quand la confiance passe sous **60 %** sans que deux
hypothèses soient à égalité. Les causes habituelles sont une photo floue, mal éclairée ou
prise de trop loin, ou une feuille qui n'appartient à aucune des cultures reconnues. La
bonne réaction est de reprendre la photo avant de conclure.

Ces avertissements existent parce qu'ils ont été mesurés utiles, pas par précaution
rhétorique. Sur 942 photographies de terrain, le réglage retenu divise par près de sept le
nombre de diagnostics faux annoncés sans le moindre signal. **Un avertissement se prend au
sérieux, il ne se contourne pas.**

### Les hypothèses classées

Les trois maladies les plus probables sont affichées avec leur score. Quand les deux
premières sont proches, l'écart se lit d'un coup d'œil sur les barres.

### La carte « Où le modèle a regardé »

La photo d'origine est affichée à gauche, la carte de chaleur à droite.

**Toute la feuille est examinée, sans exception.** Les couleurs n'indiquent pas la zone
analysée, mais ce qui a le plus pesé dans la décision : les zones rouges ont emporté le
diagnostic, les bleues n'ont pratiquement pas compté. Une lésion située ailleurs n'est donc
pas ignorée, elle deviendrait simplement la zone rouge à son tour.

Cette carte sert à vérifier le raisonnement. Si le rouge se pose sur les lésions, le
diagnostic s'appuie sur les bons indices. S'il se concentre sur le fond, sur une ombre ou
sur un doigt, il faut se méfier du résultat et reprendre la photo.

### La conduite à tenir

Chaque maladie dispose d'une fiche : l'agent responsable quand il est connu, les symptômes
à observer, les conditions qui favorisent la maladie, et les mesures à envisager. Ces
mesures restent génériques et indicatives.

## La barre latérale

Elle regroupe trois informations permanentes :

- **État du service** et version du modèle réellement chargée
- **Cultures reconnues**, avec le rappel que toute autre culture donnera un résultat
  dépourvu de sens
- **Fiabilité mesurée**, qui rappelle honnêtement qu'au champ le modèle identifie
  correctement la maladie dans environ un cas sur deux

## Messages d'erreur

| Message | Ce qui se passe | Que faire |
|---|---|---|
| Service injoignable | L'application ne joint pas le service d'inférence | Vérifier que le service tourne sur le port 8000. Hors Docker, il faut le démarrer séparément. |
| Démarré, sans modèle | Le service répond mais aucun modèle n'est chargé | Vérifier que le fichier `.keras` est bien présent dans `models/` |
| Image refusée | Format non accepté, fichier illisible ou trop lourd | Reprendre une photo en JPEG ou PNG, sous 5 Mo |
| Le service n'a pas répondu dans les temps | Le modèle était probablement en cours de chargement | Réessayer une fois après quelques secondes |

## Les limites à garder en tête

Au champ, le modèle se trompe environ une fois sur deux. Ce chiffre est mesuré, pas
supposé : 49,47 % d'exactitude sur 942 photographies prises en conditions réelles, contre
94,36 % sur des photographies de studio. L'application est conçue autour de cette limite,
en signalant ses doutes plutôt qu'en affichant un chiffre rassurant.

En pratique, elle est utile pour orienter une observation et pour attirer l'attention sur
une feuille suspecte. Elle ne suffit pas à décider seule d'un traitement.
