#!/usr/bin/env python3
"""
Automatischer KI-Newsletter – Tageslage
Holt RSS-Feeds, kategorisiert mit Punkte+Ausschluss-System, verschickt per E-Mail.
"""

import os
import re
import time
import random
import socket
import smtplib
import urllib.parse
import feedparser
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from groq import Groq

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────

RSS_FEEDS = {
    # ── Allgemein Deutschland ──────────────────────────────────────────
    "Spiegel Online":         "https://www.spiegel.de/schlagzeilen/tops/index.rss",
    "FAZ":                    "https://www.faz.net/rss/aktuell/",
    "Tagesschau":             "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml",
    "Zeit Online":            "https://newsfeed.zeit.de/index",
    "Deutschlandfunk":        "https://www.deutschlandfunk.de/politikportal-100.rss",
    "DPA":                    "https://news.google.com/rss/search?q=dpa+Nachrichtenagentur&hl=de&gl=DE&ceid=DE:de",
    "Reuters DE":             "https://news.google.com/rss/search?q=Reuters+deutsch&hl=de&gl=DE&ceid=DE:de",
    # ── Wirtschaft & Finanzen Deutschland ─────────────────────────────
    "Handelsblatt":           "https://www.handelsblatt.com/contentexport/feed/schlagzeilen",
    "Handelsblatt Finanzen":  "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Handelsblatt Technik":   "https://www.handelsblatt.com/contentexport/feed/technologie",
    "Wirtschaftswoche":       "https://www.wiwo.de/rss/feed.rss",
    "Manager Magazin":        "https://www.manager-magazin.de/schlagzeilen/index.rss",
    "Tagesspiegel Wirtschaft":"https://www.tagesspiegel.de/wirtschaft/feed.rss",
    "Google Wirtschaft DE":   "https://news.google.com/rss/search?q=wirtschaft+konjunktur+deutschland&hl=de&gl=DE&ceid=DE:de",
    "Google Finanzen DE":     "https://news.google.com/rss/search?q=boerse+aktien+dax&hl=de&gl=DE&ceid=DE:de",
    # ── International Allgemein ────────────────────────────────────────
    "BBC News":               "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters EN":             "https://feeds.reuters.com/reuters/topNews",
    "Deutsche Welle":         "https://rss.dw.com/rdf/rss-en-all",
    "Euractiv":               "https://www.euractiv.com/feed/",
    "Politico Europe":        "https://www.politico.eu/feed/",
    # ── NYT – verschiedene Ressorts ───────────────────────────────────
    "NYT World":              "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "NYT Business":           "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "NYT Economy":            "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
    "NYT Politics":           "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "NYT US":                 "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
    # ── WSJ – öffentliche Feeds ───────────────────────────────────────
    "WSJ World":              "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
    "WSJ Markets":            "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "WSJ Economy":            "https://feeds.content.dowjones.io/public/rss/RSSBusiness",
    "WSJ US":                 "https://feeds.content.dowjones.io/public/rss/RSSWSJD",
    # ── FT – öffentlicher RSS ─────────────────────────────────────────
    "FT World":               "https://www.ft.com/world?format=rss",
    "FT Economics":           "https://www.ft.com/economics?format=rss",
    "FT Markets":             "https://www.ft.com/markets?format=rss",
    "FT US":                  "https://www.ft.com/us?format=rss",
    # ── Wirtschaft & Finanzen International ───────────────────────────
    "Reuters Business":       "https://feeds.reuters.com/reuters/businessNews",
    "CNBC Economy":           "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "CNBC Finance":           "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "Google Economy EN":      "https://news.google.com/rss/search?q=economy+recession+gdp&hl=en&gl=US&ceid=US:en",
    "Google Markets EN":      "https://news.google.com/rss/search?q=stock+market+fed+interest+rates&hl=en&gl=US&ceid=US:en",
    "Google Trade EN":        "https://news.google.com/rss/search?q=trade+war+tariffs+imf&hl=en&gl=US&ceid=US:en",
    # ── USA & Außenpolitik ────────────────────────────────────────────
    "Google USA Politik":     "https://news.google.com/rss/search?q=trump+white+house+congress&hl=en&gl=US&ceid=US:en",
    "Google US Foreign":      "https://news.google.com/rss/search?q=us+foreign+policy+diplomacy&hl=en&gl=US&ceid=US:en",
}

# Deutsche Quellen – werden beim Quellen-Mixing identifiziert
_DE_SOURCES = {
    "Spiegel Online", "FAZ", "Tagesschau", "Zeit Online", "Deutschlandfunk",
    "DPA", "Reuters DE", "Handelsblatt", "Handelsblatt Finanzen",
    "Handelsblatt Technik", "Wirtschaftswoche", "Manager Magazin",
    "Tagesspiegel Wirtschaft", "Google Wirtschaft DE", "Google Finanzen DE",
}

# ─────────────────────────────────────────────
# KATEGORIEN
# ─────────────────────────────────────────────

