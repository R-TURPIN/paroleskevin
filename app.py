import streamlit as st
import requests
import random
import re
import uuid
import time

st.set_page_config(
    page_title="Lyrics Trainer PRO",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

WEBHOOK_URL = "https://n8n.scaleath.com/webhook/generate-anki"

# ==========================================
# 1. INITIALISATION DU SESSION STATE
# ==========================================
def init_state(key, default_value):
    if key not in st.session_state:
        st.session_state[key] = default_value

init_state("lyrics_text", "")
init_state("sprint_q_idx", 0)
init_state("sprint_streak", 0)
init_state("dacto_q_idx", 0)
init_state("dacto_streak", 0)
init_state("dacto_feedback", None)

# Fonction pour normaliser le texte (insensible casse & ponctuation)
def normalize_text(text):
    return re.sub(r'[^\w\s]', '', str(text)).lower().strip()

# Découpage du texte en strophes
def parse_strophes(raw_text):
    blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text) if b.strip()]
    strophes = []
    for b in blocks:
        lines = [l.strip() for l in b.split('\n') if l.strip()]
        if lines:
            strophes.append(lines)
    return strophes

st.title("🎤 Studio d'Apprentissage PRO")

# ==========================================
# 2. SIDEBAR : ENTRÉE ET MÉTRIQUES
# ==========================================
with st.sidebar:
    st.header("📄 Paroles du morceau")
    uploaded_file = st.file_uploader("Fichier texte (.txt) :", type=["txt"])
    if uploaded_file is not None:
        st.session_state.lyrics_text = uploaded_file.read().decode("utf-8")
    
    text_input = st.text_area(
        "Zone de texte brut :",
        value=st.session_state.lyrics_text,
        height=250,
        placeholder="Colle tes paroles ici...\n\nSépare chaque couplet/refrain par une ligne vide."
    )
    if text_input != st.session_state.lyrics_text:
        st.session_state.lyrics_text = text_input

    # Métriques de la chanson
    strophes = parse_strophes(st.session_state.lyrics_text)
    all_lines = [line for strophe in strophes for line in strophe]
    total_words = sum(len(line.split()) for line in all_lines)

    if all_lines:
        st.markdown("---")
        st.subheader("📊 Métriques")
        col1, col2, col3 = st.columns(3)
        col1.metric("Strophes", len(strophes))
        col2.metric("Vers", len(all_lines))
        col3.metric("Mots", total_words)

    st.markdown("---")
    st.subheader("📦 Export Flashcards")
    if st.button("Générer XML AlgoApp (IA)", type="primary", use_container_width=True):
        if not st.session_state.lyrics_text.strip():
            st.warning("Ajoute des paroles d'abord !")
        else:
            with st.spinner("Génération du XML via n8n..."):
                try:
                    res = requests.post(WEBHOOK_URL, json={"lyrics": st.session_state.lyrics_text}, timeout=90)
                    if res.status_code == 200:
                        st.success("XML prêt !")
                        st.download_button(
                            label="📥 Télécharger deck_algoapp.xml",
                            data=res.text,
                            file_name="deck_algoapp.xml",
                            mime="application/xml",
                            use_container_width=True
                        )
                    else:
                        st.error(f"Erreur HTTP {res.status_code} : {res.text}")
                except Exception as e:
                    st.error(f"Erreur réseau : {e}")

# ==========================================
# 3. MOTEUR DE JEU (100% LOCAL RAM)
# ==========================================
if not all_lines:
    st.info("👈 Commence par coller ou importer les paroles de ta chanson dans le panneau de gauche pour débloquer les modules d'entraînement.")
