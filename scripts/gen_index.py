import re
from pathlib import Path
from datetime import datetime

archiv_dir = Path("scripts/archiv")
if not archiv_dir.exists():
    print("Kein Archiv-Ordner, ueberspringe")
    exit(0)

files = sorted(archiv_dir.glob("20*.html"), reverse=True)
file_count = len(files)

COLOR_NAVY   = "#1b2a3b"
COLOR_NAVY2  = "#2c3e50"
COLOR_BLUE   = "#5a7fa0"
COLOR_MUTED  = "#7a9bb5"
COLOR_LIGHT  = "#a0b4c4"
COLOR_BORDER = "#e8e8e8"
FONT         = "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"

rows = ""
for f in files:
    m = re.match(r"(\d{4}-\d{2}-\d{2})-(morgen|abend)", f.stem)
    if not m:
        continue
    date_raw, edition = m.group(1), m.group(2)
    d = datetime.strptime(date_raw, "%Y-%m-%d")
    days_de  = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    months_de = [
        "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ]
    date_de    = "{}, {}. {} {}".format(days_de[d.weekday()], d.day, months_de[d.month - 1], d.year)
    edition_de = "Morgen" if edition == "morgen" else "Abend"

    rows += (
        '<tr style="border-bottom:1px solid ' + COLOR_BORDER + ';">'
        '<td style="padding:11px 16px;font-size:11px;color:' + COLOR_MUTED + ';white-space:nowrap;">' + date_de + '</td>'
        '<td style="padding:11px 8px;font-size:11px;color:' + COLOR_MUTED + ';">' + edition_de + '</td>'
        '<td style="padding:11px 16px;">'
        '<a href="archiv/' + f.name + '" style="font-size:13px;color:' + COLOR_BLUE + ';text-decoration:none;">'
        'Tageslage ' + date_de + ' – ' + edition_de + '-Ausgabe</a>'
        '</td></tr>\n'
    )

html = (
    '<!DOCTYPE html>\n<html lang="de">\n<head>\n'
    '  <meta charset="UTF-8">\n'
    '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    '  <title>Tageslage – Archiv</title>\n</head>\n'
    '<body style="margin:0;padding:0;background:#f0f2f4;font-family:' + FONT + ';">\n'
    '<div style="background:' + COLOR_NAVY + ';padding:36px 24px 28px;text-align:center;">\n'
    '  <div style="max-width:720px;margin:0 auto;">\n'
    '    <div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:' + COLOR_MUTED + ';margin-bottom:10px;">Newsletter-Archiv</div>\n'
    '    <div style="font-size:30px;font-weight:700;color:#fff;margin-bottom:8px;">Tageslage</div>\n'
    '    <div style="font-size:13px;color:' + COLOR_LIGHT + ';">Alle Ausgaben &middot; ' + str(file_count) + ' Eintraege</div>\n'
    '  </div>\n</div>\n'
    '<div style="background:' + COLOR_NAVY2 + ';padding:8px 24px;text-align:center;font-size:11px;color:' + COLOR_MUTED + ';">\n'
    '  Automatisch aktualisiert &middot; Archiv der letzten 365 Tage\n</div>\n'
    '<div style="max-width:720px;margin:32px auto;padding:0 16px 40px;">\n'
    '  <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid ' + COLOR_BORDER + ';border-radius:4px;border-collapse:collapse;">\n'
    '    <thead>\n'
    '      <tr style="border-bottom:2px solid ' + COLOR_NAVY2 + ';">\n'
    '        <th style="padding:12px 16px;text-align:left;font-size:10px;text-transform:uppercase;color:' + COLOR_MUTED + ';font-weight:600;">Datum</th>\n'
    '        <th style="padding:12px 8px;text-align:left;font-size:10px;text-transform:uppercase;color:' + COLOR_MUTED + ';font-weight:600;">Ausgabe</th>\n'
    '        <th style="padding:12px 16px;text-align:left;font-size:10px;text-transform:uppercase;color:' + COLOR_MUTED + ';font-weight:600;">Link</th>\n'
    '      </tr>\n    </thead>\n'
    '    <tbody>\n' + rows + '    </tbody>\n'
    '  </table>\n</div>\n'
    '<div style="background:' + COLOR_NAVY + ';padding:20px 24px;text-align:center;">\n'
    '  <p style="font-size:11px;color:' + COLOR_MUTED + ';line-height:1.8;margin:0 0 8px;">'
    'Powered by Nils</p>\n'
    '  <a href="https://forms.gle/LSavK3JVp3aAsLGm9" style="font-size:11px;color:' + COLOR_LIGHT + ';text-decoration:underline;">'
    'Newsletter abonnieren</a>\n'
    '</div>\n</body>\n</html>\n'
)

# index.html liegt im Repo-Root (wird von GitHub Pages als Startseite genutzt)
Path("scripts/archiv/index.html").write_text(html, encoding="utf-8")
print("index.html mit {} Eintraegen generiert".format(file_count))
