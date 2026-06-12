import os, json

# ─────────────────────────────────────────────
# KONFIGURATION – passt zum Apps-Script (Newsletter.gs)
# ─────────────────────────────────────────────
SHEET_TAB      = "Tabellenblatt1"   # Tab mit E-Mail + Status (NICHT der Formular-Tab "Tabelle1")
EMAIL_COLUMNS  = ["E-Mail", "Email", "Mail", "E-Mail-Adresse"]
STATUS_COLUMNS  = ["Status", "status"]
# Sicherer Ansatz: nur explizit abgemeldete Werte schliessen aus.
# Alles andere (auch leer, auch Tippfehler) gilt als aktiv – niemand faellt
# versehentlich raus.
INACTIVE_VALUES = ("inaktiv", "inactive", "nein", "no", "abgemeldet", "unsubscribed")

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

        # Status pro Adresse sammeln. Bei Dubletten (gleiche Adresse mehrfach
        # im Sheet, z.B. durch An-/Abmelde-Tests) gilt: AKTIV gewinnt.
        # Begruendung: Eine echte Abmeldung aendert per Apps-Script die
        # BESTEHENDE Zeile auf "inaktiv" – erzeugt also keine Dublette.
        # Dubletten (aktiv + inaktiv nebeneinander) stammen daher aus Tests
        # oder manuellen Eintraegen; dort ist "aktiv" der gewollte Zustand.
        status_per_email: dict[str, bool] = {}   # email -> ist_aktiv
        for row in rows:
            email  = _first_value(row, EMAIL_COLUMNS).lower()
            status = _first_value(row, STATUS_COLUMNS).lower()
            if not email or "@" not in email:
                continue
            ist_aktiv = status not in INACTIVE_VALUES
            # einmal aktiv => bleibt aktiv
            status_per_email[email] = status_per_email.get(email, False) or ist_aktiv

        active   = sum(1 for v in status_per_email.values() if v)
        inactive = sum(1 for v in status_per_email.values() if not v)

        for email, ist_aktiv in status_per_email.items():
            if ist_aktiv:
                recipients.add(email)
            else:
                recipients.discard(email)   # auch Secret-Adressen respektieren Abmeldung

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
