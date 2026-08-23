# Architecture et contrat d'interface

<!--
    CHEICK : chapitre à toi. Environ 3 pages.
    La figure est déjà insérée et se génère par build/schema.py, donc rien à
    faire de ce côté.
    Ce chapitre se termine sur le contrat, ce qui permet au chapitre 4 de
    partir directement sur le choix du modèle qui l'honore.
-->

> A REDIGER: Chapitre 3, à rédiger par Cheick. Le plan proposé figure ci-dessous, la figure est déjà en place.

## Vue d'ensemble

![Architecture de la plateforme, six couches et frontière entre les deux périmètres.](docs/architecture.png)

Points à couvrir :

- Décrire les six couches, de l'acquisition de la photographie jusqu'à l'affichage de la
  recommandation.
- Suivre une photographie de bout en bout : ce qui lui arrive à chaque étape. C'est la
  manière la plus lisible de présenter une architecture, plus que la description couche
  par couche.
- Situer la frontière entre le périmètre du binôme A et celui du binôme B, et dire
  pourquoi elle a été placée là.

## La séparation entre l'application et le service

- Pourquoi l'application ne charge jamais le modèle elle-même.
- Ce que cette séparation permet : changer de modèle sans toucher à l'application,
  remplacer l'interface sans toucher au modèle, tester les deux séparément.
- Ce qu'elle coûte : un appel réseau, une gestion des pannes, un état à afficher quand le
  service ne répond pas.

## Le contrat d'interface

Le contrat est le document qui a permis à deux personnes de travailler en parallèle sans
se bloquer. Il a été gelé au 14 août 2026 et n'a pas bougé depuis.

| Élément | Valeur retenue |
|---|---|
| Formats d'image acceptés | JPEG ou PNG, trois canaux |
| Taille maximale du fichier | 5 Mo |
| Dimension attendue par le modèle | 224 sur 224 pixels |
| Qui redimensionne | Le service, jamais l'application |
| Source de vérité des classes | `classes.json`, jamais recopié en dur |

Tableau: Principales clauses du contrat d'interface.

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/predict` | Reçoit l'image, renvoie le diagnostic complet |
| GET | `/health` | État du service et version du modèle chargé |
| GET | `/classes` | Liste ordonnée des dix classes |

Tableau: Points d'accès du service d'inférence.

Points à couvrir :

- Détailler le format de la réponse de `/predict` : classe retenue, indice, confiance,
  trois premières hypothèses, carte Grad-CAM encodée.
- Expliquer la clause « qui redimensionne » : c'est elle qui garantit qu'une seule chaîne
  de prétraitement existe. Le chapitre 6 montre ce qui arrive quand deux chaînes
  coexistent, entre le notebook et le service.
- Expliquer pourquoi l'ordre des classes est un point de contrat et non un détail : un
  indice décalé transformerait silencieusement chaque diagnostic en un autre.
- Dire ce que le gel du contrat a permis concrètement, avec un exemple : pendant que le
  service se construisait, l'application a pu être développée contre un service simulé
  respectant le même format.

## Ce que le service annonce sur lui-même

- La route `/health` renvoie la version du modèle réellement chargée, déduite du nom du
  fichier, et non une valeur écrite en dur.
- Expliquer pourquoi ce détail compte : un service qui annonce une version en en servant
  une autre rend toute mesure ininterprétable. Le cas s'est présenté pendant le projet et
  a été corrigé ; le chapitre 6 le raconte du point de vue de l'évaluation.

<!--
    SOURCES DISPONIBLES DANS LE DÉPÔT
    - contrat_interface.md, gelé au 14 août
    - docs/api.md, documentation du service
    - docs/architecture.png, produit par build/schema.py
    - src/api/main.py, src/model/inference.py
-->
