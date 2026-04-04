#!/usr/bin/env python3
"""
Automatischer KI-Newsletter
Holt RSS-Feeds, kategorisiert mit Punkte+Ausschluss-System, verschickt per E-Mail.
"""

import os
import time
import socket
import smtplib
import feedparser
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────

RSS_FEEDS = {
    "Spiegel Online":       "https://www.spiegel.de/schlagzeilen/tops/index.rss",
    "FAZ":                  "https://www.faz.net/rss/aktuell/",
    "Politico Europe":      "https://www.politico.eu/feed/",
    "DPA":                  "https://news.google.com/rss/search?q=dpa+Nachrichtenagentur&hl=de&gl=DE&ceid=DE:de",
    "Reuters":              "https://news.google.com/rss/search?q=Reuters+deutsch&hl=de&gl=DE&ceid=DE:de",
    "Tagesschau":           "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml",
    "Zeit Online":          "https://newsfeed.zeit.de/index",
    "Deutschlandfunk":      "https://www.deutschlandfunk.de/politikportal-100.rss",
    "Handelsblatt Finanzen":"https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Handelsblatt Technik": "https://www.handelsblatt.com/contentexport/feed/technologie",
    "BBC News":             "https://feeds.bbci.co.uk/news/rss.xml",
    "New York Times":       "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Deutsche Welle":       "https://rss.dw.com/rdf/rss-en-all",
    "Euractiv":             "https://www.euractiv.com/feed/",
    "Financial Times":      "https://www.ft.com/?format=rss",
    "Bloomberg Markets":    "https://feeds.bloomberg.com/markets/news.rss",
}

# ─────────────────────────────────────────────
# KATEGORIEN: keywords mit Gewicht + Ausschluss
# ─────────────────────────────────────────────
# Jede Kategorie hat:
#   "keywords": dict {keyword: punkte}  – höhere Punkte = spezifischer
#   "exclude":  list [keyword, ...]     – wenn eines davon matcht → Kategorie ausgeschlossen
#
# Punkte-Logik:
#   10 = sehr spezifisch (nur diese Kategorie)
#    5 = spezifisch
#    3 = allgemein / kann mehrfach vorkommen
#    1 = schwacher Hinweis

