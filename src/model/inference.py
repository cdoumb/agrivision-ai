"""
Module d'inférence AgriVision-AI (Binôme B).

Contient tout ce qui touche au modèle : chargement, prédiction, et génération
de la carte Grad-CAM. Volontairement indépendant de FastAPI, pour trois raisons :
il se teste sans lancer de serveur, il se réutilise tel quel dans un notebook,
et le service (lot A) n'a qu'un appel à faire.

Utilisation depuis le service :

    from model.inference import diagnostiquer

    resultat = diagnostiquer(contenu_octets)   # -> dict au format du contrat

Le modèle est chargé une seule fois, au premier appel, puis gardé en mémoire.
"""
import base64
import io
import json
import os
import re
import threading
from pathlib import Path

import numpy as np
from PIL import Image

# TensorFlow est importé paresseusement : il met plusieurs secondes à se charger
# et le module doit rester importable (pour les tests de format) sans lui.
_tf = None


def _tensorflow():
    global _tf
    if _tf is None:
        import tensorflow as tf
        _tf = tf
    return _tf


RACINE_MODULE = Path(__file__).resolve().parent

# Le v2 est entraîné sur PlantVillage et PlantWild, alors que le v1 ne
# connaissait que le studio. Sur 942 photographies de terrain, le nombre de
# diagnostics faux annoncés sans le moindre avertissement passe de 403 à 61.
# Le v1 reste chargeable en pointant AGRIVISION_MODELE dessus.
NOM_FICHIER_MODELE = "mobilenetv2_v2.keras"


def _emplacements_candidats():
    """
    Endroits où chercher le fichier .keras, du plus explicite au plus général.

    Le modèle n'est pas versionné dans Git (23 Mo), il se transmet par le Drive
    partagé. Il n'est donc pas toujours au même endroit selon qu'on lance le
    service en local ou dans le conteneur, d'où cette liste plutôt qu'un chemin
    figé.
    """
    # Une consigne explicite fait autorité : si AGRIVISION_MODELE est défini,
    # on n'ira pas chercher ailleurs. Sinon, le jour où une v2 du modèle sera
    # déployée, un chemin erroné ferait charger l'ancienne version en silence.
    surcharge = os.environ.get("AGRIVISION_MODELE")
    if surcharge:
        return [Path(surcharge)]

    candidats = []
    candidats.append(RACINE_MODULE / NOM_FICHIER_MODELE)          # à côté du code
    candidats.append(Path("/app/models") / NOM_FICHIER_MODELE)    # volume Docker

    # models/ à la racine du dépôt, convention retenue avec le lot A
    for dossier in RACINE_MODULE.parents:
        candidats.append(dossier / "models" / NOM_FICHIER_MODELE)
        if (dossier / "classes.json").exists():
            break

    return candidats


def _trouver_modele():
    for candidat in _emplacements_candidats():
        if candidat.exists():
            return candidat
    return None


# Résolu au chargement, mais re-cherché à chaque appel de charger() : en Docker
# le volume peut être monté après l'import du module.
CHEMIN_MODELE = _trouver_modele() or (RACINE_MODULE / NOM_FICHIER_MODELE)

TAILLE_ENTREE = 224


def version_depuis_chemin(chemin):
    """
    Déduit la version annoncée du nom du fichier chargé.

    Cette valeur était autrefois une constante. Elle mentait dès qu'on pointait
    AGRIVISION_MODELE sur une autre version : /health annonçait le v2 en servant
    les poids du v1, et le script d'évaluation comparait le terrain d'un modèle
    au studio de l'autre. Rien ne le signalait, puisque aucune erreur ne se
    produit dans ce cas.
    """
    correspondance = re.match(r"^([a-z0-9]+)_v(\d+)$", Path(chemin).stem.lower())
    if not correspondance:
        return "inconnu"
    architecture, numero = correspondance.groups()
    return f"{architecture}-v{numero}.0"


VERSION_MODELE = version_depuis_chemin(CHEMIN_MODELE)

