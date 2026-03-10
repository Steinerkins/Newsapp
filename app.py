import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
from gtts import gTTS
import io

# --- 1. API Keys & Konfiguration ---
NEWS_API_KEY = st.secrets["API_KEY"]  
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# KI initialisieren
genai.configure(api_key=GEMINI_API_KEY)

# NewsAPI Einstellungen
BASE_URL = 'https://newsapi.org/v2/everything'
erlaubte_quellen_liste = [
    "tagesschau.de", "zdf.de", "n-tv.de", "t-online.de", 
    "rnd.de", "dw.com", "welt.de", "zeit.de", "faz.net", "sueddeutsche.de", 
    "reuters.com", "apnews.com", "bbc.co.uk", "theguardian.com", "npr.org", "aljazeera.com"
]
erlaubte_quellen_str = ",".join(erlaubte_quellen_liste)

# Seitenlayout
st.set_page_config(page_title="KI Morning Briefing", page_icon="☕", layout="wide")

# --- Gedächtnis der App (Session State) ---
if 'briefing_text' not in st.session_state:
    st.session_state.briefing_text = ""
if 'themen_liste' not in st.session_state:
    st.session_state.themen_liste = []
if 'klick_thema' not in st.session_state:
    st.session_state.klick_thema = None

# --- 2. UI Header & Suche ---
st.title("☕ Dein KI-gestütztes Morning Briefing")
heute = datetime.now().strftime('%d.%m.%Y')
st.write(f"**Update vom {heute}** | Fokus: Geopolitik, Wirtschaft & Politik")

such_ereignis = st.text_input("🔍 Suchst du nach einem bestimmten Ereignis? (Leer lassen für das allgemeine Briefing)", "")

# --- 3. Suchparameter definieren ---
gestern = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

sport_filter = "-sport -sports -football -soccer -tennis -nfl -nba -bundesliga -basketball -olympics"

if such_ereignis:
    query = such_ereignis
else:
    # Deutsch & Englisch kombiniert
    query = "Politik OR Wirtschaft OR Ausland OR Regierung OR politics OR economy OR international OR world OR crisis OR government"

