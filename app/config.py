"""All settings come from environment variables (see .env.example).
Values marked ASSUMPTION are placeholders: replace them with sourced
numbers before quoting them anywhere."""
import os

ENV = os.getenv("ENV", "development")          # development | production
IS_PROD = ENV == "production"
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./foodloop.db")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
if IS_PROD and SECRET_KEY == "dev-secret-change-me":
    raise RuntimeError("Set SECRET_KEY before running in production.")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))

# First platform admin, created at startup if no admin exists.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Optional email for password-reset codes. Without SMTP the code is
# only logged (development) or issued by an admin from the app.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "FoodLoop <no-reply@foodloop.local>")

# Demo data (fictional orgs, simulated history). Never enable for real use.
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

# Collection rules
MIN_DROP_KG = float(os.getenv("MIN_DROP_KG", "1.0"))
MIN_PICKUP_KG = float(os.getenv("MIN_PICKUP_KG", "10.0"))
HUB_TOLERANCE = 0.05       # allowed weight mismatch at the hub (5%)
VOID_MINUTES = 10          # guard can undo a drop within this window
QR_MAX_AGE = 300           # seconds a resident QR stays valid

# Rewards (ASSUMPTION: tune after a real pilot)
POINTS_PER_KG = int(os.getenv("POINTS_PER_KG", "10"))
DAILY_CAP_KG = float(os.getenv("DAILY_CAP_KG", "10.0"))

# Impact (ASSUMPTION: placeholders, not sourced)
CO2E_KG_PER_KG_FOOD = 0.5
MEAL_KG = 0.4

REJECT_REASONS = [
    "Medicine or hazardous item",
    "Mixed with non-food waste",
    "Raw meat or fish",
    "Leaking or unsafe container",
    "Other",
]

CITIES = {
    "Delhi": (28.6139, 77.2090),
    "Noida": (28.5355, 77.3910),
    "Greater Noida": (28.4744, 77.5040),
    "Ghaziabad": (28.6692, 77.4538),
    "Gurugram": (28.4595, 77.0266),
    "Faridabad": (28.4089, 77.3178),
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Bengaluru": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Chandigarh": (30.7333, 76.7794),
}
