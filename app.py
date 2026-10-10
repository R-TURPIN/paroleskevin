import streamlit as st
import requests
import random
import re

st.set_page_config(
    page_title="Lyrics Trainer & AlgoApp",
    page_icon="🎤",
    layout="wide"
)

WEBHOOK_URL = "https://n8n.scaleath.com/webhook/generate-anki"

# Initialisation du session state
if "lyrics_text" not in st.session_state:
    st.session_state.lyrics_text = ""
if "puzzle_order" not in st.session_state:
    st.session_state.puzzle_order = []
if "puzzle_current_idx" not in st.session_state:
    st.session_state.puzzle_current_idx = 0
if "sprint_q_idx" not in st.session_state:
    st.session_state.sprint_q_idx = 0
if "sprint_score" not in st.session_state:
    st.session_state.sprint_score = 0

st.title("🎤 Studio d'Apprentissage de Paroles")

# --- ZONE D'ENTRÉE COMMUNE ---
with st.sidebar:
    st.header("📄 Paroles du morceau")
    uploaded_file = st.file_uploader("Fichier texte (.txt) :", type=["txt"])
    if uploaded_file is not None:
        st.session_state.lyrics_text = uploaded_file.read().decode("utf-8")
    
    text_input = st.text_area(
        "Ou colle le texte ici :",
        value=st.session_state.lyrics_text,
        height=300,
        placeholder="Colle les paroles avec des sauts de ligne clairs entre strophes..."
    )
    if text_input != st.session_state.lyrics_text:
        st.session_state.lyrics_text = text_input

    st.markdown("---")
    st.subheader("📦 Export Flashcards")
    if st.button("Générer XML AlgoApp (IA)", type="secondary"):
        if not st.session_state.lyrics_text.strip():
            st.warning("Ajoute des paroles d'abord !")
        else:
            with st.spinner("Appel du workflow n8n..."):
                try:
                    res = requests.post(WEBHOOK_URL, json={"lyrics": st.session_state.lyrics_text}, timeout=90)
                    if res.status_code == 200:
                        st.success("XML prêt !")
                        st.download_button(
                            label="📥 Télécharger le XML",
                            data=res.text,
                            file_name="deck_algoapp.xml",
                            mime="application/xml"
                        )
                    else:
                        st.error(f"Erreur HTTP {res.status_code}")
                except Exception as e:
                    st.error(f"Erreur réseau : {e}")

# Fonctions d'analyse locale du texte
def parse_strophes(raw_text):
    blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text) if b.strip()]
    strophes = []
    for b in blocks:
        lines = [l.strip() for l in b.split('\n') if l.strip()]
        if lines:
            strophes.append(lines)
    return strophes

strophes = parse_strophes(st.session_state.lyrics_text)
all_lines = [line for strophe in strophes for line in strophe]

# --- MODES D'ENTRAÎNEMENT INTERACTIFS ---
tab1, tab2, tab3 = st.tabs([
    "👁️ 1. Téléprompteur à Effacement",
    "🧩 2. Puzzle de Strophe",
    "⚡ 3. Sprint de Transition"
])

# ----------------- MODE 1 : EFFACEMENT PROGRESSIF -----------------
with tab1:
    st.subheader("Entraînement au Téléprompteur (Effacement progressif)")
    if not all_lines:
        st.info("Renseigne des paroles dans la barre latérale pour commencer.")
    else:
        difficulty = st.select_slider(
            "Niveau de masquage :",
            options=["0% (Texte complet)", "25% (Fins de vers masquées)", "50% (Mots clés)", "75% (Initiales / Squelette)", "100% (Mémoire totale)"],
            value="0% (Texte complet)"
        )
        
        st.markdown("---")
        for i, strophe in enumerate(strophes):
            strophe_display = []
            for line in strophe:
                words = line.split()
                if difficulty == "0% (Texte complet)":
                    strophe_display.append(line)
                elif difficulty == "25% (Fins de vers masquées)":
                    cutoff = max(1, int(len(words) * 0.7))
                    strophe_display.append(" ".join(words[:cutoff]) + " " + "____ " * (len(words) - cutoff))
                elif difficulty == "50% (Mots clés)":
                    cutoff = max(1, int(len(words) * 0.4))
                    strophe_display.append(" ".join(words[:cutoff]) + " " + "____ " * (len(words) - cutoff))
                elif difficulty == "75% (Initiales / Squelette)":
                    initials = " ".join([w[0] for w in words if w])
                    strophe_display.append(initials)
                elif difficulty == "100% (Mémoire totale)":
                    strophe_display.append("· · · · · · · · ·")
            
            st.markdown(f"**Bloc {i+1} :**")
            st.code("\n".join(strophe_display), language="text")