else:
    tab1, tab2, tab3, tab4 = st.tabs([
        "👁️ 1. Téléprompteur",
        "🧩 2. Puzzle de Strophe",
        "⚡ 3. Sprint Transition",
        "⌨️ 4. Dactylographie (Nouveau)"
    ])

    # ----------------- ONGLET 1 : EFFACEMENT PROGRESSIF -----------------
    with tab1:
        st.subheader("Téléprompteur à effacement progressif")
        difficulty = st.select_slider(
            "Niveau de difficulté (Masquage) :",
            options=["0% (Complet)", "25% (Fins de vers)", "50% (Mots clés)", "75% (Squelette)", "100% (Mémoire totale)"],
            value="0% (Complet)"
        )
        st.markdown("---")
        
        for i, strophe in enumerate(strophes):
            strophe_display = []
            for line in strophe:
                words = line.split()
                if not words: continue
                
                if difficulty == "0% (Complet)":
                    strophe_display.append(line)
                elif difficulty == "25% (Fins de vers)":
                    cutoff = max(1, int(len(words) * 0.7))
                    strophe_display.append(" ".join(words[:cutoff]) + " " + "___ " * (len(words) - cutoff))
                elif difficulty == "50% (Mots clés)":
                    cutoff = max(1, int(len(words) * 0.4))
                    strophe_display.append(" ".join(words[:cutoff]) + " " + "___ " * (len(words) - cutoff))
                elif difficulty == "75% (Squelette)":
                    initials = " ".join([w[0] for w in words])
                    strophe_display.append(initials)
                elif difficulty == "100% (Mémoire totale)":
                    strophe_display.append("· · · · · · · · ·")
            
            st.markdown(f"**Bloc {i+1}**")
            st.code("\n".join(strophe_display), language="text")

    # ----------------- ONGLET 2 : PUZZLE DE STROPHE -----------------
    with tab2:
        st.subheader("Reconstitution de Strophe (Drag & Drop visuel)")
        
        col_sel, col_reset = st.columns([3, 1])
        with col_sel:
            strophe_idx = st.selectbox(
                "Choisis le bloc à travailler :",
                range(len(strophes)),
                format_func=lambda x: f"Bloc {x+1} ({strophes[x][0][:40]}...)"
            )
        
        current_lines = strophes[strophe_idx]
        
        # Initialisation sécurisée avec UUID pour éviter les erreurs de clés dupliquées
        state_key_shuffled = f"puzzle_shuffled_{strophe_idx}"
        state_key_picked = f"puzzle_picked_{strophe_idx}"
        
        if state_key_shuffled not in st.session_state:
            # On stocke des tuples (UUID unique, texte du vers)
            shuffled = [(str(uuid.uuid4()), line) for line in current_lines]
            random.shuffle(shuffled)
            st.session_state[state_key_shuffled] = shuffled
            st.session_state[state_key_picked] = []

        with col_reset:
            if st.button("🔄 Réinitialiser le bloc", use_container_width=True):
                shuffled = [(str(uuid.uuid4()), line) for line in current_lines]
                random.shuffle(shuffled)
                st.session_state[state_key_shuffled] = shuffled
                st.session_state[state_key_picked] = []
                st.rerun()

        st.write("Clique sur les vers pour reformer la strophe dans l'ordre chronologique :")
        
        # Vers restants à cliquer
        picked_ids = [p[0] for p in st.session_state[state_key_picked]]
        available_items = [item for item in st.session_state[state_key_shuffled] if item[0] not in picked_ids]
        
        cols = st.columns(2)
        for idx, (item_id, text) in enumerate(available_items):
            with cols[idx % 2]:
                # Utilisation de l'UUID comme clé Streamlit garantie 100% unique
                if st.button(text, key=f"btn_{item_id}", use_container_width=True):
                    st.session_state[state_key_picked].append((item_id, text))
                    st.rerun()
        
        st.markdown("---")
        st.markdown("#### Ton assemblage en cours :")
        
        picked_texts = [p[1] for p in st.session_state[state_key_picked]]
        for idx, picked_text in enumerate(picked_texts):
            expected = current_lines[idx]
            if picked_text == expected:
                st.success(f"**{idx+1}.** {picked_text} ✅")
            else:
                st.error(f"**{idx+1}.** {picked_text} ❌ *(Attendu : {expected})*")
        
        if len(picked_texts) == len(current_lines):
            if picked_texts == current_lines:
                st.balloons()
                st.success("🎉 Strophe maîtrisée dans le bon ordre !")

    # ----------------- ONGLET 3 : SPRINT TRANSITION -----------------
    with tab3:
        st.subheader("Sprint de Transition (Anticiper la bascule)")
        if len(strophes) < 2:
            st.warning("Il faut au moins 2 strophes (séparées par un saut de ligne) pour jouer aux transitions.")
        else:
            transitions = []
            for i in range(len(strophes) - 1):
                last_line = strophes[i][-1]
                next_first_line = strophes[i+1][0]
                transitions.append((i+1, last_line, next_first_line))
            
            q_idx = st.session_state.sprint_q_idx % len(transitions)
            bloc_num, cue, correct_answer = transitions[q_idx]
            
            st.metric("🔥 Streak (Série en cours)", st.session_state.sprint_streak)
            st.markdown(f"**Fin du Bloc {bloc_num} :**")
            st.warning(f"🎶 « ... {cue} »")
            st.markdown("### ➡️ Quelle est la première phrase qui enchaîne ?")
            
            # Génération des leurres statiques pour la session en cours
            state_key_options = f"sprint_options_{q_idx}"
            if state_key_options not in st.session_state:
                pool = [l for l in all_lines if l != correct_answer]
                distractors = random.sample(pool, min(2, len(pool)))
                options = distractors + [correct_answer]
                random.shuffle(options)
                st.session_state[state_key_options] = options
            
            selected = st.radio("Choisis la bonne amorce scénique :", st.session_state[state_key_options], key=f"sprint_radio_{q_idx}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Valider la transition", type="primary", use_container_width=True):
                    if selected == correct_answer:
                        st.session_state.sprint_streak += 1
                        st.success("🎯 Parfait ! Enchaînement validé.")
                        time.sleep(1) # Petit délai pour apprécier la victoire
                        st.session_state.sprint_q_idx += 1
                        st.rerun()
                    else:
                        st.session_state.sprint_streak = 0
                        st.error(f"Raté ! La réponse était : **{correct_answer}**")
            with c2:
                if st.button("Passer ➡️", use_container_width=True):
                    st.session_state.sprint_q_idx += 1
                    st.rerun()

    # ----------------- ONGLET 4 : DACTYLOGRAPHIE (SPEED TYPING) -----------------
    with tab4:
        st.subheader("Dactylographie & Blind-Test")
        st.write("L'ordinateur masque le mot clé d'un vers au hasard. Tape-le sans faire de faute (insensible à la casse).")
        
        st.metric("🔥 Streak (Série en cours)", st.session_state.dacto_streak)
        
        # Prendre un vers au hasard qui a au moins 3 mots
        valid_lines = [l for l in all_lines if len(l.split()) > 2]
        if not valid_lines:
            st.warning("Tes vers sont trop courts pour ce mode.")
        else:
            if "dacto_current_line" not in st.session_state:
                st.session_state.dacto_current_line = random.choice(valid_lines)
            
            target_line = st.session_state.dacto_current_line
            words = target_line.split()
            # On masque le dernier mot (la rime)
            target_word = words[-1]
            masked_line = " ".join(words[:-1]) + " [ ... ? ]"
            
            st.info(f"### 🎶 {masked_line}")
            
            # Formulaire de saisie rapide (La touche Entrée valide automatiquement)
            with st.form(key="dacto_form", clear_on_submit=True):
                user_input = st.text_input("Tape le mot manquant et appuie sur Entrée :", autocomplete="off")
                submit_button = st.form_submit_button("Vérifier")
                
                if submit_button:
                    if normalize_text(user_input) == normalize_text(target_word):
                        st.session_state.dacto_streak += 1
                        st.session_state.dacto_feedback = ("success", f"Bravo ! C'était bien **{target_word}**.")
                        # On change de vers pour le prochain tour
                        st.session_state.dacto_current_line = random.choice(valid_lines)
                        st.rerun()
                    else:
                        st.session_state.dacto_streak = 0
                        st.session_state.dacto_feedback = ("error", f"Faux ! Attendu : **{target_word}** (tu as tapé '{user_input}')")
                        st.rerun()
            
            # Affichage du feedback de la tentative précédente
            if st.session_state.dacto_feedback:
                ftype, msg = st.session_state.dacto_feedback
                if ftype == "success":
                    st.success(msg)
                else:
                    st.error(msg)
            
            if st.button("Passer au vers suivant ⏭️"):
                st.session_state.dacto_feedback = None
                st.session_state.dacto_current_line = random.choice(valid_lines)
                st.rerun()
