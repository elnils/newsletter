import os, json

# ─────────────────────────────────────────────
# KONFIGURATION – passt zum Apps-Script (Newsletter.gs)
# ─────────────────────────────────────────────
SHEET_TAB      = "Tabellenblatt1"   # Tab mit E-Mail + Status (NICHT der Formular-Tab "Tabelle1")
EMAIL_COLUMNS  = ["E-Mail", "Email", "Mail", "E-Mail-Adresse"]
STATUS_COLUMNS = ["Status", "status"]
ACTIVE_VALUES  = ("aktiv", "active", "ja", "yes", "")  # "" = kein Status → als aktiv werten

# ─────────────────────────────────────────────

base     = os.environ.get("RECIPIENT_EMAIL", "")
sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
creds    = os.environ.get("GOOGLE_CREDENTIALS", "")

recipients = {e.strip().lower() for e in base.split(",") if e.strip() and "@" in e}


def _first_value(row, columns):
    for col in columns:
        if col in row and str(row[col]).strip():
            return str(row[col]).strip()
    return ""


if sheet_id and creds:
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        info   = json.loads(creds)
        # Diagnose: zeigt die Service-Account-Adresse (zum Abgleich mit der Sheet-Freigabe)
        print("Service-Account:", info.get("client_email", "??? FEHLT IN JSON"))
        print("Sheet-ID (Laenge):", len(sheet_id), "Zeichen")

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        gc     = gspread.authorize(Credentials.from_service_account_info(info, scopes=scopes))
        ss     = gc.open_by_key(sheet_id)
        print("Sheet geoeffnet:", ss.title)
        print("Vorhandene Tabs:", [w.title for w in ss.worksheets()])

        try:
            ws = ss.worksheet(SHEET_TAB)
        except Exception:
            print("Hinweis: Tab '" + SHEET_TAB + "' nicht gefunden - nutze erstes Blatt")
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
                recipients.discard(email)
                inactive += 1

        print("Sheet geladen:", active, "aktiv,", inactive, "abgemeldet ->",
              len(recipients), "Empfaenger gesamt")

    except Exception as e:
        print("FEHLER-TYP:", type(e).__name__)
        print("FEHLER-DETAIL:", str(e))
        import traceback
        traceback.print_exc()
        print("Fallback auf Secret-Empfaenger")
else:
    print("Kein Sheet konfiguriert - Empfaenger nur aus Secret")

final_list = sorted(recipients)
print("Finale Empfaengerzahl:", len(final_list))
with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write("RECIPIENT_LIST=" + ",".join(final_list) + "\n")