# Chargement protégé par un verrou : sans lui, deux requêtes simultanées
# arrivant sur un service fraîchement démarré chargeraient le modèle deux fois.
_verrou = threading.Lock()
_etat = {"modele": None, "base": None, "tete": None, "classes": None}


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------

def _trouver_classes_json(depart: Path) -> Path:
    """Cherche classes.json en remontant l'arborescence (même logique que le service)."""
    for dossier in [depart, *depart.parents]:
        candidat = dossier / "classes.json"
        if candidat.exists():
            return candidat
    raise FileNotFoundError(f"classes.json introuvable en remontant depuis {depart}")


def _charger_classes():
    """
    Libellés lus depuis classes.json, source unique imposée par le contrat.

    On ne recopie jamais la liste ici : si elle change, elle doit changer à un
    seul endroit.
    """
    with open(_trouver_classes_json(RACINE_MODULE), encoding="utf-8") as f:
        classes = json.load(f)["classes"]
    classes.sort(key=lambda c: c["index"])
    return [{"index": c["index"], "label": f"{c['culture']} - {c['etat']}"} for c in classes]


def _decouper_modele(modele):
    """
    Sépare le réseau en deux morceaux, nécessaires au Grad-CAM.

    Le réseau entraîné a cette forme :

        entrée -> augmentation -> preprocess_input -> MobileNetV2 -> tête -> 10 sorties

    MobileNetV2 y est un sous-modèle imbriqué, donc `get_layer("out_relu")`
    échoue depuis le modèle principal : la couche n'est pas au premier niveau.
    Comme MobileNetV2 est instancié sans sa tête de classification, sa sortie
    EST celle de `out_relu`, ce qui évite d'aller la chercher à l'intérieur.

    Renvoie (extracteur, tête) :
      - extracteur : image **déjà normalisée** -> cartes (7, 7, 1280)
      - tête       : cartes de caractéristiques -> 10 probabilités

    Deux pièges, tous deux rencontrés en vrai :

    L'extracteur est le sous-modèle MobileNetV2 brut, et la normalisation doit
    donc être appliquée avant de l'appeler. On pourrait croire qu'il suffit de
    rejouer les couches situées avant lui, mais Keras 3 ne fait pas figurer
    `preprocess_input` dans `layers` : c'est une opération, pas un objet Layer.
    La rejouer ainsi sauterait la normalisation en silence, et le réseau
    recevrait des valeurs de 0 à 255 au lieu de -1 à 1.

    La tête, elle, est reconstruite en suivant les connexions réelles du
    graphe et non en enchaînant les couches l'une après l'autre. Le modèle v2
    place un pooling moyen et un pooling maximum en parallèle avant de les
    concaténer, ce qu'un simple enchaînement ne sait pas reproduire.
    """
    tf = _tensorflow()

    indice_base = None
    for i, couche in enumerate(modele.layers):
        if isinstance(couche, tf.keras.Model) and "mobilenet" in couche.name.lower():
            indice_base = i
            break
    if indice_base is None:
        raise RuntimeError(
            "Sous-modèle MobileNetV2 introuvable dans le réseau chargé. "
            "Le modèle vient-il bien des notebooks du projet ?"
        )

    extracteur = modele.layers[indice_base]
    base = extracteur

    # La tête, elle, peut se ramifier. On note quelle couche produit quel
    # tenseur, puis on rebranche chacune sur ses véritables entrées. Un tenseur
    # qu'aucune couche de la tête ne produit vient forcément de la base.
    couches_tete = modele.layers[indice_base + 1:]
    producteur = {}
    for couche in couches_tete:
        for tenseur in tf.nest.flatten(couche.output):
            producteur[id(tenseur)] = couche.name

    entree_tete = tf.keras.Input(shape=base.output.shape[1:], name="caracteristiques")
    reconstruits = {}
    sortie = entree_tete

    for couche in couches_tete:
        entrees = []
        for tenseur in tf.nest.flatten(couche.input):
            nom = producteur.get(id(tenseur))
            entrees.append(reconstruits[nom] if nom else entree_tete)
        sortie = couche(entrees[0] if len(entrees) == 1 else entrees)
        reconstruits[couche.name] = sortie

    tete = tf.keras.Model(entree_tete, sortie, name="tete_classification")
    return extracteur, tete


