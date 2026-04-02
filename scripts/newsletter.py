
#!/usr/bin/env python3
"""
Automatischer KI-Newsletter
Holt RSS-Feeds, kategorisiert mit Gemini, verschickt per E-Mail.
"""

import os
import json
import smtplib
import feedparser
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.generativeai as genai

# ─────────────────────────────────────────────

# KONFIGURATION

# ─────────────────────────────────────────────

RSS_FEEDS = {
"Spiegel Online":   "https://www.spiegel.de/schlagzeilen/tops/index.rss",
"FAZ":              "https://www.faz.net/rss/aktuell/",
"Politico Europe":  "https://www.politico.eu/feed/",

}

CATEGORIES = {
"🏛️ Innenpolitik":        ["bundestag", "regierung", "koalition", "merz", "scholz", "spd", "cdu", "csu", "grüne", "fdp", "afd", "wahl", "bundesrat", "minister", "kanzler"],
"🌍 Außenpolitik":        ["ukraine", "russland", "usa", "china", "nato", "eu", "außenminister", "diplomatie", "krieg", "konflikt", "trump", "biden", "g7", "g20", "un", "sanktionen"],
"💰 Wirtschaft":          ["wirtschaft", "dax", "aktie", "inflation", "ezb", "bundesbank", "rezession", "wachstum", "arbeitslos", "unternehmen", "konzern", "export", "import", "haushalt", "schulden"],
"💻 Tech & KI":           ["ki", "ai", "künstliche intelligenz", "openai", "google", "microsoft", "apple", "meta", "amazon", "startup", "software", "hardware", "chip", "halbleiter", "cyber", "hacker", "heise", "tech"],
"⚡ Energie & Klima":     ["energie", "strom", "gas", "öl", "solar", "wind", "erneuerbar", "co2", "klima", "klimawandel", "temperatur", "ipcc", "atomkraft", "kernkraft", "wärmepumpe"],
"🏥 Gesundheit":          ["gesundheit", "krankenhaus", "arzt", "medizin", "impf", "krankheit", "virus", "corona", "rki", "pharma", "forschung", "studie", "therapie", "pflege"],
"🔬 Wissenschaft":        ["wissenschaft", "forschung", "studie", "weltraum", "nasa", "esa", "physik", "biologie", "chemie", "entdeckung", "universum", "mars", "mond"],
"⚖️ Recht & Justiz":      ["gericht", "urteil", "klage", "recht", "gesetz", "bgh", "bverfg", "staatsanwalt", "strafrecht", "prozess", "verfahren", "anwalt"],
"🛡️ Sicherheit & Verteidigung": ["bundeswehr", "militär", "verteidigung", "rüstung", "soldat", "nato", "drohne", "rakete", "sicherheit", "geheimdienst", "bnd", "verfassungsschutz"],
"📊 Finanzen & Märkte":   ["börse", "aktien", "fonds", "etf", "anleihe", "euro", "dollar", "zinsen", "fed", "ezb", "krypto", "bitcoin", "investment", "ipo"],
"🌿 Umwelt & Natur":      ["umwelt", "natur", "tier", "artensterben", "wald", "ozean", "meer", "plastik", "recycling", "nachhaltigkeit", "ozon", "biodiversität"],
"🏙️ Gesellschaft":        ["gesellschaft", "sozial", "armut", "bildung", "schule", "universität", "familie", "rente", "migration", "integration", "flüchtling"],
"🚗 Mobilität & Verkehr": ["auto", "bahn", "flugzeug", "verkehr", "mobilität", "elektroauto", "tesla", "volkswagen", "bmw", "mercedes", "lufthansa", "deutsche bahn"],
"🏗️ Immobilien & Bauen":  ["immobilien", "wohnen", "miete", "bauen", "wohnungsnot", "eigenheim", "grundstück", "baukosten"],
"🌐 Europa & EU":         ["europa", "eu", "europäisch", "brüssel", "europaparlament", "kommission", "von der leyen", "macron", "draghi", "euro"],
"🗳️ Wahlen & Parteien":   ["wahl", "abstimmung", "partei", "kandidat", "wahlkampf", "umfrage", "koalition", "opposition", "mandat"],
"📱 Medien & Kultur":     ["medien", "zeitung", "fernsehen", "film", "musik", "kunst", "kultur", "theater", "buch", "streaming", "netflix", "social media"],
"⚽ Sport":               ["sport", "fußball", "bundesliga", "champions league", "olympia", "formel 1", "tennis", "basketball", "handball"],
"🌎 International":       ["international", "welt", "global", "ausland", "nahost", "israel", "palästina", "iran", "nordkorea", "asien", "afrika", "lateinamerika"],
"🔥 Sonstiges":           [],  # Fallback
}

