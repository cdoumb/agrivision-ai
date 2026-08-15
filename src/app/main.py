"""
Application de diagnostic AgriVision-AI — SQUELETTE MINIMAL.

Ce fichier n'est PAS la version finale. C'est un placeholder pour que la
chaîne complète (photo -> service -> diagnostic affiché) fonctionne dès
maintenant via docker-compose, en attendant l'application définitive du
Binôme B (indicateur de confiance soigné, top3, carte Grad-CAM superposée,
recommandation par maladie — cf. guide de projet §6.4).
"""
import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AgriVision-AI", page_icon="🌿")
st.title("🌿 AgriVision-AI — Diagnostic de feuille")
st.caption("Version squelette — à enrichir par le Binôme B")

uploaded_file = st.file_uploader("Dépose une photo de feuille (JPEG ou PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Image envoyée", width=300)

    if st.button("Diagnostiquer"):
        with st.spinner("Analyse en cours..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post(f"{API_URL}/predict", files=files, timeout=30)
                response.raise_for_status()
                result = response.json()

                st.success(f"Diagnostic : **{result['predicted_class']}**")
                st.metric("Confiance", f"{result['confidence']:.0%}")
                st.write("Top 3 hypothèses :")
                for hyp in result["top3"]:
                    st.write(f"- {hyp['label']} : {hyp['score']:.0%}")
                st.caption(f"Modèle : {result['model_version']}")

            except requests.exceptions.RequestException as e:
                st.error(f"Impossible de contacter le service d'inférence : {e}")