CATEGORIES = {
    "🏛️ Innenpolitik": {
        "keywords": {
            # Deutsche Institutionen – hohe Gewichtung
            "bundestag": 10, "bundesrat": 10, "bundesregierung": 10,
            "koalitionsvertrag": 10, "fraktionsvorsitz": 10,
            "bundestagswahl": 10, "landtagswahl": 10,
            "kanzler": 10, "koalition": 10,
            # Merz ist Bundeskanzler seit März 2025
            "merz": 10, "friedrich merz": 10,
            # Scholz ist jetzt SPD-Oppositionsführer
            "scholz": 5,
            "habeck": 7, "baerbock": 7, "lindner": 7,
            "spd": 8, "cdu": 8, "csu": 8, "grüne": 8, "fdp": 7, "afd": 8,
            "kabinett": 8, "große koalition": 10,
            "abgeordneter": 8,
            # Explizit deutsche Kontexte
            "german government": 10, "german parliament": 10,
            "german chancellor": 10, "german coalition": 10,
            "german minister": 8, "german election": 8,
            "bundestag election": 10, "german politics": 8,
        },
        "exclude": [
            "europawahl", "eu-wahl", "european election",
            "bundesliga", "fußball", "soccer",
            "uk government", "british government", "french government",
            "italian government", "spanish government", "polish government",
            "uk parliament", "british parliament", "house of commons",
            "macron", "sunak", "starmer", "meloni",
            "white house", "congress", "senate",
        ],
    },

    "🌍 Außenpolitik": {
        "keywords": {
            "ukraine": 8, "russland": 8, "nato": 8, "krieg": 5,
            "außenminister": 10, "außenpolitik": 10, "diplomatie": 10,
            "botschafter": 10, "staatsbesuch": 10, "gipfel": 8,
            "sanktionen": 8, "friedensverhandlung": 10, "waffenstillstand": 10,
            "trump": 5, "biden": 5, "g7": 8, "g20": 8,
            # Vereinte Nationen gehören zur Außenpolitik, nicht Innenpolitik
            "vereinte nationen": 10, "un-sicherheitsrat": 10,
            "konflikt": 5,
            "foreign policy": 10, "foreign minister": 10,
            "diplomacy": 10, "diplomatic": 8, "ambassador": 10,
            "ceasefire": 10, "peace talks": 10, "peace deal": 10,
            "sanctions": 8, "summit": 8, "bilateral": 8,
            "united nations": 10, "un security council": 10,
            "nato summit": 10, "state visit": 10,
            "ukraine war": 10, "kremlin": 10,
        },
        "exclude": [
            "bundesliga", "fußball", "soccer",
            "formel 1", "formula 1", "tennis", "olympic",
        ],
    },

    "🌐 Großmächte & Geopolitik": {
        # Zusammenführung der früheren Kategorien "USA & Amerika" und "International"
        # Fokus: USA, China, Russland als Weltmächte + geopolitische Konfliktherde
        "keywords": {
            # ── USA / Washington ──────────────────────────────────────
            "trump": 10, "white house": 10, "congress": 10, "senate": 10,
            "house of representatives": 10, "oval office": 10,
            "republican": 8, "democrat": 8, "washington": 8,
            "president trump": 10, "us president": 10, "american politics": 10,
            "us election": 10, "us congress": 10,
            "pentagon": 10, "state department": 10, "us treasury": 10,
            "us tariff": 10, "us trade": 10,
            "us foreign policy": 10, "us sanctions": 10,
            "us military": 10, "us troops": 10,
            "canada": 6, "mexico": 6,
            # ── China ─────────────────────────────────────────────────
            "china": 8, "xi jinping": 10, "beijing": 10, "peking": 10,
            "kommunistische partei china": 10, "volksrepublik": 8,
            "south china sea": 10, "taiwan strait": 10,
            "taiwan": 10, "hongkong": 8,
            "chinese economy": 10, "china trade": 10,
            # ── Russland ──────────────────────────────────────────────
            "putin": 10, "kremlin": 10, "moskau": 8, "moscow": 8,
            "russland": 8, "russia": 8,
            "ukraine war": 10, "ukraine": 7,
            # ── Geopolitische Konfliktherde ───────────────────────────
            "nahost": 10, "gazastreifen": 10, "westjordanland": 10,
            "israel": 8, "palästina": 10, "iran": 8,
            "nordkorea": 10, "north korea": 10,
            "syrien": 10, "jemen": 10, "irak": 10, "afghanistan": 10,
            "middle east": 10, "gaza strip": 10, "west bank": 10,
            "iran nuclear": 10, "saudi arabia": 8,
            "african union": 8, "latin america": 7, "venezuela": 8,
            # ── Weltordnung ───────────────────────────────────────────
            "g7": 8, "g20": 8, "brics": 10,
            "geopolitik": 10, "geopolitics": 10,
            "superpower": 10, "great power": 10,
        },
        "exclude": [
            "bundesliga", "fußball", "soccer",
            "formel 1", "formula 1", "olympic", "champions league",
            # Nicht mit Innenpolitik überschneiden
            "bundestag", "bundesrat", "bundesregierung",
        ],
    },

    "💰 Wirtschaft": {
        "keywords": {
            "wirtschaft": 10, "konjunktur": 10, "rezession": 10,
            "bruttoinlandsprodukt": 10, "bip": 10, "ifo": 10,
            "arbeitslosigkeit": 10, "arbeitslosenquote": 10,
            "inflation": 8, "wachstum": 5, "exportrückgang": 10,
            "handelsbilanz": 10, "lieferkette": 10,
            "fachkräftemangel": 10, "tarifvertrag": 10,
            "mindestlohn": 10, "insolvenz": 10, "kurzarbeit": 10,
            "unternehmen": 3, "konzern": 5, "deindustrialisierung": 10,
            "bundeshaushalt": 8, "schulden": 5,
            "stellenabbau": 10, "entlassungen": 10, "gewinnwarnung": 10,
            "quartalszahlen": 10, "umsatzrückgang": 10, "haushaltskrise": 10,
            "wirtschaftskrise": 10, "handelsstreit": 10, "zölle": 10,
            "wirtschaftswachstum": 10, "wirtschaftsabschwung": 10,
            "economic growth": 10, "economic recession": 10,
            "gdp": 10, "unemployment rate": 10,
            "trade deficit": 10, "trade war": 10,
            "supply chain": 10, "labour market": 8, "labor market": 8,
            "manufacturing": 5, "bankruptcy": 10, "wage growth": 8,
            "layoffs": 10, "job cuts": 10, "profit warning": 10,
            "quarterly results": 10, "earnings report": 10,
            "revenue decline": 10, "economic outlook": 10,
            "federal budget": 10, "fiscal policy": 10,
            "imf": 10, "world bank": 10, "oecd": 10,
            "economic crisis": 10, "austerity": 10,
            "trade policy": 10, "import tariff": 10,
            "inflation rate": 10, "consumer prices": 10,
            "interest rate": 8, "recession risk": 10,
            # tariff ohne "us" bleibt Wirtschaft, da Handelskontext
            "tariff": 6,
        },
        "exclude": [
            "fußball", "soccer", "bundesliga",
            "aktienmarkt", "börsenhandel", "kryptowährung",
            "stock market", "cryptocurrency", "bitcoin",
            # Gaspreise/Energiepreise → Energie-Kategorie hat Vorrang
            # (höhere Gewichtung dort verhindert Fehlzuweisung)
        ],
    },

    "📊 Finanzen & Märkte": {
        "keywords": {
            "aktienmarkt": 10, "aktienkurs": 10, "börse": 10, "dax": 10,
            "zinsentscheid": 10, "leitzins": 10, "ezb": 10,
            "staatsanleihe": 10, "bundesanleihe": 10, "anleihe": 8,
            "kryptowährung": 10, "bitcoin": 10, "ethereum": 10,
            "hedgefonds": 10, "investmentfonds": 10, "etf": 10,
            "dividende": 10, "quartalsbericht": 10,
            "währung": 8, "wechselkurs": 10,
            "stock market": 10, "share price": 10, "nasdaq": 10,
            "s&p 500": 10, "dow jones": 10, "ftse": 10,
            "bond yield": 10, "interest rate decision": 10,
            "federal reserve": 10, "central bank": 8,
            "cryptocurrency": 10, "bitcoin price": 10,
            "hedge fund": 10, "private equity": 10, "venture capital": 10,
            "quarterly earnings": 10, "exchange rate": 10,
            "ipo": 10, "merger": 10, "acquisition": 10,
        },
        "exclude": [
            "fußball", "soccer", "bundesliga", "olympic", "tennis",
        ],
    },

    "💻 Tech & KI": {
        "keywords": {
            "künstliche intelligenz": 10, "sprachmodell": 10,
            "chatbot": 8, "halbleiter": 10, "quantencomputer": 10,
            "rechenzentrum": 8, "cyberangriff": 10, "hackerangriff": 10,
            "datenschutzverletzung": 10, "ransomware": 10,
            "technologiekonzern": 8, "softwareupdate": 8,
            "artificial intelligence": 10, "large language model": 10,
            "generative ai": 10, "ai model": 10,
            "machine learning": 10, "deep learning": 10,
            "openai": 10, "anthropic": 10, "google deepmind": 10,
            "nvidia": 10, "semiconductor": 10, "microchip": 10,
            "data center": 8, "cloud computing": 8,
            "cybersecurity": 10, "cyber attack": 10,
            "data breach": 10, "big tech": 8, "silicon valley": 8,
        },
        "exclude": [
            "fußball", "soccer", "bundesliga",
            "formel 1", "formula 1", "tennis",
            "basketball", "handball", "olympia", "olympic",
        ],
    },

    "⚡ Energie & Klima": {
        "keywords": {
            # Energiepreise – hohe Gewichtung damit Energie > Wirtschaft gewinnt
            "gaspreise": 15, "gaspreis": 15, "gas price": 15, "gas prices": 15,
            "strompreis": 15, "strompreise": 15, "electricity price": 15,
            "ölpreis": 15, "oil price": 15, "energy prices": 15,
            "energiepreise": 15,
            # Allgemeine Energiethemen
            "energie": 8, "strom": 5, "gas": 5, "öl": 5,
            "windkraft": 10, "solaranlage": 10, "photovoltaik": 10,
            "kernkraftwerk": 10, "atomkraftwerk": 10, "atomkraft": 10,
            "co2": 10, "klimawandel": 10, "klimaschutz": 10,
            "energiewende": 10, "stromerzeugung": 10,
            "flüssiggas": 10, "lng": 10,
            "erneuerbar": 10, "wärmepumpe": 10, "kohlekraftwerk": 10,
            "renewable energy": 10, "solar energy": 10, "wind energy": 10,
            "nuclear power": 10, "nuclear plant": 10,
            "fossil fuel": 10,
            "carbon emissions": 10, "carbon tax": 10, "net zero": 10,
            "climate change": 10, "global warming": 10,
            "paris agreement": 10, "energy transition": 10,
        },
        "exclude": ["fußball", "soccer", "bundesliga", "olympic"],
    },

    "🏥 Gesundheit": {
        "keywords": {
            "krankenhaus": 10, "krankenhausreform": 10,
            "gesundheitssystem": 10, "krankenkasse": 10,
            "impfung": 10, "impfkampagne": 10, "impfpflicht": 10,
            "virus": 8, "corona": 10, "rki": 10,
            "medikament": 10, "arzneimittel": 8, "pharma": 8,
            "klinik": 8, "pflegenotstand": 10, "ärztemangel": 10,
            "healthcare": 10, "hospital": 10,
            "vaccine": 10, "vaccination": 10, "pandemic": 10,
            "disease outbreak": 10, "drug approval": 10,
            "clinical trial": 10, "mental health": 10,
            "nhs": 10, "pharmaceutical": 8,
        },
        "exclude": ["fußball", "soccer", "bundesliga"],
    },

    "🔬 Wissenschaft": {
        "keywords": {
            "weltraum": 10, "raumfahrt": 10, "nasa": 10, "esa": 10,
            "satellitenstart": 10, "marslandung": 10, "mondmission": 10,
            "quantencomputer": 10, "genomeditierung": 10,
            "crispr": 10, "dna": 10, "stammzelle": 10,
            "nobelpreis": 10, "teilchenbeschleuniger": 10,
            "wissenschaftler": 5, "forschungsergebnis": 8,
            "spacex": 10, "rocket launch": 10, "space mission": 10,
            "asteroid": 10, "quantum computing": 10,
            "gene editing": 10, "genome": 10, "stem cell": 10,
            "nobel prize": 10, "scientific breakthrough": 8,
            "particle physics": 10, "dark matter": 10,
            "archaeology": 10, "fossil discovery": 8,
        },
        "exclude": [
            "fußball", "soccer", "bundesliga",
            "aktienmarkt", "stock market",
        ],
    },

    "⚖️ Recht & Justiz": {
        "keywords": {
            "bundesgerichtshof": 10, "bundesverfassungsgericht": 10,
            "landgericht": 8, "oberverwaltungsgericht": 10,
            "urteil": 10, "strafurteil": 10, "freiheitsstrafe": 10,
            "staatsanwaltschaft": 10, "ermittlung": 8,
            "haftbefehl": 10, "verhaftung": 8, "anklage": 10,
            "gesetzgebung": 8, "verfassungsklage": 10,
            "court ruling": 10, "supreme court": 10,
            "lawsuit": 10, "verdict": 10, "criminal trial": 10,
            "indictment": 10, "conviction": 10, "acquittal": 10,
            "european court": 10, "attorney general": 10,
            "arrest warrant": 10, "criminal investigation": 8,
        },
        "exclude": ["fußball", "soccer", "bundesliga", "olympic"],
    },

    "🛡️ Sicherheit & Verteidigung": {
        "keywords": {
            "bundeswehr": 10, "militär": 10, "verteidigung": 8,
            "rüstung": 10, "soldat": 10, "waffenlieferung": 10,
            "drohnenangriff": 10, "raketenabwehr": 10,
            "geheimdienst": 10, "bnd": 10, "verfassungsschutz": 10,
            "terroranschlag": 10, "terrorismus": 10,
            "verteidigungshaushalt": 10, "nato-bündnis": 10,
            "military operation": 10, "defense spending": 10,
            "weapons delivery": 10, "arms shipment": 10,
            "intelligence agency": 10, "terrorist attack": 10,
            "drone strike": 10, "missile defense": 10,
            "frontline": 10, "military aid": 10,
        },
        "exclude": ["fußball", "soccer", "bundesliga", "olympic", "tennis"],
    },

    "🌿 Umwelt & Natur": {
        "keywords": {
            "artensterben": 10, "naturschutz": 10, "waldsterben": 10,
            "waldbrand": 10, "hochwasser": 10, "dürre": 10,
            "meeresspiegel": 10, "plastikverschmutzung": 10,
            "biodiversität": 10, "ozonschicht": 10,
            "umweltkatastrophe": 10, "nachhaltigkeit": 8,
            "biodiversity": 10, "species extinction": 10,
            "deforestation": 10, "ocean pollution": 10,
            "plastic pollution": 10, "wildfire": 10,
            "flood disaster": 10, "drought": 10,
            "ecosystem": 10, "ozone layer": 10,
        },
        "exclude": ["fußball", "soccer", "aktienmarkt", "stock market"],
    },

    "🏙️ Gesellschaft": {
        "keywords": {
            "bildungsreform": 10, "schulreform": 10,
            "rentenreform": 10, "rentenniveau": 10,
            "migrationspolitik": 10, "asylrecht": 10, "flüchtling": 10,
            "bevölkerungsentwicklung": 10, "geburtenrate": 10,
            "diskriminierung": 10, "gleichstellung": 10,
            "sozialleistung": 8, "armut": 10,
            "education reform": 10, "pension reform": 10,
            "migration policy": 10, "asylum seekers": 10,
            "refugee crisis": 10, "immigration policy": 10,
            "demographic change": 10, "gender equality": 10,
            "discrimination": 10, "poverty": 10,
        },
        "exclude": ["fußball", "soccer", "aktienmarkt", "stock market"],
    },

    "🚗 Mobilität & Verkehr": {
        "keywords": {
            "elektroauto": 10, "elektromobilität": 10,
            "ladeinfrastruktur": 10, "bahnstreik": 10,
            "deutsche bahn": 10, "lufthansa": 10,
            "volkswagen": 10, "bmw": 10, "mercedes": 10,
            "flughafenausbau": 10, "verkehrswende": 10,
            "stau": 8, "zugverspätung": 10,
            "electric vehicle": 10, "ev charging": 10,
            "self-driving car": 10, "railway strike": 10,
            "high speed rail": 10, "airline": 10,
            "airport expansion": 10, "tesla": 10,
        },
        "exclude": [
            "fußball", "soccer",
            "formel 1", "formula 1", "grand prix",
            "aktienmarkt", "stock market",
        ],
    },

    "🏗️ Immobilien & Bauen": {
        "keywords": {
            "wohnungsmarkt": 10, "immobilienmarkt": 10,
            "mietpreise": 10, "mietpreisbremse": 10,
            "wohnungsbau": 10, "wohnungsnot": 10,
            "baukosten": 10, "baugenehmigung": 10,
            "eigenheim": 10, "vermieter": 10, "mietrecht": 10,
            "housing market": 10, "real estate": 10,
            "rent increase": 10, "housing crisis": 10,
            "mortgage rate": 10, "house prices": 10,
            "construction costs": 10, "affordable housing": 10,
        },
        "exclude": ["fußball", "soccer", "bundesliga"],
    },

    "🇪🇺 Europa & EU": {
        "keywords": {
            "europaparlament": 10, "eu-kommission": 10,
            "eu-gipfel": 10, "eu-haushalt": 10,
            "eu-verordnung": 10, "eu-richtlinie": 10,
            "schengen": 10, "eurozone": 10,
            "von der leyen": 10, "eu-erweiterung": 10,
            "europäische union": 10, "brüssel": 8,
            "european union": 10, "european commission": 10,
            "european parliament": 10, "eu summit": 10,
            "brussels": 8, "eu regulation": 10,
            "eu enlargement": 10, "eu budget": 10,
        },
        "exclude": [
            "fußball", "soccer", "bundesliga",
            "formel 1", "formula 1", "olympic",
        ],
    },

    "🗳️ Wahlen & Parteien": {
        "keywords": {
            "bundestagswahl": 10, "landtagswahl": 10, "kommunalwahl": 10,
            "wahlkampf": 10, "wahlprogramm": 10, "wahlergebnis": 10,
            "hochrechnung": 10, "wahlbeteiligung": 10,
            "volksbegehren": 10, "volksabstimmung": 10,
            "general election": 10, "snap election": 10,
            "election campaign": 10, "election result": 10,
            "exit poll": 10, "voter turnout": 10,
            "referendum": 10, "polling data": 8,
        },
        "exclude": ["fußball", "soccer", "bundesliga", "olympic", "formula 1"],
    },

    "📱 Medien & Kultur": {
        "keywords": {
            "pressefreiheit": 10, "medienkonzern": 10,
            "rundfunkbeitrag": 10, "öffentlich-rechtlich": 10,
            "filmfestspiele": 10, "berlinale": 10, "buchpreis": 10,
            "streaming-plattform": 8, "soziale medien": 8,
            "desinformation": 8, "kulturförderung": 10,
            "press freedom": 10, "media censorship": 10,
            "streaming platform": 8, "social media": 8,
            "film festival": 10, "journalism": 8,
            "disinformation": 8, "content moderation": 10,
        },
        "exclude": ["fußball", "soccer", "bundesliga", "aktienmarkt", "stock market"],
    },

    "⚽ Sport": {
        "keywords": {
            "fußball": 10, "bundesliga": 10, "champions league": 10,
            "olympia": 10, "formel 1": 10, "tennis": 10,
            "basketball": 10, "handball": 10, "dfl": 10, "dfb": 10,
            "spieltag": 10, "stadion": 8, "torschütze": 10,
            "abstieg": 8, "aufstieg": 8, "weltmeister": 10,
            "transfermarkt": 10, "ablösesumme": 10,
            "halbfinale": 10, "pokalfinale": 10, "dfb-pokal": 10,
            "schiedsrichter": 10, "europameisterschaft": 10,
            "premier league": 10, "la liga": 10, "serie a": 10,
            "formula one": 10, "olympic games": 10, "olympics": 10,
            "wimbledon": 10, "nba": 10, "nfl": 10,
            "world cup": 10, "transfer window": 10,
            "championship final": 10, "relegation": 10,
        },
        "exclude": [],
    },

    "🔥 Sonstiges": {
        "keywords": {},
        "exclude": [],
    },
}

