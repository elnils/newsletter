#!/usr/bin/env python3
"""
Automatischer KI-Newsletter – Tageslage
Holt RSS-Feeds, kategorisiert mit Punkte+Ausschluss-System, verschickt per E-Mail.
"""

import os
import re
import json
import time
import random
import socket
import smtplib
import urllib.parse
import urllib.request
import urllib.error
import feedparser
from datetime import datetime, timezone, timedelta
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
    "Wirtschaftswoche":       "https://feeds.cms.wiwo.de/rss/schlagzeilen",
    "Manager Magazin":        "https://www.manager-magazin.de/news/index.rss",
    "Tagesspiegel":           "https://www.tagesspiegel.de/contentexport/feed/home",
    "Google Wirtschaft DE":   "https://news.google.com/rss/search?q=wirtschaft+konjunktur+deutschland&hl=de&gl=DE&ceid=DE:de",
    "Google Finanzen DE":     "https://news.google.com/rss/search?q=boerse+aktien+dax&hl=de&gl=DE&ceid=DE:de",
    # ── International Allgemein ────────────────────────────────────────
    "BBC News":               "https://feeds.bbci.co.uk/news/rss.xml",
    "Guardian World":         "https://www.theguardian.com/world/rss",
    "Reuters EN":             "https://news.google.com/rss/search?q=reuters+world+news&hl=en&gl=US&ceid=US:en",
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
    "Guardian Business":      "https://www.theguardian.com/business/rss",
    "Reuters Business":       "https://news.google.com/rss/search?q=reuters+business+markets&hl=en&gl=US&ceid=US:en",
    "WiWo Finanzen":          "https://feeds.cms.wiwo.de/rss/finanzen",
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
    "Tagesspiegel", "Google Wirtschaft DE", "Google Finanzen DE",
    "WiWo Finanzen",
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
MAX_ARTICLES_FOR_SUMMARY = 240   # erhöht: mehr Artikel im Pool = mehr Auswahl pro Kategorie
ARTICLES_PER_CATEGORY    = 18    # wie viele Artikel pro Kategorie an die KI gehen (mehr Auswahl)
TOP_CATEGORIES_COUNT     = 5
FEED_TIMEOUT             = 15
GROQ_TIMEOUT             = 30
GROQ_RETRIES             = 1

# Groq-Modell: "openai/gpt-oss-120b" (Reasoning-Modell, klueger) oder
# "llama-3.3-70b-versatile" (schneller, kein Reasoning). Hier umstellbar.
GROQ_MODEL               = "openai/gpt-oss-120b"
# reasoning_effort: nur fuer gpt-oss-Modelle relevant ("low"/"medium"/"high").
# "low" = kurz nachdenken, spart Tokens + Zeit. Bei Llama wird es ignoriert.
GROQ_REASONING_EFFORT    = "low"
# Fallback-Modell: wird automatisch genutzt, sobald GROQ_MODEL einmal im
# Lauf versagt (Fehler ODER leere Antwort). Dann bleibt es bis Lauf-Ende dabei.
GROQ_FALLBACK_MODEL      = "llama-3.3-70b-versatile"

SIGNUP_URL    = "https://forms.gle/LSavK3JVp3aAsLGm9"
ARCHIVE_URL   = "https://elnils.github.io/newsletter/"

GITHUB_PAGES_BASE_URL = os.environ.get(
    "PAGES_BASE_URL",
    "https://elnils.github.io/newsletter"
).rstrip("/")

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

MAX_ARTICLE_AGE_HOURS  = 18   # Artikel älter als X Stunden werden gefiltert
DUPLICATE_THRESHOLD    = 0.45 # Jaccard-Schwelle: niedriger = strenger gegen Dopplungen
HISTORY_LOOKBACK_ISSUES = 3   # so viele letzte Ausgaben gegen Wiederholung pruefen
HISTORY_DEDUP_THRESHOLD = 0.55 # Aehnlichkeit zu alten Titeln, ab der gefiltert wird

# Ausgabe-Verzeichnis fuer das JSON-Archiv. GitHub Pages liest aus der
# main-WURZEL, daher liegt data/ in der Repo-Wurzel. Da newsletter.py in
# scripts/ laeuft, ist das eine Ebene hoeher → "../data".
# Per Env DOCS_DATA_DIR ueberschreibbar.
DOCS_DATA_DIR          = os.environ.get("DOCS_DATA_DIR", "../data")
ARCHIVE_RETENTION_DAYS = 365  # Ausgaben aelter als 1 Jahr werden geloescht


def load_recent_titles(data_dir: str = DOCS_DATA_DIR,
                       lookback: int = HISTORY_LOOKBACK_ISSUES) -> set[str]:
    """
    Liest die letzten `lookback` Ausgaben aus dem JSON-Archiv und gibt die
    normalisierten Titel ihrer Artikel zurueck. Damit lassen sich Themen
    filtern, die in den Vortagen schon dran waren. Leere Menge wenn kein
    Archiv vorhanden (erster Lauf).
    """
    index_path = os.path.join(data_dir, "index.json")
    if not os.path.exists(index_path):
        return set()
    try:
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
    except Exception:
        return set()

    titles: set[str] = set()
    for entry in index[:lookback]:   # index ist bereits neueste-zuerst sortiert
        fpath = os.path.join(data_dir, entry.get("datei", ""))
        try:
            with open(fpath, encoding="utf-8") as f:
                ausgabe = json.load(f)
        except Exception:
            continue
        # Titel aus der vollstaendigen Artikelliste der Ausgabe ziehen
        for cat_rows in ausgabe.get("alle_artikel", {}).values():
            for row in cat_rows:
                t = _normalize_title(row.get("titel", ""))
                if t:
                    titles.add(t)
    if titles:
        print(f"  ℹ {len(titles)} Titel aus {min(lookback, len(index))} Vorausgabe(n) geladen (Wiederholungsfilter)")
    return titles


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _is_too_old(entry) -> bool:
    """True wenn Artikel älter als MAX_ARTICLE_AGE_HOURS. False wenn kein Datum (Fallback: behalten)."""
    for field in ("published_parsed", "updated_parsed"):
        ts = getattr(entry, field, None)
        if ts:
            try:
                pub = datetime(*ts[:6], tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - pub) > timedelta(hours=MAX_ARTICLE_AGE_HOURS)
            except Exception:
                pass
    return False  # kein Datum → Artikel behalten


def _token_overlap(a: str, b: str) -> float:
    """Jaccard-Koeffizient der Wort-Tokens (0.0–1.0)."""
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _is_near_duplicate(norm_title: str, seen_norms: set[str],
                       threshold: float = DUPLICATE_THRESHOLD) -> bool:
    """True wenn ein ähnlicher Titel bereits gesehen wurde."""
    for seen in seen_norms:
        if _token_overlap(norm_title, seen) >= threshold:
            return True
    return False


def fetch_feeds(recent_titles: set[str] | None = None) -> list[dict]:
    articles    = []
    seen_titles = set()
    recent_titles = recent_titles or set()
    repeat_count_total = 0

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

                count       = 0
                old_count   = 0
                dup_count   = 0
                for entry in feed.entries:
                    if count >= MAX_ARTICLES_PER_FEED:
                        break

                    # ── Altersfilter ───────────────────────────────────
                    if _is_too_old(entry):
                        old_count += 1
                        continue

                    title   = entry.get("title", "").strip()
                    summary = entry.get("summary", entry.get("description", "")).strip()
                    link    = entry.get("link", "")
                    # 600 statt 400: mehr Originalkontext für die KI → weniger Halluzinationen
                    summary = summary[:600] if summary else ""

                    if not title:
                        continue

                    norm = _normalize_title(title)

                    # ── Exakt-Duplikat ─────────────────────────────────
                    if norm in seen_titles:
                        dup_count += 1
                        continue

                    # ── Fuzzy-Duplikat (Jaccard) ──────────────────────
                    if _is_near_duplicate(norm, seen_titles):
                        dup_count += 1
                        continue

                    # ── Wiederholung aus Vorausgaben (Tagesfilter) ────
                    if recent_titles and _is_near_duplicate(
                        norm, recent_titles, threshold=HISTORY_DEDUP_THRESHOLD
                    ):
                        repeat_count_total += 1
                        continue

                    seen_titles.add(norm)
                    articles.append({
                        "source":  source,
                        "title":   title,
                        "summary": summary,
                        "link":    link,
                    })
                    count += 1

                extras = []
                if old_count: extras.append(f"{old_count} zu alt")
                if dup_count: extras.append(f"{dup_count} Dopplung")
                note = f" ({', '.join(extras)})" if extras else ""

                print(f"  ✓ {source}: {count} Artikel{note}")

            except Exception as e:
                print(f"  ✗ {source}: {e}")

    finally:
        socket.setdefaulttimeout(old_timeout)

    if repeat_count_total:
        print(f"  ℹ {repeat_count_total} Artikel als Wiederholung aus Vorausgaben gefiltert")

    return articles[:MAX_ARTICLES_FOR_SUMMARY]