CATEGORIES = {
    "⚽ Sport": {
        "keywords": {
            # Deutsch
            "sport": 10, "fußball": 10, "bundesliga": 10, "champions league": 10,
            "olympia": 10, "olympisch": 10, "formel 1": 10, "tennis": 10,
            "basketball": 10, "handball": 10, "dfl": 10, "dfb": 10,
            "spieltag": 10, "trikot": 8, "trainer": 5, "stadion": 8,
            "abstieg": 8, "aufstieg": 8, "weltmeister": 10,
            "em 2024": 10, "wm 2026": 10, "transfer": 8, "meister": 5,
            "tor": 5, "schiedsrichter": 10, "halbfinale": 10, "finale": 8,
            "pokal": 10, "liga": 8, "verein": 5, "athletik": 8,
            # Englisch
            "soccer": 10, "football club": 10, "premier league": 10,
            "la liga": 10, "serie a": 10, "ligue 1": 10,
            "formula 1": 10, "f1": 8, "grand prix": 10,
            "olympic": 10, "olympics": 10, "nba": 10, "nfl": 10,
            "golf tournament": 10, "wimbledon": 10, "tour de france": 10,
            "world cup": 10, "euros": 8, "athlete": 5, "coach": 5,
            "match": 5, "fixture": 8, "squad": 8, "goalkeeper": 10,
            "transfer window": 10, "championship": 8, "relegation": 10,
        },
        "exclude": [],
    },
    "🏛️ Innenpolitik": {
        "keywords": {
            # Deutsch
            "bundestag": 10, "bundesrat": 10, "kanzler": 10, "koalition": 10,
            "merz": 8, "scholz": 8, "habeck": 8, "baerbock": 8,
            "spd": 8, "cdu": 8, "csu": 8, "grüne": 8, "fdp": 8, "afd": 8,
            "regierung": 5, "minister": 5, "wahl": 5, "partei": 3,
            "opposition": 5, "bundesregierung": 10, "kabinett": 8,
            "koalitionsvertrag": 10, "ampel": 8, "große koalition": 10,
            "fraktionsvorsitz": 10, "abgeordneter": 8, "volkspartei": 8,
            # Englisch (DE-spezifisch)
            "german government": 10, "german parliament": 10,
            "german chancellor": 10, "german coalition": 10,
            "german minister": 8, "german election": 8,
            "bundestag election": 10, "german politics": 8,
        },
        "exclude": [
            "europawahl", "eu-wahl", "european election",
            "sport", "fußball", "soccer", "bundesliga",
        ],
    },
    "🌍 Außenpolitik": {
        "keywords": {
            # Deutsch
            "ukraine": 8, "russland": 8, "nato": 8, "krieg": 5,
            "außenminister": 10, "diplomatie": 10, "sanktionen": 8,
            "trump": 5, "biden": 5, "g7": 8, "g20": 8,
            "un": 5, "vereinte nationen": 10, "konflikt": 3,
            "friedensverhandlung": 10, "staatsbesuch": 10,
            "außenpolitik": 10, "botschafter": 10, "gipfel": 8,
            # Englisch
            "foreign policy": 10, "foreign minister": 10,
            "diplomacy": 10, "diplomatic": 8, "ambassador": 10,
            "ceasefire": 10, "peace talks": 10, "peace deal": 10,
            "sanctions": 8, "summit": 8, "bilateral": 8,
            "united nations": 10, "un security council": 10,
            "nato summit": 10, "state visit": 10,
            "ukraine war": 10, "russia": 5, "kremlin": 10,
            "white house": 5, "pentagon": 8, "state department": 10,
        },
        "exclude": [
            "bundesliga", "sport", "fußball", "soccer",
            "formel 1", "formula 1", "tennis", "olympic",
        ],
    },
    "💰 Wirtschaft": {
        "keywords": {
            # Deutsch
            "wirtschaft": 10, "dax": 10, "rezession": 10, "inflation": 10,
            "wachstum": 5, "arbeitslos": 10, "unternehmen": 3,
            "konzern": 5, "export": 8, "import": 8,
            "haushalt": 5, "schulden": 5, "konjunktur": 10,
            "ifo": 10, "bip": 10, "bruttoinlandsprodukt": 10,
            "lieferkette": 10, "fachkräftemangel": 10, "tarifvertrag": 10,
            "mindestlohn": 10, "insolvenz": 10, "kurzarbeit": 10,
            # Englisch
            "economy": 10, "economic": 8, "recession": 10,
            "inflation": 10, "gdp": 10, "gross domestic product": 10,
            "unemployment": 10, "jobs report": 10, "trade deficit": 10,
            "supply chain": 10, "labour market": 8, "labor market": 8,
            "wage": 5, "tariff": 8, "trade war": 10,
            "manufacturing": 5, "industry output": 8,
            "bankruptcy": 10, "insolvency": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer", "aktie", "börse", "fonds",
            "stocks", "shares", "bond", "crypto", "bitcoin",
        ],
    },
    "📊 Finanzen & Märkte": {
        "keywords": {
            # Deutsch
            "börse": 10, "aktie": 10, "aktien": 10, "fonds": 10,
            "etf": 10, "anleihe": 10, "zinsen": 8, "fed": 8, "ezb": 8,
            "krypto": 10, "bitcoin": 10, "ethereum": 10, "ipo": 10,
            "investment": 8, "depot": 10, "rendite": 10, "dividende": 10,
            "euro": 3, "dollar": 3, "währung": 8, "zinserhöhung": 10,
            "leitzins": 10, "staatsanleihe": 10, "hedgefonds": 10,
            # Englisch
            "stock market": 10, "stock exchange": 10, "shares": 8,
            "nasdaq": 10, "s&p 500": 10, "dow jones": 10, "ftse": 10,
            "bond yield": 10, "treasury": 8, "interest rate": 10,
            "federal reserve": 10, "ecb": 10, "central bank": 8,
            "cryptocurrency": 10, "crypto": 10, "blockchain": 8,
            "hedge fund": 10, "private equity": 10, "venture capital": 10,
            "ipo": 10, "earnings": 8, "dividend": 10,
            "currency": 8, "forex": 10, "exchange rate": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
            "olympic", "tennis", "formula 1",
        ],
    },
    "💻 Tech & KI": {
        "keywords": {
            # Deutsch
            "künstliche intelligenz": 10, "ki": 10, "sprachmodell": 10,
            "openai": 10, "chatgpt": 10, "llm": 10,
            "microsoft": 5, "apple": 5, "meta": 5, "amazon": 5,
            "startup": 5, "software": 5, "hardware": 5,
            "chip": 8, "halbleiter": 10, "cyber": 8, "hacker": 8,
            "datenschutz": 5, "algorithmus": 8, "roboter": 8,
            "nvidia": 10, "google deepmind": 10, "quantencomputer": 10,
            "rechenzentr": 8, "cloud": 5, "plattform": 3,
            # Englisch
            "artificial intelligence": 10, "ai model": 10,
            "machine learning": 10, "deep learning": 10,
            "large language model": 10, "generative ai": 10,
            "chatgpt": 10, "openai": 10, "anthropic": 10,
            "google deepmind": 10, "mistral": 10, "llama": 8,
            "semiconductor": 10, "microchip": 10, "data center": 8,
            "cybersecurity": 10, "cyber attack": 10, "ransomware": 10,
            "data breach": 10, "hacking": 8, "encryption": 8,
            "cloud computing": 8, "big tech": 8, "silicon valley": 8,
            "tech giant": 8, "software update": 5, "operating system": 5,
            "smartphone": 5, "iphone": 8, "android": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
            "formel 1", "formula 1", "tennis", "basketball",
            "handball", "olympia", "olympic",
        ],
    },
    "⚡ Energie & Klima": {
        "keywords": {
            # Deutsch
            "energie": 8, "strom": 5, "gas": 5, "öl": 5,
            "solar": 10, "wind": 5, "windkraft": 10, "erneuerbar": 10,
            "co2": 10, "klimawandel": 10, "klimaschutz": 10,
            "atomkraft": 10, "kernkraft": 10, "wärmepumpe": 10,
            "energiewende": 10, "stromerzeugung": 10, "strompreis": 10,
            "gaspreise": 10, "flüssiggas": 10, "lng": 10,
            # Englisch
            "energy": 5, "electricity": 5, "power grid": 8,
            "solar energy": 10, "solar panel": 10, "wind energy": 10,
            "wind farm": 10, "renewable energy": 10, "clean energy": 10,
            "nuclear energy": 10, "nuclear power": 10, "nuclear plant": 10,
            "fossil fuel": 10, "oil price": 8, "gas price": 8,
            "carbon emission": 10, "carbon tax": 10, "net zero": 10,
            "climate change": 10, "climate crisis": 10, "global warming": 10,
            "paris agreement": 10, "cop29": 10, "cop30": 10,
            "heat pump": 10, "lng": 10, "liquefied natural gas": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga", "olympic",
        ],
    },
    "🏥 Gesundheit": {
        "keywords": {
            # Deutsch
            "gesundheit": 10, "krankenhaus": 10, "arzt": 8,
            "medizin": 8, "impf": 10, "impfung": 10,
            "virus": 8, "corona": 10, "rki": 10, "who": 5,
            "pharma": 8, "therapie": 8, "pflege": 8,
            "klinik": 8, "diagnose": 8, "medikament": 10,
            "krankenkasse": 10, "gesundheitssystem": 10,
            "krebs": 8, "herzinfarkt": 10, "demenz": 10,
            # Englisch
            "health": 5, "healthcare": 10, "hospital": 10,
            "doctor": 5, "physician": 8, "medical": 5,
            "vaccine": 10, "vaccination": 10, "pandemic": 10,
            "epidemic": 10, "outbreak": 8, "virus": 8,
            "cancer": 8, "treatment": 5, "clinical trial": 10,
            "drug approval": 10, "fda": 10, "ema": 10,
            "mental health": 10, "nhs": 10, "health insurance": 8,
            "pharmaceutical": 8, "medicine": 5, "surgery": 8,
        },
        "exclude": [
            "sport", "fußball", "soccer", "research", "study",
            "forschung", "studie",
        ],
    },
    "🔬 Wissenschaft": {
        "keywords": {
            # Deutsch
            "wissenschaft": 10, "weltraum": 10, "nasa": 10, "esa": 10,
            "physik": 10, "biologie": 8, "chemie": 8,
            "entdeckung": 5, "universum": 10, "mars": 8, "mond": 5,
            "forschung": 5, "studie": 3, "labor": 8,
            "gen": 8, "dna": 10, "crispr": 10,
            # Englisch
            "science": 5, "scientific": 5, "research": 5, "study": 3,
            "space": 5, "spacex": 10, "nasa": 10, "esa": 10,
            "rocket launch": 10, "satellite": 8, "astronaut": 10,
            "mars mission": 10, "moon landing": 10, "asteroid": 10,
            "physics": 10, "quantum": 10, "particle": 8,
            "biology": 8, "genetics": 10, "genome": 10,
            "dna": 10, "crispr": 10, "stem cell": 10,
            "archaeology": 10, "fossil": 8, "dinosaur": 10,
            "nobel prize": 10, "breakthrough": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer", "wirtschaft", "economy",
            "börse", "stocks", "krankenhaus", "hospital",
            "impf", "vaccine", "corona", "rki",
        ],
    },
    "⚖️ Recht & Justiz": {
        "keywords": {
            # Deutsch
            "gericht": 10, "urteil": 10, "klage": 10, "recht": 5,
            "gesetz": 5, "bgh": 10, "bverfg": 10,
            "staatsanwalt": 10, "strafrecht": 10, "prozess": 8,
            "verfahren": 5, "anwalt": 8, "richter": 8, "freispruch": 10,
            "haftstrafe": 10, "ermittlung": 8, "verhaftung": 10,
            # Englisch
            "court": 10, "ruling": 10, "lawsuit": 10, "verdict": 10,
            "judge": 8, "trial": 10, "sentence": 8, "conviction": 10,
            "acquittal": 10, "indictment": 10, "prosecution": 8,
            "supreme court": 10, "european court": 10, "ecj": 10,
            "attorney general": 10, "law": 5, "legislation": 5,
            "regulation": 5, "fine": 5, "penalty": 5,
            "arrest": 8, "investigation": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga", "olympic",
        ],
    },
    "🛡️ Sicherheit & Verteidigung": {
        "keywords": {
            # Deutsch
            "bundeswehr": 10, "militär": 10, "verteidigung": 8,
            "rüstung": 10, "soldat": 10, "drohne": 8, "rakete": 8,
            "geheimdienst": 10, "bnd": 10, "verfassungsschutz": 10,
            "anschlag": 8, "terrorismus": 10, "polizei": 5,
            "sicherheit": 3, "waffenlieferung": 10, "panzer": 10,
            # Englisch
            "military": 10, "defense": 8, "defence": 8,
            "troops": 10, "soldiers": 8, "army": 8, "navy": 8,
            "air force": 10, "missile": 10, "drone strike": 10,
            "weapon": 5, "arms": 5, "ammunition": 10,
            "intelligence agency": 10, "cia": 10, "mi6": 10,
            "terrorism": 10, "terrorist": 10, "attack": 5,
            "security forces": 8, "war": 5, "combat": 8,
            "frontline": 10, "offensive": 8, "military aid": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga", "olympic",
            "tennis", "basketball",
        ],
    },
    "🌿 Umwelt & Natur": {
        "keywords": {
            # Deutsch
            "umwelt": 10, "natur": 8, "artensterben": 10,
            "wald": 8, "ozean": 10, "meer": 8, "plastik": 10,
            "recycling": 10, "nachhaltigkeit": 8, "ozon": 10,
            "biodiversität": 10, "naturschutz": 10, "tier": 5,
            "hochwasser": 10, "dürre": 10, "waldbrand": 10,
            # Englisch
            "environment": 10, "environmental": 8, "nature": 5,
            "wildlife": 10, "biodiversity": 10, "extinction": 10,
            "deforestation": 10, "amazon rainforest": 10,
            "ocean pollution": 10, "plastic waste": 10,
            "recycling": 10, "sustainability": 8, "sustainable": 5,
            "flood": 8, "drought": 10, "wildfire": 10, "forest fire": 10,
            "ozone layer": 10, "ecosystem": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer",
            "wirtschaft", "economy", "börse", "stocks",
        ],
    },
    "🏙️ Gesellschaft": {
        "keywords": {
            # Deutsch
            "gesellschaft": 10, "sozial": 5, "armut": 10,
            "bildung": 8, "schule": 8, "universität": 8,
            "familie": 8, "rente": 10, "migration": 10,
            "integration": 8, "flüchtling": 10, "demografie": 10,
            "diskriminierung": 10, "gleichstellung": 10, "inklusion": 8,
            # Englisch
            "society": 8, "social": 3, "poverty": 10,
            "education": 8, "school": 5, "university": 5,
            "family": 5, "pension": 10, "retirement": 8,
            "migration": 10, "refugee": 10, "asylum": 10,
            "immigration": 10, "diversity": 5, "inequality": 8,
            "discrimination": 10, "gender equality": 10,
            "demographics": 10, "population": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer",
            "wirtschaft", "economy", "börse", "stocks",
        ],
    },
    "🚗 Mobilität & Verkehr": {
        "keywords": {
            # Deutsch
            "bahn": 8, "flugzeug": 5, "verkehr": 8,
            "mobilität": 8, "elektroauto": 10, "tesla": 10,
            "volkswagen": 10, "bmw": 10, "mercedes": 10,
            "lufthansa": 10, "deutsche bahn": 10,
            "stau": 8, "bahnstreik": 10, "verspätung": 8,
            "auto": 5, "lkw": 8, "fahrrad": 5,
            # Englisch
            "electric vehicle": 10, "ev": 8, "electric car": 10,
            "autonomous vehicle": 10, "self-driving": 10,
            "tesla": 10, "volkswagen": 10, "toyota": 8,
            "airline": 10, "airport": 8, "flight": 5,
            "railway": 10, "train": 5, "high speed rail": 10,
            "traffic": 5, "transport": 5, "infrastructure": 5,
            "highway": 5, "road": 3, "shipping": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer",
            "formel 1", "formula 1", "f1", "grand prix",
            "börse", "stocks",
        ],
    },
    "🏗️ Immobilien & Bauen": {
        "keywords": {
            # Deutsch
            "immobilien": 10, "wohnen": 8, "miete": 10,
            "bauen": 8, "wohnungsnot": 10, "eigenheim": 10,
            "grundstück": 10, "baukosten": 10, "mietpreise": 10,
            "wohnungsbau": 10, "vermieter": 10, "mietrecht": 10,
            # Englisch
            "real estate": 10, "housing market": 10, "property": 5,
            "rent": 8, "rental": 8, "landlord": 10, "tenant": 10,
            "mortgage": 10, "house prices": 10, "home prices": 10,
            "construction": 8, "building permit": 10,
            "housing crisis": 10, "affordable housing": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
        ],
    },
    "🌐 Europa & EU": {
        "keywords": {
            # Deutsch
            "eu": 5, "europäisch": 8, "brüssel": 10,
            "europaparlament": 10, "eu-kommission": 10,
            "von der leyen": 10, "macron": 5, "draghi": 8,
            "europawahl": 10, "eu-wahl": 10, "schengen": 10,
            "eurozone": 10, "eu-haushalt": 10, "eu-gipfel": 10,
            # Englisch
            "european union": 10, "european commission": 10,
            "european parliament": 10, "eu summit": 10,
            "brussels": 10, "eurozone": 10, "euro area": 10,
            "von der leyen": 10, "eu regulation": 10,
            "eu policy": 8, "eu funding": 8, "eu law": 8,
            "brexit": 10, "schengen": 10,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
            "formula 1", "formel 1", "olympic",
        ],
    },
    "🗳️ Wahlen & Parteien": {
        "keywords": {
            # Deutsch
            "wahl": 8, "abstimmung": 8, "wahlkampf": 10,
            "umfrage": 5, "mandat": 8, "kandidat": 8,
            "wahlprogramm": 10, "stimmzettel": 10, "hochrechnung": 10,
            "exit poll": 10, "volksbegehren": 10,
            # Englisch
            "election": 10, "vote": 5, "voting": 8, "ballot": 10,
            "poll": 5, "polling": 8, "exit poll": 10,
            "campaign": 8, "candidate": 8, "primary": 8,
            "midterm": 10, "referendum": 10, "snap election": 10,
            "voter": 5, "constituency": 10, "majority": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
            "olympic", "formula 1",
        ],
    },
    "📱 Medien & Kultur": {
        "keywords": {
            # Deutsch
            "medien": 10, "zeitung": 8, "fernsehen": 8,
            "film": 5, "musik": 5, "kunst": 5, "kultur": 5,
            "theater": 8, "buch": 5, "streaming": 8,
            "netflix": 10, "social media": 10, "tiktok": 10,
            "instagram": 8, "presse": 8, "rundfunk": 10,
            # Englisch
            "media": 8, "newspaper": 8, "television": 8, "tv": 5,
            "film": 5, "movie": 5, "music": 5, "art": 3,
            "book": 5, "streaming": 8, "netflix": 10,
            "spotify": 10, "youtube": 8, "tiktok": 10,
            "social media": 10, "twitter": 8, "x platform": 8,
            "press freedom": 10, "journalism": 8, "broadcaster": 8,
            "podcast": 8, "influencer": 8,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
            "wirtschaft", "economy", "börse", "stocks",
        ],
    },
    "🌎 International": {
        "keywords": {
            # Deutsch
            "nahost": 10, "israel": 8, "palästina": 10,
            "iran": 8, "nordkorea": 10, "asien": 5,
            "afrika": 5, "lateinamerika": 8, "china": 5,
            "usa": 3, "welt": 3, "global": 3,
            "syrien": 10, "irak": 10, "jemen": 10,
            # Englisch
            "middle east": 10, "israel": 8, "palestine": 10,
            "gaza": 10, "west bank": 10, "iran": 8,
            "north korea": 10, "south korea": 5,
            "asia": 5, "china": 5, "beijing": 8,
            "taiwan": 10, "india": 5, "pakistan": 8,
            "africa": 5, "latin america": 8,
            "brazil": 5, "mexico": 5, "venezuela": 8,
            "syria": 10, "iraq": 10, "yemen": 10,
            "saudi arabia": 8, "gulf": 5,
        },
        "exclude": [
            "sport", "fußball", "soccer", "bundesliga",
            "formula 1", "olympic", "champions league",
        ],
    },
    "🔥 Sonstiges": {
        "keywords": {},
        "exclude": [],
    },
}

