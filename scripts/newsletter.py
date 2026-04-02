#!/usr/bin/env python3
"""
Nils automatisierter KI-Newsletter 
"""

import os
import json
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

def _normalize_title(title: str) -> str:
    """Titel normalisieren für Duplikat-Erkennung."""
    import re
    t = title.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def fetch_feeds() -> list[dict]:
    """Alle RSS-Feeds holen, Duplikate entfernen und Artikel sammeln."""
    articles = []
    seen_titles = set()

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
                summary = summary[:400] if summary else ""

                if not title:
                    continue

                # Duplikat-Check über normalisierten Titel
                norm = _normalize_title(title)
                if norm in seen_titles:
                    continue
                seen_titles.add(norm)

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

# ─────────────────────────────────────────────
# KATEGORISIERUNG (lokal, schnell)
# ─────────────────────────────────────────────

def categorize_article(article: dict) -> str:
    """Artikel einer Kategorie zuordnen anhand von Keywords."""
    text = (article["title"] + " " + article["summary"]).lower()

    if article["source"] == "Heise / c't":
        return "💻 Tech & KI"

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


def group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    """Artikel nach Kategorie gruppieren."""
    grouped = {}
    for article in articles:
        cat = categorize_article(article)
        grouped.setdefault(cat, []).append(article)
    sorted_grouped = {}
    for cat in CATEGORIES.keys():
        if cat in grouped:
            sorted_grouped[cat] = grouped[cat]
    return sorted_grouped

# ─────────────────────────────────────────────
# KI-ZUSAMMENFASSUNG MIT GROQ
# ─────────────────────────────────────────────

def summarize_with_gemini(grouped: dict[str, list[dict]]) -> dict[str, list[str]]:
    """Groq fasst jede Kategorie in Stichsätzen zusammen."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY nicht gesetzt!")

    client = Groq(api_key=api_key)

    summaries = {}

    for category, articles in grouped.items():
        if not articles:
            continue

        articles_text = "\n".join([
            f"- [{a['source']}] {a['title']}"
            + (f": {a['summary'][:200]}" if a['summary'] else "")
            for a in articles[:8]
        ])

        prompt = f"""Du bist ein präziser Nachrichtenredakteur in einem deutschen TOP-Blatt. Fasse die folgenden Nachrichten der Kategorie "{category}" in genau 2 knappen deutschen Stichsätzen zusammen.

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
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            bullet_points = [
                line.strip()
                for line in text.split("\n")
                if line.strip() and (line.strip().startswith("•") or line.strip().startswith("-") or line.strip().startswith("*"))
            ]
            bullet_points = ["• " + bp.lstrip("•-* ").strip() for bp in bullet_points]
            summaries[category] = bullet_points[:2]
            print(f"✓ Zusammenfassung: {category} ({len(summaries[category])} Punkte)")
        except Exception as e:
            print(f"✗ Groq-Fehler bei {category}: {e}")
            summaries[category] = [f"• Fehler beim Laden der Zusammenfassung: {e}"]

    return summaries

# ─────────────────────────────────────────────
# HTML-NEWSLETTER ERSTELLEN
# ─────────────────────────────────────────────