# ─────────────────────────────────────────────
# KATEGORISIERUNG
# ─────────────────────────────────────────────

def _kw_match(kw: str, text: str) -> bool:
    if " " in kw:
        return kw in text
    return bool(re.search(r"\b" + re.escape(kw) + r"\b", text))


# Titel-Treffer zaehlen mehr als Summary-Treffer: der Titel definiert das
# Hauptthema, die Summary liefert nur Kontext. Verhindert in den meisten
# Faellen, dass z.B. eine "Volksabstimmung ueber X" in Wirtschaft statt
# Wahlen landet. (Reines Keyword-System hat Grenzen bei mehrdeutigen Themen.)
TITLE_WEIGHT_MULTIPLIER = 3.0


def categorize_article(article: dict) -> str:
    title_text   = article["title"].lower()
    summary_text = article["summary"].lower()
    scores: dict[str, float] = {}

    for category, config in CATEGORIES.items():
        if category == "🔥 Sonstiges":
            continue
        # Ausschluss prüft Titel UND Summary
        full_text = title_text + " " + summary_text
        if any(_kw_match(kw, full_text) for kw in config.get("exclude", [])):
            continue

        score = 0.0
        for kw, weight in config["keywords"].items():
            if _kw_match(kw, title_text):
                score += weight * TITLE_WEIGHT_MULTIPLIER   # Titel-Treffer = doppelt
            elif _kw_match(kw, summary_text):
                score += weight                              # Summary-Treffer = normal
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

# Zentraler Anti-Halluzinations-Block – wird in Intro- und Summary-Prompt
# eingefügt. Verhindert dass die KI veraltete Amtsträger, Zahlen oder
# Ereignisse aus den Trainingsdaten "ergänzt", die im Quelltext nicht stehen.
QUELLENTREUE_REGELN = """QUELLENTREUE (oberste Prioritaet, ueberschreibt alle anderen Regeln):
- Heute ist der {today}. Deine Trainingsdaten sind veraltet.
- Verwende AUSSCHLIESSLICH Fakten (Namen, Aemter, Zahlen, Daten, Orte) die WOERTLICH in den Quelltexten unten stehen.
- Wenn ein Name im Quelltext steht: gerne uebernehmen, exakt wie geschrieben.
- Wenn ein Amt erwaehnt wird, der Name aber NICHT im Quelltext steht:
  schreibe die INSTITUTION statt der Person (vermeidet falsche Namen UND falsches Geschlecht).
  Beispiele:
    Quelltext "Wirtschaftsminister kuendigt an" → "Das Wirtschaftsministerium kuendigt an"
    Quelltext "Bundeskanzler reist nach Paris" → "Die Bundesregierung reist nach Paris" oder "Das Bundeskanzleramt..."
    Quelltext "US-Praesident trifft Merz" → "Das Weisse Haus trifft Merz" oder "Die US-Regierung..."
    Quelltext "russischer Praesident droht" → "Der Kreml droht" oder "Moskau droht"
    Quelltext "EU-Kommissionspraesident kuendigt an" → "Die EU-Kommission kuendigt an"
- Niemals Anreden wie "der/die" oder Genderformen ("Minister:in") verwenden – immer Institution.

NIEMALS META-KOMMENTARE schreiben:
- VERBOTEN: "ist nicht erwaehnt", "laut Quelltext", "Quelle sagt", "im Artikel steht"
- VERBOTEN: "unklar bleibt", "nicht spezifiziert", "ohne Namen genannt"
- Schreibe direkt die Nachricht – kommentiere NIE was du nicht weisst.
- Wenn du etwas nicht weisst: lass es weg. Nicht ueber das Weglassen schreiben.

KEINE LEEREN PHRASEN (sehr wichtig):
- VERBOTEN: "die internationale Staatengemeinschaft", "Beobachter sehen", "Experten warnen"
- VERBOTEN: "negative Auswirkungen", "globale Wirtschaft", "weitreichende Folgen"
- VERBOTEN: vage Subjekte ohne konkreten Akteur, vage Verben ohne konkrete Handlung
- Schreibe konkret: WER macht WAS mit WELCHEM Effekt – oder lass den Satz weg.

LAENDER KURZ HALTEN (Platz sparen):
- Nutze kurze, gaengige Bezeichnungen: USA, EU, UK, China, Russland, Israel, Iran, Ukraine.
- NICHT ausschreiben: "Vereinigte Staaten von Amerika" → "USA", "Volksrepublik China" → "China", "Vereinigtes Koenigreich" → "UK".
- Adjektive kurz: "US-", "EU-", "UK-" als Praefix ("US-Zoelle", "EU-Gipfel"), nicht "amerikanische Zoelle".
- KEINE kryptischen Codes wie "DEU" oder "GBR" – nur etablierte Kuerzel.

UEBERSETZUNG (viele Quellen sind englisch):
- Schreibe IMMER fluessiges, idiomatisches Deutsch – nie woertlich aus dem Englischen uebersetzt.
- Englische Begriffe ins Deutsche uebertragen, NICHT stehen lassen:
  "lawmakers" → "Abgeordnete", "officials" → "Behoerden/Beamte", "bill" → "Gesetzentwurf",
  "administration" → "Regierung", "billion" → "Milliarde" (nicht "Billion"!), "trillion" → "Billion".
- ACHTUNG falsche Freunde: englisch "billion" = deutsch "Milliarde"; englisch "trillion" = deutsch "Billion".
- Eigennamen, Firmen und Institutionen bleiben im Original (z.B. "Federal Reserve", "Supreme Court", "House of Representatives").
- Keine englische Satzstellung, keine Anglizismen wie "realisieren" (statt "erkennen"), "kontrollieren" (statt "steuern")."""

# Modul-weites Flag: aktuell aktives Modell. Startet mit GROQ_MODEL.
# Sobald GROQ_MODEL einmal versagt, wird dies dauerhaft auf den Fallback
# gesetzt – fuer den Rest des Laufs.
_active_model = GROQ_MODEL


def _one_groq_attempt(client: Groq, prompt: str, model: str, max_tokens: int) -> str:
    """Ein einzelner API-Versuch mit gegebenem Modell. Wirft bei Fehler."""
    extra = {}
    effective_max = max_tokens
    if "gpt-oss" in model:
        extra["reasoning_effort"] = GROQ_REASONING_EFFORT
        # Reasoning-Modelle verbrauchen Tokens fuers "Nachdenken" BEVOR die
        # Antwort kommt. Ohne Puffer kaeme die Antwort leer zurueck.
        effective_max = max_tokens + 1200

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=effective_max,
        temperature=0.3,
        timeout=GROQ_TIMEOUT,
        **extra,
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""


