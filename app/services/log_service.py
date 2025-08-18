import os, csv
from datetime import datetime
from ..constants import LOG_FILE

def append_log(evento: str, ip: str = "", impressora: str = "", detalhes: str = ""):
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "evento", "ip", "impressora", "detalhes"])
    ts = datetime.now().isoformat(sep=" ", timespec="seconds")
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([ts, evento, ip, impressora, detalhes])