MAX_ARTICLES_PER_FEED    = 15
MAX_ARTICLES_FOR_SUMMARY = 160   # erhöht: genug Puffer damit EN-Quellen nicht abgeschnitten werden
TOP_CATEGORIES_COUNT     = 5
FEED_TIMEOUT             = 15
GROQ_TIMEOUT             = 30
GROQ_RETRIES             = 1

SIGNUP_URL    = "https://forms.gle/LSavK3JVp3aAsLGm9"
ARCHIVE_URL   = "https://www.thesignmaker.co.nz/wp-content/smush-webp/2019/04/C16_Work-In-Progress-600x600.png.webp"

GITHUB_PAGES_BASE_URL = os.environ.get(
    "PAGES_BASE_URL",
    "https://www.thesignmaker.co.nz/wp-content/smush-webp/2019/04/C16_Work-In-Progress-600x600.png.webp"
)

# ─────────────────────────────────────────────
# ANKER-ID HELPER
# ─────────────────────────────────────────────

def _anchor_id(category: str) -> str:
    """Erzeugt eine saubere HTML-Anker-ID aus dem Kategorienamen."""
    s = category.replace("&", "und").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^\w-]", "-", s)
    s = re.sub(r"-{2,}", "-", s)   # mehrfache Bindestriche zusammenfassen
    return s.strip("-")