def _groq_call(client: Groq, prompt: str, max_tokens: int = 200) -> str:
    """
    Ruft das aktive Modell auf (mit Retries). Versagt das primaere Modell
    (Fehler ODER leere Antwort), wird EINMALIG und dauerhaft auf
    GROQ_FALLBACK_MODEL umgeschaltet.
    """
    global _active_model

    # ── Versuch mit aktuell aktivem Modell (inkl. Retries) ────────────
    last_error = None
    for attempt in range(GROQ_RETRIES + 1):
        try:
            result = _one_groq_attempt(client, prompt, _active_model, max_tokens)
            if result:
                return result
            last_error = "leere Antwort"
            break  # leere Antwort → kein Retry, direkt zum Fallback
        except Exception as e:
            last_error = e
            if attempt < GROQ_RETRIES:
                print(f"  ↻ Retry ({_active_model}): {e}")
                time.sleep(2)

    # ── Umschalten auf Fallback, falls noch nicht geschehen ───────────
    if _active_model != GROQ_FALLBACK_MODEL:
        print(f"  ⚠ {_active_model} versagt ({last_error}) → Wechsel auf {GROQ_FALLBACK_MODEL}")
        _active_model = GROQ_FALLBACK_MODEL
        try:
            result = _one_groq_attempt(client, prompt, _active_model, max_tokens)
            if result:
                return result
            print(f"  ✗ Auch {GROQ_FALLBACK_MODEL} lieferte leere Antwort")
            return ""
        except Exception as e:
            print(f"  ✗ Auch Fallback {GROQ_FALLBACK_MODEL} versagt: {e}")
            raise

    # Bereits auf Fallback und trotzdem fehlgeschlagen
    if isinstance(last_error, Exception):
        raise last_error
    return ""

# ─────────────────────────────────────────────
# QUELLEN-MIXING
# ─────────────────────────────────────────────