MAX_ARTICLES_PER_FEED   = 15
MAX_ARTICLES_FOR_SUMMARY = 60
FEED_TIMEOUT            = 15   # Sekunden pro Feed
GROQ_TIMEOUT            = 30   # Sekunden pro Groq-Call
GROQ_RETRIES            = 1    # Einmal retry bei Timeout

# ─────────────────────────────────────────────
# RSS FEEDS HOLEN
# ─────────────────────────────────────────────

def _normalize_title(title: str) -> str:
    """Titel normalisieren für Duplikat-Erkennung."""
    import re
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def fetch_feeds() -> list[dict]:
    """Alle RSS-Feeds holen, Duplikate entfernen und Artikel sammeln."""
    articles = []
    seen_titles = set()

    # feedparser nutzt socket-Timeout global
    socket.setdefaulttimeout(FEED_TIMEOUT)

    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)

            # feedparser gibt bei Netzwerkfehler einen leeren Feed zurück
            if feed.bozo and not feed.entries:
                print(f"⚠ {source}: Feed nicht erreichbar (bozo={feed.bozo_exception})")
                continue

            count = 0
            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED:
                    break
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                summary = summary[:400] if summary else ""

                if not title:
                    continue

                norm = _normalize_title(title)
                if norm in seen_titles:
                    continue
                seen_titles.add(norm)

                articles.append({
                    "source":  source,
                    "title":   title,
                    "summary": summary,
                    "link":    link,
                })
                count += 1

            print(f"✓ {source}: {count} Artikel geladen")

        except Exception as e:
            print(f"✗ Fehler bei {source}: {e}")

    return articles[:MAX_ARTICLES_FOR_SUMMARY]

