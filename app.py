import streamlit as st
import requests

# Configuration de la page
st.set_page_config(
    page_title="Générateur de Flashcards Musicales",
    page_icon="🎵",
    layout="centered"
)

st.title("🎵 Générateur de Decks AlgoApp")
st.write("Colle les paroles d'un morceau pour générer un deck d'apprentissage (Squelette, Rimes, Transitions).")

# URL du webhook n8n en production
WEBHOOK_URL = "https://n8n.scaleath.com/webhook/generate-anki"

# Zone de saisie
lyrics_input = st.text_area(
    "Paroles du morceau :",
    placeholder="Colle les paroles complètes ici...",
    height=280
)

# Bouton de génération
if st.button("Générer les cartes", type="primary"):
    if not lyrics_input.strip():
        st.warning("Veuillez renseigner les paroles avant de lancer la génération.")
    else:
        with st.spinner("Génération du deck XML en cours..."):
            try:
                response = requests.post(
                    WEBHOOK_URL,
                    json={"lyrics": lyrics_input},
                    timeout=90
                )
                
                if response.status_code == 200:
                    xml_content = response.text
                    
                    st.success("Deck généré avec succès !")
                    
                    # Bouton de téléchargement direct du fichier XML
                    st.download_button(
                        label="📥 Télécharger le fichier XML pour AlgoApp",
                        data=xml_content,
                        file_name="deck_algoapp.xml",
                        mime="application/xml"
                    )
                    
                    # Affichage du code pour copie manuelle rapide
                    with st.expander("Voir le XML généré (pour copier/coller directement)"):
                        st.code(xml_content, language="xml")
                else:
                    st.error(f"Erreur lors de la génération (Code {response.status_code}) : {response.text}")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à n8n : {e}")
