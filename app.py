import streamlit as st
import requests
from datetime import datetime

# --- Konfiguration ---
API_KEY = st.secrets["API_KEY"]  
BASE_URL = 'https://newsapi.org/v2/everything'

# --- Seiten-Design & Header ---
st.set_page_config(page_title="Mein Morning Briefing", page_icon="☕", layout="centered")

st.title("☕ Dein Morgentliches Briefing")
heute = datetime.now().strftime('%d.%m.%Y')
st.write(f"**Aktuelles Update vom {heute}** | Fokus: Geopolitik, Wirtschaft & Politik")
st.write("✅ *Gefiltert: Nur kostenlose Quellen (Keine Paywalls)*")
st.divider()

# --- Suchlogik aufbauen ---
suchbegriffe = "(Politik OR Wirtschaft OR Geopolitik OR Weltgeschehen OR Bundesregierung)"
ausschluss = "-Sport -Fußball -Promi -Stars -TV -Fernsehen -Werbung -Klatsch"
query = f"{suchbegriffe} {ausschluss}"

# NEU: Unsere Liste mit kostenlosen Nachrichtenquellen (kommagetrennt, ohne Leerzeichen)
# Hier nutzen wir z.B. Öffentlich-Rechtliche und werbefinanzierte Portale
erlaubte_quellen = "tagesschau.de,zdf.de,n-tv.de,t-online.de,rnd.de,dw.com"

# Parameter für die API-Anfrage definieren
params = {
    'q': query,
    'apiKey': API_KEY,
    'language': 'de',
    'sortBy': 'relevancy',
    'pageSize': 10,
    'domains': erlaubte_quellen  # NEU: Die API sucht jetzt NUR auf diesen Websites!
}

# --- Daten abrufen und anzeigen ---
with st.spinner('Dein kostenfreies Briefing wird zusammengestellt...'):
    response = requests.get(BASE_URL, params=params)
    data = response.json()

if data.get('status') == 'ok':
    articles = data.get('articles', [])
    
    if not articles:
        st.info("Heute gibt es keine neuen Artikel, die genau auf deine Präferenzen passen.")
    else:
        for art in articles:
            title = art.get('title', 'Kein Titel')
            description = art.get('description', 'Keine Beschreibung verfügbar.')
            url = art.get('url', '#')
            image_url = art.get('urlToImage')
            source = art.get('source', {}).get('name', 'Unbekannte Quelle')
            
            st.subheader(title)
            st.caption(f"📰 Quelle: {source}") 
            
            if image_url:
                st.image(image_url, use_container_width=True)
            
            st.write(description)
            st.markdown(f"**[➡️ Artikel komplett lesen]({url})**")
            st.divider() 
else:
    st.error("Fehler beim Abrufen der Nachrichten. Bitte prüfe die API-Verbindung.")
