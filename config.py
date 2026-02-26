import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db" / "tracker.db"

# Optional SMTP settings for automated email opt-outs
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

SMTP_CONFIGURED = bool(SMTP_USER and SMTP_PASS)

# Optional: CapSolver API key for automated CAPTCHA solving
# Get yours at https://capsolver.com — ~$0.80/1000 Turnstile, $1/1000 reCAPTCHA v2
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "")
CAPSOLVER_CONFIGURED = bool(CAPSOLVER_API_KEY)
