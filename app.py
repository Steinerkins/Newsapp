import streamlit as st
import requests

# Konfiguration
API_KEY = 3f8ce342ed6344deb2cdcf28e0729b13  # Ersetze dies durch deinen echten Key
BASE_URL = 'https://newsapi.org/v2/everything'

st.title("My News App 📰")

# Eingabefeld für dein Interesse
query = st.text_input("Worüber möchtest du lesen?", "Künstliche Intelligenz")

if query:
    # Parameter für die Anfrage
    params = {
        'q': query,
        'apiKey': API_KEY,
        'language': 'de',      # Nur deutsche Artikel
        'sortBy': 'publishedAt' # Neueste zuerst
    }

    # Anfrage an die API senden
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if data.get('status') == 'ok':
        articles = data.get('articles', [])
        
        for art in articles[:10]: # Zeige die ersten 10 Artikel
            st.subheader(art['title'])
            if art['urlToImage']:
                st.image(art['urlToImage'])
            st.write(art['description'])
            st.write(f"[Zum vollen Artikel]({art['url']})")
            st.divider()
    else:
        st.error("Fehler beim Abrufen der Nachrichten. Überprüfe deinen API-Key.")
