"""
Application de diagnostic AgriVision-AI (Binôme B).

Remplace le squelette de validation du Binôme A. L'application ne contient
aucune logique de modèle : elle envoie l'image au service d'inférence et met
en forme la réponse définie par contrat_interface.md.

Un parti pris guide tout l'affichage : montrer le doute plutôt que le masquer.
Un diagnostic annoncé à 52 % contre 48 % n'est pas un diagnostic, c'est une
hésitation entre deux maladies, et l'utilisateur doit le voir immédiatement.

Lancement :
    streamlit run src/app/main.py
"""
import base64
import json
import os
from pathlib import Path

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")
RACINE = Path(__file__).resolve().parent
DELAI_DIAGNOSTIC = 60  # secondes ; le premier appel peut réveiller le service

# En dessous de ce seuil, le diagnostic est présenté comme incertain.
#
# La valeur n'est pas choisie au hasard : elle a été réglée en mesurant, sur
# 942 photographies de terrain, ce que l'utilisateur voit vraiment. Avec le
# modèle v1 et un seuil à 0,70, l'application affirmait 672 diagnostics dont
# 403 faux, soit une fiabilité de 40 % quand elle se prononçait. Avec le v2 à
# 0,60, elle se prononce moins souvent mais a raison dans 72 % des cas, et le
# nombre de diagnostics faux annoncés sans avertissement tombe à 61.
#
# Le v2 produit des probabilités plus basses que le v1, parce qu'il a été
# entraîné avec un lissage des étiquettes : conserver 0,70 l'aurait rendu
# muet dans 85 % des cas.
SEUIL_CONFIANCE_FAIBLE = 0.60
# Écart minimal entre les deux premières hypothèses pour trancher franchement.
ECART_MINIMAL = 0.20

COULEURS_GRAVITE = {
    "aucune": "#2e7d32",
    "modérée": "#ef6c00",
    "modérée à élevée": "#e65100",
    "élevée": "#c62828",
}