# ─────────────────────────────────────────────
# RSS FEEDS HOLEN
# ─────────────────────────────────────────────

def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def fetch_feeds() -> list[dict]:
    articles    = []
    seen_titles = set()

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(FEED_TIMEOUT)

    # Feeds zufällig mischen – verhindert dass deutsche Quellen (die zuerst
    # definiert sind) bei MAX_ARTICLES_FOR_SUMMARY immer den Pool dominieren
    feed_items = list(RSS_FEEDS.items())
    random.shuffle(feed_items)

    try:
        for source, url in feed_items:
            try:
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    print(f"  ⚠ {source}: nicht erreichbar ({feed.bozo_exception})")
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

                print(f"  ✓ {source}: {count} Artikel")

            except Exception as e:
                print(f"  ✗ {source}: {e}")

    finally:
        socket.setdefaulttimeout(old_timeout)

    return articles[:MAX_ARTICLES_FOR_SUMMARY]

# ─────────────────────────────────────────────
# KATEGORISIERUNG
# ─────────────────────────────────────────────

def _kw_match(kw: str, text: str) -> bool:
    if " " in kw:
        return kw in text
    return bool(re.search(r"\b" + re.escape(kw) + r"\b", text))


def categorize_article(article: dict) -> str:
    text   = (article["title"] + " " + article["summary"]).lower()
    scores: dict[str, int] = {}

    for category, config in CATEGORIES.items():
        if category == "🔥 Sonstiges":
            continue
        if any(_kw_match(kw, text) for kw in config.get("exclude", [])):
            continue
        score = sum(
            weight
            for kw, weight in config["keywords"].items()
            if _kw_match(kw, text)
        )
        if score > 0:
            scores[category] = score

    if not scores:
        return "🔥 Sonstiges"
    return max(scores, key=lambda c: scores[c])