def _select_links_with_groq(client: Groq, category: str,
                            articles: list[dict], max_total: int = 5,
                            summary_context: str = "") -> list[dict]:
    """
    Lässt Groq die relevantesten und quellenmäßig vielfältigsten Artikel
    aus der Kategorie auswählen. Groq gibt Indizes zurück (0-basiert).
    summary_context: die erzeugte Zusammenfassung – damit die Links zu den
    im Text genannten Themen passen (Konsistenz).
    Fallback: einfaches Shuffeln mit max 2x pro Quelle.
    """
    if not articles:
        return []

    # Kandidaten: begrenzt auf ARTICLES_PER_CATEGORY – genug Auswahl, nicht zu viel Token-Verbrauch
    candidates = articles[:ARTICLES_PER_CATEGORY]

    lines = "\n".join(
        f"{i}: [{a['source']}] {a['title']}"
        for i, a in enumerate(candidates)
    )

    # Wenn eine Zusammenfassung vorliegt: Links sollen zu deren Themen passen
    kontext_block = ""
    if summary_context.strip():
        kontext_block = f"""
Die Zusammenfassung dieser Kategorie behandelt diese Themen:
"{summary_context.strip()}"

WICHTIG: Waehle bevorzugt Artikel, die zu diesen Themen passen – die Leser
sollen zu dem weiterlesen koennen, was im Text steht.
"""

    prompt = f"""Du kuratierst Links für die Newsletter-Kategorie "{category}".
{kontext_block}
Wähle {max_total} Artikel aus. Regeln:
- Passend zu den oben genannten Themen (falls angegeben)
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
    Generiert zwei flüssige deutsche Sätze, die die wichtigsten Themen
    des Tages zusammenfassen. Kein HTML, keine Links.
    """
    top_topics = []
    for cat in top_cats[:6]:
        articles = grouped.get(cat, [])
        for a in articles[:2]:
            top_topics.append(f"[{cat}] {a['title']}")

    topics_text = "\n".join(f"- {t}" for t in top_topics)

    today_str = datetime.now().strftime("%d.%m.%Y")
    quellentreue = QUELLENTREUE_REGELN.format(today=today_str)

    prompt = f"""Du schreibst die Einleitung eines deutschen Nachrichten-Newsletters.

{quellentreue}

Schreibe GENAU ZWEI deutsche Saetze, die die wichtigsten Themen des Tages benennen.

STRIKTE Regeln:
- Satz 1: das wichtigste Thema des Tages, konkret mit Fakten.
- Satz 2: das zweitwichtigste Thema ODER ein verbundener Aspekt des ersten.
- Laenge flexibel (ca. 12-28 Woerter je Satz): so lang wie noetig fuer Klarheit, so kurz wie moeglich.
- Bei Personen IMMER die Rolle/Position nennen, damit der Leser sie einordnen kann:
  "CSU-Vize Weber" statt nur "Weber", "EZB-Chefin Lagarde" statt nur "Lagarde",
  "US-Verteidigungsminister Hegseth" statt nur "Hegseth".
- Pro Satz MAXIMAL 2 Subjekte – nicht zusammenstopfen. Lieber klar als ueberladen.
- Jeder Satz startet mit einem konkreten Subjekt – NIE mit "Die Lage", "Es", "Der Tag", "Heute"
- VERBOTEN: "gepragt von", "im Zeichen von", "Debatten", "Diskussionen", "Entwicklungen", "Themen", "Lage", "Geschehen", "Spannungen"

GUTE Beispiele (zwei Saetze, Rollen genannt, Laender kurz):
"EZB-Chefin Lagarde senkt den Leitzins um 25 Basispunkte; der DAX legt um 1,2 Prozent zu. Das Weisse Haus kuendigt zugleich neue Zoelle auf EU-Stahl an."
"Kanzler Merz praesentiert den Bundeshaushalt 2026, waehrend CSU-Vize Weber die Schuldenbremse verteidigt. In der Ukraine stocken die Waffenstillstandsgespraeche erneut."

SCHLECHTE Beispiele – NIEMALS so:
"Die Innenpolitik ist gepragt von Debatten und Diskussionen..."
"Das Weisse Haus droht mit Zoellen, waehrend die Bundesregierung den UN-Sicherheitsrat anpeilt und der IMF warnt."
  → drei unverbundene Themen in einem Satz, klingt zusammengestopft
"Weber kritisiert Soeder."
  → Rolle fehlt (wer ist Weber?), kein Inhalt

Schlagzeilen:
{topics_text}

Zwei Saetze:"""

    try:
        text = _groq_call(client, prompt, max_tokens=120)
        # Mehrzeilige Antwort zu Fliesstext zusammenfuehren, Anfuehrungszeichen weg
        text = text.strip().strip('"').strip("'")
        text = " ".join(line.strip() for line in text.split("\n") if line.strip())
        text = re.sub(r"\s+", " ", text).strip()
        if text and not text.endswith((".", "!", "?")):
            text += "."
        return text or "Die wichtigsten Nachrichten des Tages im Überblick."
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
    global _active_model
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY nicht gesetzt!")

    client = Groq(api_key=api_key)

    # Aktives Modell auf das primaere zuruecksetzen (falls Funktion mehrfach läuft)
    _active_model = GROQ_MODEL
    print(f"  → Modell: {GROQ_MODEL} (Fallback: {GROQ_FALLBACK_MODEL})")

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
        # Anzahl Stichsaetze an Artikelzahl koppeln: 1 Artikel → 1 Satz,
        # ab 2 Artikeln → 2 Saetze. Verhindert mit Floskeln aufgefuellte
        # zweite Bullets bei duennen Kategorien.
        n_bullets = 1 if len(articles) == 1 else 2

        # 400 Zeichen Summary (statt 200): mehr Originalkontext = weniger Halluzinationen
        articles_text = "\n".join([
            f"- [{a['source']}] {a['title']}"
            + (f": {a['summary'][:400]}" if a["summary"] else "")
            for a in articles[:ARTICLES_PER_CATEGORY]
        ])

        today_str = datetime.now().strftime("%d.%m.%Y")
        quellentreue = QUELLENTREUE_REGELN.format(today=today_str)

        satz_wort = "einem deutschen Stichsatz" if n_bullets == 1 else "genau 2 deutschen Stichsaetzen"
        regel_anzahl = (
            "- Genau 1 Stichsatz, beginnt mit Bullet-Zeichen (•)"
            if n_bullets == 1 else
            "- Genau 2 Stichsaetze, jeder beginnt mit Bullet-Zeichen (•)"
        )

        # Kategorie-spezifischer Zusatz: Finanzen/Wirtschaft brauchen mehr Fachtiefe
        fach_zusatz = ""
        if category in ("📊 Finanzen & Märkte", "💰 Wirtschaft"):
            fach_zusatz = """

FACHLICHE TIEFE (Finanzen/Wirtschaft – besonders wichtig):
- Bei Firmen IMMER kurz sagen, was sie tun: "der Chiphersteller Nvidia", "der Triebwerksbauer MTU", "die Direktbank ING" – nie nur den Namen.
- Bei Zinspolitik praezise und verstaendlich: WER (EZB/Fed), WAS (anheben/senken/halten), um WIE VIEL (Basispunkte/Prozent), auf WELCHES Niveau, und WARUM (Inflation/Konjunktur).
  FALSCH: "Die Zinspolitik bleibt im Fokus der Maerkte." (nichtssagend)
  RICHTIG: "Die EZB haelt den Leitzins bei 2,5 Prozent und begruendet das mit der hartnaeckigen Kerninflation."
- Sage IMMER "Leitzins", nicht "Hauptrefinanzierungssatz" oder "Hauptrefinanzierungsgeschaeft" – das gelaeufige Wort, nicht der Fachterminus.
- KEINE konstruierten Ursachenketten. Verknuepfe Zins, Inflation und Ausloeser NUR, wenn alle drei Glieder so im Quelltext stehen.
  FALSCH (so NIEMALS): "Die EZB erhoeht den Hauptrefinanzierungssatz auf 2,25 Prozent, um die durch die Nahost-Energiekrise angetriebene Inflation zu daempfen."
    → Dreifach-Kausalkette (Zins ← Inflation ← Nahost-Energie) ist konstruiert und sperrig.
  RICHTIG: "Die EZB hebt den Leitzins auf 2,25 Prozent an und reagiert damit auf die gestiegene Inflation."
    → nur der Zusammenhang, der wirklich belegt ist; kurz und klar.
- Zahlen einordnen: nicht nur "der DAX faellt", sondern "der DAX faellt um 2,1 Prozent auf 18.400 Punkte".
- Relevanz herstellen: WARUM ist das fuer Anleger oder die Wirtschaft wichtig?

NUR DEUTSCH – englische Finanzbegriffe IMMER uebersetzen (haeufiger Fehler!):
- Schreibe NIEMALS englische Saetze oder englische Fachbegriffe. Alles auf Deutsch.
  FALSCH (so NIEMALS): "Federal Reserve expectations raise US bond yields, market prices possible rate hike of 25 basis points pushing 10-year yield above 4%."
  RICHTIG: "Die Erwartung steigender US-Leitzinsen treibt die Renditen US-amerikanischer Staatsanleihen; die Maerkte preisen eine moegliche Anhebung um 25 Basispunkte ein, die Rendite zehnjaehriger Anleihen steigt ueber 4 Prozent."
- Uebersetzungstabelle Finanzbegriffe:
  "Federal Reserve / the Fed" → "die US-Notenbank Fed", "bond yield" → "Anleiherendite",
  "rate hike" → "Zinsanhebung", "rate cut" → "Zinssenkung", "basis points" → "Basispunkte",
  "yield" → "Rendite", "Treasury" → "US-Staatsanleihe", "market prices in" → "die Maerkte preisen ein",
  "earnings" → "Quartalszahlen/Gewinn", "guidance" → "Prognose", "sell-off" → "Ausverkauf".
- Eigennamen bleiben: "Federal Reserve" als Institution ok, aber dann deutsch eingebettet ("die US-Notenbank Federal Reserve")."""

        prompt = f"""Fasse die Nachrichten der Kategorie "{category}" in {satz_wort} zusammen.

{quellentreue}

Regeln:
{regel_anzahl}
- Jeder Stichsatz: 15-30 Woerter, ein VOLLSTAENDIGER, fuer sich allein verstaendlicher Satz.
- Sachlich, informativ, keine Wertung
- Keine Einleitung, keine Schlussformel
- Bei Aemtern ohne Namen im Quelltext: Institution statt Person ("Das Wirtschaftsministerium", "Das Weisse Haus", "Die Bundesregierung", "Der Kreml")
- Bei auslaendischen Amtstraegern IMMER das Land voranstellen: "US-Verteidigungsminister Hegseth" (nicht nur "Verteidigungsminister Hegseth"), "franzoesischer Praesident Macron", "britischer Premier Starmer"{fach_zusatz}

AUSWAHL (wichtig):
- Waehle nur UEBERREGIONAL bedeutsame Nachrichten: Bundes-/EU-/Weltpolitik, grosse Konzerne, gesamtwirtschaftliche Themen.
- IGNORIERE rein lokale oder einzelbetriebliche Meldungen (z.B. "Logistikzentrum einer Handelskette", "Stadtrat beschliesst", "Filiale schliesst") – auch wenn sie in der Liste stehen.
- JEDES Thema nur EINMAL: Wenn mehrere Schlagzeilen dasselbe Ereignis behandeln (z.B. dieselbe EZB-Zinsentscheidung aus drei Quellen), fasse sie zu EINEM Stichsatz zusammen – niemals zwei Stichsaetze zum selben Ereignis.

SATZBAU (sehr wichtig – haeufige Fehler vermeiden):
- Jeder Satz muss ALLEIN verstaendlich sein. Keine abgehackten Fragmente.
  FALSCH: "CSU-Vize Weber kritisiert Soeder ohne vorbereiteten Plan."
    → "ohne vorbereiteten Plan" haengt sinnlos in der Luft – WAS hat keinen Plan?
  RICHTIG: "CSU-Vize Weber wirft Soeder vor, die Stromsteuer-Senkung ohne Gegenfinanzierung zu fordern."
- KEINE konstruierten oder zirkulaeren Kausalzusaetze. Haenge NICHT "was X beeinflusst" an, wenn es nicht im Quelltext steht.
  FALSCH: "Chinas Xi besucht Nordkorea, was die Verhandlungsposition gegenueber Nordkorea beeinflusst."
    → tautologisch (Nordkorea-Besuch beeinflusst Nordkorea-Position) und erfunden.
  RICHTIG: "Chinas Staatschef Xi reist erstmals seit 2019 nach Nordkorea und trifft Machthaber Kim."
- Nenne einen Effekt NUR, wenn er konkret im Quelltext steht. Sonst beschreibe einfach das Ereignis.
- EIN Satz = EIN Kerngedanke. Stopfe nicht mehrere Ereignisse in einen Schachtelsatz. Lieber zwei kurze Saetze oder das Nebensaechliche weglassen.
  FALSCH (so NIEMALS): "Das Weisse Haus verkuendet, dass die USA kurz vor einem Abkommen mit dem Iran stehen und gleichzeitig die geplanten Angriffe auf den Iran absagen, wodurch die Oelpreise fallen."
    → drei Ereignisse (Abkommen nahe + Angriffe abgesagt + Oelpreise) in einem verschachtelten Satz mit konstruiertem "wodurch".
  RICHTIG: "Die USA stehen laut Weissem Haus kurz vor einem Atomabkommen mit dem Iran und setzen geplante Militaerschlaege aus."
    → ein klarer Kerngedanke; der Oelpreis-Effekt entfaellt, wenn er nicht zentral belegt ist.

SCHLECHTE Beispiele – NIEMALS so:
"• Die internationale Staatengemeinschaft warnt vor negativen Auswirkungen auf die globale Wirtschaft."
  → vages Subjekt, vages Verb, kein Fakt
"• Beobachter sehen weitreichende Folgen fuer den Markt."
  → keine konkrete Information

GUTE Beispiele:
"• Das Weisse Haus verhaengt 25-Prozent-Zoelle auf EU-Stahlimporte ab Juli und trifft damit vor allem deutsche Hersteller."
"• Der IMF senkt seine Wachstumsprognose fuer die Eurozone auf 0,8 Prozent und nennt die Handelskonflikte als Hauptgrund."

Nachrichten:
{articles_text}

Stichsaetze:"""

        try:
            text = _groq_call(client, prompt, max_tokens=320)
            bullet_points = [
                line.strip()
                for line in text.split("\n")
                if line.strip() and line.strip()[0] in ("•", "-", "*")
            ]
            bullet_points = ["• " + bp.lstrip("•-* ").strip() for bp in bullet_points]
            if bullet_points:
                summaries[category] = bullet_points[:n_bullets]
                print(f"  ✓ {category}: {len(summaries[category])} Punkte")
            else:
                # Leere Antwort (z.B. Reasoning-Budget aufgebraucht) → Kategorie überspringen
                print(f"  ⚠ {category}: leere Antwort, übersprungen")
                continue
        except Exception as e:
            print(f"  ✗ Fehler bei {category}: {e}")
            summaries[category] = ["• Fehler beim Laden der Zusammenfassung."]

        # ── Link-Auswahl via Groq ─────────────────────────────────────
        # Die erzeugte Zusammenfassung wird als Kontext uebergeben, damit die
        # Links zu den im Text genannten Themen passen (Text-Link-Konsistenz).
        print(f"  → Links für {category} wählen...")
        summary_context = " ".join(summaries.get(category, []))
        selected_links[category] = _select_links_with_groq(
            client, category, articles, summary_context=summary_context
        )
        sources = [a["source"] for a in selected_links[category]]
        print(f"  ✓ Links: {', '.join(sources)}")

    if _active_model != GROQ_MODEL:
        print(f"  ℹ Hinweis: Lauf auf Fallback-Modell {_active_model} beendet")

    return intro, summaries, top_cats, selected_links

