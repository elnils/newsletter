from pathlib import Path
from datetime import datetime, timedelta
import re

cutoff = datetime.now() - timedelta(days=365)
archiv = Path("scripts/archiv")

if not archiv.exists():
    print("Kein Archiv-Ordner, ueberspringe")
    exit(0)

removed = 0
for f in archiv.glob("20*.html"):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", f.stem)
    if m:
        file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        if file_date < cutoff:
            f.unlink()
            removed += 1
            print("  Geloescht: {}".format(f.name))

print("Fertig: {} alte Dateien entfernt".format(removed))