def build_html(summaries: dict[str, list[str]], grouped: dict[str, list[dict]]) -> str:
    """Schönen HTML-Newsletter bauen – seriös, mobile-first."""
    now = datetime.now()
    daytime = "Morgen" if now.hour < 13 else "Abend"
    date_str = now.strftime("%A, %d. %B %Y")

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

    category_blocks = ""
    for category, bullets in summaries.items():
        articles = grouped.get(category, [])

        # Artikel-Links – voller Titel, kein Abschneiden, jeder Link einzeln klickbar
        links_html = ""
        seen_links = set()
        for a in articles[:5]:
            if a["link"] and a["link"] not in seen_links:
                seen_links.add(a["link"])
                links_html += (
                    f'<a href="{a["link"]}" class="article-link">'
                    f'<span class="article-source">{a["source"]}</span>'
                    f'<span class="article-title">{a["title"]}</span>'
                    f'</a>\n'
                )

        bullets_html = "".join(
            f'<li>{b.lstrip("• ").strip()}</li>\n' for b in bullets
        )

        category_blocks += f"""
  <div class="cat-block">
    <h2 class="cat-title">{category}</h2>
    <ul class="summary-list">{bullets_html}</ul>
    <div class="articles">{links_html}</div>
  </div>
"""

    total_articles = sum(len(v) for v in grouped.values())

    css = """
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
        background: #f4f4f4;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        color: #1c1c1e;
        line-height: 1.6;
        -webkit-text-size-adjust: 100%;
    }

    .wrapper {
        max-width: 640px;
        margin: 0 auto;
        background: #ffffff;
    }

    /* HEADER */
    .header {
        background: #1b2a3b;
        padding: 36px 32px 28px;
        text-align: center;
    }
    .header-eyebrow {
        font-size: 10px;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: #7a9bb5;
        margin-bottom: 10px;
    }
    .header-title {
        font-size: 30px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.5px;
        margin-bottom: 6px;
    }
    .header-date {
        font-size: 13px;
        color: #a0b4c4;
    }

    /* META BAR */
    .meta-bar {
        background: #2c3e50;
        padding: 8px 32px;
        text-align: center;
        font-size: 11px;
        color: #7a9bb5;
        letter-spacing: 0.3px;
    }

    /* CONTENT */
    .content {
        padding: 0 24px 24px;
    }

    /* CATEGORY BLOCK */
    .cat-block {
        padding: 24px 0 20px;
        border-bottom: 1px solid #e8e8e8;
    }
    .cat-block:last-child {
        border-bottom: none;
    }
    .cat-title {
        font-size: 16px;
        font-weight: 700;
        color: #1b2a3b;
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 2px solid #2c3e50;
        display: inline-block;
    }

    /* SUMMARY BULLETS */
    .summary-list {
        list-style: none;
        margin-bottom: 14px;
    }
    .summary-list li {
        font-size: 14px;
        line-height: 1.6;
        color: #3a3a3c;
        padding: 3px 0 3px 14px;
        position: relative;
    }
    .summary-list li::before {
        content: "–";
        position: absolute;
        left: 0;
        color: #5a7fa0;
        font-weight: 600;
    }

    /* ARTICLE LINKS */
    .articles {
        display: block;
    }
    .article-link {
        display: block;
        text-decoration: none;
        padding: 8px 12px;
        margin-bottom: 4px;
        background: #f8f9fa;
        border-left: 3px solid #d0dce8;
        border-radius: 2px;
        transition: border-color 0.15s, background 0.15s;
    }
    .article-link:hover {
        background: #eef3f8;
        border-left-color: #2c3e50;
    }
    .article-source {
        display: block;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #5a7fa0;
        margin-bottom: 2px;
    }
    .article-title {
        display: block;
        font-size: 13px;
        color: #1c1c1e;
        line-height: 1.4;
        word-break: break-word;
    }

    /* FOOTER */
    .footer {
        background: #1b2a3b;
        padding: 20px 32px;
        text-align: center;
        font-size: 11px;
        color: #7a9bb5;
        line-height: 1.8;
    }
    .footer a {
        color: #a0b4c4;
        text-decoration: none;
    }

    /* MOBILE */
    @media (max-width: 480px) {
        .header { padding: 28px 20px 22px; }
        .header-title { font-size: 24px; }
        .meta-bar { padding: 8px 16px; }
        .content { padding: 0 16px 20px; }
        .footer { padding: 18px 16px; }
        .article-link { padding: 10px 12px; }
        .article-title { font-size: 14px; }
        .summary-list li { font-size: 14px; }
    }
    """

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>Tagesbrief – {date_str}</title>
  <style>{css}</style>
</head>
<body>
<div class="wrapper">

  <div class="header">
    <div class="header-eyebrow">Ihr täglicher Nachrichtenüberblick</div>
    <div class="header-title">Tagesbrief</div>
    <div class="header-date">{date_str} &middot; {daytime}s-Ausgabe</div>
  </div>

  <div class="meta-bar">
    {len(RSS_FEEDS)} Quellen &nbsp;·&nbsp; {total_articles} Artikel &nbsp;·&nbsp; Zusammengefasst mit KI
  </div>

  <div class="content">
    {category_blocks}
  </div>

  <div class="footer">
    Automatisch erstellt am {now.strftime("%d.%m.%Y")} um {now.strftime("%H:%M")} Uhr<br>
    Quellen: Spiegel Online · FAZ · Politico Europe<br>
    <a href="https://github.com">Powered by GitHub Actions</a>
  </div>

</div>
</body>
</html>"""

    return html

# ─────────────────────────────────────────────
# E-MAIL VERSENDEN
# ─────────────────────────────────────────────

def send_email(html_content: str):
    """Newsletter per Gmail SMTP versenden."""
    sender = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL", sender)

    if not sender or not password:
        raise ValueError("GMAIL_ADDRESS oder GMAIL_APP_PASSWORD nicht gesetzt!")

    now = datetime.now()
    daytime = "Morgen" if now.hour < 13 else "Abend"
    subject = f"🗞️ Tagesbrief – {now.strftime('%d.%m.%Y')} ({daytime}s-Ausgabe)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Tagesbrief <{sender}>"
    msg["To"] = recipient

    plain = f"Tagesbrief – {now.strftime('%d.%m.%Y')}\nBitte HTML-Ansicht aktivieren."
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())

    print(f"✓ Newsletter verschickt an {recipient}")

# ─────────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"  TAGESBRIEF – {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}\n")

    print("1/4 · RSS-Feeds laden...")
    articles = fetch_feeds()
    print(f"     → {len(articles)} Artikel gesammelt\n")

    print("2/4 · Kategorisieren...")
    grouped = group_by_category(articles)
    for cat, arts in grouped.items():
        print(f"     {cat}: {len(arts)} Artikel")
    print()

    print("3/4 · KI-Zusammenfassung mit Groq...")
    summaries = summarize_with_gemini(grouped)
    print()

    print("4/4 · E-Mail erstellen & versenden...")
    html = build_html(summaries, grouped)
    send_email(html)

    print(f"\n✅ Fertig! Newsletter verschickt.\n")


if __name__ == "__main__":
    main()