# ─────────────────────────────────────────────
# ARCHIV ALS JSON (GitHub Pages, docs/)
# ─────────────────────────────────────────────


def build_archive_json(grouped: dict[str, list[dict]], intro: str,
                       summaries: dict[str, list[str]],
                       selected_links: dict[str, list[dict]],
                       history_fact: str, history_url: str,
                       now: datetime, daytime: str,
                       destatis_fact: str = "", destatis_url: str = "",
                       destatis_zahl: str = "", wm_info: dict | None = None) -> str:
    """
    Schreibt die aktuelle Ausgabe als JSON nach docs/data/ und pflegt
    docs/data/index.json (Liste aller Ausgaben fuer die Archiv-Webseite).
    Loescht Ausgaben aelter als ARCHIVE_RETENTION_DAYS.
    Gibt den Basisnamen der Ausgabe zurueck (z.B. "2026-06-10-morgen").
    """
    os.makedirs(DOCS_DATA_DIR, exist_ok=True)

    datum    = now.strftime("%Y-%m-%d")
    basename = f"{datum}-{daytime}"
    fname    = f"{basename}.json"
    fpath    = os.path.join(DOCS_DATA_DIR, fname)

    # ── Newsletter-Inhalte (Zusammenfassungen + kuratierte Links) ──────
    kategorien = []
    for cat, bullets in summaries.items():
        links = [
            {"quelle": a["source"], "titel": a["title"], "url": a["link"]}
            for a in selected_links.get(cat, []) if a.get("link")
        ]
        kategorien.append({"name": cat, "punkte": bullets, "links": links})

    # ── Vollstaendige Artikelliste (alle Kategorien, kompakt) ──────────
    alle_artikel = {}
    for cat, arts in grouped.items():
        rows = [
            {"quelle": a["source"], "titel": a["title"], "url": a["link"]}
            for a in arts if a.get("link")
        ]
        if rows:
            alle_artikel[cat] = rows

    ausgabe = {
        "datum":      datum,
        "zeit":       daytime,
        "erstellt":   now.strftime("%d.%m.%Y %H:%M"),
        "intro":      intro,
        "wikipedia":  {"text": history_fact, "url": history_url},
        "destatis":   {"zahl": destatis_zahl, "text": destatis_fact, "url": destatis_url},
        "wm":         wm_info or {},
        "kategorien": kategorien,
        "alle_artikel": alle_artikel,
    }
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(ausgabe, f, ensure_ascii=False, indent=1)

    # ── index.json pflegen ─────────────────────────────────────────────
    index_path = os.path.join(DOCS_DATA_DIR, "index.json")
    index: list[dict] = []
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = []

    # Suchtext: Intro + alle Stichpunkte + beide Datumsformate (lowercase)
    datum_de = now.strftime("%d.%m.%Y")
    suchtext = " ".join(
        [intro, datum, datum_de]
        + [b for k in kategorien for b in k["punkte"]]
        + [k["name"] for k in kategorien]
    ).lower()

    eintrag = {
        "datei": fname,
        "datum": datum,
        "zeit":  daytime,
        "intro": intro,
        "suchtext": suchtext,
    }
    # Re-Run derselben Ausgabe ersetzt den alten Eintrag
    index = [e for e in index if e.get("datei") != fname]
    index.append(eintrag)

    # ── Aufbewahrung: aelter als ARCHIVE_RETENTION_DAYS loeschen ───────
    cutoff = (now - timedelta(days=ARCHIVE_RETENTION_DAYS)).strftime("%Y-%m-%d")
    keep, drop = [], []
    for e in index:
        (keep if e.get("datum", "") >= cutoff else drop).append(e)
    for e in drop:
        try:
            os.remove(os.path.join(DOCS_DATA_DIR, e["datei"]))
        except OSError:
            pass
    if drop:
        print(f"     {len(drop)} alte Ausgabe(n) geloescht (>1 Jahr)")

    # Neueste zuerst (Datum absteigend, Abend vor Morgen am selben Tag)
    def _rank(e):
        return (e.get("datum", ""), 1 if e.get("zeit") == "abend" else 0)
    index = sorted(keep, key=_rank, reverse=True)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)

    return basename

# ─────────────────────────────────────────────
# NEWSLETTER-HTML
# ─────────────────────────────────────────────

