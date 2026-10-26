"""Central configuration, read from environment variables (see .env.example)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader so the project has no python-dotenv dependency."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.1"))
LOCATION_REGION = os.getenv("LOCATION_REGION", AWS_REGION)
TRANSACTIONS_FILE = Path(os.getenv("TRANSACTIONS_FILE", ROOT / "data" / "transactions.json"))

# Geo-velocity thresholds (tunable; documented in docs/ADR-001)
SAME_METRO_KM = float(os.getenv("SAME_METRO_KM", "50"))
MAX_GROUND_KMH = float(os.getenv("MAX_GROUND_KMH", "120"))
AIR_CRUISE_KMH = float(os.getenv("AIR_CRUISE_KMH", "850"))
AIR_OVERHEAD_HOURS = float(os.getenv("AIR_OVERHEAD_HOURS", "1.5"))
