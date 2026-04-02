# 🗞️ Tagesbrief – Dein automatischer KI-Newsletter

Täglich 2× eine KI-Zusammenfassung der wichtigsten Nachrichten – kostenlos, automatisch, direkt in dein Postfach.

**Quellen:** Spiegel Online · FAZ · Tagesschau · Politico Europe · Heise/c’t  
**KI:** Google Gemini (kostenloser Tier)  
**Versand:** Gmail SMTP  
**Automation:** GitHub Actions

-----

## 📋 Was du brauchst

|Was                 |Wo                 |Kosten   |
|--------------------|-------------------|---------|
|GitHub-Account      |github.com         |Kostenlos|
|Gemini API-Key      |aistudio.google.com|Kostenlos|
|Gmail-Konto (Sender)|gmail.com          |Kostenlos|

-----

## 🚀 Einrichtung (15 Minuten)

### Schritt 1 – Repository erstellen

1. Gehe zu [github.com/new](https://github.com/new)
1. Name: `tagesbrief` (oder beliebig)
1. **Private** auswählen (empfohlen)
1. Repository erstellen

### Schritt 2 – Dateien hochladen

Lade alle Dateien aus diesem Ordner in dein Repository:

```
.github/workflows/newsletter.yml
scripts/newsletter.py
requirements.txt
README.md
```

Alternativ per Git:

```bash
git clone https://github.com/DEIN-USERNAME/tagesbrief.git
# Dateien reinkopieren
git add .
git commit -m "Newsletter einrichten"
git push
```

### Schritt 3 – Gemini API-Key holen

1. Gehe zu **[aistudio.google.com](https://aistudio.google.com)**
1. Klicke oben rechts auf **„Get API Key”**
1. → **„Create API key”**
1. Key kopieren und sicher aufbewahren

> ✅ Der kostenlose Tier reicht völlig: 1.500 Anfragen/Tag, 15 Anfragen/Minute

### Schritt 4 – Gmail App-Passwort erstellen

> ⚠️ Du brauchst ein **App-Passwort**, nicht dein normales Gmail-Passwort.  
> Tipp: Erstelle ein eigenes Gmail-Konto nur für den Newsletter (z.B. `deinname.tagesbrief@gmail.com`)

1. Gehe zu [myaccount.google.com/security](https://myaccount.google.com/security)
1. Stelle sicher, dass **2-Faktor-Authentifizierung** aktiviert ist
1. Suche nach **„App-Passwörter”** (im Suchfeld oben)
1. App: **„E-Mail”**, Gerät: **„Windows-Computer”** (egal was)
1. **„Erstellen”** → 16-stelliges Passwort wird angezeigt → kopieren!

### Schritt 5 – GitHub Secrets eintragen

1. In deinem Repository: **Settings → Secrets and variables → Actions**
1. Auf **„New repository secret”** klicken
1. Diese 4 Secrets anlegen:

|Name                |Wert                                                       |
|--------------------|-----------------------------------------------------------|
|`GEMINI_API_KEY`    |Dein Gemini API-Key aus Schritt 3                          |
|`GMAIL_ADDRESS`     |Die Gmail-Adresse des Senders (z.B. `name.brief@gmail.com`)|
|`GMAIL_APP_PASSWORD`|Das 16-stellige App-Passwort aus Schritt 4                 |
|`RECIPIENT_EMAIL`   |Deine E-Mail-Adresse, an die der Newsletter geht           |

### Schritt 6 – Testen!

1. Gehe zu **Actions** in deinem Repository
1. Klicke auf **„🗞️ Tagesbrief Newsletter”**
1. Rechts: **„Run workflow”** → **„Run workflow”**
1. Nach ~1-2 Minuten: E-Mail prüfen! 📬

-----

## ⏰ Sendezeiten anpassen

Die Zeiten stehen in `.github/workflows/newsletter.yml`:

```yaml
schedule:
  - cron: '0 5 * * *'   # 07:00 Uhr MEZ (Sommer)
  - cron: '0 17 * * *'  # 19:00 Uhr MEZ (Sommer)
```

> **Hinweis:** GitHub Actions läuft auf UTC. Deutschland = UTC+1 (Winter) / UTC+2 (Sommer).
> 
> |Gewünschte Zeit (MEZ)|Winter (UTC+1)|Sommer (UTC+2)|
> |---------------------|--------------|--------------|
> |7:00 Uhr             |`0 6 * * *`   |`0 5 * * *`   |
> |8:00 Uhr             |`0 7 * * *`   |`0 6 * * *`   |
> |18:00 Uhr            |`0 17 * * *`  |`0 16 * * *`  |
> |19:00 Uhr            |`0 18 * * *`  |`0 17 * * *`  |

-----

## 📰 RSS-Feeds anpassen

In `scripts/newsletter.py` ganz oben:

```python
RSS_FEEDS = {
    "Spiegel Online":   "https://www.spiegel.de/schlagzeilen/tops/index.rss",
    "FAZ":              "https://www.faz.net/rss/aktuell/",
    "Tagesschau":       "https://www.tagesschau.de/xml/rss2/",
    "Politico Europe":  "https://www.politico.eu/feed/",
    "Heise / c't":      "https://www.heise.de/rss/heise-top-atom.xml",
    # Weitere Quellen einfach hinzufügen:
    # "Zeit Online":    "https://newsfeed.zeit.de/alle",
    # "Handelsblatt":   "https://www.handelsblatt.com/contentexport/feed/schlagzeilen",
    # "Süddeutsche":    "https://rss.sueddeutsche.de/rss/Topthemen",
}
```

-----

## 🗂️ Kategorien

20 vordefinierte Kategorien – nur Kategorien mit Artikeln erscheinen im Newsletter:

🏛️ Innenpolitik · 🌍 Außenpolitik · 💰 Wirtschaft · 💻 Tech & KI · ⚡ Energie & Klima  
🏥 Gesundheit · 🔬 Wissenschaft · ⚖️ Recht & Justiz · 🛡️ Sicherheit · 📊 Finanzen  
🌿 Umwelt · 🏙️ Gesellschaft · 🚗 Mobilität · 🏗️ Immobilien · 🌐 Europa & EU  
🗳️ Wahlen & Parteien · 📱 Medien & Kultur · ⚽ Sport · 🌎 International · 🔥 Sonstiges

-----

## 💰 Kostenübersicht

|Dienst        |Limit (kostenlos)|Verbrauch                   |
|--------------|-----------------|----------------------------|
|GitHub Actions|2.000 Min/Monat  |~2 Min/Tag = ~60 Min/Monat ✅|
|Gemini Flash  |1.500 Req/Tag    |~15 Req/Tag ✅               |
|Gmail SMTP    |500 Mails/Tag    |2 Mails/Tag ✅               |

**Gesamtkosten: 0 €/Monat** 🎉

-----

## 🔧 Troubleshooting

**Newsletter kommt nicht an?**

- Actions → letzter Run → Logs ansehen
- Secrets korrekt eingetragen? (Keine Leerzeichen!)
- Gmail App-Passwort korrekt? (Ohne Leerzeichen eintragen)

**Gemini-Fehler?**

- API-Key in [aistudio.google.com](https://aistudio.google.com) prüfen
- Kostenloses Kontingent erschöpft? (Sehr unwahrscheinlich)

**Keine Artikel?**

- RSS-URLs direkt im Browser testen
- Manche Feeds ändern gelegentlich ihre URL

-----

*Erstellt mit Claude von Anthropic · Läuft auf GitHub Actions · KI: Google Gemini*