def build_html(intro: str, summaries: dict[str, list[str]],
               grouped: dict[str, list[dict]],
               selected_links: dict[str, list[dict]],
               archive_url: str = "",
               signup_url: str = "",
               history_fact: str = "",
               history_url: str = "",
               destatis_fact: str = "",
               destatis_url: str = "",
               destatis_zahl: str = "",
               wm_info: dict | None = None) -> str:
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

    # ── "Heute vor X Jahren" – nur wenn vorhanden ─────────────────────────
    history_html = ""
    if history_fact:
        # Wenn ein Wikipedia-Link da ist: ganzen Fakt anklickbar machen
        if history_url:
            fact_html = (
                f'<a href="{history_url}" style="color:{COLOR_TEXT2};'
                f'text-decoration:none;border-bottom:1px solid {COLOR_LIGHT};">'
                f'{history_fact}</a>'
            )
        else:
            fact_html = history_fact
        history_html = (
            f'<tr><td style="padding:14px 32px;background:{COLOR_BG};'
            f'border-bottom:1px solid {COLOR_BORDER};">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
            f'<td style="font-family:{FONT};font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;color:{COLOR_BLUE};'
            f'padding-bottom:4px;">📅 An diesem Tag</td></tr>'
            f'<tr><td style="font-family:{FONT};font-size:13px;line-height:1.6;'
            f'color:{COLOR_TEXT2};">{fact_html}'
            f'<span style="color:{COLOR_MUTED};font-size:10px;"> &middot; Quelle: Wikipedia</span>'
            f'</td></tr></table>'
            f'</td></tr>'
        )

    # ── "Zahl des Tages" (Destatis) – grosse Zahl + Text ─────────────────
    destatis_html = ""
    if destatis_fact:
        # Text ggf. verlinken
        if destatis_url:
            text_inner = (
                f'<a href="{destatis_url}" style="color:{COLOR_TEXT2};'
                f'text-decoration:none;border-bottom:1px solid {COLOR_LIGHT};">'
                f'{destatis_fact}</a>'
            )
        else:
            text_inner = destatis_fact

        # Wenn eine Zahl erkannt wurde: gross voranstellen
        if destatis_zahl:
            zahl_block = (
                f'<span style="font-family:{FONT};font-size:26px;font-weight:800;'
                f'color:{COLOR_NAVY};line-height:1.1;display:inline-block;'
                f'margin-right:10px;vertical-align:middle;">{destatis_zahl}</span>'
            )
            body = (
                f'{zahl_block}'
                f'<span style="font-family:{FONT};font-size:14px;line-height:1.5;'
                f'color:{COLOR_TEXT2};vertical-align:middle;">{text_inner}</span>'
            )
        else:
            body = (
                f'<span style="font-family:{FONT};font-size:13px;line-height:1.6;'
                f'color:{COLOR_TEXT2};">{text_inner}</span>'
            )

        destatis_html = (
            f'<tr><td style="padding:14px 32px;background:{COLOR_BG};'
            f'border-bottom:1px solid {COLOR_BORDER};">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
            f'<td style="font-family:{FONT};font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;color:{COLOR_BLUE};'
            f'padding-bottom:6px;">📊 Zahl des Tages</td></tr>'
            f'<tr><td>{body}'
            f'<div style="font-family:{FONT};color:{COLOR_MUTED};font-size:10px;'
            f'margin-top:4px;">Quelle: Destatis</div>'
            f'</td></tr></table>'
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
            f'style="margin-top:10px;background:#d4e3ed;border-radius:4px;padding:4px 0;">'
        )
        for i, a in enumerate(clean):
            links_html += (
                f'<tr><td style="padding:3px 12px;">'
                f'<a href="{a["link"]}" style="text-decoration:none;font-family:{FONT};'
                f'font-size:12px;line-height:1.3;color:{COLOR_TEXT2};">'
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

    # ── WM-Block (ans Ende, nur waehrend des Turniers) ───────────────────
    wm_html = ""
    if wm_info and (wm_info.get("letztes") or wm_info.get("heute") or wm_info.get("naechste")):
        wm_link = wm_info.get("link", "")
        zeilen = ""
        # Letztes Ergebnis
        if wm_info.get("letztes"):
            zeilen += (
                f'<tr><td style="font-family:{FONT};font-size:13px;line-height:1.7;'
                f'color:{COLOR_TEXT2};padding:1px 0;">'
                f'<span style="color:{COLOR_MUTED};">Zuletzt:</span> '
                f'<strong style="color:{COLOR_NAVY};">{wm_info["letztes"]}</strong>'
                f'</td></tr>'
            )
        # Spiele heute
        if wm_info.get("heute"):
            spiele = "<br>".join(wm_info["heute"])
            zeilen += (
                f'<tr><td style="font-family:{FONT};font-size:13px;line-height:1.7;'
                f'color:{COLOR_TEXT2};padding:1px 0;">'
                f'<span style="color:{COLOR_MUTED};">Heute:</span> {spiele}'
                f'</td></tr>'
            )
        elif wm_info.get("naechste"):
            spiele = "<br>".join(wm_info["naechste"])
            zeilen += (
                f'<tr><td style="font-family:{FONT};font-size:13px;line-height:1.7;'
                f'color:{COLOR_TEXT2};padding:1px 0;">'
                f'<span style="color:{COLOR_MUTED};">Als Nächstes:</span> {spiele}'
                f'</td></tr>'
            )
        # Link zu allen Ergebnissen
        link_zeile = ""
        if wm_link:
            link_zeile = (
                f'<tr><td style="padding-top:6px;">'
                f'<a href="{wm_link}" style="font-family:{FONT};font-size:11px;'
                f'font-weight:600;color:{COLOR_BLUE};text-decoration:none;">'
                f'Alle Ergebnisse & Spielplan →</a></td></tr>'
            )

        wm_html = (
            f'<tr><td style="padding:18px 32px 20px;background:{COLOR_BG};'
            f'border-top:2px solid {COLOR_BORDER};">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%">'
            f'<tr><td style="font-family:{FONT};font-size:13px;font-weight:700;'
            f'color:{COLOR_NAVY};padding-bottom:8px;">⚽ Fußball-WM 2026</td></tr>'
            f'{zeilen}{link_zeile}'
            f'</table></td></tr>'
        )

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
        + history_html
        + destatis_html
        + category_blocks
        + wm_html
        + footer_html +
        '</table>\n</td></tr>\n</table>\n</body>\n</html>'
    )

# ─────────────────────────────────────────────
# "HEUTE VOR X JAHREN" – WIKIPEDIA
# ─────────────────────────────────────────────

HISTORY_FETCH_TIMEOUT = 15  # Sekunden
# Deutsche Wikipedia "On this day" – kuratierte Ereignisse (selected), CC BY-SA
WIKIPEDIA_ONTHISDAY_URL = "https://de.wikipedia.org/api/rest_v1/feed/onthisday/selected/{month}/{day}"


def fetch_history_fact() -> tuple[str, str]:
    """
    Holt ein historisches Ereignis des heutigen Kalendertags von der
    deutschen Wikipedia (CC BY-SA). Gibt (Text, Wikipedia-URL) zurück
    oder ("", "") bei Fehler/keinem passenden Eintrag (dann faellt der Block weg).
    """
    now = datetime.now()
    url = WIKIPEDIA_ONTHISDAY_URL.format(
        month=now.strftime("%m"), day=now.strftime("%d")
    )
    try:
        # Wikimedia verlangt einen aussagekraeftigen User-Agent, sonst 403
        req = urllib.request.Request(
            url, headers={"User-Agent": "Tageslage-Newsletter/1.0 (RSS-Digest)"}
        )
        with urllib.request.urlopen(req, timeout=HISTORY_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        events = data.get("selected") or data.get("events") or []
        # Nur Eintraege mit Jahr und vernuenftiger Textlaenge (nicht zu lang/kurz)
        usable = [
            e for e in events
            if e.get("year") and e.get("text")
            and 20 <= len(str(e["text"]).strip()) <= 170
        ]
        if not usable:
            print("  ⚠ Wikipedia-Fakt: kein passender Eintrag")
            return "", ""

        ev        = random.choice(usable)
        year      = int(ev["year"])
        years_ago = now.year - year
        text      = str(ev["text"]).strip()

        if years_ago <= 0:
            return "", ""

        # Link zum passenden Wikipedia-Artikel aus dem "pages"-Array ziehen
        link = ""
        pages = ev.get("pages") or []
        if pages:
            content_urls = pages[0].get("content_urls") or {}
            desktop = content_urls.get("desktop") or {}
            link = desktop.get("page", "") or ""

        print(f"  ✓ Wikipedia-Fakt: vor {years_ago} Jahren ({year})")
        return f"Vor {years_ago} Jahren ({year}): {text}", link

    except (urllib.error.URLError, socket.timeout) as e:
        print(f"  ⚠ Wikipedia nicht erreichbar: {e}")
        return "", ""
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"  ⚠ Wikipedia-Antwort ungueltig: {e}")
        return "", ""
    except Exception as e:
        print(f"  ⚠ Wikipedia-Fakt Fehler: {e}")
        return "", ""

# ─────────────────────────────────────────────
# STATISTIK DES TAGES – DESTATIS
# ─────────────────────────────────────────────

# Taegliche Pressemitteilungen des Statistischen Bundesamts (CC: "Verbreitung
# mit Quellenangabe erwuenscht"). Liefert seriose, deutsche Zahlen.
DESTATIS_RSS_URL = "https://www.destatis.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed/Aktuell.xml?nn=241288"


