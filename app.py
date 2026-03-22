import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import asyncio
import edge_tts
import tempfile
from bs4 import BeautifulSoup

# --- 1. Initialisierung & API-Setup ---
# Lädt die API-Keys aus den Streamlit Secrets und konfiguriert das Gemini-Modell.
NEWS_API_KEY = st.secrets["API_KEY"]  
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. Basis-Konfiguration & Session State ---
# Definiert Seitenlayout, Konstanten und die bereinigte Liste kostenloser Nachrichtenquellen.
# Der Session State speichert Daten (wie generierte Texte), damit sie beim Neuladen der Seite nicht verschwinden.
st.set_page_config(page_title="KI Morning Briefing", page_icon="☕", layout="wide")
BASE_URL = 'https://newsapi.org/v2/everything'
erlaubte_quellen_liste = [
    "tagesschau.de", "zdf.de", "deutschlandfunk.de", "n-tv.de", "t-online.de", 
    "rnd.de", "dw.com", "derstandard.at", "srf.ch",
    "apnews.com", "bbc.com", "theguardian.com", "npr.org", "aljazeera.com", "euronews.com"
]
erlaubte_quellen_str = ",".join(erlaubte_quellen_liste)

if 'briefing_text' not in st.session_state:
    st.session_state.briefing_text = ""
if 'themen_liste' not in st.session_state:
    st.session_state.themen_liste = []
if 'klick_thema' not in st.session_state:
    st.session_state.klick_thema = None
if 'deep_dive_text' not in st.session_state:
    st.session_state.deep_dive_text = ""

# --- 3. Hilfsfunktionen: Scraping & KI-Helfer ---
# Beinhaltet Funktionen, um Artikeltexte von Webseiten zu extrahieren (Scraping) 
# und das beste verfügbare Gemini-Modell (Flash/Pro) automatisch auszuwählen.
def hole_bestes_modell():
    verfuegbare_modelle = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for wunsch_modell in ['models/gemini-1.5-pro', 'models/gemini-1.5-flash']:
        if wunsch_modell in verfuegbare_modelle:
            return wunsch_modell
    return verfuegbare_modelle[0]

