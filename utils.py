from datetime import datetime

def format_date_ru(date_iso: str) -> str:
    if not date_iso:
        return ""
    dt = datetime.fromisoformat(date_iso)
    return dt.strftime("%d.%m.%Y")

def parse_date_ru(date_str: str) -> str:
    dt = datetime.strptime(date_str.strip(), "%d.%m.%Y")
    return dt.date().isoformat()