def _extract_destatis_number(title: str) -> tuple[str, str]:
    """
    Versucht aus einem Destatis-Titel die markanteste Zahl herauszuloesen
    und gibt (zahl, resttext) zurueck. Beispiele:
      "Rund 129 300 Ehescheidungen im Jahr 2024"
        → ("129.300", "Ehescheidungen im Jahr 2024")
      "Inflationsrate im Mai 2026 bei +2,1 %"
        → ("+2,1 %", "Inflationsrate im Mai 2026")
      "Exporte im April 2026: -3,2 % zum Vormonat"
        → ("-3,2 %", "Exporte im April 2026 zum Vormonat")
    Wenn keine sinnvolle Zahl gefunden wird: ("", title).
    """
    t = title.strip()

    # Muster nach Prioritaet: Geldbetraege, Prozent, grosse Zahlen mit Einheit
    patterns = [
        # 11 Mrd./Mio. Euro  |  1,5 Milliarden Euro
        r"([+-]?\d[\d\.\s]*(?:,\d+)?\s*(?:Mrd\.?|Mio\.?|Milliarden|Millionen|Billionen)\s*(?:Euro|€|EUR)?)",
        # Prozent: +2,1 %  | -3,2 Prozent
        r"([+-]?\d+(?:,\d+)?\s*(?:%|Prozent))",
        # grosse Zahl mit Tausender-Leerzeichen: 129 300  | 1 234 567
        r"(\d{1,3}(?:\s\d{3})+)",
        # einfache Zahl mit Einheit/Jahr-unabhaengig: 2,3 Millionen etc. schon oben
        # einzelne groessere Zahl (>=3 Stellen), aber NICHT eine Jahreszahl
        r"(?<!\d)(\d{3,}(?:,\d+)?)(?!\d)",
    ]

    for pat in patterns:
        m = re.search(pat, t)
        if not m:
            continue
        zahl = m.group(1).strip()
        # Jahreszahlen (1900-2099) als alleinige Zahl ignorieren
        if re.fullmatch(r"(19|20)\d{2}", zahl.replace(" ", "")):
            continue
        # Tausender-Leerzeichen → Punkt (129 300 → 129.300)
        zahl_fmt = re.sub(r"(\d)\s(\d{3})", r"\1.\2", zahl)
        zahl_fmt = re.sub(r"(\d)\s(\d{3})", r"\1.\2", zahl_fmt)  # 2x fuer Millionen
        # Resttext: die Zahl rausschneiden, Fuellwoerter aufraeumen
        rest = (t[:m.start()] + t[m.end():]).strip()
        rest = re.sub(r"^\s*(Rund|Etwa|Circa|Ca\.?|Knapp|Mehr als|Fast)\s+", "", rest, flags=re.I)
        rest = re.sub(r"\s{2,}", " ", rest).strip(" :–-,")
        # Hae­ngende Praepositionen/Fuellwoerter am Rand entfernen
        rest = re.sub(r"\s+(bei|auf|um|von|im|zum|zur|mit|fuer)\s*$", "", rest, flags=re.I).strip(" :–-,")
        rest = re.sub(r"^(bei|auf|um|von|im|zum|zur|mit|fuer|steigen|steigt|sinkt|sinken|liegt|liegen)\s+", "", rest, flags=re.I).strip(" :–-,")
        if rest:
            return zahl_fmt, rest

    return "", t


def fetch_destatis_stat() -> tuple[str, str, str]:
    """
    Holt die neueste Destatis-Pressemitteilung als "Zahl des Tages".
    Gibt (zahl, text, link) zurueck – die Zahl wird im Newsletter gross
    dargestellt, der Text daneben. Bei fehlender Zahl ist zahl="" und der
    Titel steht komplett im Text. ("","","") bei Fehler/nichts Aktuellem.
    """
    try:
        feed = feedparser.parse(DESTATIS_RSS_URL)
        if not feed.entries:
            print("  ⚠ Destatis: keine Eintraege")
            return "", "", ""

        now = datetime.now(timezone.utc)
        for entry in feed.entries[:6]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()
            if not title:
                continue

            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            if ts:
                try:
                    pub = datetime(*ts[:6], tzinfo=timezone.utc)
                    if (now - pub) > timedelta(hours=48):
                        continue
                except Exception:
                    pass

            zahl, text = _extract_destatis_number(title)
            # Bevorzugt PMs MIT erkennbarer Zahl – sonst naechste pruefen
            if zahl:
                print(f"  ✓ Destatis: {zahl} – {text[:45]}")
                return zahl, text, link
            # keine Zahl: merken, aber weitersuchen ob eine bessere kommt
            fallback = (("", title, link))

        # keine PM mit klarer Zahl gefunden → erste frische als Text
        try:
            return fallback
        except NameError:
            print("  ⚠ Destatis: nichts Aktuelles (max 48h)")
            return "", "", ""
    except Exception as e:
        print(f"  ⚠ Destatis-Fehler: {e}")
        return "", "", ""


# ─────────────────────────────────────────────
# FUSSBALL-WM 2026 (nur waehrend des Turniers)
# ─────────────────────────────────────────────

# Public-Domain-Daten von openfootball (kein API-Key, erlaubte raw-Domain).
# Wird ca. 1x taeglich manuell aktualisiert – fuer 2 Ausgaben/Tag ausreichend.
WM_JSON_URL    = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
WM_FETCH_TIMEOUT = 15
# Turnierfenster: nur in diesem Zeitraum erscheint der WM-Block.
WM_START_DATE  = "2026-06-11"
WM_END_DATE    = "2026-07-19"

# Englische → deutsche Laendernamen (nur die WM-Teilnehmer 2026).
WM_TEAM_DE = {
    "Mexico": "Mexiko", "South Africa": "Südafrika", "South Korea": "Südkorea",
    "Czech Republic": "Tschechien", "Canada": "Kanada",
    "Bosnia & Herzegovina": "Bosnien-Herz.", "Qatar": "Katar", "Switzerland": "Schweiz",
    "Brazil": "Brasilien", "Morocco": "Marokko", "Haiti": "Haiti", "Scotland": "Schottland",
    "USA": "USA", "Paraguay": "Paraguay", "Australia": "Australien", "Turkey": "Türkei",
    "Germany": "Deutschland", "Curaçao": "Curaçao", "Ivory Coast": "Elfenbeinküste",
    "Ecuador": "Ecuador", "Netherlands": "Niederlande", "Japan": "Japan",
    "Sweden": "Schweden", "Tunisia": "Tunesien", "Belgium": "Belgien", "Egypt": "Ägypten",
    "Iran": "Iran", "New Zealand": "Neuseeland", "Spain": "Spanien", "Cape Verde": "Kap Verde",
    "Saudi Arabia": "Saudi-Arabien", "Uruguay": "Uruguay", "France": "Frankreich",
    "Senegal": "Senegal", "Iraq": "Irak", "Norway": "Norwegen", "Argentina": "Argentinien",
    "Algeria": "Algerien", "Austria": "Österreich", "Jordan": "Jordanien",
    "Portugal": "Portugal", "DR Congo": "DR Kongo", "Uzbekistan": "Usbekistan",
    "Colombia": "Kolumbien", "England": "England", "Croatia": "Kroatien", "Ghana": "Ghana",
    "Panama": "Panama",
}


def _wm_team(name: str) -> str:
    """Englischen Teamnamen ins Deutsche uebersetzen (Fallback: Original)."""
    return WM_TEAM_DE.get(name.strip(), name.strip())


# Top-Nationen (engl. Namen wie im Feed) – fuer "nur Topspiele" bei vollem
# Spieltag. Deutschland immer dabei, plus Titelanwaerter/grosse Fussballlaender.
WM_TOP_TEAMS = {
    "Germany", "Spain", "France", "England", "Brazil", "Argentina",
    "Portugal", "Netherlands", "Italy", "Belgium", "Croatia", "USA",
}


def _wm_is_top(m: dict) -> bool:
    """True, wenn mindestens eine Top-Nation am Spiel beteiligt ist."""
    return m.get("team1", "") in WM_TOP_TEAMS or m.get("team2", "") in WM_TOP_TEAMS


