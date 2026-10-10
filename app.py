import streamlit as st
import requests
import xml.etree.ElementTree as ET
import random

st.set_page_config(page_title="Flashcards Scène", page_icon="🎤", layout="centered")

WEBHOOK_URL = "https://n8n.scaleath.com/webhook/generate-anki"

tab_gen, tab_play = st.tabs(["🎵 Générer un deck", "🎮 S'entraîner avec un XML"])

# --- ONGLET 1 : GÉNÉRATION DU XML ---
with tab_gen:
    st.subheader("Générer un nouveau deck")
    lyrics_input = st.text_area("Paroles du morceau :", placeholder="Colle le texte complet...", height=240)
    
    if st.button("Générer via IA", type="primary"):
        if not lyrics_input.strip():
            st.warning("Veuillez renseigner des paroles.")
        else:
            with st.spinner("Génération du XML en cours..."):
                try:
                    res = requests.post(WEBHOOK_URL, json={"lyrics": lyrics_input}, timeout=90)
                    if res.status_code == 200:
                        xml_data = res.text
                        st.success("Deck généré avec succès !")
                        st.download_button(
                            label="📥 Télécharger le XML",
                            data=xml_data,
                            file_name="deck_morceau.xml",
                            mime="application/xml"
                        )
                    else:
                        st.error(f"Erreur HTTP {res.status_code} : {res.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Impossible de joindre n8n : {e}")

# --- ONGLET 2 : MODE INTERACTIF HORS-LIGNE ---
with tab_play:
    st.subheader("Entraînement & Réflexes")
    uploaded_file = st.file_uploader("Charge un fichier XML AlgoApp existant :", type=["xml"])
    
    if uploaded_file is not None:
        try:
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            cards = []
            
            for card in root.findall(".//card"):
                front = card.find("./text[@name='Front']")
                back = card.find("./text[@name='Back']")
                tag = card.attrib.get("tags", "Général")
                if front is not None and back is not None:
                    cards.append({
                        "front": front.text or "",
                        "back": back.text or "",
                        "tag": tag
                    })
            
            if cards:
                st.success(f"{len(cards)} cartes chargées !")
                
                # Filtre par tag si voulu
                tags = list(set(c["tag"] for c in cards))
                selected_tag = st.selectbox("Filtrer par type de carte :", ["Tous"] + tags)
                
                filtered_cards = cards if selected_tag == "Tous" else [c for c in cards if c["tag"] == selected_tag]
                
                # Gestion de la carte courante en mémoire de session
                if "card_idx" not in st.session_state:
                    st.session_state.card_idx = 0
                if "revealed" not in st.session_state:
                    st.session_state.revealed = False

                current_card = filtered_cards[st.session_state.card_idx % len(filtered_cards)]
                
                st.markdown(f"**Type :** `{current_card['tag']}`")
                st.info(f"### {current_card['front']}")
                
                if st.button("👁️ Révéler la réponse"):
                    st.session_state.revealed = True
                
                if st.session_state.revealed:
                    st.success(f"### {current_card['back']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("➡️ Suivante"):
                        st.session_state.card_idx += 1
                        st.session_state.revealed = False
                        st.rerun()
                with col2:
                    if st.button("🔀 Aléatoire"):
                        st.session_state.card_idx = random.randint(0, len(filtered_cards) - 1)
                        st.session_state.revealed = False
                        st.rerun()
            else:
                st.error("Aucune carte trouvée dans ce XML.")
        except Exception as e:
            st.error(f"Fichier XML invalide : {e}")
