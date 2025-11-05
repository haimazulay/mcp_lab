from datetime import datetime, timezone

def get_now_iso_utc() -> str:
    """Return current UTC time in ISO-8601 format with 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