MAX_ARTICLES_PER_FEED = 15
MAX_ARTICLES_FOR_SUMMARY = 60

# ─────────────────────────────────────────────

# RSS FEEDS HOLEN

# ─────────────────────────────────────────────

def fetch_feeds() -> list[dict]:
"""Alle RSS-Feeds holen und Artikel sammeln."""
articles = []
cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)

```
for source, url in RSS_FEEDS.items():
    try:
        feed = feedparser.parse(url)
        count = 0
        for entry in feed.entries:
            if count >= MAX_ARTICLES_PER_FEED:
                break
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            link = entry.get("link", "")
            # Länge begrenzen
            summary = summary[:400] if summary else ""
            if title:
                articles.append({
                    "source": source,
                    "title": title,
                    "summary": summary,
                    "link": link,
                })
                count += 1
        print(f"✓ {source}: {count} Artikel geladen")
    except Exception as e:
        print(f"✗ Fehler bei {source}: {e}")

return articles[:MAX_ARTICLES_FOR_SUMMARY]
```

# ─────────────────────────────────────────────

# KATEGORISIERUNG (lokal, schnell)

# ─────────────────────────────────────────────

def categorize_article(article: dict) -> str:
"""Artikel einer Kategorie zuordnen anhand von Keywords."""
text = (article["title"] + " " + article["summary"]).lower()

```
# Heise-Artikel immer Tech
if article["source"] == "Heise / c't":
    return "💻 Tech & KI"

# Politico immer Europa/Außenpolitik bevorzugen
if article["source"] == "Politico Europe":
    for cat in ["🌐 Europa & EU", "🌍 Außenpolitik", "🗳️ Wahlen & Parteien"]:
        keywords = CATEGORIES[cat]
        if any(kw in text for kw in keywords):
            return cat
    return "🌐 Europa & EU"

for category, keywords in CATEGORIES.items():
    if category == "🔥 Sonstiges":
        continue
    if any(kw in text for kw in keywords):
        return category

return "🔥 Sonstiges"
```

def group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
"""Artikel nach Kategorie gruppieren."""
grouped = {}
for article in articles:
cat = categorize_article(article)
grouped.setdefault(cat, []).append(article)
# Nach Kategoriereihenfolge sortieren
sorted_grouped = {}
for cat in CATEGORIES.keys():
if cat in grouped:
sorted_grouped[cat] = grouped[cat]
return sorted_grouped

# ─────────────────────────────────────────────

# KI-ZUSAMMENFASSUNG MIT GEMINI

# ─────────────────────────────────────────────

def summarize_with_gemini(grouped: dict[str, list[dict]]) -> dict[str, list[str]]:
"""Gemini fasst jede Kategorie in Stichsätzen zusammen."""
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
raise ValueError("GEMINI_API_KEY nicht gesetzt!")

```
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

summaries = {}

for category, articles in grouped.items():
    if not articles:
        continue

    # Artikel-Liste für Prompt aufbauen
    articles_text = "\n".join([
        f"- [{a['source']}] {a['title']}"
        + (f": {a['summary'][:200]}" if a['summary'] else "")
        for a in articles[:8]  # Max 8 pro Kategorie
    ])

    prompt = f"""Du bist ein präziser Nachrichtenredakteur. Fasse die folgenden Nachrichten der Kategorie "{category}" in 3-5 knappen deutschen Stichsätzen zusammen.
```

Regeln:

- Jeder Stichsatz beginnt mit einem Bullet-Punkt (•)
- Maximal 2 Zeilen pro Stichsatz
- Sachlich, informativ, keine Wertung
- Wichtigste Information zuerst
- Keine Einleitung, keine Schlussformel

Nachrichten:
{articles_text}

