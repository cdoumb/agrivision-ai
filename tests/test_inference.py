"""
Tests du module d'inférence — AgriVision-AI (Binôme B).

Usage :
  pip install pytest
  pytest tests/test_inference.py -v

Les tests qui ont besoin du modèle sont ignorés automatiquement si le fichier
.keras est absent (il n'est pas versionné dans Git, cf. .gitignore). Le reste
s'exécute partout, y compris en intégration continue.
"""
import base64
import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from model import inference  # noqa: E402

modele_requis = pytest.mark.skipif(
    not inference.CHEMIN_MODELE.exists(),
    reason=f"modèle absent ({inference.CHEMIN_MODELE}), récupérable sur le Drive partagé",
)


def feuille_jpeg(taille=(400, 300), couleur=(40, 120, 30)):
    """Fabrique une image JPEG valide, sans dépendre d'un fichier sur disque."""
    tampon = io.BytesIO()
    Image.new("RGB", taille, couleur).save(tampon, format="JPEG")
    return tampon.getvalue()


# ---------------------------------------------------------------------------
# Libellés : le contrat impose classes.json comme source unique
# ---------------------------------------------------------------------------

def test_dix_classes_dans_l_ordre():
    classes = inference._charger_classes()
    assert len(classes) == 10
    assert [c["index"] for c in classes] == list(range(10))


def test_libelles_conformes_au_contrat():
    classes = inference._charger_classes()
    # exemple donné en section 4 du contrat d'interface
    assert classes[1]["label"] == "Tomate - Mildiou tardif"
    # les accents doivent survivre : ils partent tels quels dans l'API
    assert classes[4]["label"] == "Maïs - Sain"
    assert classes[2]["label"] == "Tomate - Tache bactérienne"


# ---------------------------------------------------------------------------
# Prétraitement : c'est le service qui redimensionne, cf. section 2 du contrat
# ---------------------------------------------------------------------------

def test_redimensionnement_en_224():
    tableau, image = inference.preparer_image(feuille_jpeg())
    assert tableau.shape == (1, 224, 224, 3)
    assert image.size == (224, 224)


def test_valeurs_non_normalisees():
    """La normalisation est intégrée au modèle : on lui passe bien du 0-255."""
    tableau, _ = inference.preparer_image(feuille_jpeg(couleur=(255, 255, 255)))
    assert tableau.dtype == np.float32
    assert tableau.max() > 1.0


def test_png_transparent_converti_en_rgb():
    tampon = io.BytesIO()
    Image.new("RGBA", (200, 200), (10, 200, 10, 90)).save(tampon, format="PNG")
    tableau, image = inference.preparer_image(tampon.getvalue())
    assert image.mode == "RGB"
    assert tableau.shape[-1] == 3


def test_image_en_niveaux_de_gris_acceptee():
    tampon = io.BytesIO()
    Image.new("L", (200, 200), 128).save(tampon, format="JPEG")
    tableau, _ = inference.preparer_image(tampon.getvalue())
    assert tableau.shape == (1, 224, 224, 3)


# ---------------------------------------------------------------------------
# Carte de chaleur
# ---------------------------------------------------------------------------

def test_palette_va_du_bleu_au_rouge():
    couleurs = inference._coloriser(np.array([0.0, 1.0], dtype=np.float32))
    froid, chaud = couleurs[0], couleurs[1]
    assert froid[2] > froid[0]   # bleu dominant en bas d'échelle
    assert chaud[0] > chaud[2]   # rouge dominant en haut


def test_palette_ecrete_les_valeurs_hors_bornes():
    couleurs = inference._coloriser(np.array([-5.0, 12.0], dtype=np.float32))
    assert couleurs.shape == (2, 3)
    assert couleurs.min() >= 0.0 and couleurs.max() <= 1.0


def test_superposition_produit_un_png_base64_de_meme_taille():
    _, image = inference.preparer_image(feuille_jpeg())
    carte = np.zeros((7, 7), dtype=np.float32)
    carte[3, 3] = 1.0

    encode = inference.superposer_gradcam(carte, image)
    rendu = Image.open(io.BytesIO(base64.b64decode(encode)))

    assert rendu.format == "PNG"
    assert rendu.size == image.size


