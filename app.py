import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime

# --- 1. Konfiguration & API Keys ---
NEWS_API_KEY = st.secrets["API_KEY"]  
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Gemini KI konfigurieren
genai.configure(api_key=GEMINI_API_KEY)

BASE_URL = 'https://newsapi.org/v2/everything'
erlaubte_quellen = "tagesschau.de,zdf.de,n-tv.de,t-online.de,rnd.de,dw.com"

st.set_page_config(page_title="KI Morning Briefing", page_icon="☕", layout="wide")

# --- 2. Kopfbereich & Ereignis-Suche ---
st.title("☕ Dein KI-gestütztes Morning Briefing")
st.write(f"**Update vom {datetime.now().strftime('%d.%m.%Y')}** | Nur kostenlose Quellen")

# Suchfeld für ein spezielles Ereignis
such_ereignis = st.text_input("🔍 Suchst du nach einem bestimmten Ereignis? (Lass es leer für das allgemeine Briefing)", "")

# --- 3. Suchlogik aufbauen ---
if such_ereignis:
    # Wenn der Nutzer etwas sucht, ignorieren wir die Standard-Themen
    query = f"({such_ereignis}) -Sport -Fußball -Promi -Stars -TV -Werbung"
else:
    # Standard-Briefing
    suchbegriffe = "(Politik OR Wirtschaft OR Geopolitik OR Weltgeschehen OR Bundesregierung)"
    ausschluss = "-Sport -Fußball -Promi -Stars -TV -Fernsehen -Werbung -Klatsch"
    query = f"{suchbegriffe} {ausschluss}"

# Wir holen jetzt 50 Artikel, um genug Auswahl für die Filter zu haben!
params = {
    'q': query,
    'apiKey': NEWS_API_KEY,
    'language': 'de',
    'sortBy': 'relevancy',
    'pageSize': 50, 
    'domains': erlaubte_quellen  
}

# --- 4. Daten abrufen ---
@st.cache_data(ttl=3600) # Speichert die Daten für 1 Stunde, damit die App schneller lädt
def hole_nachrichten(parameter):
    response = requests.get(BASE_URL, params=parameter)
    return response.json()

with st.spinner('Lade weltweite Nachrichten...'):
    data = hole_nachrichten(params)

if data.get('status') == 'ok':
    alle_artikel = data.get('articles', [])
    
    if not alle_artikel:
        st.info("Dazu wurden heute leider keine passenden Artikel gefunden.")
    else:
        # --- 5. Filter im Layout (Zwei Spalten) ---
        col1, col2 = st.columns(2)
        
        # Quellen automatisch aus den abgerufenen Artikeln extrahieren
        verfügbare_quellen = list(set([art.get('source', {}).get('name') for art in alle_artikel if art.get('source', {}).get('name')]))
        
        with col1:
            gewaehlte_quelle = st.selectbox("Nach Quelle filtern:", ["Alle"] + verfügbare_quellen)
        with col2:
            gewaehltes_thema = st.selectbox("Nach Stichwort im Titel filtern:", ["Alle", "Politik", "Wirtschaft", "Krise", "Regierung"])

        # Artikel anhand der Dropdowns filtern
        gefilterte_artikel = []
        for art in alle_artikel:
            quelle_passt = (gewaehlte_quelle == "Alle") or (art.get('source', {}).get('name') == gewaehlte_quelle)
            thema_passt = (gewaehltes_thema == "Alle") or (gewaehltes_thema.lower() in art.get('title', '').lower())
            
            if quelle_passt and thema_passt:
                gefilterte_artikel.append(art)

        # --- 6. KI Zusammenfassung generieren ---
        st.divider()
        st.subheader("✨ KI-Kurzzusammenfassung der aktuellen Lage")
        
        # Wir nehmen die Titel der Top 10 gefilterten Artikel für die KI
        top_titel = [art.get('title') for art in gefilterte_artikel[:10]]
        prompt = f"Fasse die folgenden Nachrichtentitel in 3 bis 4 kurzen, professionellen Stichpunkten zusammen. Ignoriere irrelevantes. Titel: {top_titel}"
        
        if st.button("Zusammenfassung jetzt generieren"):
            with st.spinner("Gemini liest die Nachrichten..."):
                try:
                    # Wir lassen den Code alle verfügbaren Modelle abfragen
                    verfuegbare_modelle = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    
                    if verfuegbare_modelle:
                        # Wir nehmen einfach das erste funktionierende Modell aus der Liste
                        gewaehltes_modell = verfuegbare_modelle[0]
                        model = genai.GenerativeModel(gewaehltes_modell) 
                        antwort = model.generate_content(prompt)
                        st.success("Hier ist deine Zusammenfassung:")
                        st.info(antwort.text)
                    else:
                        st.error("Dein API-Key hat aktuell keinen Zugriff auf Text-Modelle.")
                        
                except Exception as e:
                    st.error(f"Leider gab es ein Problem mit der KI: {e}")

        st.divider()

        # --- 7. Artikel anzeigen ---
        st.subheader(f"📰 Deine Artikel ({len(gefilterte_artikel)} gefunden)")
        
        for art in gefilterte_artikel[:15]: # Wir zeigen max. 15 an, damit die Seite nicht zu lang wird
            title = art.get('title', 'Kein Titel')
            url = art.get('url', '#')
            source = art.get('source', {}).get('name', 'Unbekannte Quelle')
            
            st.write(f"**{title}**")
            st.caption(f"Quelle: {source} | [Artikel lesen]({url})")
            st.write("---")
else:
    st.error("Fehler beim Abrufen der Nachrichten.")