def charger(force=False):
    """
    Charge le modèle et prépare les morceaux nécessaires au Grad-CAM.

    Appelé automatiquement au premier diagnostic. Peut être appelé explicitement
    au démarrage du service pour que la première requête ne paie pas l'attente.
    """
    global CHEMIN_MODELE

    with _verrou:
        if _etat["modele"] is not None and not force:
            return _etat

        chemin = _trouver_modele()
        if chemin is None:
            emplacements = "\n  ".join(str(c) for c in _emplacements_candidats())
            raise FileNotFoundError(
                f"Modèle {NOM_FICHIER_MODELE} introuvable. Cherché dans :\n  {emplacements}\n"
                "Le fichier .keras n'est pas versionné dans Git (23 Mo). Le récupérer "
                "sur le Drive partagé et le placer dans models/ à la racine du dépôt, "
                "ou définir la variable d'environnement AGRIVISION_MODELE."
            )
        CHEMIN_MODELE = chemin

        tf = _tensorflow()
        modele = tf.keras.models.load_model(chemin)
        extracteur, tete = _decouper_modele(modele)

        _etat.update({
            "modele": modele,
            "base": extracteur,
            "tete": tete,
            "classes": _charger_classes(),
        })
        return _etat


def est_charge():
    """Indique si le modèle est déjà en mémoire (utile pour /health)."""
    return _etat["modele"] is not None


# ---------------------------------------------------------------------------
# Prétraitement
# ---------------------------------------------------------------------------

def preparer_image(contenu: bytes):
    """
    Transforme les octets reçus en tableau prêt pour le réseau.

    Renvoie (tableau_224, image_pil_224) : le premier pour le modèle, le second
    pour superposer la carte de chaleur.

    Conformément au contrat d'interface, c'est bien ici, côté service, que le
    redimensionnement a lieu. La normalisation des valeurs, elle, est intégrée
    au modèle : on lui passe donc des valeurs de 0 à 255 telles quelles.
    """
    image = Image.open(io.BytesIO(contenu))
    image = image.convert("RGB")  # écarte le canal alpha des PNG et les niveaux de gris
    image = image.resize((TAILLE_ENTREE, TAILLE_ENTREE), Image.BILINEAR)
    tableau = np.asarray(image, dtype=np.float32)
    return tableau[np.newaxis, ...], image


# ---------------------------------------------------------------------------
# Carte de chaleur
# ---------------------------------------------------------------------------

# Points de contrôle d'une palette allant du bleu (zone ignorée) au rouge
# (zone décisive). Recodée à la main plutôt qu'importée de matplotlib, qui
# n'a pas sa place dans l'image Docker du service.
_PALETTE = np.array([
    [0.0, 0.0, 0.5],
    [0.0, 0.0, 1.0],
    [0.0, 1.0, 1.0],
    [1.0, 1.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.5, 0.0, 0.0],
], dtype=np.float32)


def _coloriser(carte: np.ndarray) -> np.ndarray:
    """Applique la palette à une carte de valeurs entre 0 et 1."""
    positions = np.clip(carte, 0.0, 1.0) * (len(_PALETTE) - 1)
    bas = np.floor(positions).astype(int)
    haut = np.minimum(bas + 1, len(_PALETTE) - 1)
    fraction = (positions - bas)[..., np.newaxis]
    return _PALETTE[bas] * (1 - fraction) + _PALETTE[haut] * fraction