Stichsätze:"""

```
    try:
        response = model.generate_content(prompt)
        bullet_points = [
            line.strip()
            for line in response.text.strip().split("\n")
            if line.strip() and (line.strip().startswith("•") or line.strip().startswith("-") or line.strip().startswith("*"))
        ]
        # Normalisieren
        bullet_points = ["• " + bp.lstrip("•-* ").strip() for bp in bullet_points]
        summaries[category] = bullet_points[:5]
        print(f"✓ Zusammenfassung: {category} ({len(bullet_points)} Punkte)")
    except Exception as e:
        print(f"✗ Gemini-Fehler bei {category}: {e}")
        summaries[category] = [f"• Fehler beim Laden der Zusammenfassung: {e}"]

return summaries
```

# ─────────────────────────────────────────────

# HTML-NEWSLETTER ERSTELLEN

# ─────────────────────────────────────────────

def build_html(summaries: dict[str, list[str]], grouped: dict[str, list[dict]]) -> str:
"""Schönen HTML-Newsletter bauen."""
now = datetime.now()
daytime = "Morgen" if now.hour < 13 else "Abend"
date_str = now.strftime("%A, %d. %B %Y")

```
# Monatsnamen auf Deutsch
months = {
    "January": "Januar", "February": "Februar", "March": "März",
    "April": "April", "May": "Mai", "June": "Juni",
    "July": "Juli", "August": "August", "September": "September",
    "October": "Oktober", "November": "November", "December": "Dezember"
}
days = {
    "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
    "Thursday": "Donnerstag", "Friday": "Freitag",
    "Saturday": "Samstag", "Sunday": "Sonntag"
}
for en, de in {**months, **days}.items():
    date_str = date_str.replace(en, de)

# Kategorie-Blöcke bauen
category_blocks = ""
for category, bullets in summaries.items():
    articles = grouped.get(category, [])
    # Quellenlinks
    sources_html = ""
    seen_links = set()
    for a in articles[:5]:
        if a["link"] and a["link"] not in seen_links:
            seen_links.add(a["link"])
            sources_html += f'<a href="{a["link"]}" class="source-link">{a["source"]}: {a["title"][:60]}{"…" if len(a["title"]) > 60 else ""}</a>\n'

    bullets_html = "".join(f"<li>{b.lstrip('• ')}</li>\n" for b in bullets)

    category_blocks += f"""
    <div class="category-block">
        <h2 class="category-title">{category}</h2>
        <ul class="bullets">
            {bullets_html}
        </ul>
        <div class="sources">
            <span class="sources-label">Quellen:</span>
            {sources_html}
        </div>
    </div>
```

"""

```
total_articles = sum(len(v) for v in grouped.values())

html = f"""<!DOCTYPE html>
```

<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dein Newsletter – {date_str}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;500;600&display=swap');

- {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
background-color: #f5f0e8;
font-family: ‘Source Sans 3’, Georgia, sans-serif;
color: #1a1a1a;
line-height: 1.6;
}}

.wrapper {{
max-width: 680px;
margin: 0 auto;
background: #faf7f2;
}}

/* HEADER */
.header {{
background: #1a1a2e;
padding: 40px 40px 32px;
text-align: center;
}}
.header-label {{
font-size: 11px;
letter-spacing: 3px;
text-transform: uppercase;
color: #c9a84c;
font-family: ‘Source Sans 3’, sans-serif;
font-weight: 600;
margin-bottom: 12px;
}}
.header-title {{
font-family: ‘Playfair Display’, Georgia, serif;
font-size: 36px;
font-weight: 700;
color: #faf7f2;
line-height: 1.2;
margin-bottom: 8px;
}}
.header-sub {{
font-size: 13px;
color: #8899aa;
letter-spacing: 0.5px;
}}
.header-date {{
display: inline-block;
margin-top: 20px;
padding: 6px 18px;
border: 1px solid #c9a84c;
color: #c9a84c;
font-size: 12px;
letter-spacing: 1.5px;
text-transform: uppercase;
}}

/* STATS BAR */
.stats-bar {{
background: #c9a84c;
padding: 10px 40px;
display: flex;
justify-content: space-between;
align-items: center;
font-size: 12px;
color: #1a1a2e;
font-weight: 600;
letter-spacing: 0.5px;
}}

/* CONTENT */
.content {{
padding: 32px 40px;
}}

/* CATEGORY BLOCK */
.category-block {{
margin-bottom: 32px;
border-left: 3px solid #c9a84c;
padding-left: 20px;
}}
.category-title {{
font-family: ‘Playfair Display’, Georgia, serif;
font-size: 20px;
font-weight: 600;
color: #1a1a2e;
margin-bottom: 12px;
line-height: 1.3;
}}
.bullets {{
list-style: none;
margin-bottom: 14px;
}}
.bullets li {{
font-size: 14.5px;
line-height: 1.65;
color: #2c2c2c;
padding: 5px 0;
padding-left: 16px;
position: relative;
}}
.bullets li::before {{
content: "›";
position: absolute;
left: 0;
color: #c9a84c;
font-weight: 700;
font-size: 16px;
line-height: 1.5;
}}

/* SOURCES */
.sources {{
background: #f0ebe0;
border-radius: 4px;
padding: 10px 14px;
font-size: 12px;
}}
.sources-label {{
color: #888;
font-weight: 600;
text-transform: uppercase;
letter-spacing: 0.5px;
font-size: 10px;
display: block;
margin-bottom: 4px;
}}
.source-link {{
display: block;
color: #555;
text-decoration: none;
padding: 2px 0;
border-bottom: 1px solid transparent;
transition: color 0.2s;
white-space: nowrap;
overflow: hidden;
text-overflow: ellipsis;
}}
.source-link:hover {{ color: #c9a84c; }}

/* DIVIDER */
.divider {{
height: 1px;
background: linear-gradient(to right, transparent, #d4c9b0, transparent);
margin: 8px 0 32px;
}}

/* FOOTER */
.footer {{
background: #1a1a2e;
padding: 24px 40px;
text-align: center;
font-size: 11px;
color: #556;
line-height: 1.8;
}}
.footer a {{ color: #c9a84c; text-decoration: none; }}

/* RESPONSIVE */
@media (max-width: 600px) {{
.content, .header {{ padding: 24px 20px; }}
.stats-bar {{ padding: 10px 20px; flex-direction: column; gap: 4px; }}
.header-title {{ font-size: 28px; }}
.footer {{ padding: 20px; }}
}}
</style>

</head>
<body>
<div class="wrapper">

  <div class="header">
    <div class="header-label">Ihr persönlicher Nachrichtenüberblick</div>
    <div class="header-title">Der Tages&shy;brief</div>
    <div class="header-sub">Spiegel · FAZ · Tagesschau · Politico · Heise</div>
    <div class="header-date">{date_str} · {daytime}s-Ausgabe</div>
  </div>

  <div class="stats-bar">
    <span>📡 {len(RSS_FEEDS)} Quellen ausgewertet</span>
    <span>📰 {total_articles} Artikel analysiert</span>
    <span>🤖 Zusammengefasst mit Gemini AI</span>
  </div>

  <div class="content">
    {category_blocks}
    <div class="divider"></div>
  </div>

  <div class="footer">
    Automatisch erstellt · {now.strftime("%d.%m.%Y %H:%M")} Uhr<br>
    Quellen: Spiegel Online, FAZ, Tagesschau, Politico Europe, Heise/c't<br>
    <a href="https://github.com">Powered by GitHub Actions + Gemini AI</a>
  </div>

</div>
</body>
</html>"""

