import streamlit as st
import requests
from datetime import datetime

# --- Konfiguration ---
# Wir holen den API-Key sicher aus den Streamlit Secrets
API_KEY = st.secrets["API_KEY"]  
BASE_URL = 'https://newsapi.org/v2/everything'

# --- Seiten-Design & Header ---
# Gibt dem Browser-Tab einen Titel und ein Icon
st.set_page_config(page_title="Mein Morning Briefing", page_icon="☕", layout="centered")

st.title("☕ Dein Morgentliches Briefing")
# Zeigt das aktuelle Datum an
heute = datetime.now().strftime('%d.%m.%Y')
st.write(f"**Aktuelles Update vom {heute}** | Fokus: Geopolitik, Wirtschaft & Politik")
st.divider()

# --- Suchlogik aufbauen ---
# 1. Was wir sehen wollen (Klammern fassen diese als eine Gruppe zusammen)
suchbegriffe = "(Politik OR Wirtschaft OR Geopolitik OR Weltgeschehen OR Bundesregierung)"

# 2. Was wir NICHT sehen wollen (Minuszeichen schließt die Wörter aus)
ausschluss = "-Sport -Fußball -Promi -Stars -TV -Fernsehen -Werbung -Klatsch"

# Wir setzen beides zu einer einzigen Suchanfrage (Query) zusammen
query = f"{suchbegriffe} {ausschluss}"

# Parameter für die API-Anfrage definieren
params = {
    'q': query,
    'apiKey': API_KEY,
    'language': 'de',        # Nur deutsche Artikel
    'sortBy': 'relevancy',   # 'relevancy' ist hier besser als 'publishedAt', da wir starke inhaltliche Filter haben
    'pageSize': 10           # Wir beschränken es auf die 10 wichtigsten Artikel für ein kompaktes Briefing
}

# --- Daten abrufen und anzeigen ---
# Zeigt einen Ladekreis an, während die Daten geholt werden
with st.spinner('Dein Briefing wird zusammengestellt...'):
    response = requests.get(BASE_URL, params=params)
    data = response.json()

# Prüfen, ob die Anfrage erfolgreich war
if data.get('status') == 'ok':
    articles = data.get('articles', [])
    
    if not articles:
        st.info("Heute gibt es keine neuen Artikel, die genau auf deine Präferenzen passen.")
    else:
        # Jeden Artikel in der Liste durchgehen und anzeigen
        for art in articles:
            # Wir speichern die Daten in Variablen und geben Fallback-Werte an, falls etwas fehlt
            title = art.get('title', 'Kein Titel')
            description = art.get('description', 'Keine Beschreibung verfügbar.')
            url = art.get('url', '#')
            image_url = art.get('urlToImage')
            source = art.get('source', {}).get('name', 'Unbekannte Quelle')
            
            # --- UI Elemente für den Artikel ---
            st.subheader(title)
            st.caption(f"📰 Quelle: {source}") # Zeigt die Nachrichtenquelle klein darunter an
            
            # Bild anzeigen, falls vorhanden. 'use_container_width=True' passt es schön an die Spalte an.
            if image_url:
                st.image(image_url, use_container_width=True)
            
            st.write(description)
            # Ein klickbarer Link zum Original-Artikel
            st.markdown(f"**[➡️ Artikel komplett lesen]({url})**")
            st.divider() # Eine visuelle Trennlinie zum nächsten Artikel
else:
    # Fehlermeldung, falls die API zickt
    st.error("Fehler beim Abrufen der Nachrichten. Bitte prüfe die API-Verbindung.")