# ─────────────────────────────────────────────
# KATEGORISIERUNG (Punkte + Ausschluss)
# ─────────────────────────────────────────────

def categorize_article(article: dict) -> str:
    """
    Artikel per gewichtetem Punkte-System kategorisieren.
    Ausschluss-Keywords verhindern Fehlzuordnungen (z.B. Sport → KI).
    """
    text = (article["title"] + " " + article["summary"]).lower()

    scores: dict[str, int] = {}

    for category, config in CATEGORIES.items():
        if category == "🔥 Sonstiges":
            continue

        # Ausschluss prüfen
        excluded = any(kw in text for kw in config.get("exclude", []))
        if excluded:
            continue

        # Punkte summieren
        score = sum(
            weight
            for kw, weight in config["keywords"].items()
            if kw in text
        )

        if score > 0:
            scores[category] = score

    if not scores:
        return "🔥 Sonstiges"

    # Kategorie mit den meisten Punkten gewinnt
    return max(scores, key=lambda c: scores[c])


def group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    """Artikel nach Kategorie gruppieren, Reihenfolge wie in CATEGORIES."""
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        cat = categorize_article(article)
        grouped.setdefault(cat, []).append(article)

    # Reihenfolge aus CATEGORIES beibehalten
    sorted_grouped = {}
    for cat in CATEGORIES.keys():
        if cat in grouped:
            sorted_grouped[cat] = grouped[cat]
    return sorted_grouped