def calculer_gradcam(tableau: np.ndarray, indice_classe: int) -> np.ndarray:
    """
    Calcule la carte Grad-CAM pour une classe donnée.

    Principe : on regarde de combien le score de la classe prédite varierait si
    chacune des 1 280 cartes de caractéristiques finales changeait un peu. Les
    cartes qui pèsent le plus reçoivent le plus de poids, et leur somme
    pondérée indique les zones de l'image qui ont emporté la décision.

    Renvoie une carte 7x7 avec des valeurs entre 0 et 1.
    """
    tf = _tensorflow()
    etat = charger()

    # L'extracteur est le MobileNetV2 brut : la normalisation doit être
    # appliquée ici, elle ne fait pas partie du sous-modèle.
    entree = tf.keras.applications.mobilenet_v2.preprocess_input(tf.identity(tableau))

    with tf.GradientTape() as bande:
        caracteristiques = etat["base"](entree, training=False)
        bande.watch(caracteristiques)
        predictions = etat["tete"](caracteristiques, training=False)
        score = predictions[:, indice_classe]

    gradients = bande.gradient(score, caracteristiques)
    poids = tf.reduce_mean(gradients, axis=(0, 1, 2))       # importance de chaque carte
    carte = tf.reduce_sum(caracteristiques[0] * poids, axis=-1)
    carte = tf.nn.relu(carte)                                # seules les contributions positives

    carte = carte.numpy()
    maximum = carte.max()
    if maximum > 0:
        carte = carte / maximum
    return carte


def superposer_gradcam(carte: np.ndarray, image: Image.Image, intensite=0.45) -> str:
    """
    Superpose la carte de chaleur à la photo et renvoie un PNG encodé en base64.

    Le base64 est imposé par le contrat d'interface : il permet de transporter
    une image dans un champ texte du JSON, sans second appel réseau.
    """
    # Un tableau 2D d'octets est interprété en niveaux de gris : préciser
    # mode="L" est inutile et Pillow 13 supprimera le paramètre.
    carte_image = Image.fromarray((carte * 255).astype(np.uint8))
    carte_image = carte_image.resize(image.size, Image.BICUBIC)

    chaleur = _coloriser(np.asarray(carte_image, dtype=np.float32) / 255.0)
    chaleur = (chaleur * 255).astype(np.uint8)

    fond = np.asarray(image, dtype=np.float32)
    melange = fond * (1 - intensite) + chaleur.astype(np.float32) * intensite
    resultat = Image.fromarray(np.clip(melange, 0, 255).astype(np.uint8))

    tampon = io.BytesIO()
    resultat.save(tampon, format="PNG", optimize=True)
    return base64.b64encode(tampon.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def diagnostiquer(contenu: bytes, avec_gradcam=True) -> dict:
    """
    Diagnostic complet à partir des octets d'une image.

    Renvoie exactement la structure définie en section 4 du contrat d'interface :
    predicted_class, class_index, confidence, top3, gradcam_base64, model_version.

    `avec_gradcam=False` saute la carte de chaleur, qui coûte une passe de
    gradients supplémentaire. Utile pour les tests et le traitement par lots.
    """
    tf = _tensorflow()
    etat = charger()

    tableau, image = preparer_image(contenu)

    entree = tf.keras.applications.mobilenet_v2.preprocess_input(tf.identity(tableau))
    caracteristiques = etat["base"](entree, training=False)
    probabilites = etat["tete"](caracteristiques, training=False).numpy()[0]

    classes = etat["classes"]
    indice = int(np.argmax(probabilites))

    ordre = np.argsort(probabilites)[::-1][:3]
    top3 = [
        {
            "class_index": int(i),
            "label": classes[int(i)]["label"],
            "score": round(float(probabilites[i]), 4),
        }
        for i in ordre
    ]

    gradcam = None
    if avec_gradcam:
        carte = calculer_gradcam(tableau, indice)
        gradcam = superposer_gradcam(carte, image)

    return {
        "predicted_class": classes[indice]["label"],
        "class_index": indice,
        "confidence": round(float(probabilites[indice]), 4),
        "top3": top3,
        "gradcam_base64": gradcam,
        "model_version": VERSION_MODELE,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage : python src/model/inference.py chemin/vers/une_photo.jpg")
        raise SystemExit(2)

    with open(sys.argv[1], "rb") as f:
        octets = f.read()

    resultat = diagnostiquer(octets)
    apercu = dict(resultat)
    apercu["gradcam_base64"] = (
        f"<PNG base64, {len(resultat['gradcam_base64'])} caractères>"
        if resultat["gradcam_base64"] else None
    )
    print(json.dumps(apercu, ensure_ascii=False, indent=2))