```
return html
```

# ─────────────────────────────────────────────

# E-MAIL VERSENDEN

# ─────────────────────────────────────────────

def send_email(html_content: str):
"""Newsletter per Gmail SMTP versenden."""
sender = os.environ.get("GMAIL_ADDRESS")
password = os.environ.get("GMAIL_APP_PASSWORD")
recipient = os.environ.get("RECIPIENT_EMAIL", sender)

```
if not sender or not password:
    raise ValueError("GMAIL_ADDRESS oder GMAIL_APP_PASSWORD nicht gesetzt!")

now = datetime.now()
daytime = "Morgen" if now.hour < 13 else "Abend"
subject = f"🗞️ Tagesbrief – {now.strftime('%d.%m.%Y')} ({daytime}s-Ausgabe)"

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"] = f"Tagesbrief <{sender}>"
msg["To"] = recipient

# Plain-Text Fallback
plain = f"Tagesbrief – {now.strftime('%d.%m.%Y')}\nBitte HTML-Ansicht aktivieren."
msg.attach(MIMEText(plain, "plain", "utf-8"))
msg.attach(MIMEText(html_content, "html", "utf-8"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(sender, password)
    server.sendmail(sender, [recipient], msg.as_string())

print(f"✓ Newsletter verschickt an {recipient}")
```

# ─────────────────────────────────────────────

# HAUPTPROGRAMM

# ─────────────────────────────────────────────

def main():
print(f"\n{’=’*50}")
print(f"  TAGESBRIEF – {datetime.now().strftime(’%d.%m.%Y %H:%M’)}")
print(f"{’=’*50}\n")

```
print("1/4 · RSS-Feeds laden...")
articles = fetch_feeds()
print(f"     → {len(articles)} Artikel gesammelt\n")

print("2/4 · Kategorisieren...")
grouped = group_by_category(articles)
for cat, arts in grouped.items():
    print(f"     {cat}: {len(arts)} Artikel")
print()

print("3/4 · KI-Zusammenfassung mit Gemini...")
summaries = summarize_with_gemini(grouped)
print()

print("4/4 · E-Mail erstellen & versenden...")
html = build_html(summaries, grouped)
send_email(html)

print(f"\n✅ Fertig! Newsletter verschickt.\n")
```

if **name** == "**main**":
main()