def test_la_zone_chaude_ressort_en_rouge():
    _, image = inference.preparer_image(feuille_jpeg())
    carte = np.zeros((7, 7), dtype=np.float32)
    carte[3, 3] = 1.0

    rendu = Image.open(io.BytesIO(base64.b64decode(inference.superposer_gradcam(carte, image))))
    pixels = np.asarray(rendu, dtype=np.float32)

    assert pixels[112, 112][0] > pixels[3, 3][0]   # centre plus rouge que le coin
    assert pixels[3, 3][2] > pixels[112, 112][2]   # coin plus bleu que le centre


# ---------------------------------------------------------------------------
# Diagnostic complet — nécessite le modèle
# ---------------------------------------------------------------------------

@modele_requis
def test_reponse_conforme_au_contrat():
    resultat = inference.diagnostiquer(feuille_jpeg())

    attendus = {"predicted_class", "class_index", "confidence",
                "top3", "gradcam_base64", "model_version"}
    assert set(resultat) == attendus
    assert resultat["model_version"] == "mobilenetv2-v1.0"


@modele_requis
def test_indice_et_libelle_coherents():
    resultat = inference.diagnostiquer(feuille_jpeg(), avec_gradcam=False)
    classes = inference._charger_classes()
    assert 0 <= resultat["class_index"] <= 9
    assert resultat["predicted_class"] == classes[resultat["class_index"]]["label"]


@modele_requis
def test_top3_trie_et_coherent_avec_la_prediction():
    resultat = inference.diagnostiquer(feuille_jpeg(), avec_gradcam=False)
    top3 = resultat["top3"]

    assert len(top3) == 3
    scores = [h["score"] for h in top3]
    assert scores == sorted(scores, reverse=True)
    # la meilleure hypothèse doit être la classe annoncée
    assert top3[0]["class_index"] == resultat["class_index"]
    assert top3[0]["score"] == resultat["confidence"]


@modele_requis
def test_confiance_est_une_probabilite():
    resultat = inference.diagnostiquer(feuille_jpeg(), avec_gradcam=False)
    assert 0.0 <= resultat["confidence"] <= 1.0


@modele_requis
def test_gradcam_est_un_png_decodable():
    resultat = inference.diagnostiquer(feuille_jpeg())
    rendu = Image.open(io.BytesIO(base64.b64decode(resultat["gradcam_base64"])))
    assert rendu.format == "PNG"
    assert rendu.size == (224, 224)


@modele_requis
def test_gradcam_desactivable():
    resultat = inference.diagnostiquer(feuille_jpeg(), avec_gradcam=False)
    assert resultat["gradcam_base64"] is None


@modele_requis
def test_deux_appels_donnent_le_meme_resultat():
    """
    Le réseau contient des couches d'augmentation et un dropout, actifs
    uniquement à l'entraînement. S'ils fuyaient en inférence, deux appels
    identiques donneraient deux diagnostics différents.
    """
    octets = feuille_jpeg()
    premier = inference.diagnostiquer(octets, avec_gradcam=False)
    second = inference.diagnostiquer(octets, avec_gradcam=False)
    assert premier == second


def test_surcharge_explicite_fait_autorite(monkeypatch):
    """
    Un chemin donné par AGRIVISION_MODELE ne doit pas être complété par une
    recherche de repli : sinon un chemin erroné ferait charger silencieusement
    une autre version du modèle que celle demandée.
    """
    monkeypatch.setenv("AGRIVISION_MODELE", "/chemin/qui/n/existe/pas.keras")
    candidats = inference._emplacements_candidats()
    assert len(candidats) == 1
    assert inference._trouver_modele() is None


def test_recherche_de_repli_sans_surcharge(monkeypatch):
    monkeypatch.delenv("AGRIVISION_MODELE", raising=False)
    candidats = inference._emplacements_candidats()
    assert len(candidats) > 1


@modele_requis
def test_modele_charge_une_seule_fois():
    inference.diagnostiquer(feuille_jpeg(), avec_gradcam=False)
    assert inference.est_charge()
    reference = inference._etat["modele"]
    inference.diagnostiquer(feuille_jpeg(), avec_gradcam=False)
    assert inference._etat["modele"] is reference