st.set_page_config(
    page_title="AgriVision-AI",
    page_icon="🌿",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Données et service
# ---------------------------------------------------------------------------

@st.cache_data
def charger_recommandations():
    with open(RACINE / "recommandations.json", encoding="utf-8") as f:
        contenu = json.load(f)
    return contenu["recommandations"], contenu["_avertissement"]


def interroger_sante():
    """Renvoie l'état du service, ou None s'il est injoignable."""
    try:
        reponse = requests.get(f"{API_URL}/health", timeout=5)
        reponse.raise_for_status()
        return reponse.json()
    except requests.exceptions.RequestException:
        return None


def recuperer_classes():
    try:
        reponse = requests.get(f"{API_URL}/classes", timeout=5)
        reponse.raise_for_status()
        return reponse.json()
    except requests.exceptions.RequestException:
        return None


def demander_diagnostic(fichier):
    """
    Envoie l'image au service. Renvoie (resultat, message_erreur).

    L'image part telle quelle : c'est le service qui redimensionne, comme
    l'impose la section 2 du contrat d'interface.
    """
    fichiers = {"file": (fichier.name, fichier.getvalue(), fichier.type)}
    try:
        reponse = requests.post(f"{API_URL}/predict", files=fichiers, timeout=DELAI_DIAGNOSTIC)
    except requests.exceptions.Timeout:
        return None, ("Le service n'a pas répondu dans les temps. S'il vient de démarrer, "
                      "le chargement du modèle prend une dizaine de secondes : réessayer.")
    except requests.exceptions.RequestException as erreur:
        return None, f"Service d'inférence injoignable ({API_URL}) : {erreur}"

    if reponse.status_code == 200:
        return reponse.json(), None

    try:
        detail = reponse.json().get("detail", reponse.text)
    except ValueError:
        detail = reponse.text

    if reponse.status_code == 400:
        return None, f"Image refusée : {detail}"
    if reponse.status_code == 503:
        return None, (f"Le service fonctionne mais aucun modèle n'est chargé. {detail}")
    return None, f"Erreur du service (code {reponse.status_code}) : {detail}"


# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

def afficher_barre_laterale():
    with st.sidebar:
        st.subheader("État du service")

        sante = interroger_sante()
        if sante is None:
            st.error("Injoignable")
            st.caption(f"Adresse interrogée : {API_URL}")
            st.caption("Si l'application tourne hors Docker, vérifier que le service "
                       "est démarré sur le port 8000.")
        elif sante.get("model_loaded"):
            st.success("Opérationnel")
            st.caption(f"Modèle : {sante.get('model_version', 'inconnu')}")
        else:
            st.warning("Démarré, sans modèle")
            st.caption("Le service répond mais ne peut pas diagnostiquer. "
                       "Le fichier .keras est-il bien dans models/ ?")

        classes = recuperer_classes()
        if classes:
            st.subheader(f"Cultures reconnues ({len(classes)})")
            par_culture = {}
            for classe in classes:
                par_culture.setdefault(classe["culture"], []).append(classe["etat"])
            for culture, etats in par_culture.items():
                st.markdown(f"**{culture}**")
                for etat in etats:
                    st.caption(f"· {etat}")

        st.divider()
        st.caption("Toute autre culture ou maladie sera rapprochée de force de l'une "
                   "de ces classes. Le diagnostic n'a alors aucun sens.")

        st.divider()
        st.subheader("Fiabilité mesurée")
        st.caption(
            "Le modèle a été entraîné sur des photographies de studio, complétées "
            "par des images de terrain. Sa fiabilité dépend fortement des conditions "
            "de prise de vue.\n\n"
            "Sur un corpus de 942 photographies prises au champ, il identifie "
            "correctement la maladie dans environ un cas sur deux. C'est pourquoi "
            "l'application signale explicitement les diagnostics dont elle n'est pas "
            "sûre : **un avertissement doit être pris au sérieux, pas contourné**.\n\n"
            "Une photo nette, cadrée sur une seule feuille à plat et sur fond uni "
            "améliore nettement le résultat."
        )


def afficher_verdict(resultat, recommandation):
    """Diagnostic principal, avec le niveau de certitude rendu explicite."""
    confiance = resultat["confidence"]
    top3 = resultat["top3"]
    ecart = confiance - top3[1]["score"] if len(top3) > 1 else 1.0

    gravite = recommandation.get("gravite", "")
    couleur = COULEURS_GRAVITE.get(gravite, "#37474f")

    st.markdown(
        f"""
        <div style="border-left: 6px solid {couleur}; padding: 0.9rem 1.2rem;
                    background: rgba(128,128,128,0.08); border-radius: 4px;">
          <div style="font-size: 0.85rem; text-transform: uppercase;
                      letter-spacing: 0.08em; opacity: 0.7;">Diagnostic</div>
          <div style="font-size: 1.6rem; font-weight: 600; margin: 0.2rem 0;">
            {resultat['predicted_class']}</div>
          <div style="font-size: 0.95rem; opacity: 0.85;">
            Confiance {confiance:.0%}{f" — gravité {gravite}" if gravite and gravite != "aucune" else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Le cas important : deux hypothèses trop proches pour trancher
    if ecart < ECART_MINIMAL and len(top3) > 1:
        st.warning(
            f"**Diagnostic incertain.** Les deux premières hypothèses sont trop proches "
            f"pour être départagées ({confiance:.0%} contre {top3[1]['score']:.0%}, "
            f"soit {ecart:.0%} d'écart). Il s'agit vraisemblablement de "
            f"**{resultat['predicted_class']}** ou de **{top3[1]['label']}**. "
            "Comparer les deux descriptions ci-dessous avant de décider."
        )
    elif confiance < SEUIL_CONFIANCE_FAIBLE:
        st.warning(
            f"**Confiance limitée ({confiance:.0%}).** La photo est peut-être floue, "
            "mal éclairée, prise de trop loin, ou la feuille n'appartient à aucune "
            "des cultures reconnues. Reprendre la photo de près, à plat, en lumière "
            "naturelle et sur fond uni."
        )


def afficher_hypotheses(resultat):
    st.subheader("Hypothèses classées")
    st.caption("Le modèle répartit toujours 100 % entre les 10 classes. "
               "Un score élevé signifie qu'il hésite peu, pas qu'il a raison.")

    for rang, hypothese in enumerate(resultat["top3"], start=1):
        colonne_texte, colonne_score = st.columns([4, 1])
        with colonne_texte:
            marque = "**" if rang == 1 else ""
            st.markdown(f"{rang}. {marque}{hypothese['label']}{marque}")
            st.progress(min(hypothese["score"], 1.0))
        with colonne_score:
            st.markdown(f"### {hypothese['score']:.0%}")


def afficher_images(fichier, resultat):
    st.subheader("Où le modèle a regardé")

    gauche, droite = st.columns(2)
    with gauche:
        st.image(fichier, caption="Photo envoyée", width="stretch")
    with droite:
        if resultat.get("gradcam_base64"):
            image = base64.b64decode(resultat["gradcam_base64"])
            st.image(image, caption="Zones décisives", width="stretch")
        else:
            st.info("Carte non disponible pour ce diagnostic.")

    st.caption(
        "**Toute la feuille est examinée**, sans exception. Les couleurs indiquent "
        "seulement ce qui a le plus pesé dans la décision : les zones **rouges** ont "
        "emporté le diagnostic, les **bleues** n'ont pratiquement pas compté. Une "
        "lésion située ailleurs n'est donc pas ignorée, elle deviendrait simplement "
        "la zone rouge à son tour.\n\n"
        "Cette carte sert à vérifier le raisonnement : si le rouge se pose sur les "
        "lésions, le diagnostic s'appuie sur les bons indices. S'il se concentre sur "
        "le fond, sur une ombre ou sur un doigt, il faut se méfier du résultat et "
        "reprendre la photo."
    )


def afficher_recommandation(indice, recommandations, avertissement, titre_suffixe=""):
    fiche = recommandations.get(str(indice))
    if fiche is None:
        st.info("Aucune fiche disponible pour cette classe.")
        return

    if fiche.get("agent"):
        st.markdown(f"*Agent responsable : {fiche['agent']}*")
    st.markdown(f"**{fiche['constat']}**")

    st.markdown("**Ce qu'on observe**")
    st.write(fiche["symptomes"])

    if fiche.get("conditions"):
        st.markdown("**Conditions qui favorisent la maladie**")
        st.write(fiche["conditions"])

    st.markdown("**Que faire**")
    for mesure in fiche["mesures"]:
        st.markdown(f"- {mesure}")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

recommandations, avertissement = charger_recommandations()

st.title("🌿 AgriVision-AI")
st.caption("Diagnostic des maladies de la tomate, du maïs et du poivron "
           "à partir d'une photo de feuille.")

afficher_barre_laterale()

fichier = st.file_uploader(
    "Déposer une photo de feuille",
    type=["jpg", "jpeg", "png"],
    help="JPEG ou PNG, 5 Mo maximum. Cadrer une seule feuille, à plat, "
         "en lumière naturelle et sur un fond uni.",
)

if fichier is None:
    st.info(
        "**Pour un diagnostic fiable :** une seule feuille par photo, prise de près "
        "et bien à plat, en lumière du jour, sur un fond uni. Éviter les photos "
        "floues, les contre-jours et les feuilles encore mouillées."
    )
    st.caption(avertissement)
else:
    apercu, action = st.columns([1, 2])
    with apercu:
        st.image(fichier, width=220)
    with action:
        st.write("")
        lancer = st.button("Diagnostiquer", type="primary", width="stretch")

    if lancer:
        with st.spinner("Analyse en cours..."):
            resultat, erreur = demander_diagnostic(fichier)

        if erreur:
            st.error(erreur)
        else:
            st.divider()
            fiche_principale = recommandations.get(str(resultat["class_index"]), {})
            afficher_verdict(resultat, fiche_principale)

            st.write("")
            colonne_gauche, colonne_droite = st.columns([1, 1])
            with colonne_gauche:
                afficher_hypotheses(resultat)
            with colonne_droite:
                afficher_images(fichier, resultat)

            st.divider()

            # Quand deux hypothèses se disputent le diagnostic, on présente les
            # deux fiches côte à côte : c'est le seul moyen pour l'utilisateur
            # de trancher lui-même sur le terrain.
            top3 = resultat["top3"]
            ecart = resultat["confidence"] - top3[1]["score"] if len(top3) > 1 else 1.0

            if ecart < ECART_MINIMAL and len(top3) > 1:
                st.subheader("Départager les deux hypothèses")
                premiere, seconde = st.tabs([
                    f"{top3[0]['label']} ({top3[0]['score']:.0%})",
                    f"{top3[1]['label']} ({top3[1]['score']:.0%})",
                ])
                with premiere:
                    afficher_recommandation(top3[0]["class_index"], recommandations, avertissement)
                with seconde:
                    afficher_recommandation(top3[1]["class_index"], recommandations, avertissement)
            else:
                st.subheader("Conduite à tenir")
                afficher_recommandation(resultat["class_index"], recommandations, avertissement)

            st.divider()
            st.caption(avertissement)
            st.caption(f"Modèle {resultat['model_version']}")