def group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        cat = categorize_article(article)
        grouped.setdefault(cat, []).append(article)

    sorted_grouped = {}
    for cat in CATEGORIES.keys():
        if cat in grouped:
            sorted_grouped[cat] = grouped[cat]
    return sorted_grouped

# ─────────────────────────────────────────────
# GROQ HELPER
# ─────────────────────────────────────────────

def _groq_call(client: Groq, prompt: str, max_tokens: int = 200) -> str:
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
                print(f"  ↻ Retry: {e}")
                time.sleep(2)
            else:
                raise

# ─────────────────────────────────────────────
# QUELLEN-MIXING
# ─────────────────────────────────────────────

def _select_links_with_groq(client: Groq, category: str,
                            articles: list[dict], max_total: int = 5) -> list[dict]:
    """
    Lässt Groq die relevantesten und quellenmäßig vielfältigsten Artikel
    aus der Kategorie auswählen. Groq gibt Indizes zurück (0-basiert).
    Fallback: einfaches Shuffeln mit max 2x pro Quelle.
    """
    if not articles:
        return []

    # Kandidaten: max 12 Artikel – genug Auswahl, nicht zu viel Token-Verbrauch
    candidates = articles[:12]

    lines = "\n".join(
        f"{i}: [{a['source']}] {a['title']}"
        for i, a in enumerate(candidates)
    )

    prompt = f"""Du kuratierst Links für die Newsletter-Kategorie "{category}".

Wähle {max_total} Artikel aus. Regeln:
- MAXIMAL 2 Artikel von derselben Quelle (z.B. nicht 3x Spiegel Online)
- Mix aus deutschen UND englischen Quellen wenn vorhanden
- Thematische Vielfalt (nicht 3x dasselbe Thema)

Antworte NUR mit den Zeilennummern, kommagetrennt, z.B.: 0,3,5,7,9
Keine Erklärung, keine anderen Zeichen.

Artikel:
{lines}

Auswahl:"""

    try:
        raw = _groq_call(client, prompt, max_tokens=20)
        indices = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
        indices = [i for i in indices if 0 <= i < len(candidates)]
        # Sicherheitsnetz: max 2x pro Quelle auch wenn Groq es ignoriert
        source_count: dict[str, int] = {}
        safe_indices = []
        for i in indices:
            src = candidates[i]["source"]
            if source_count.get(src, 0) < 2:
                safe_indices.append(i)
                source_count[src] = source_count.get(src, 0) + 1
        selected = [candidates[i] for i in safe_indices[:max_total]]
        if selected:
            return selected
    except Exception as e:
        print(f"  ⚠ Link-Auswahl Fallback ({e})")

    # Fallback: shuffle, max 2x pro Quelle
    pool = candidates.copy()
    random.shuffle(pool)
    result: list[dict] = []
    source_count: dict[str, int] = {}
    for a in pool:
        if len(result) >= max_total:
            break
        src = a["source"]
        if source_count.get(src, 0) < 2:
            result.append(a)
            source_count[src] = source_count.get(src, 0) + 1
    return result

# ─────────────────────────────────────────────
# INTRO – dynamisch mit Anker-Links
# ─────────────────────────────────────────────

def generate_intro(grouped: dict[str, list[dict]], client: Groq,
                   top_cats: list[str]) -> str:
    """
    Generiert einen einzigen flüssigen deutschen Satz, der die
    wichtigsten Themen des Tages zusammenfasst. Kein HTML, keine Links.
    """
    top_topics = []
    for cat in top_cats[:6]:
        articles = grouped.get(cat, [])
        for a in articles[:2]:
            top_topics.append(f"[{cat}] {a['title']}")

    topics_text = "\n".join(f"- {t}" for t in top_topics)

    prompt = f"""Du schreibst den Einleitungssatz eines deutschen Nachrichten-Newsletters.

Schreibe GENAU EINEN deutschen Satz (15-22 Woerter) der die 2-3 wichtigsten Themen direkt benennt.

STRIKTE Regeln:
- Starte mit einem konkreten Subjekt (Person, Institution, Land) – NIE mit "Die Lage", "Es", "Der Tag"
- Nenne konkrete Fakten: Namen, Zahlen, Entscheidungen – keine abstrakten Beschreibungen
- VERBOTEN: "gepragt von", "im Zeichen von", "Debatten", "Diskussionen", "Entwicklungen", "Themen", "Lage", "Geschehen"
- Verbinde Themen mit "waehrend", ";", "und" – nicht mit "sowie" oder "darueber hinaus"

GUTE Beispiele:
"Merz praesentiert den Bundeshaushalt 2026, waehrend Trump neue Zoelle auf EU-Waren ankuendigt."
"Die EZB senkt den Leitzins; der DAX faellt, und Gazaverhandlungen stocken erneut."
"Trump verhaengt 25-Prozent-Zoelle auf EU-Importe; Merz kuendigt Sondervermoegen fuer die Bundeswehr an."

SCHLECHTE Beispiele – NIEMALS so:
"Die Innenpolitik ist gepragt von Debatten und Diskussionen wie der Diskussion um..."
"Heute gibt es wichtige Entwicklungen in Wirtschaft und Politik."
"Der Tag steht im Zeichen von Spannungen und wichtigen Entscheidungen."

Schlagzeilen:
{topics_text}

Satz:"""

    try:
        sentence = _groq_call(client, prompt, max_tokens=60)
        sentence = sentence.strip().strip('"').strip("'").split("\n")[0].strip()
        if not sentence.endswith("."):
            sentence += "."
        return sentence
    except Exception as e:
        print(f"  ✗ Intro-Fehler: {e}")
        return "Die wichtigsten Nachrichten des Tages im Überblick."

# ─────────────────────────────────────────────
# TOP-KATEGORIEN
# ─────────────────────────────────────────────

