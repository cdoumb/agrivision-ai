# Rapport de projet : mode d'emploi

Le rapport se rédige en Markdown, un fichier par chapitre, dans `chapitres/`. Le
document Word final est produit par un script. Personne n'a besoin d'écrire une ligne de
Python.

## Pourquoi pas Word ou Google Docs

Trois raisons, dans l'ordre d'importance.

**Git suit qui écrit quoi.** Un fichier par chapitre, donc aucun conflit possible entre
nous deux, et un historique qui rattache chaque paragraphe à son auteur. La soutenance
comporte une part individuelle : cette traçabilité nous sert.

**La mise en forme est faite une fois pour toutes.** Titres, tableaux, figures, légendes
numérotées, sommaire : le générateur s'en charge de façon identique d'un bout à l'autre.
Un document Word à quatre mains diverge toujours.

**Le style est contrôlé par une machine.** Un script refuse les tirets cadratins, les
apostrophes typographiques, les flèches, les emojis et une liste de tournures qui font
« texte généré automatiquement ». La même règle s'applique aux deux, sans discussion.

## Qui écrit quoi

| Fichier | Chapitre | Qui | État |
|---|---|---|---|
| `01_contexte.md` | Contexte et problématique | Cheick | squelette |
| `02_corpus.md` | Corpus, nettoyage, découpage | Cheick | squelette, tableaux remplis |
| `03_architecture.md` | Architecture et contrat d'interface | Cheick | squelette |
| `04_choix_techniques.md` | Choix techniques | partagé | 4.1 rédigé, 4.2 squelette |
| `05_resultats_studio.md` | Résultats v1 en studio | Faustin | premier jet |
| `06_robustesse.md` | Robustesse studio contre terrain | Faustin | premier jet |
| `07_version_2.md` | La version 2 | Faustin | premier jet |
| `08_interpretabilite.md` | Interprétabilité, Grad-CAM | Faustin | premier jet |
| `09_limites.md` | Limites connues | Faustin | premier jet |
| `10_perspectives.md` | Perspectives | Cheick | squelette |

Le numéro de chapitre vient du nom du fichier. Renommer un fichier suffit à réordonner le
rapport, sans toucher au code.

## Générer le document

```bash
python rapport/build/build_rapport.py
```

Le script refuse de produire quoi que ce soit si le contrôle de style échoue, ou si un
numéro de chapitre manque dans la suite. Il écrit `rapport/AgriVision-AI_Rapport.docx`.

Une fois le fichier ouvert dans Word, faire **Ctrl+A puis F9** pour renseigner le
sommaire. Word ne calcule les tables des matières qu'à la demande.

Pour ne vérifier que le style, sans générer :

```bash
python rapport/build/controle_style.py
```

## La syntaxe utilisable dans les chapitres

Volontairement restreinte. Tout ce qui n'est pas listé ici est traité comme un
paragraphe ordinaire.

| Ce qu'on écrit | Ce que ça donne |
|---|---|
| `# Titre` | Titre du chapitre, une seule fois, en tête du fichier |
| `## Section` | Titre de section, repris dans le sommaire |
| `### Sous-section` | Titre de sous-section, repris dans le sommaire |
| `#### Intertitre` | Petit intertitre, absent du sommaire |
| `- element` | Puce |
| `1. element` | Liste numérotée |
| `**gras**` | Gras |
| `*italique*` | Italique |
| `` `code` `` | Chasse fixe, pour les noms de fichiers et de fonctions |

### Encadrés

```
> RETENIR: le texte de l'encadré
> ATTENTION: le texte de l'encadré
> A REDIGER: signale un trou qui reste à combler
```

Les encadrés « À RÉDIGER » sont volontairement visibles dans le document généré : un trou
doit se voir à la relecture, pas se cacher.

### Tableaux

```
| Classe | F1 |
|---|---|
| Tomate - Saine | 0,986 |
Tableau: La légende, sur la ligne qui suit le tableau.
```

La ligne `Tableau:` est facultative, mais un tableau sans légende n'est pas numéroté et
ne figure pas dans la table des illustrations.

### Figures

```
![La légende de la figure.](reports/matrice_confusion.png)
![Une figure plus étroite.|12](reports/gradcam_exemples.png)
```

Le chemin part de la racine du dépôt. Le nombre après la barre verticale est la largeur
en centimètres, 15 par défaut. Une figure introuvable ne fait pas échouer la génération :
elle laisse un encadré visible dans le document et un avertissement dans la console.

### Commentaires

```
<!-- Ce texte n'apparaît pas dans le document final. -->
```

Utilisés dans les squelettes pour les consignes de rédaction et les rappels de sources.

## Règles de rédaction

**Aucun chiffre ne vient de mémoire.** Tout chiffre cité doit exister dans un fichier de
`reports/`. En cas de doute sur une valeur, demander plutôt que de recopier le README,
qui est un résumé et non une source.

**Pas de tiret cadratin, pas d'apostrophe typographique.** Le contrôle de style les
refuse, mais autant les éviter en écrivant.

**Une phrase par idée.** Le générateur ne rattrape pas une phrase de six lignes.

**Les renvois entre chapitres se font par leur numéro**, par exemple « le chapitre 6 le
mesure ». Ne pas renvoyer à un numéro de page : il change à chaque génération.

## Calendrier

| Quand | Quoi |
|---|---|
| 27 août au soir | Brouillons complets des deux côtés, poussés sur `main` |
| 28 août | Relecture croisée, chasse aux contradictions de chiffres |
| 29 août au matin | Génération finale et relecture du document en entier |
| 29 après-midi et 30 | Marge |