def fetch_wm_info(now: datetime | None = None) -> dict:
    """
    Liefert WM-Infos als strukturiertes Dict – nur waehrend des Turniers,
    sonst {}. Felder:
      letztes:  "Kanada 2:0 Bosnien" (oder "")
      heute:    Liste ["21:00 Kanada – Bosnien", ...] (Spiele heute)
      naechste: Liste (Fallback: kommende Spiele, falls heute keine)
      link:     Sportschau-Ergebnislink
    """
    now = now or datetime.now()
    today = now.strftime("%Y-%m-%d")
    link = "https://www.sportschau.de/live-und-ergebnisse/fussball/fifa-wm/spiele-und-ergebnisse"

    if not (WM_START_DATE <= today <= WM_END_DATE):
        return {}

    def _has_score(m):
        return m.get("score1") is not None and m.get("score2") is not None

    def _uhr(m):
        # "21:00 UTC-6" → "21:00"; leere/unbekannte Zeit → ""
        raw = str(m.get("time", "")).strip()
        mt = re.match(r"(\d{1,2}:\d{2})", raw)
        return mt.group(1) if mt else ""

    try:
        req = urllib.request.Request(
            WM_JSON_URL, headers={"User-Agent": "Tageslage-Newsletter/1.0"}
        )
        with urllib.request.urlopen(req, timeout=WM_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        matches = data.get("matches", [])
        if not matches:
            return {}

        # ── Letztes gespieltes Ergebnis ──────────────────────────────
        letztes_str = ""
        letztes = None
        for m in matches:
            d = m.get("date", "")
            if d and d <= today and _has_score(m):
                if letztes is None or d >= letztes.get("date", ""):
                    letztes = m
        if letztes:
            letztes_str = (
                f"{_wm_team(letztes.get('team1',''))} "
                f"{letztes.get('score1')}:{letztes.get('score2')} "
                f"{_wm_team(letztes.get('team2',''))}"
            )

        # ── Spiele HEUTE (noch ohne Ergebnis) ────────────────────────
        heute_raw = [
            m for m in matches
            if m.get("date", "") == today and not _has_score(m)
        ]
        # Bei vollem Spieltag (>2 Spiele) auf Topspiele begrenzen, damit der
        # Block kompakt bleibt. Sind es 2 oder weniger, alle zeigen.
        if len(heute_raw) > 2:
            top = [m for m in heute_raw if _wm_is_top(m)]
            if top:
                heute_raw = top[:3]   # max. 3 Topspiele
        heute = []
        for m in heute_raw:
            u  = _uhr(m)
            t1 = _wm_team(m.get("team1", ""))
            t2 = _wm_team(m.get("team2", ""))
            heute.append((u, f"{(u + ' ') if u else ''}{t1} – {t2}"))
        heute.sort(key=lambda x: x[0])
        heute_list = [s for _, s in heute]

        # ── Fallback: naechste Spiele (falls heute keine mehr) ───────
        naechste_list = []
        if not heute_list:
            kommende = sorted(
                [m for m in matches if m.get("date", "") > today and not _has_score(m)],
                key=lambda m: (m.get("date", ""), _uhr(m))
            )
            for m in kommende[:2]:
                d = m.get("date", "")
                try:
                    dd = datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.")
                except Exception:
                    dd = d
                u  = _uhr(m)
                t1 = _wm_team(m.get("team1", ""))
                t2 = _wm_team(m.get("team2", ""))
                zeit = f"{dd}{(' ' + u) if u else ''}"
                naechste_list.append(f"{zeit} {t1} – {t2}")

        if not (letztes_str or heute_list or naechste_list):
            return {}

        print(f"  ✓ WM-Info: zuletzt '{letztes_str}', heute {len(heute_list)} Spiel(e)")
        return {
            "letztes":  letztes_str,
            "heute":    heute_list,
            "naechste": naechste_list,
            "link":     link,
        }

    except (urllib.error.URLError, socket.timeout) as e:
        print(f"  ⚠ WM-Daten nicht erreichbar: {e}")
        return {}
    except Exception as e:
        print(f"  ⚠ WM-Fehler: {e}")
        return {}

# ─────────────────────────────────────────────
# EMPFÄNGER-LISTE
# ─────────────────────────────────────────────

def fetch_subscribers() -> list[str]:
    """
    Liest die Empfaengerliste, die scripts/recipients.py vorher aus dem
    Google Sheet zusammengestellt und in die Umgebungsvariable RECIPIENT_LIST
    (bzw. die Datei $GITHUB_ENV) geschrieben hat.
    Fallback: RECIPIENT_EMAIL (kommagetrennt).

    Returns:
        Liste deduplizierter, lowercase E-Mail-Adressen.

    Raises:
        ValueError: wenn keine Empfaenger gefunden werden.
    """
    def _parse(raw: str) -> list[str]:
        return sorted({
            e.strip().lower()
            for e in raw.split(",")
            if e.strip() and "@" in e
        })

    # ── Versuch 1: RECIPIENT_LIST aus dem Environment ─────────────
    emails = _parse(os.environ.get("RECIPIENT_LIST", ""))
    if emails:
        print(f"  ✓ {len(emails)} Empfaenger via RECIPIENT_LIST geladen")
        return emails

    # ── Versuch 2: RECIPIENT_LIST direkt aus der $GITHUB_ENV-Datei ──
    # Falls die YAML die Variable nicht in den naechsten Step durchreicht,
    # lesen wir die von recipients.py geschriebene Zeile selbst aus.
    gh_env = os.environ.get("GITHUB_ENV", "")
    if gh_env and os.path.exists(gh_env):
        try:
            with open(gh_env, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("RECIPIENT_LIST="):
                        emails = _parse(line.split("=", 1)[1])
                        if emails:
                            print(f"  ✓ {len(emails)} Empfaenger aus GITHUB_ENV-Datei geladen")
                            return emails
        except Exception as e:
            print(f"  ⚠ GITHUB_ENV nicht lesbar: {e}")

    # ── Versuch 3: Fallback RECIPIENT_EMAIL ───────────────────────
    fallback = _parse(os.environ.get("RECIPIENT_EMAIL", ""))
    if fallback:
        print(f"  ✓ {len(fallback)} Empfaenger via RECIPIENT_EMAIL (Fallback)")
        return fallback

    raise ValueError(
        "Keine Empfaenger gefunden! "
        "Pruefe, ob scripts/recipients.py vor newsletter.py laeuft und "
        "RECIPIENT_LIST setzt (oder setze RECIPIENT_EMAIL als Fallback)."
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
        # Apps-Script (Newsletter.gs) erwartet nur ?email=... (kein action-Parameter)
        sep = "&" if "?" in unsubscribe_base else "?"
        unsubscribe_url = (
            f"{unsubscribe_base}{sep}email={urllib.parse.quote(recipient)}"
        )
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

    # ── Nativer "Abbestellen"-Button in Gmail/Apple Mail/Outlook ──────────
    # List-Unsubscribe zeigt den Button neben dem Absender. List-Unsubscribe-Post
    # erlaubt 1-Klick-Abmeldung (RFC 8058) direkt im Mailclient ohne Seitenaufruf.
    if unsubscribe_base and unsubscribe_url != "#":
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

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

    unsubscribe_base = os.environ.get("UNSUBSCRIBE_URL", "")
    signup_url       = os.environ.get("SIGNUP_URL", SIGNUP_URL)

    print("0/5 – Empfaengerliste laden...")
    recipients = fetch_subscribers()
    print(f"Empfänger: {len(recipients)}\n")

    print("1/5 – RSS-Feeds laden...")
    recent_titles = load_recent_titles()
    articles = fetch_feeds(recent_titles=recent_titles)
    print(f"     {len(articles)} Artikel gesammelt\n")

    print("2/5 – Kategorisieren...")
    grouped = group_by_category(articles)
    for cat, arts in grouped.items():
        print(f"     {cat}: {len(arts)}")
    print()

    print("3/5 – KI-Zusammenfassung mit Groq...")
    intro, summaries, top_cats, selected_links = summarize_with_groq(grouped)
    print()

    print("    → 'Heute vor X Jahren' von Wikipedia holen...")
    history_fact, history_url = fetch_history_fact()
    print("    → 'Zahl des Tages' von Destatis holen...")
    destatis_zahl, destatis_fact, destatis_url = fetch_destatis_stat()
    print("    → WM-Spielstand holen (nur waehrend Turnier)...")
    wm_info = fetch_wm_info()
    print()

    now      = datetime.now()
    daytime  = "morgen" if now.hour < 13 else "abend"

    print("4/5 – Archiv-JSON erstellen...")
    archive_basename = build_archive_json(
        grouped, intro, summaries, selected_links,
        history_fact, history_url, now, daytime,
        destatis_fact=destatis_fact, destatis_url=destatis_url,
        destatis_zahl=destatis_zahl, wm_info=wm_info,
    )
    # Deep-Link: Landing Page oeffnet direkt diese Ausgabe
    archive_url = f"{GITHUB_PAGES_BASE_URL}/?a={archive_basename}"
    print(f"     docs/data/{archive_basename}.json geschrieben\n")

    print("5/5 – Newsletter versenden...")
    html_template = build_html(
        intro, summaries, grouped,
        selected_links=selected_links,
        archive_url=archive_url,
        signup_url=signup_url,
        history_fact=history_fact,
        history_url=history_url,
        destatis_fact=destatis_fact,
        destatis_url=destatis_url,
        destatis_zahl=destatis_zahl,
        wm_info=wm_info,
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