def select_top_categories(grouped: dict[str, list[dict]], client: Groq,
                          n: int = 5) -> list[str]:
    overview = []
    for cat, arts in grouped.items():
        if cat == "🔥 Sonstiges" or not arts:
            continue
        titles = "; ".join(a["title"] for a in arts[:2])
        overview.append(f"- {cat} ({len(arts)} Artikel): {titles}")

    prompt = f"""Du bist Chefredakteur eines deutschen Nachrichtenbriefs.
Kategorien heute:

{chr(10).join(overview)}

Waehle die {n} wichtigsten Kategorien.
Nur exakte Kategorienamen, eine pro Zeile, keine Erklaerung.
Beispiel:
💰 Wirtschaft
🌍 Aussenpolitik"""

    try:
        text     = _groq_call(client, prompt, max_tokens=150)
        selected = [line.strip() for line in text.strip().split("\n") if line.strip()]
        valid    = [c for c in selected if c in grouped]
        if len(valid) >= 3:
            print(f"  ✓ Top-Kategorien: {', '.join(valid[:n])}")
            return valid[:n]
    except Exception as e:
        print(f"  ⚠ Kategorie-Auswahl fehlgeschlagen ({e}), Fallback")

    sorted_cats = sorted(
        [c for c in grouped if c != "🔥 Sonstiges"],
        key=lambda c: len(grouped[c]),
        reverse=True
    )
    return sorted_cats[:n]

# ─────────────────────────────────────────────
# ZUSAMMENFASSUNGEN
# ─────────────────────────────────────────────

def summarize_with_groq(grouped: dict[str, list[dict]]) -> tuple[str, dict[str, list[str]], list[str], dict[str, list[dict]]]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY nicht gesetzt!")

    client = Groq(api_key=api_key)

    print("  → Top-Kategorien wählen...")
    top_cats = select_top_categories(grouped, client, n=TOP_CATEGORIES_COUNT)

    print("  → Intro generieren...")
    top_grouped = {c: grouped[c] for c in top_cats if c in grouped}
    intro = generate_intro(top_grouped, client, top_cats)
    print(f"  ✓ Intro: {intro[:60]}...")

    summaries:     dict[str, list[str]]  = {}
    selected_links: dict[str, list[dict]] = {}

    for category in top_cats:
        articles = grouped.get(category, [])
        if not articles:
            continue

        # ── Zusammenfassung ──────────────────────────────────────────
        articles_text = "\n".join([
            f"- [{a['source']}] {a['title']}"
            + (f": {a['summary'][:200]}" if a["summary"] else "")
            for a in articles[:8]
        ])

        prompt = f"""Fasse die Nachrichten der Kategorie "{category}" in genau 2 deutschen Stichsaetzen zusammen.

Regeln:
- Genau 2 Stichsaetze, jeder beginnt mit Bullet-Zeichen (•)
- Maximal 1 Zeile pro Stichsatz
- Sachlich, informativ, keine Wertung
- Keine Einleitung, keine Schlussformel

Nachrichten:
{articles_text}

Stichsaetze:"""

        try:
            text = _groq_call(client, prompt, max_tokens=200)
            bullet_points = [
                line.strip()
                for line in text.split("\n")
                if line.strip() and line.strip()[0] in ("•", "-", "*")
            ]
            bullet_points = ["• " + bp.lstrip("•-* ").strip() for bp in bullet_points]
            summaries[category] = bullet_points[:2]
            print(f"  ✓ {category}: {len(summaries[category])} Punkte")
        except Exception as e:
            print(f"  ✗ Fehler bei {category}: {e}")
            summaries[category] = ["• Fehler beim Laden der Zusammenfassung."]

        # ── Link-Auswahl via Groq ─────────────────────────────────────
        print(f"  → Links für {category} wählen...")
        selected_links[category] = _select_links_with_groq(client, category, articles)
        sources = [a["source"] for a in selected_links[category]]
        print(f"  ✓ Links: {', '.join(sources)}")

    return intro, summaries, top_cats, selected_links

# ─────────────────────────────────────────────
# ARCHIV-HTML
# ─────────────────────────────────────────────

def build_archive_html(grouped: dict[str, list[dict]], intro: str,
                       now: datetime, daytime: str) -> str:
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

    daytime_label  = "Morgen" if daytime == "morgen" else "Abend"
    total_articles = sum(len(v) for v in grouped.values())

    FONT         = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    COLOR_NAVY   = "#1b2a3b"
    COLOR_NAVY2  = "#2c3e50"
    COLOR_BLUE   = "#5a7fa0"
    COLOR_LIGHT  = "#a0b4c4"
    COLOR_MUTED  = "#7a9bb5"
    COLOR_BORDER = "#e8e8e8"
    COLOR_TEXT   = "#1c1c1e"
    COLOR_TEXT2  = "#3a3a3c"
    COLOR_LABEL  = "#8fa8bc"

    nav_links = ""
    for cat in grouped:
        anchor = _anchor_id(cat)
        nav_links += (
            f'<a href="#{anchor}" style="display:inline-block;margin:3px 4px;'
            f'font-size:11px;color:{COLOR_LIGHT};text-decoration:none;'
            f'border:1px solid #3a5068;padding:3px 9px;border-radius:2px;">{cat}</a>'
        )

    cat_blocks = ""
    all_cats   = list(grouped.items())
    for idx, (category, articles) in enumerate(all_cats):
        if not articles:
            continue
        anchor        = _anchor_id(category)
        is_last       = (idx == len(all_cats) - 1)
        border_bottom = "none" if is_last else f"2px solid {COLOR_BORDER}"

        rows = ""
        for a in articles:
            if not a.get("link"):
                continue
            rows += (
                f'<div style="display:flex;align-items:baseline;padding:9px 0;'
                f'border-bottom:1px solid #f0f2f4;">'
                f'<span style="flex:0 0 120px;font-size:10px;font-weight:600;'
                f'text-transform:uppercase;letter-spacing:0.6px;color:{COLOR_LABEL};'
                f'padding-right:12px;white-space:nowrap;overflow:hidden;'
                f'text-overflow:ellipsis;">{a["source"]}</span>'
                f'<a href="{a["link"]}" style="flex:1;font-size:13.5px;'
                f'color:{COLOR_TEXT};text-decoration:none;line-height:1.45;">'
                f'{a["title"]}</a>'
                f'</div>'
            )

        # <a name="..."> für Anker-Kompatibilität im Browser (Archiv-Seite)
        cat_blocks += (
            f'<div style="padding:28px 0;border-bottom:{border_bottom};">'
            f'<a name="{anchor}" style="display:block;height:0;overflow:hidden;"></a>'
            f'<div style="display:flex;align-items:center;margin-bottom:16px;'
            f'padding-bottom:10px;border-bottom:2px solid {COLOR_NAVY2};">'
            f'<span style="font-size:16px;font-weight:700;color:{COLOR_NAVY};flex:1;">'
            f'{category}</span>'
            f'<span style="font-size:11px;color:{COLOR_MUTED};">{len(articles)} Artikel</span>'
            f'</div>{rows}</div>'
        )

    intro_plain = re.sub(r"<[^>]+>", "", intro)

    return (
        '<!DOCTYPE html>\n<html lang="de">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'  <title>Tageslage Archiv - {date_str} ({daytime_label})</title>\n'
        f'  <style>body{{margin:0;padding:0;background:#f0f2f4;font-family:{FONT}}}'
        f'a{{color:{COLOR_TEXT}}}a:hover{{opacity:.75}}'
        f'@media(max-width:600px){{.nav-wrap{{display:none}}}}</style>\n'
        '</head>\n<body>\n'
        f'<div style="background:{COLOR_NAVY};padding:36px 24px 28px;text-align:center;">'
        f'<div style="max-width:760px;margin:0 auto;">'
        f'<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;'
        f'color:{COLOR_MUTED};margin-bottom:10px;">Vollständiges Archiv</div>'
        f'<div style="font-size:30px;font-weight:700;color:#fff;margin-bottom:8px;">Tageslage</div>'
        f'<div style="font-size:13px;color:{COLOR_LIGHT};margin-bottom:20px;">'
        f'{date_str} &middot; {daytime_label}-Ausgabe</div>'
        f'<div class="nav-wrap" style="margin-top:16px;line-height:2;">{nav_links}</div>'
        f'</div></div>'
        f'<div style="background:{COLOR_NAVY2};padding:8px 24px;text-align:center;'
        f'font-size:11px;color:{COLOR_MUTED};">'
        f'{len(RSS_FEEDS)}&nbsp;Quellen &middot; {total_articles}&nbsp;Artikel '
        f'&middot; {len(grouped)}&nbsp;Kategorien &middot; KI-kuratiert</div>'
        f'<div style="background:#fff;border-bottom:1px solid {COLOR_BORDER};">'
        f'<div style="max-width:760px;margin:0 auto;padding:20px 24px;">'
        f'<p style="font-size:14px;line-height:1.75;color:{COLOR_TEXT2};'
        f'margin:0;font-style:italic;">{intro_plain}</p></div></div>'
        f'<div style="max-width:760px;margin:0 auto;padding:0 24px 40px;">'
        f'<div style="background:#fff;border:1px solid {COLOR_BORDER};'
        f'border-top:none;padding:0 32px;">{cat_blocks}</div></div>'
        f'<div style="background:{COLOR_NAVY};padding:20px 24px;text-align:center;">'
        f'<p style="font-size:11px;color:{COLOR_MUTED};line-height:1.8;margin:0;">'
        f'Erstellt am {now.strftime("%d.%m.%Y")} um {now.strftime("%H:%M")} Uhr'
        f'&nbsp;&middot;&nbsp;Powered by Nils</p></div>'
        '</body>\n</html>\n'
    )