params = {
    'q': query,
    'apiKey': NEWS_API_KEY,
    'sortBy': 'publishedAt', 
    'from': gestern,         
    'pageSize': 100,         
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
        
        # NEU: Checkboxen für die Regionen
        st.write("**Nach Regionen filtern:**")
        col_de, col_us, col_gb, col_int = st.columns(4)
        zeige_de = col_de.checkbox("[DE] Deutschland", value=True)
        zeige_us = col_us.checkbox("[US] USA", value=True)
        zeige_gb = col_gb.checkbox("[GB] Großbritannien", value=True)
        zeige_int = col_int.checkbox("[INT] International", value=True)
        
        # Die bisherigen Filter
        col1, col2 = st.columns(2)
        verfuegbare_quellen = []
        for art in alle_artikel:
            quelle = art.get('source', {}).get('name')
            if quelle and quelle not in verfuegbare_quellen:
                verfuegbare_quellen.append(quelle)
        
        with col1:
            gewaehlte_quelle = st.selectbox("Nach Quelle filtern:", ["Alle"] + sorted(verfuegbare_quellen))
        with col2:
            gewaehltes_thema = st.selectbox("Nach Thema filtern:", ["Alle", "Politik", "Wirtschaft", "Krise", "Regierung"])

        # --- Vorfilterung anwenden (inklusive Regionen) ---
        vorauswahl = []
        for art in alle_artikel:
            titel = art.get('title') or ""
            quelle = art.get('source', {}).get('name') or ""
            url = (art.get('url') or "").lower()
            
            # Region des Artikels bestimmen
            region = "INT"
            if ".de" in url or "dw.com" or "faz.net" in url:
                region = "DE"
            elif "bbc" in url or "theguardian" in url:
                region = "GB"
            elif "reuters" in url or "apnews" in url or "npr" in url:
                region = "US"
                
            # Prüfen, ob die gefundene Region angehakt ist
            region_erlaubt = False
            if region == "DE" and zeige_de: region_erlaubt = True
            elif region == "US" and zeige_us: region_erlaubt = True
            elif region == "GB" and zeige_gb: region_erlaubt = True
            elif region == "INT" and zeige_int: region_erlaubt = True
            
            quelle_passt = (gewaehlte_quelle == "Alle") or (quelle == gewaehlte_quelle)
            thema_passt = (gewaehltes_thema == "Alle") or (gewaehltes_thema.lower() in titel.lower())
            
            # Nur hinzufügen, wenn Region, Quelle UND Thema passen
            if region_erlaubt and quelle_passt and thema_passt:
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

# --- 7. KI-Briefing mit Debug-Ansicht & Pro-Modell ---
        st.divider()
        st.subheader("✨ Dein ausführliches KI-Briefing")
        
        # --- DEBUG-FENSTER (Direkt unter der Überschrift, VOR dem Button) ---
        with st.expander("🔍 Debug: Was liest die KI genau? (Hier klicken)"):
            debug_texte = [f"Titel: {a.get('title')} | Teaser: {a.get('description')}" for a in gefilterte_artikel if a.get('title') and a.get('description')]
            st.info("\n\n".join(debug_texte[:10]))
        # ----------------------------------------------

        # Hier gibt es nur EINEN EINZIGEN Button-Aufruf
        if st.button("Ausführliches Briefing generieren"):
            if not gefilterte_artikel:
                st.warning("Keine Artikel zum Zusammenfassen gefunden.")
            else:
                with st.spinner("Redaktion arbeitet... Bitte hab einen Moment Geduld."):
                    try:
                        # Daten für die KI aufbereiten (Titel + Teaser)
                        artikel_daten = []
                        for art in gefilterte_artikel:
                            titel = art.get('title') or ""
                            teaser = art.get('description') or ""
                            if titel and teaser:
                                artikel_daten.append(f"SCHLAGZEILE: {titel} | ZUSAMMENFASSUNG: {teaser}")
                        
                        quellen_text = "\n".join(artikel_daten)

                        prompt = f"""
                        Du bist ein professioneller Nachrichtensprecher. Erstelle ein tagesaktuelles Morgen-Briefing, das AUSSCHLIESSLICH auf den folgenden redaktionellen Meldungen von heute basiert:
                        
                        QUELLMATERIAL:
                        {quellen_text}
                        
                        DEINE AUFGABE UND REGELN:
                        1. Stil & Länge: Schreibe einen sachlichen, professionellen Fließtext von ca. 300 Wörtern.
                        2. Struktur: Gliedere den Text in sinnvolle Themenblöcke.
                        3. Strikte Faktenbindung: Verwende KEIN externes Wissen! Bleib exakt bei den Fakten aus dem Quellmaterial. Erfinde NICHTS dazu.
                        4. Konkrete Themen-Buttons: Benenne spezifische, im Text erwähnte Ereignisse.
                        5. Quellmaterial ist teilweise auf Deutsch und teilweise auf Englisch. Der Ausgegebene Text soll aber komplett in sauberem Deutsch sein.
                        
                        WICHTIG: Füge GANZ AM ENDE deines Textes exakt diese Zeile ein:
                        SCHLAGWÖRTER: Ereignis 1, Ereignis 2, Ereignis 3
                        """
                        
                        # --- MODELL-AUSWAHL: Wir erzwingen ein intelligenteres Modell ---
                        verfuegbare_modelle = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        # Wir suchen gezielt nach den besten Modellen (Pro oder Flash)
                        bestes_modell = None
                        for wunsch_modell in ['models/gemini-1.5-pro', 'models/gemini-1.5-flash']:
                            if wunsch_modell in verfuegbare_modelle:
                                bestes_modell = wunsch_modell
                                break # Stoppt, sobald das beste gefunden wurde
                        
                        # Fallback, falls Pro/Flash für diesen API-Key noch nicht freigeschaltet sind
                        if not bestes_modell:
                            bestes_modell = verfuegbare_modelle[0]
                            st.toast(f"Hinweis: Nutze Standard-Modell ({bestes_modell})")
                            
                        model = genai.GenerativeModel(bestes_modell) 
                        antwort = model.generate_content(prompt)
                        
                        # Text und Schlagwörter trennen...
                        if "SCHLAGWÖRTER:" in antwort.text:
                            teile = antwort.text.split("SCHLAGWÖRTER:")
                            st.session_state.briefing_text = teile[0].strip()
                            st.session_state.themen_liste = [t.strip() for t in teile[1].split(",") if t.strip()]
                        else:
                            st.session_state.briefing_text = antwort.text
                            st.session_state.themen_liste = []
                            
                        st.session_state.klick_thema = None 
                            
                    except Exception as e:
                        st.error(f"Fehler bei der Textgenerierung: {e}")
                            
                    except Exception as e:
                        st.error(f"Fehler bei der Textgenerierung: {e}")

        # --- Anzeige des Briefings, Audio und Buttons (aus dem Gedächtnis) ---
        if st.session_state.briefing_text:
            st.success("Dein heutiges Briefing:")
            st.markdown(st.session_state.briefing_text)
            
            # Audio-Player erstellen (wird nur neu geladen, wenn sich der Text ändert)
            with st.spinner("Generiere Audio..."):
                tts = gTTS(text=st.session_state.briefing_text, lang='de')
                audio_bytes = io.BytesIO()
                tts.write_to_fp(audio_bytes)
                st.audio(audio_bytes, format="audio/mp3")

            # Themen-Buttons anzeigen
            if st.session_state.themen_liste:
                st.write("**Top-Themen vertiefen (Klicken zum Filtern):**")
                # Erstellt für jedes Thema einen Button nebeneinander
                spalten = st.columns(len(st.session_state.themen_liste))
                for i, thema in enumerate(st.session_state.themen_liste):
                    if spalten[i].button(thema):
                        st.session_state.klick_thema = thema

        # --- 8. Artikel anzeigen (mit Klick-Thema Filter) ---
        st.divider()
        
        # Prüfen, ob ein Button geklickt wurde, und Liste entsprechend filtern
        anzeige_artikel = gefilterte_artikel
        if st.session_state.klick_thema:
            st.subheader(f"📰 Spezifische Artikel zum Thema: {st.session_state.klick_thema}")
            # Filtert die Liste nach dem angeklickten Wort
            anzeige_artikel = [art for art in gefilterte_artikel if st.session_state.klick_thema.lower() in (art.get('title') or '').lower()]
        else:
            st.subheader(f"📰 Top-Meldungen ({len(anzeige_artikel)} gefunden - Bunt gemischt)")
        
       # Artikel darstellen
        for art in anzeige_artikel:
            titel = art.get('title') or 'Kein Titel verfügbar'
            url = art.get('url') or '#'
            quelle = art.get('source', {}).get('name') or 'Unbekannte Quelle'
            
            # Windows-kompatible Text-Tags
            tag = "[INT]"
            url_lower = url.lower()
            if ".de" in url_lower or "dw.com" in url_lower:
                tag = "[DE]"
            elif "bbc" in url_lower or "theguardian" in url_lower:
                tag = "[GB]"
            elif "reuters" in url_lower or "apnews" in url_lower or "npr" in url_lower:
                tag = "[US]"
            
            # Tag vor den Titel setzen
            st.write(f"**{tag} {titel}**")
            st.caption(f"Quelle: {quelle} | [Zum Artikel]({url})")
            st.write("---")
            
else:
    st.error(f"Fehler beim Abrufen der Nachrichten. API-Status: {data.get('status')}")
