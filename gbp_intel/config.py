"""Settings come from environment variables (or a local .env file, never committed)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
DB_PATH = Path(os.environ.get("GBP_INTEL_DB", ROOT / "data" / "gbp_intel.db"))
# Optional. When set, every page asks for this password (any username).
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

# Google Maps Platform terms: Place IDs may be stored indefinitely; other
# Places content may be cached for at most 30 days.
PLACES_CACHE_DAYS = 30

PROJECTS = ["Deck repair", "Concrete", "Pest control", "Window cleaning", "House cleaning", "Other"]