# ─────────────────────────────────────────────
# GROQ HELPER (mit Timeout + Retry)
# ─────────────────────────────────────────────

def _groq_call(client: Groq, prompt: str, max_tokens: int = 200) -> str:
    """Groq-API-Call mit einem Retry bei Fehler."""
    for attempt in range(GROQ_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
                timeout=GROQ_TIMEOUT,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < GROQ_RETRIES:
                print(f"  ↻ Retry nach Fehler: {e}")
                time.sleep(2)
            else:
                raise

# ─────────────────────────────────────────────
# MODERATOREN-INTRO
# ─────────────────────────────────────────────

def generate_intro(grouped: dict[str, list[dict]], client: Groq) -> str:
    """
    Groq generiert einen kurzen Moderatoren-Text (3–4 Sätze),
    der die Tageslage einordnet – wie ein Nachrichtenmoderator.
    """
    # Top-Schlagzeilen aus den größten Kategorien ziehen
    top_headlines = []
    for articles in grouped.values():
        for a in articles[:2]:
            top_headlines.append(f"- [{a['source']}] {a['title']}")
        if len(top_headlines) >= 12:
            break

    headlines_text = "\n".join(top_headlines)

    prompt = f"""Du bist Chefredakteur eines seriösen deutschen Nachrichtenbriefs. 
Schreibe einen kurzen Einstiegstext (3–4 Sätze) für die heutige Ausgabe.

Regeln:
- Sachlich und präzise, aber mit leicht persönlicher Moderation ("Heute bestimmt...", "Im Fokus steht...", "Bewegung gibt es bei...")
- Die 2–3 wichtigsten Themen des Tages kurz einordnen
- Kein Clickbait, keine Wertung, keine Fragen
- Kein Betreff, keine Grußformel, direkt loslegen
- Deutsch

Heutige Schlagzeilen:
{headlines_text}

Einstiegstext:"""

    try:
        text = _groq_call(client, prompt, max_tokens=250)
        return text
    except Exception as e:
        print(f"✗ Intro-Fehler: {e}")
        return "Die wichtigsten Nachrichten des Tages im Überblick."


# ─────────────────────────────────────────────
# KI-ZUSAMMENFASSUNG MIT GROQ
# ─────────────────────────────────────────────

def summarize_with_groq(grouped: dict[str, list[dict]]) -> tuple[str, dict[str, list[str]]]:
    """
    Groq fasst jede Kategorie in Stichsätzen zusammen.
    Gibt (intro_text, summaries_dict) zurück.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY nicht gesetzt!")

    client = Groq(api_key=api_key)

    # Moderatoren-Intro zuerst
    print("  → Generiere Moderatoren-Intro...")
    intro = generate_intro(grouped, client)
    print(f"  ✓ Intro generiert")

    summaries: dict[str, list[str]] = {}

    for category, articles in grouped.items():
        if not articles:
            continue

        articles_text = "\n".join([
            f"- [{a['source']}] {a['title']}"
            + (f": {a['summary'][:200]}" if a["summary"] else "")
            for a in articles[:8]
        ])

        prompt = f"""Du bist ein präziser Nachrichtenredakteur eines TOP-Blatts in Deutschland. Fasse die folgenden Nachrichten der Kategorie "{category}" in genau 2 knappen deutschen Stichsätzen zusammen.

Regeln:
- Genau 2 Stichsätze, nicht mehr
- Jeder Stichsatz beginnt mit einem Bullet-Punkt (•)
- Maximal 1 Zeile pro Stichsatz
- Sachlich, informativ, keine Wertung
- Die wichtigsten 2 Meldungen herausgreifen
- Keine Einleitung, keine Schlussformel

Nachrichten:
{articles_text}

Stichsätze:"""

        try:
            text = _groq_call(client, prompt, max_tokens=200)
            bullet_points = [
                line.strip()
                for line in text.split("\n")
                if line.strip() and line.strip()[0] in ("•", "-", "*")
            ]
            bullet_points = ["• " + bp.lstrip("•-* ").strip() for bp in bullet_points]
            summaries[category] = bullet_points[:2]
            print(f"  ✓ Zusammenfassung: {category} ({len(summaries[category])} Punkte)")
        except Exception as e:
            print(f"  ✗ Groq-Fehler bei {category}: {e}")
            summaries[category] = [f"• Fehler beim Laden der Zusammenfassung."]

    return intro, summaries

# ─────────────────────────────────────────────
# HTML-NEWSLETTER ERSTELLEN
# ─────────────────────────────────────────────

def build_html(intro: str, summaries: dict[str, list[str]], grouped: dict[str, list[dict]]) -> str:
    """HTML-Newsletter mit vollständig inline-gestyltem HTML (forward-safe)."""
    now = datetime.now()
    daytime  = "Morgen" if now.hour < 13 else "Abend"
    date_str = now.strftime("%A, %d. %B %Y")

    months = {
        "January": "Januar", "February": "Februar", "March": "März",
        "April": "April", "May": "Mai", "June": "Juni",
        "July": "Juli", "August": "August", "September": "September",
        "October": "Oktober", "November": "November", "December": "Dezember",
    }
    days = {
        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag", "Friday": "Freitag",
        "Saturday": "Samstag", "Sunday": "Sonntag",
    }
    for en, de in {**months, **days}.items():
        date_str = date_str.replace(en, de)

    FONT         = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    COLOR_NAVY   = "#1b2a3b"
    COLOR_NAVY2  = "#2c3e50"
    COLOR_BLUE   = "#5a7fa0"
    COLOR_LIGHT  = "#a0b4c4"
    COLOR_MUTED  = "#7a9bb5"
    COLOR_BG     = "#f8f9fa"
    COLOR_BORDER = "#e8e8e8"
    COLOR_TEXT   = "#1c1c1e"
    COLOR_TEXT2  = "#3a3a3c"

    # ── Moderatoren-Intro Block ──────────────────────────────────────────
    intro_html = (
        f'<tr><td style="padding:20px 32px 16px;border-bottom:1px solid {COLOR_BORDER};">\n'
        f'  <p style="font-family:{FONT};font-size:14px;line-height:1.75;'
        f'color:{COLOR_TEXT2};margin:0;font-style:italic;">{intro}</p>\n'
        f'</td></tr>\n'
    )

    # ── Kategorien-Blöcke ────────────────────────────────────────────────
    category_blocks = ""
    items = list(summaries.items())
    for idx, (category, bullets) in enumerate(items):
        articles  = grouped.get(category, [])
        is_last   = (idx == len(items) - 1)
        border_bottom = "none" if is_last else f"1px solid {COLOR_BORDER}"

        bullets_html = ""
        for b in bullets:
            text = b.lstrip("• ").strip()
            bullets_html += (
                f'<tr>'
                f'<td style="font-family:{FONT};font-size:14px;line-height:1.6;'
                f'color:{COLOR_BLUE};font-weight:600;padding:3px 8px 3px 0;'
                f'vertical-align:top;white-space:nowrap;">–</td>'
                f'<td style="font-family:{FONT};font-size:14px;line-height:1.6;'
                f'color:{COLOR_TEXT2};padding:3px 0;">{text}</td>'
                f'</tr>\n'
            )

        links_html  = ""
        seen_links  = set()
        for a in articles[:5]:
            if a["link"] and a["link"] not in seen_links:
                seen_links.add(a["link"])
                links_html += (
                    f'<a href="{a["link"]}" style="display:block;text-decoration:none;'
                    f'padding:9px 12px;margin-bottom:4px;background:{COLOR_BG};'
                    f'border-left:3px solid #c8d8e8;border-radius:2px;">'
                    f'<span style="display:block;font-family:{FONT};font-size:10px;'
                    f'font-weight:600;text-transform:uppercase;letter-spacing:0.8px;'
                    f'color:{COLOR_BLUE};margin-bottom:3px;">{a["source"]}</span>'
                    f'<span style="display:block;font-family:{FONT};font-size:13px;'
                    f'color:{COLOR_TEXT};line-height:1.45;word-break:break-word;">'
                    f'{a["title"]}</span>'
                    f'</a>\n'
                )

        category_blocks += (
            f'<tr><td style="padding:24px 32px 20px;border-bottom:{border_bottom};">\n'
            f'  <table width="100%" cellpadding="0" cellspacing="0" border="0">\n'
            f'    <tr><td style="padding-bottom:10px;border-bottom:2px solid {COLOR_NAVY2};">\n'
            f'      <span style="font-family:{FONT};font-size:15px;font-weight:700;'
            f'color:{COLOR_NAVY};">{category}</span>\n'
            f'    </td></tr>\n'
            f'    <tr><td style="padding-top:10px;padding-bottom:14px;">\n'
            f'      <table cellpadding="0" cellspacing="0" border="0">{bullets_html}</table>\n'
            f'    </td></tr>\n'
            f'    <tr><td>{links_html}</td></tr>\n'
            f'  </table>\n'
            f'</td></tr>\n'
        )

    total_articles = sum(len(v) for v in grouped.values())

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="de">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light">\n'
        f'  <title>Tagesbrief &ndash; {date_str}</title>\n'
        '</head>\n'
        f'<body style="margin:0;padding:0;background:#f0f2f4;font-family:{FONT};'
        f'-webkit-text-size-adjust:100%;mso-line-height-rule:exactly;">\n'
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:#f0f2f4;">\n<tr><td align="center" style="padding:20px 8px;">\n'
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="max-width:620px;background:#ffffff;border-radius:4px;'
        f'border:1px solid #dde3e8;">\n'

        # HEADER
        f'<tr><td style="background:{COLOR_NAVY};padding:32px 32px 26px;text-align:center;'
        f'border-radius:4px 4px 0 0;">\n'
        f'  <div style="font-family:{FONT};font-size:10px;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:{COLOR_MUTED};margin-bottom:10px;">'
        f'Dein täglicher Nachrichtenüberblick</div>\n'
        f'  <div style="font-family:{FONT};font-size:28px;font-weight:700;'
        f'color:#ffffff;letter-spacing:-0.5px;margin-bottom:8px;">Tageslage</div>\n'
        f'  <div style="font-family:{FONT};font-size:13px;color:{COLOR_LIGHT};">'
        f'{date_str} &middot; {daytime}-Ausgabe</div>\n'
        f'</td></tr>\n'

        # META BAR
        f'<tr><td style="background:{COLOR_NAVY2};padding:8px 32px;text-align:center;'
        f'font-family:{FONT};font-size:11px;color:{COLOR_MUTED};">\n'
        f'  {len(RSS_FEEDS)}&nbsp;Quellen &nbsp;&middot;&nbsp; '
        f'{total_articles}&nbsp;Artikel &nbsp;&middot;&nbsp; KI-Zusammenfassung\n'
        f'</td></tr>\n'

        # INTRO
        + intro_html

        # KATEGORIEN
        + category_blocks +

        # FOOTER
        f'<tr><td style="background:{COLOR_NAVY};padding:20px 32px;text-align:center;'
        f'border-radius:0 0 4px 4px;">\n'
        f'  <p style="font-family:{FONT};font-size:11px;color:{COLOR_MUTED};'
        f'line-height:1.8;margin:0;">\n'
        f'    Automatisch erstellt am {now.strftime("%d.%m.%Y")} '
        f'um {now.strftime("%H:%M")} Uhr<br>\n'
        f'    Quellen: Spiegel Online &middot; FAZ &middot; Politico Europe u.v.m.<br>\n'
        f'    <a href="https://www.google.de" style="color:{COLOR_LIGHT};text-decoration:none;">'
        f'Powered by Nils</a>\n'
        f'  </p>\n'
        f'</td></tr>\n'

        '</table>\n'
        '</td></tr>\n'
        '</table>\n'
        '</body>\n</html>'
    )

    return html

# ─────────────────────────────────────────────
# E-MAIL VERSENDEN
# ─────────────────────────────────────────────

def send_email(html_content: str):
    """Newsletter per Gmail SMTP versenden."""
    sender       = os.environ.get("GMAIL_ADDRESS")
    password     = os.environ.get("GMAIL_APP_PASSWORD")
    recipient_raw = os.environ.get("RECIPIENT_EMAIL", sender)
    recipients   = [r.strip() for r in recipient_raw.split(",") if r.strip()]

    if not sender or not password:
        raise ValueError("GMAIL_ADDRESS oder GMAIL_APP_PASSWORD nicht gesetzt!")

    now     = datetime.now()
    daytime = "Morgen" if now.hour < 13 else "Abend"
    subject = f"🗞️ Tageslage – {now.strftime('%d.%m.%Y')} ({daytime}-Ausgabe)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Tageslage <{sender}>"
    msg["To"]      = ", ".join(recipients)

    plain = f"Tageslage – {now.strftime('%d.%m.%Y')}\nBitte HTML-Ansicht aktivieren."
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        print(f"✓ Newsletter verschickt an {', '.join(recipients)}")
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("SMTP-Login fehlgeschlagen – App-Passwort prüfen!")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"SMTP-Fehler beim Versand: {e}")
    except socket.timeout:
        raise RuntimeError("SMTP-Verbindung timeout – Gmail nicht erreichbar.")

# ─────────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"  TAGESLAGE – {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}\n")

    print("1/4 · RSS-Feeds laden...")
    articles = fetch_feeds()
    print(f"     → {len(articles)} Artikel gesammelt\n")

    print("2/4 · Kategorisieren...")
    grouped = group_by_category(articles)
    for cat, arts in grouped.items():
        print(f"     {cat}: {len(arts)} Artikel")
    print()

    print("3/4 · KI-Zusammenfassung & Intro mit Groq...")
    intro, summaries = summarize_with_groq(grouped)
    print()

    print("4/4 · E-Mail erstellen & versenden...")
    html = build_html(intro, summaries, grouped)
    send_email(html)

    print(f"\n✅ Fertig! Newsletter verschickt.\n")


if __name__ == "__main__":
    main()