# ─────────────────────────────────────────────
# NEWSLETTER-HTML
# ─────────────────────────────────────────────

def build_html(intro: str, summaries: dict[str, list[str]],
               grouped: dict[str, list[dict]],
               selected_links: dict[str, list[dict]],
               archive_url: str = "",
               signup_url: str = "") -> str:
    """
    Baut den HTML-Newsletter.
    Platzhalter ##UNSUBSCRIBE_URL## wird in send_email() ersetzt.
    """
    now      = datetime.now()
    daytime  = "Morgen" if now.hour < 13 else "Abend"
    date_str = now.strftime("%A, %d. %B %Y")

    months = {
        "January": "Januar", "February": "Februar", "March": "März",
        "April": "April", "May": "Mai", "June": "Juni",
        "July": "Juli", "August": "August", "September": "September",
        "October": "Oktober", "November": "November", "December": "Dezember",
    }
    days_de = {
        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag", "Friday": "Freitag",
        "Saturday": "Samstag", "Sunday": "Sonntag",
    }
    for en, de in {**months, **days_de}.items():
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

    # ── Intro-Block ──────────────────────────────────────────────────────
    intro_html = (
        f'<tr><td style="padding:20px 32px 18px;border-bottom:2px solid {COLOR_BORDER};">'
        f'<p style="font-family:{FONT};font-size:14px;line-height:1.9;'
        f'color:{COLOR_TEXT2};margin:0;">{intro}</p>'
        f'</td></tr>'
    )

    # ── Kategorien-Blöcke ────────────────────────────────────────────────
    category_blocks = ""
    items = list(summaries.items())
    for idx, (category, bullets) in enumerate(items):
        is_last       = (idx == len(items) - 1)
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
                f'</tr>'
            )

        # Links aus Groq-Auswahl
        mixed = selected_links.get(category, [])
        clean = []
        seen_links: set[str] = set()
        for a in mixed:
            if a["link"] and a["link"] not in seen_links:
                seen_links.add(a["link"])
                clean.append(a)

        links_html = (
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin-top:10px;background:#d4e3ed;border-radius:4px;">'
        )
        for i, a in enumerate(clean):
            is_last_link = (i == len(clean) - 1)
            row_border   = "none" if is_last_link else f"1px solid #bdd0de"
            links_html += (
                f'<tr><td style="padding:5px 12px;border-bottom:{row_border};">'
                f'<a href="{a["link"]}" style="text-decoration:none;font-family:{FONT};'
                f'font-size:12px;line-height:1.4;color:{COLOR_TEXT2};">'
                f'<span style="font-weight:700;color:{COLOR_NAVY};">{a["source"]}:</span>'
                f'&nbsp;{a["title"]}'
                f'</a>'
                f'</td></tr>'
            )
        links_html += '</table>'

        category_blocks += (
            f'<tr><td style="padding:20px 32px 20px;border-bottom:{border_bottom};">'
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
            f'<tr><td style="padding-bottom:10px;border-bottom:2px solid {COLOR_NAVY2};">'
            f'<span style="font-family:{FONT};font-size:15px;font-weight:700;'
            f'color:{COLOR_NAVY};">{category}</span>'
            f'</td></tr>'
            f'<tr><td style="padding-top:10px;padding-bottom:14px;">'
            f'<table cellpadding="0" cellspacing="0" border="0">{bullets_html}</table>'
            f'</td></tr>'
            f'<tr><td>{links_html}</td></tr>'
            f'</table></td></tr>'
        )

    total_articles = sum(len(v) for v in grouped.values())

    # ── Footer ────────────────────────────────────────────────────────────
    footer_html = (
        f'<tr><td style="background:{COLOR_NAVY};padding:20px 32px;text-align:center;'
        f'border-radius:0 0 4px 4px;">'
        f'<p style="font-family:{FONT};font-size:11px;color:{COLOR_MUTED};'
        f'line-height:1.8;margin:0 0 12px;">'
        f'Top-Themen des Tages – kuratiert aus {len(RSS_FEEDS)}&nbsp;Quellen.</p>'
        f'<a href="{ARCHIVE_URL}" style="display:inline-block;font-family:{FONT};'
        f'font-size:12px;font-weight:600;color:#ffffff;text-decoration:none;'
        f'background:{COLOR_BLUE};padding:8px 20px;border-radius:3px;">'
        f'Vollständiges Archiv &amp; alle Kategorien</a>'
        f'<p style="font-family:{FONT};font-size:10px;color:{COLOR_MUTED};'
        f'margin:12px 0 0;line-height:1.8;">'
        f'Automatisch erstellt am {now.strftime("%d.%m.%Y")} um {now.strftime("%H:%M")} Uhr'
        f'&nbsp;&middot;&nbsp;Powered by Nils'
        f'&nbsp;&middot;&nbsp;'
        f'<a href="{signup_url or SIGNUP_URL}" style="font-family:{FONT};font-size:10px;'
        f'color:{COLOR_LIGHT};text-decoration:underline;">Newsletter abonnieren</a>'
        f'</p>'
        f'<p style="font-family:{FONT};font-size:10px;color:{COLOR_MUTED};margin:4px 0 0;">'
        f'<a href="##UNSUBSCRIBE_URL##" style="font-family:{FONT};font-size:10px;'
        f'color:{COLOR_MUTED};text-decoration:underline;">Newsletter abbestellen</a>'
        f'</p>'
        f'</td></tr>'
    )

    # ── Gesamt-HTML ──────────────────────────────────────────────────────
    # Desktop: max-width 680px, zentriert mit Außen-Padding
    # Mobile:  100% Breite, kein Padding (Outlook/Gmail-kompatibel)
    return (
        '<!DOCTYPE html>\n<html lang="de">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light">\n'
        f'  <title>Tageslage - {date_str}</title>\n'
        '  <style>\n'
        '    @media only screen and (max-width: 680px) {\n'
        '      .email-outer { padding: 0 !important; }\n'
        '      .email-body { border-radius: 0 !important; border-left: none !important; border-right: none !important; }\n'
        '    }\n'
        '  </style>\n'
        '</head>\n'
        f'<body style="margin:0;padding:0;background:#f0f2f4;font-family:{FONT};">\n'
        # Äußerer Wrapper – auf Desktop zentriert mit Padding oben/unten
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:#f0f2f4;" class="email-outer">'
        f'<tr><td align="center" style="padding:28px 16px;">\n'
        # Innerer Container – 680px max-width
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="max-width:680px;background:#ffffff;border-radius:6px;'
        f'border:1px solid #d0d8e0;box-shadow:0 2px 8px rgba(0,0,0,0.06);" '
        f'class="email-body">\n'
        # HEADER
        f'<tr><td style="background:{COLOR_NAVY};padding:36px 36px 28px;'
        f'text-align:center;border-radius:6px 6px 0 0;">'
        f'<div style="font-family:{FONT};font-size:10px;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:{COLOR_MUTED};margin-bottom:10px;">'
        f'Dein täglicher Nachrichtenüberblick</div>'
        f'<div style="font-family:{FONT};font-size:30px;font-weight:700;'
        f'color:#ffffff;letter-spacing:-0.5px;margin-bottom:8px;">Tageslage</div>'
        f'<div style="font-family:{FONT};font-size:13px;color:{COLOR_LIGHT};">'
        f'{date_str} &middot; {daytime}-Ausgabe</div>'
        f'</td></tr>\n'
        # META BAR
        f'<tr><td style="background:{COLOR_NAVY2};padding:7px 36px;text-align:center;'
        f'font-family:{FONT};font-size:11px;color:{COLOR_MUTED};">'
        f'{len(RSS_FEEDS)}&nbsp;Quellen &middot; {total_articles}&nbsp;Artikel '
        f'&middot; kuratiert mit KI</td></tr>\n'
        + intro_html
        + category_blocks
        + footer_html +
        '</table>\n</td></tr>\n</table>\n</body>\n</html>'
    )