# ----------------- MODE 2 : PUZZLE DE STROPHE -----------------
with tab2:
    st.subheader("Reconstitution de Strophe")
    if len(strophes) == 0:
        st.info("Renseigne des paroles pour générer les puzzles.")
    else:
        col_sel, col_reset = st.columns([3, 1])
        with col_sel:
            strophe_idx = st.selectbox(
                "Choisis le bloc à travailler :",
                range(len(strophes)),
                format_func=lambda x: f"Bloc {x+1} ({strophes[x][0][:35]}...)"
            )
        
        current_lines = strophes[strophe_idx]
        
        # Initialisation du puzzle
        if f"shuffled_{strophe_idx}" not in st.session_state:
            shuffled = current_lines.copy()
            random.shuffle(shuffled)
            st.session_state[f"shuffled_{strophe_idx}"] = shuffled
            st.session_state[f"picked_{strophe_idx}"] = []

        with col_reset:
            if st.button("🔄 Réinitialiser le bloc"):
                shuffled = current_lines.copy()
                random.shuffle(shuffled)
                st.session_state[f"shuffled_{strophe_idx}"] = shuffled
                st.session_state[f"picked_{strophe_idx}"] = []
                st.rerun()

        st.write("Clique sur les vers dans l'ordre chronologique de la chanson :")
        
        # Affichage des boutons pour choisir le vers suivant
        available_lines = [l for l in st.session_state[f"shuffled_{strophe_idx}"] if l not in st.session_state[f"picked_{strophe_idx}"]]
        
        cols = st.columns(2)
        for idx, line in enumerate(available_lines):
            with cols[idx % 2]:
                if st.button(line, key=f"btn_{strophe_idx}_{line}"):
                    st.session_state[f"picked_{strophe_idx}"].append(line)
                    st.rerun()
        
        st.markdown("---")
        st.markdown("#### Ton assemblage en cours :")
        for idx, picked in enumerate(st.session_state[f"picked_{strophe_idx}"]):
            expected = current_lines[idx]
            if picked == expected:
                st.success(f"Vers {idx+1} : {picked} ✅")
            else:
                st.error(f"Vers {idx+1} : {picked} ❌ (Attendu : {expected})")
        
        if len(st.session_state[f"picked_{strophe_idx}"]) == len(current_lines):
            if st.session_state[f"picked_{strophe_idx}"] == current_lines:
                st.balloons()
                st.success("🎉 Strophe maîtrisée dans le bon ordre !")

# ----------------- MODE 3 : SPRINT DE TRANSITION -----------------
with tab3:
    st.subheader("Sprint de Transition (Anticiper le premier mot)")
    if len(strophes) < 2:
        st.info("Il te faut au moins 2 strophes distinctes (séparées par une ligne vide) pour jouer aux transitions.")
    else:
        # Questions de transition : dernier vers strophe N -> premier vers strophe N+1
        transitions = []
        for i in range(len(strophes) - 1):
            last_line = strophes[i][-1]
            next_first_line = strophes[i+1][0]
            transitions.append((i+1, last_line, next_first_line))
        
        q_idx = st.session_state.sprint_q_idx % len(transitions)
        bloc_num, cue, correct_answer = transitions[q_idx]
        
        st.markdown(f"**Fin du Bloc {bloc_num} :**")
        st.warning(f"🎶 « ... {cue} »")
        st.markdown("### Quelle est la première phrase qui enchaîne ?")
        
        # Générer 3 leurres
        pool = [l for l in all_lines if l != correct_answer]
        distractors = random.sample(pool, min(2, len(pool)))
        options = distractors + [correct_answer]
        random.shuffle(options)
        
        selected = st.radio("Choisis la bonne amorce scénique :", options, key=f"sprint_radio_{q_idx}")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Valider la réponse", type="primary"):
                if selected == correct_answer:
                    st.success("🎯 Parfait ! Enchaînement validé.")
                else:
                    st.error(f"Raté ! La réponse était : {correct_answer}")
        with c2:
            if st.button("Transition suivante ➡️"):
                st.session_state.sprint_q_idx += 1
                st.rerun()
