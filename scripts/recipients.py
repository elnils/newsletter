import os, json

base     = os.environ.get("RECIPIENT_EMAIL", "")
sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
creds    = os.environ.get("GOOGLE_CREDENTIALS", "")

recipients = [e.strip() for e in base.split(",") if e.strip()]

if sheet_id and creds:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        info   = json.loads(creds)
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        gc     = gspread.authorize(Credentials.from_service_account_info(info, scopes=scopes))
        sheet  = gc.open_by_key(sheet_id).sheet1
        rows   = sheet.get_all_records()
        for row in rows:
            email  = str(row.get("E-Mail", row.get("email", ""))).strip().lower()
            status = str(row.get("Status", row.get("status", "aktiv"))).strip().lower()
            if email and status in ("aktiv", "active", "ja", "yes", ""):
                if email not in recipients:
                    recipients.append(email)
        print("Sheet geladen: {} aktive Empfaenger".format(len(recipients)))
    except Exception as e:
        print("Warnung: Google Sheet nicht erreichbar: {}".format(e))
else:
    print("Kein Sheet konfiguriert – {} Empfaenger aus Secret".format(len(recipients)))

with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write("RECIPIENT_LIST={}\n".format(",".join(recipients)))