# ─────────────────────────────────────────────
# E-MAIL VERSENDEN
# ─────────────────────────────────────────────

def send_email(html_template: str, recipient: str,
               unsubscribe_base: str = "") -> None:
    """Sendet den Newsletter an einen einzelnen Empfänger."""
    sender   = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not password:
        raise ValueError("GMAIL_ADDRESS oder GMAIL_APP_PASSWORD nicht gesetzt!")

    if unsubscribe_base:
        unsubscribe_url = unsubscribe_base + "?email=" + urllib.parse.quote(recipient)
    else:
        unsubscribe_url = "#"
    html_content = html_template.replace("##UNSUBSCRIBE_URL##", unsubscribe_url)

    now     = datetime.now()
    daytime = "Morgen" if now.hour < 13 else "Abend"
    subject = f"Tageslage – {now.strftime('%d.%m.%Y')} ({daytime}-Ausgabe)"

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Tageslage <{sender}>"
    msg["To"]      = recipient

    plain = f"Tageslage – {now.strftime('%d.%m.%Y')}\nBitte HTML-Ansicht aktivieren."
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("SMTP-Login fehlgeschlagen – App-Passwort prüfen!")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"SMTP-Fehler: {e}")
    except socket.timeout:
        raise RuntimeError("SMTP-Verbindung timeout.")

# ─────────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"  TAGESLAGE – {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}\n")

    recipient_raw    = os.environ.get("RECIPIENT_EMAIL", "")
    unsubscribe_base = os.environ.get("UNSUBSCRIBE_URL", "")
    signup_url       = os.environ.get("SIGNUP_URL", SIGNUP_URL)
    recipients       = [r.strip() for r in recipient_raw.split(",") if r.strip()]

    if not recipients:
        raise ValueError("RECIPIENT_EMAIL nicht gesetzt!")
    print(f"Empfänger: {len(recipients)}\n")

    print("1/5 – RSS-Feeds laden...")
    articles = fetch_feeds()
    print(f"     {len(articles)} Artikel gesammelt\n")

    print("2/5 – Kategorisieren...")
    grouped = group_by_category(articles)
    for cat, arts in grouped.items():
        print(f"     {cat}: {len(arts)}")
    print()

    print("3/5 – KI-Zusammenfassung mit Groq...")
    intro, summaries, top_cats, selected_links = summarize_with_groq(grouped)
    print()

    now      = datetime.now()
    daytime  = "morgen" if now.hour < 13 else "abend"
    filename = f"{now.strftime('%Y-%m-%d')}-{daytime}.html"
    archive_url = f"{GITHUB_PAGES_BASE_URL}/archiv/{filename}"

    print("4/5 – Archiv-HTML erstellen...")
    archive_html = build_archive_html(grouped, intro, now, daytime)
    archive_path = f"archiv/{filename}"
    os.makedirs("archiv", exist_ok=True)
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(archive_html)
    print(f"     {archive_path} geschrieben\n")

    print("5/5 – Newsletter versenden...")
    html_template = build_html(
        intro, summaries, grouped,
        selected_links=selected_links,
        archive_url=archive_url,
        signup_url=signup_url,
    )

    sent   = 0
    errors = 0
    for recipient in recipients:
        try:
            send_email(html_template, recipient, unsubscribe_base=unsubscribe_base)
            print(f"     ✓ Gesendet: {recipient}")
            sent += 1
        except Exception as e:
            print(f"     ✗ Fehler bei {recipient}: {e}")
            errors += 1

    print(f"\nFertig: {sent} gesendet, {errors} Fehler.\n")


if __name__ == "__main__":
    main()
