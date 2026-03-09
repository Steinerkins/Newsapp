import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime

# --- 1. Konfiguration & API Keys ---
NEWS_API_KEY = st.secrets["API_KEY"]  
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)

BASE_URL = 'https://newsapi.org/v2/everything'

# Erweiterte Liste für mehr Vielfalt
erlaubte_quellen_liste = [
    "tagesschau.de", "zdf.de", "n-tv.de", "t-online.de", 
    "rnd.de", "dw.com", "welt.de", "zeit.de", "faz.net", "sueddeutsche.de"
]
erlaubte_quellen_str = ",".join(erlaubte_quellen_liste)

st.set_page_config(page_title="KI Morning Briefing", page_icon="☕", layout="wide")

# --- 2. Kopfbereich & Suche ---
st.title("☕ Dein KI-gestütztes Morning Briefing")
st.write(f"**Update vom {datetime.now().strftime('%d.%m.%Y')}** | Fokus: Geopolitik, Wirtschaft & Politik")

such_ereignis = st.text_input("🔍 Suchst du nach einem bestimmten Ereignis?", "")

# --- 3. Suchlogik & Datenabruf ---
if such_ereignis:
    query = f"({such_ereignis}) -Sport -Fußball -Promi -Stars -TV -Werbung"
else:
    query = "(Politik OR Wirtschaft OR Geopolitik OR Weltgeschehen OR Bundesregierung) -Sport -Fußball -Promi -Stars -TV -Werbung"

params = {
    'q': query,
    'apiKey': NEWS_API_KEY,
    'language': 'de',
    'sortBy': 'relevancy',
    'pageSize': 80, # Mehr laden für bessere Misch-Möglichkeiten
    'domains': erlaubt_quellen_str  
}

@st.cache_data(ttl=3600)
def hole_nachrichten(p):
    return requests.get(BASE_URL, params=p).json()

with st.spinner('Lade weltweite Nachrichten...'):
    data = hole_nachrichten(params)

if data.get('status') == 'ok':
    alle_artikel = data.get('articles', [])
    
    if not alle_artikel:
        st.info("Keine Artikel gefunden.")
    else:
        # --- 4. Filter UI (Manuelle Filter) ---
        col1, col2 = st.columns(2)
        verfuegbare_quellen = list(set([a.get('source', {}).get('name') for a in alle_artikel if a.get('source', {}).get('name')]))
        
        with col1:
            q_filter = st.selectbox("Quelle wählen:", ["Alle"] + verfuegbare_quellen)
        with col2:
            t_filter = st.selectbox("Thema filtern:", ["Alle", "Politik", "Wirtschaft", "Krise", "Regierung"])

        # Vor-Filterung basierend auf deiner Auswahl
        vorauswahl = []
        for a in alle_artikel:
            q_ok = (q_filter == "Alle" or a.get('source', {}).get('name') == q_filter)
            t_ok = (t_filter == "Alle" or t_filter.lower() in a.get('title', '').lower())
            if q_ok and t_ok:
                vorauswahl.append(a)

        # --- 5. Misch-Logik (Diversität erzwingen) ---
        # Wir gruppieren die Artikel nach Quelle
        nach_quelle = {}
        for a in vorauswahl:
            name = a.get('source', {}).get('name', 'Andere')
            if name not in nach_quelle: nach_quelle[name] = []
            nach_quelle[name].append(a)
        
        # Bunte Mischung zusammenstellen
        gefilterte_artikel = []
        while len(gefilterte_artikel) < 20 and nach_quelle:
            for q in list(nach_quelle.keys()):
                if nach_quelle[q]:
                    gefilterte_artikel.append(nach_quelle[q].pop(0))
                else:
                    del nach_quelle[q]
                if len(gefilterte_artikel) >= 20: break

        # --- 6. KI-Briefing ---
        st.divider()
        st.subheader("✨ Dein ausführliches KI-Briefing")
        if st.button("Briefing generieren"):
            with st.spinner("Redaktion arbeitet..."):
                try:
                    titel_liste = [a.get('title') for a in gefilterte_artikel]
                    prompt = f"Erstelle ein ausführliches Morning-Briefing (ca. 400 Wörter) zu diesen Titeln: {titel_liste}. Fokus auf tagesaktuelle Politik/Wirtschaft. Strukturiere in Abschnitte."
                    
                    model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(model_list[0])
                    antwort = model.generate_content(prompt)
                    st.info(antwort.text)
                except Exception as e:
                    st.error(f"KI-Fehler: {e}")

        # --- 7. Artikel-Liste ---
        st.divider()
        st.subheader(f"📰 Top-Meldungen (Bunt gemischt)")
        for a in gefilterte_artikel[:15]:
            st.write(f"**{a.get('title')}**")
            st.caption(f"Quelle: {a.get('source', {}).get('name')} | [Link]({a.get('url')})")
            st.write("---")
else:
    st.error("API-Verbindung fehlgeschlagen.")
