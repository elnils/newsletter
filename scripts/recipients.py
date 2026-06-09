import os, json

# ─────────────────────────────────────────────
# KONFIGURATION – passt zum Apps-Script (Newsletter.gs)
# ─────────────────────────────────────────────
# Das Apps-Script pflegt EINE Tabelle: Spalte A = E-Mail, Spalte B = Status.
# Status "aktiv" = bekommt Newsletter, "inaktiv" = abgemeldet.
SHEET_TAB     = "Tabelle1"   # exakt wie im Apps-Script CONFIG.SHEET_NAME (ohne Leerzeichen!)
EMAIL_COLUMNS = ["E-Mail", "Email", "Mail", "E-Mail-Adresse"]
STATUS_COLUMNS = ["Status", "status"]
ACTIVE_VALUES  = ("aktiv", "active", "ja", "yes", "")  # "" = kein Status gesetzt → als aktiv werten

# ─────────────────────────────────────────────

base     = os.environ.get("RECIPIENT_EMAIL", "")
sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
creds    = os.environ.get("GOOGLE_CREDENTIALS", "")

# Start: feste Adressen aus dem Secret (Fallback / Test)
recipients = {e.strip().lower() for e in base.split(",") if e.strip() and "@" in e}


def _first_value(row, columns):
    """Gibt den ersten nicht-leeren Wert aus den moeglichen Spaltennamen zurueck."""
    for col in columns:
        if col in row and str(row[col]).strip():
            return str(row[col]).strip()
    return ""


if sheet_id and creds:
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        info   = json.loads(creds)
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        gc     = gspread.authorize(Credentials.from_service_account_info(info, scopes=scopes))
        ss     = gc.open_by_key(sheet_id)

        # Tab oeffnen (per Name; faellt auf erstes Blatt zurueck, falls Name abweicht)
        try:
            ws = ss.worksheet(SHEET_TAB)
        except Exception:
            print(f"  Hinweis: Tab '{SHEET_TAB}' nicht gefunden – nutze erstes Blatt")
            ws = ss.sheet1

        rows = ws.get_all_records()

        active   = 0
        inactive = 0
        for row in rows:
            email  = _first_value(row, EMAIL_COLUMNS).lower()
            status = _first_value(row, STATUS_COLUMNS).lower()
            if not email or "@" not in email:
                continue
            if status in ACTIVE_VALUES:
                recipients.add(email)
                active += 1
            else:
                # "inaktiv" o.ae. → sicherstellen, dass die Adresse NICHT drin ist
                recipients.discard(email)
                inactive += 1

        print(f"Sheet geladen: {active} aktiv, {inactive} abgemeldet "
              f"→ {len(recipients)} Empfaenger gesamt")

    except Exception as e:
        print(f"FEHLER-TYP: {type(e).__name__}")
        print(f"FEHLER-DETAIL: {e}")
        import traceback
        traceback.print_exc()
        print(f"Fallback: {len(recipients)} Empfaenger aus Secret"
else:
    print(f"Kein Sheet konfiguriert – {len(recipients)} Empfaenger aus Secret")

# sortierte, deduplizierte Liste rausschreiben
final_list = sorted(recipients)
with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write("RECIPIENT_LIST={}\n".format(",".join(final_list)))
