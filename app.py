import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime

# --- 1. API Keys & Konfiguration ---
NEWS_API_KEY = st.secrets["API_KEY"]  
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# KI initialisieren
genai.configure(api_key=GEMINI_API_KEY)

# NewsAPI Einstellungen
BASE_URL = 'https://newsapi.org/v2/everything'
erlaubte_quellen_liste = [
    "tagesschau.de", "zdf.de", "n-tv.de", "t-online.de", 
    "rnd.de", "dw.com", "welt.de", "zeit.de", "faz.net", "sueddeutsche.de"
]
erlaubte_quellen_str = ",".join(erlaubte_quellen_liste)

# Seitenlayout
st.set_page_config(page_title="KI Morning Briefing", page_icon="☕", layout="wide")

# --- 2. UI Header & Suche ---
st.title("☕ Dein KI-gestütztes Morning Briefing")
heute = datetime.now().strftime('%d.%m.%Y')
st.write(f"**Update vom {heute}** | Fokus: Geopolitik, Wirtschaft & Politik")

such_ereignis = st.text_input("🔍 Suchst du nach einem bestimmten Ereignis? (Leer lassen für das allgemeine Briefing)", "")

# --- 3. Suchparameter definieren ---
if such_ereignis:
    query = f"({such_ereignis}) -Sport -Fußball -Promi -Stars -TV -Werbung"
else:
    # Standard-Suche
    query = "(Politik OR Wirtschaft OR Geopolitik OR Weltgeschehen OR Bundesregierung) -Sport -Fußball -Promi -Stars -TV -Werbung -Klatsch"

params = {
    'q': query,
    'apiKey': NEWS_API_KEY,
    'language': 'de',
    'sortBy': 'relevancy',
    'pageSize': 80, # 80 Artikel laden für einen großen "Misch-Topf"
    'domains': erlaubte_quellen_str  
}

# --- 4. Daten abrufen (mit Cache) ---
@st.cache_data(ttl=3600)
def hole_nachrichten(p):
    response = requests.get(BASE_URL, params=p)
    return response.json()

with st.spinner('Lade weltweite Nachrichten...'):
    data = hole_nachrichten(params)

# --- Hauptlogik ---
if data.get('status') == 'ok':
    alle_artikel = data.get('articles', [])
    
    if not alle_artikel:
        st.info("Heute gibt es leider keine passenden Artikel zu dieser Suche.")
    else:
        # --- 5. Filter UI ---
        st.divider()
        col1, col2 = st.columns(2)
        
        # Sicheres Auslesen aller Quellen für das Dropdown-Menü
        verfuegbare_quellen = []
        for art in alle_artikel:
            quelle = art.get('source', {}).get('name')
            if quelle and quelle not in verfuegbare_quellen:
                verfuegbare_quellen.append(quelle)
        
        with col1:
            gewaehlte_quelle = st.selectbox("Nach Quelle filtern:", ["Alle"] + sorted(verfuegbare_quellen))
        with col2:
            gewaehltes_thema = st.selectbox("Nach Thema filtern:", ["Alle", "Politik", "Wirtschaft", "Krise", "Regierung"])

        # --- Vorfilterung anwenden ---
        vorauswahl = []
        for art in alle_artikel:
            # Fallback auf leere Strings, falls die API 'None' liefert
            titel = art.get('title') or ""
            quelle = art.get('source', {}).get('name') or ""
            
            quelle_passt = (gewaehlte_quelle == "Alle") or (quelle == gewaehlte_quelle)
            thema_passt = (gewaehltes_thema == "Alle") or (gewaehltes_thema.lower() in titel.lower())
            
            if quelle_passt and thema_passt:
                vorauswahl.append(art)

        # --- 6. Misch-Logik (Diversität erzwingen) ---
        # Artikel nach Quelle gruppieren
        artikel_nach_quelle = {}
        for art in vorauswahl:
            q_name = art.get('source', {}).get('name', 'Andere')
            if q_name not in artikel_nach_quelle:
                artikel_nach_quelle[q_name] = []
            artikel_nach_quelle[q_name].append(art)

        gefilterte_artikel = []
        max_anzeige = 20
        
        # Abwechselnd einen Artikel pro Quelle ziehen
        while len(gefilterte_artikel) < max_anzeige and artikel_nach_quelle:
            quellen_namen = list(artikel_nach_quelle.keys())
            for q in quellen_namen:
                if artikel_nach_quelle[q]:
                    gefilterte_artikel.append(artikel_nach_quelle[q].pop(0))
                else:
                    del artikel_nach_quelle[q]
                
                if len(gefilterte_artikel) >= max_anzeige:
                    break

        # --- 7. KI-Briefing ---
        st.divider()
        st.subheader("✨ Dein ausführliches KI-Briefing")
        
        if st.button("Ausführliches Briefing generieren"):
            if not gefilterte_artikel:
                st.warning("Keine Artikel zum Zusammenfassen gefunden.")
            else:
                with st.spinner("Redaktion arbeitet... Bitte hab einen Moment Geduld."):
                    try:
                        titel_liste = [art.get('title') for art in gefilterte_artikel]
                        prompt = f"""
                        Du bist ein erfahrener Nachrichtenredakteur. Erstelle ein ausführliches, flüssig lesbares Morgen-Briefing 
                        basierend auf den folgenden tagesaktuellen Schlagzeilen: {titel_liste}.
                        
                        DEINE AUFGABE:
                        1. Schreibe eine Zusammenfassung mit ca. 400-500 Wörtern.
                        2. Konzentriere dich EXKLUSIV auf tagesaktuelle Entwicklungen von heute.
                        3. Strukturiere den Text in klare Abschnitte (z.B. Geopolitik, Nationale Politik, Wirtschaft).
                        4. Der Ton soll professionell, sachlich und informativ sein.
                        """
                        
                        verfuegbare_modelle = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        if verfuegbare_modelle:
                            model = genai.GenerativeModel(verfuegbare_modelle[0]) 
                            antwort = model.generate_content(prompt)
                            st.success("Dein heutiges Briefing:")
                            st.markdown(antwort.text)
                        else:
                            st.error("Dein API-Key hat aktuell keinen Zugriff auf Text-Modelle.")
                            
                    except Exception as e:
                        st.error(f"Fehler bei der Textgenerierung: {e}")

        # --- 8. Artikel anzeigen ---
        st.divider()
        st.subheader(f"📰 Top-Meldungen ({len(gefilterte_artikel)} gefunden - Bunt gemischt)")
        
        for art in gefilterte_artikel:
            titel = art.get('title') or 'Kein Titel verfügbar'
            url = art.get('url') or '#'
            quelle = art.get('source', {}).get('name') or 'Unbekannte Quelle'
            
            st.write(f"**{titel}**")
            st.caption(f"Quelle: {quelle} | [Zum Artikel]({url})")
            st.write("---")
else:
    st.error(f"Fehler beim Abrufen der Nachrichten. API-Status: {data.get('status')}")
