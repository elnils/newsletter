import os, json

# ─────────────────────────────────────────────
# KONFIGURATION – Tab- und Spaltennamen
# ─────────────────────────────────────────────
# Anmelde-Tabs (werden zusammengefuehrt). Pro Tab: (Tab-Name, moegliche Spaltennamen fuer die Mail)
SUBSCRIBE_TABS = [
    ("Tabelle 1", ["Mail-Adresse eintragen", "E-Mail", "Email", "E-Mail-Adresse"]),
    ("Bestand",   ["E-Mail", "Email", "Mail", "E-Mail-Adresse"]),
]
# Abmelde-Tab (wird abgezogen)
UNSUBSCRIBE_TAB     = "Unsubscribed"
UNSUBSCRIBE_COLUMNS = ["E-Mail", "Email", "Mail", "E-Mail-Adresse"]

# ─────────────────────────────────────────────

base     = os.environ.get("RECIPIENT_EMAIL", "")
sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
creds    = os.environ.get("GOOGLE_CREDENTIALS", "")

# Start: Empfaenger aus dem Secret (Fallback / zusaetzliche feste Adressen)
recipients = {e.strip().lower() for e in base.split(",") if e.strip() and "@" in e}


def _emails_from_tab(spreadsheet, tab_name, possible_columns):
    """Liest alle Mail-Adressen aus einem Tab. Probiert mehrere Spaltennamen.
    Gibt leere Menge zurueck, wenn der Tab fehlt oder leer ist."""
    found = set()
    try:
        ws = spreadsheet.worksheet(tab_name)
    except Exception:
        print(f"  Hinweis: Tab '{tab_name}' nicht gefunden – uebersprungen")
        return found

    try:
        rows = ws.get_all_records()
    except Exception as e:
        print(f"  Warnung: Tab '{tab_name}' nicht lesbar: {e}")
        return found

    for row in rows:
        # ersten passenden Spaltennamen nehmen, der einen Wert hat
        value = ""
        for col in possible_columns:
            if col in row and str(row[col]).strip():
                value = str(row[col]).strip()
                break
        email = value.lower()
        if email and "@" in email:
            found.add(email)
    return found


if sheet_id and creds:
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        info   = json.loads(creds)
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        gc     = gspread.authorize(Credentials.from_service_account_info(info, scopes=scopes))
        ss     = gc.open_by_key(sheet_id)

        # 1) Anmeldungen aus allen Subscribe-Tabs sammeln
        subscribed = set()
        for tab_name, cols in SUBSCRIBE_TABS:
            tab_emails = _emails_from_tab(ss, tab_name, cols)
            print(f"  Tab '{tab_name}': {len(tab_emails)} Adressen")
            subscribed |= tab_emails

        # 2) Abmeldungen abziehen
        unsubscribed = _emails_from_tab(ss, UNSUBSCRIBE_TAB, UNSUBSCRIBE_COLUMNS)
        print(f"  Tab '{UNSUBSCRIBE_TAB}': {len(unsubscribed)} Abmeldungen")

        active = subscribed - unsubscribed
        recipients |= active

        # Sicherheitsnetz: auch aus dem Secret stammende Adressen respektieren Abmeldungen
        recipients -= unsubscribed

        print(f"Sheet geladen: {len(active)} aktive (Sheet) + Secret, "
              f"{len(unsubscribed)} abgemeldet → {len(recipients)} gesamt")

    except Exception as e:
        print(f"Warnung: Google Sheet nicht erreichbar: {e}")
        print(f"Fallback: {len(recipients)} Empfaenger aus Secret")
else:
    print(f"Kein Sheet konfiguriert – {len(recipients)} Empfaenger aus Secret")

# sortierte, deduplizierte Liste rausschreiben
final_list = sorted(recipients)
with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write("RECIPIENT_LIST={}\n".format(",".join(final_list)))
