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
    """HTML-Newsletter mit vollständig inline-gestyltem HTML (forward-safe)."""
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

    # Inline-Style-Konstanten
    FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    COLOR_NAVY   = "#1b2a3b"
    COLOR_NAVY2  = "#2c3e50"
    COLOR_BLUE   = "#5a7fa0"
    COLOR_LIGHT  = "#a0b4c4"
    COLOR_MUTED  = "#7a9bb5"
    COLOR_BG     = "#f8f9fa"
    COLOR_BORDER = "#e8e8e8"
    COLOR_TEXT   = "#1c1c1e"
    COLOR_TEXT2  = "#3a3a3c"

    category_blocks = ""
    items = list(summaries.items())
    for idx, (category, bullets) in enumerate(items):
        articles = grouped.get(category, [])
        is_last = (idx == len(items) - 1)
        border_bottom = "none" if is_last else f"1px solid {COLOR_BORDER}"

        # Bullet-Punkte – mit Dash als Prefix-Zeichen (inline, kein ::before)
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

        # Artikel-Links
        links_html = ""
        seen_links = set()
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
    FONT_ESC = FONT  # alias for use in f-strings below

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="de">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light">\n'
        f'  <title>Tagesbrief &ndash; {date_str}</title>\n'
        '</head>\n'
        f'<body style="margin:0;padding:0;background:#f0f2f4;font-family:{FONT_ESC};'
        f'-webkit-text-size-adjust:100%;mso-line-height-rule:exactly;">\n'

        # Outer wrapper
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:#f0f2f4;">\n<tr><td align="center" style="padding:20px 8px;">\n'

        # Inner card
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="max-width:620px;background:#ffffff;border-radius:4px;'
        f'border:1px solid #dde3e8;">\n'

        # HEADER
        f'<tr><td style="background:{COLOR_NAVY};padding:32px 32px 26px;text-align:center;'
        f'border-radius:4px 4px 0 0;">\n'
        f'  <div style="font-family:{FONT_ESC};font-size:10px;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:{COLOR_MUTED};margin-bottom:10px;">'
        f'Dein täglicher Nachrichtenüberblick</div>\n'
        f'  <div style="font-family:{FONT_ESC};font-size:28px;font-weight:700;'
        f'color:#ffffff;letter-spacing:-0.5px;margin-bottom:8px;">Tageslage</div>\n'
        f'  <div style="font-family:{FONT_ESC};font-size:13px;color:{COLOR_LIGHT};">'
        f'{date_str} &middot; {daytime}s-Ausgabe</div>\n'
        f'</td></tr>\n'

        # META BAR
        f'<tr><td style="background:{COLOR_NAVY2};padding:8px 32px;text-align:center;'
        f'font-family:{FONT_ESC};font-size:11px;color:{COLOR_MUTED};">\n'
        f'  {len(RSS_FEEDS)}&nbsp;Quellen &nbsp;&middot;&nbsp; '
        f'{total_articles}&nbsp;Artikel &nbsp;&middot;&nbsp; KI-Zusammenfassung\n'
        f'</td></tr>\n'

        # CATEGORY BLOCKS
        + category_blocks +

        # FOOTER
        f'<tr><td style="background:{COLOR_NAVY};padding:20px 32px;text-align:center;'
        f'border-radius:0 0 4px 4px;">\n'
        f'  <p style="font-family:{FONT_ESC};font-size:11px;color:{COLOR_MUTED};'
        f'line-height:1.8;margin:0;">\n'
        f'    Automatisch erstellt am {now.strftime("%d.%m.%Y")} '
        f'um {now.strftime("%H:%M")} Uhr<br>\n'
        f'    Quellen: Spiegel Online &middot; FAZ &middot; Politico Europe<br>\n'
        f'    <a href="https://www.google.de" style="color:{COLOR_LIGHT};text-decoration:none;">'
        f'Powered by Nils</a>\n'
        f'  </p>\n'
        f'</td></tr>\n'

        '</table>\n'   # inner card
        '</td></tr>\n'
        '</table>\n'   # outer wrapper
        '</body>\n</html>'
    )

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
    subject = f"🗞️ Tageslage – {now.strftime('%d.%m.%Y')} ({daytime}s-Ausgabe)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Tageslage <{sender}>"
    msg["To"] = recipient

    plain = f"Tageslage – {now.strftime('%d.%m.%Y')}\nBitte HTML-Ansicht aktivieren."
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

    print("3/4 · KI-Zusammenfassung mit Groq...")
    summaries = summarize_with_gemini(grouped)
    print()

    print("4/4 · E-Mail erstellen & versenden...")
    html = build_html(summaries, grouped)
    send_email(html)

    print(f"\n✅ Fertig! Newsletter verschickt.\n")


if __name__ == "__main__":
    main()
