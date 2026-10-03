"""Project paths, all resolved from the repository root."""

from pathlib import Path

# Resolve root from this file's location
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "aarogya.db"
SEED_CSV = DATA_DIR / "patients_sample.csv"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "aarogya.log"