def scrape_artikel_text(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        absatze = soup.find_all('p')
        text = " ".join([p.get_text() for p in absatze if len(p.get_text()) > 20])
        return text[:8000] if text else None
    except:
        return None

def optimiere_suchanfrage(user_input):
    if not user_input:
        return "Politik OR Wirtschaft OR Ausland OR Regierung OR politics OR economy OR international"
    
    prompt = f"""Übersetze die folgende Nutzereingabe in einen booleschen Suchstring für die NewsAPI.
    Nutze OR, AND und Klammern. Fokussiere dich auf Kernbegriffe, lass Füllwörter weg.
    Beispiel Eingabe: 'Was passiert im Nahen Osten?' -> Ausgabe: (Israel OR Gaza OR Libanon OR "Naher Osten" OR Nahost)
    Eingabe: '{user_input}'
    Gib AUSSCHLIESSLICH den Suchstring zurück, keinen anderen Text."""
    
    try:
        model = genai.GenerativeModel(hole_bestes_modell())
        antwort = model.generate_content(prompt)
        return antwort.text.strip()
    except:
        return user_input # Fallback bei Fehler

# --- 4. UI Header & Eingabe ---
# Baut den Titel und das Suchfeld für die App auf.
st.title("☕ Dein KI-gestütztes Morning Briefing")
heute = datetime.now().strftime('%d.%m.%Y')
st.write(f"**Update vom {heute}** | Fokus: Geopolitik, Wirtschaft & Politik")

such_ereignis = st.text_input("🔍 Suchst du nach einem bestimmten Ereignis? (Leer lassen für das allgemeine Briefing)", "")

# --- 5. Datenbeschaffung (NewsAPI) ---
# Bereitet die Suchparameter vor (inkl. KI-Optimierung der Suchbegriffe) und ruft die API ab.
gestern = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
api_query = optimiere_suchanfrage(such_ereignis) if such_ereignis else optimiere_suchanfrage(None)

params = {
    'q': api_query,
    'apiKey': NEWS_API_KEY,
    'sortBy': 'publishedAt', 
    'from': gestern,         
    'pageSize': 100,         
    'domains': erlaubte_quellen_str
}

@st.cache_data(ttl=3600)
def hole_nachrichten(p):
    response = requests.get(BASE_URL, params=p)
    return response.json()

with st.spinner('Lade weltweite Nachrichten...'):
    data = hole_nachrichten(params)

# --- 6. Hauptlogik & Filter-UI ---
# Wertet die API-Antwort aus, erstellt die Filter (Regionen, Quellen) und wendet diese auf die Artikel an.
if data.get('status') == 'ok':
    alle_artikel = data.get('articles', [])
    
    if not alle_artikel:
        st.info("Heute gibt es leider keine passenden Artikel zu dieser Suche.")
    else:
        st.divider()
        st.write("**Nach Regionen filtern:**")
        col_de, col_us, col_gb, col_int = st.columns(4)
        zeige_de = col_de.checkbox("[DE] Deutschland", value=True)
        zeige_us = col_us.checkbox("[US] USA", value=True)
        zeige_gb = col_gb.checkbox("[GB] Großbritannien", value=True)
        zeige_int = col_int.checkbox("[INT] International", value=True)
        
        vorauswahl = []
        for art in alle_artikel:
            url = (art.get('url') or "").lower()
            if ".de" in url or "dw.com" in url or "derstandard" in url or "srf" in url:
                region = "DE"
            elif "bbc" in url or "theguardian" in url:
                region = "GB"
            elif "apnews" in url or "npr" in url:
                region = "US"
            else:
                region = "INT"
                
            art['region'] = region

            if (region == "DE" and zeige_de) or (region == "US" and zeige_us) or \
               (region == "GB" and zeige_gb) or (region == "INT" and zeige_int):
                vorauswahl.append(art)

        # Diversität: Mischen der Quellen auf max. 20 Artikel
        artikel_nach_quelle = {}
        for art in vorauswahl:
            q_name = art.get('source', {}).get('name', 'Andere')
            artikel_nach_quelle.setdefault(q_name, []).append(art)

        gefilterte_artikel = []
        while len(gefilterte_artikel) < 20 and artikel_nach_quelle:
            for q in list(artikel_nach_quelle.keys()):
                if artikel_nach_quelle[q]:
                    gefilterte_artikel.append(artikel_nach_quelle[q].pop(0))
                else:
                    del artikel_nach_quelle[q]
                if len(gefilterte_artikel) >= 20: break

        # --- 7. Allgemeines KI-Briefing generieren ---
        # Nimmt die gefilterten Artikel, extrahiert Teaser und lässt Gemini das Morning-Briefing schreiben.
        st.divider()
        st.subheader("✨ Dein ausführliches KI-Briefing")
        
        if st.button("Ausführliches Briefing generieren"):
            with st.spinner("Redaktion arbeitet... Bitte hab einen Moment Geduld."):
                artikel_daten = [f"SCHLAGZEILE: {a.get('title')} | ZUSAMMENFASSUNG: {a.get('description')}" 
                                 for a in gefilterte_artikel if a.get('title') and a.get('description')]
                quellen_text = "\n".join(artikel_daten)

                prompt = f"""Du bist ein professioneller Nachrichtensprecher. Erstelle ein tagesaktuelles Briefing basierend auf diesen Meldungen:
                {quellen_text}
                
                REGELN:
                1. Schreibe einen sachlichen, gut strukturierten Text (ca. 300 Wörter) auf Deutsch, mit Einleitung Hauptteil und Schluss. Strukturiere die Themen sinnvoll nach Brisanz, Region oder anderen geeigneten Überthemen.
                1.1 Beginne den Text mit einer geeigneten Begrüßung z. B. "guten Morgen, willkommen zum KI-Briefing", Achte dabei auf die Tageszeit. Beende den Artikel mit einer geeigneten Verabschiedung.
                1.2 Der Artikel soll von einer automatischen Stimme vorgelesen werden. Verzichte auf Textbausteine wie +++ die die Vorlesequalität beinträchtigen könnten. 
                2. Bleib exakt bei den Fakten aus dem Material. Keine Erfindungen.
                3. Extrahiere am Ende 5 bis 8 sehr spezifische Kernthemen/Ereignisse als Suchbegriffe.
                
                WICHTIG: Füge GANZ AM ENDE diese Zeile ein:
                SCHLAGWÖRTER: Begriff 1, Begriff 2, Begriff 3..."""
                
                try:
                    model = genai.GenerativeModel(hole_bestes_modell())
                    antwort = model.generate_content(prompt)
                    
                    if "SCHLAGWÖRTER:" in antwort.text:
                        teile = antwort.text.split("SCHLAGWÖRTER:")
                        st.session_state.briefing_text = teile[0].strip()
                        st.session_state.themen_liste = [t.strip() for t in teile[1].split(",") if t.strip()]
                    else:
                        st.session_state.briefing_text = antwort.text
                        st.session_state.themen_liste = []
                        
                    st.session_state.klick_thema = None 
                    st.session_state.deep_dive_text = ""
                except Exception as e:
                    st.error(f"Fehler bei der Textgenerierung: {e}")

        # --- 8. Anzeige Briefing & Audio ---
        # Zeigt den generierten Text an und wandelt ihn asynchron in Sprache (Edge TTS) um.
        if st.session_state.briefing_text:
            st.success("Dein heutiges Briefing:")
            st.markdown(st.session_state.briefing_text)
            
            with st.spinner("Tonstudio generiert Sprachausgabe..."):
                async def generiere_audio(text):
                    sprecher = edge_tts.Communicate(text, "de-DE-ConradNeural", rate="+5%") 
                    tmp_datei = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    await sprecher.save(tmp_datei.name)
                    return tmp_datei.name
                
                try:
                    audio_pfad = asyncio.run(generiere_audio(st.session_state.briefing_text))
                    st.audio(audio_pfad, format="audio/mp3")
                except Exception as e:
                    st.error("Audio-Generierung fehlgeschlagen.")

            # --- 9. Themen-Buttons (Deep-Dive Trigger) ---
            # Zeigt die extrahierten Schlagwörter als Buttons an, um tiefere KI-Analysen auszulösen.
            if st.session_state.themen_liste:
                st.write("**Top-Themen vertiefen (Volltext-Analyse):**")
                spalten = st.columns(len(st.session_state.themen_liste))
                for i, thema in enumerate(st.session_state.themen_liste):
                    if spalten[i].button(thema, key=f"btn_{i}"):
                        st.session_state.klick_thema = thema
                        st.session_state.deep_dive_text = "" # Reset beim Klick
                        st.rerun()
# --- 10. Deep-Dive: Volltext-Analyse ---
        st.divider()
        if st.session_state.klick_thema:
            st.subheader(f"🔎 Fokus-Thema: {st.session_state.klick_thema}")
            
            if st.button("❌ Zurück zur Übersicht"):
                st.session_state.klick_thema = None
                st.session_state.deep_dive_text = ""
                st.rerun()

            # Schritt 1: Artikel blitzschnell suchen und als Liste anzeigen
            opt_query = optimiere_suchanfrage(st.session_state.klick_thema)
            thema_params = {
                'q': opt_query, 'apiKey': NEWS_API_KEY, 'sortBy': 'relevancy', 
                'from': gestern, 'pageSize': 15, 'domains': erlaubte_quellen_str
            }
            thema_daten = hole_nachrichten(thema_params)
            
            if thema_daten.get('status') == 'ok' and thema_daten.get('articles'):
                gefundene_artikel = thema_daten['articles']
                
                # Artikel-Vorschau anzeigen (Top 5)
                st.write(f"**Aktuelle Artikel zu '{st.session_state.klick_thema}':**")
                for art in gefundene_artikel[:5]:
                    st.markdown(f"- **{art.get('source', {}).get('name')}**: [{art.get('title')}]({art.get('url')})")
                
                st.write("---")
                
                # Schritt 2: Der neue Button für das ausführliche Briefing
                if st.button("📝 Deep-Dive Briefing inkl. Audio generieren (ca. 1 Min. Ladezeit)"):
                    with st.spinner("Lese die Top 3 Artikel im Volltext und schreibe Hintergrundbericht..."):
                        # Begrenzung auf 3 Artikel, um KI und Ladezeiten nicht zu überlasten
                        top_artikel = gefundene_artikel[:3] 
                        gesammelter_text = ""
                        
                        for art in top_artikel:
                            url = art.get('url')
                            if url:
                                volltext = scrape_artikel_text(url)
                                if volltext:
                                    gesammelter_text += f"\n\nQUELLE: {art.get('source', {}).get('name')} | TITEL: {art.get('title')}\n{volltext}"
                                else:
                                    gesammelter_text += f"\n\nQUELLE: {art.get('source', {}).get('name')} | TITEL: {art.get('title')}\n{art.get('content')}"

                        dd_prompt = f"""Schreibe eine detaillierte, journalistische Hintergrundanalyse zu folgendem Thema.
                        Umfang: ca. 500 bis 800 Wörter.
                        Nutze Absätze und Aufzählungszeichen für eine gute Lesbarkeit.
                        
                        MATERIAL:
                        {gesammelter_text}
                        """
                        try:
                            model = genai.GenerativeModel(hole_bestes_modell())
                            dd_antwort = model.generate_content(dd_prompt)
                            st.session_state.deep_dive_text = dd_antwort.text
                        except Exception as e:
                            st.error(f"Fehler bei der Deep-Dive Generierung: {e}")

                # Schritt 3: Anzeige des Textes UND des neuen Audio-Players
                if st.session_state.deep_dive_text:
                    st.success("Dein Deep-Dive Briefing:")
                    st.markdown(st.session_state.deep_dive_text)
                    
                    with st.spinner("Tonstudio generiert Sprachausgabe für den Deep-Dive..."):
                        async def generiere_dd_audio(text):
                            sprecher = edge_tts.Communicate(text, "de-DE-ConradNeural", rate="+5%") 
                            tmp_datei = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                            await sprecher.save(tmp_datei.name)
                            return tmp_datei.name
                        
                        try:
                            dd_audio_pfad = asyncio.run(generiere_dd_audio(st.session_state.deep_dive_text))
                            st.audio(dd_audio_pfad, format="audio/mp3")
                        except Exception as e:
                            st.error("Audio-Generierung fehlgeschlagen.")

            else:
                st.info("Leider keine passenden Artikel für diesen Deep-Dive gefunden.")

        # Fall 2: Keine spezifische Auswahl -> Standard-Feed anzeigen
        else:
            st.subheader(f"📰 Rohdaten-Feed (Die aktuellsten Meldungen)")
            for art in gefilterte_artikel:
                st.write(f"**[{art.get('region', 'INT')}] {art.get('title', 'Kein Titel')}**")
                st.caption(f"Quelle: {art.get('source', {}).get('name')} | [Zum Artikel]({art.get('url', '#')})")
                st.write("---")

else:
    st.error(f"Fehler beim Abrufen der Nachrichten. API-Status: {data.get('status')}")
