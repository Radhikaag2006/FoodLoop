"""All settings come from environment variables (see .env.example).
Values marked ASSUMPTION are placeholders: replace them with sourced
numbers before quoting them anywhere."""
import os


def load_env_file(path=".env"):
    """Read KEY=VALUE lines from a .env file (git-ignored) into the
    environment. Real environment variables always win."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip("\"'"))


load_env_file()

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
def _env(name, default=""):
    """An environment value without stray spaces or line breaks. Hosting
    dashboards use multi-line boxes, so an invisible newline at the end of a
    pasted value is easy to add and would make a login impossible."""
    return os.getenv(name, default).strip()


ADMIN_EMAIL = _env("ADMIN_EMAIL")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")
# The admin above is only created when no admin exists yet. Set this to 1
# for one deploy to make an existing admin use ADMIN_EMAIL / ADMIN_PASSWORD
# (forgotten password, wrong first setup). Remove it afterwards.
ADMIN_PASSWORD_RESET = os.getenv("ADMIN_PASSWORD_RESET", "0") == "1"

# Optional email for password-reset codes. Without SMTP the code is
# only logged (development) or issued by an admin from the app.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "FoodLoop <no-reply@foodloop.local>")

# Demo data (fictional orgs, simulated history). Never enable for real use.
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

# Billing. Razorpay TEST keys only (rzp_test_...); with no keys the app
# uses a built-in simulated gateway (development only). Live keys are
# refused unless ALLOW_LIVE_PAYMENTS=1, so nobody is billed by accident.
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
ALLOW_LIVE_PAYMENTS = os.getenv("ALLOW_LIVE_PAYMENTS", "0") == "1"
# UPI QR for ride bills: money is paid straight to this UPI ID, so it must
# be YOUR account. Leave it empty to get a harmless demo QR (development only).
UPI_VPA = os.getenv("UPI_VPA", "").strip()
UPI_NAME = os.getenv("UPI_PAYEE_NAME", "FoodLoop").strip() or "FoodLoop"
FREE_PICKUPS = int(os.getenv("FREE_PICKUPS", "3"))   # trial per business
PLAN_DAYS = 30                                       # monthly plan length

# Driver fare for one run (paise). ASSUMPTION: placeholders, tune after a
# pilot with real drivers. fare = base + per km (road) + per extra stop
# + per kg handled. Straight-line km are scaled by ROAD_FACTOR.
DRIVER_BASE_PAISE = int(os.getenv("DRIVER_BASE_PAISE", "15000"))      # Rs 150
DRIVER_PER_KM_PAISE = int(os.getenv("DRIVER_PER_KM_PAISE", "1400"))   # Rs 14
DRIVER_PER_STOP_PAISE = int(os.getenv("DRIVER_PER_STOP_PAISE", "2500"))
DRIVER_PER_KG_PAISE = int(os.getenv("DRIVER_PER_KG_PAISE", "50"))
ROAD_FACTOR = float(os.getenv("ROAD_FACTOR", "1.3"))
# Dispatch: each run a collector already holds counts as this many km
# when picking the nearest one, so work spreads out.
DISPATCH_LOAD_KM = float(os.getenv("DISPATCH_LOAD_KM", "5"))

# Collection rules
MIN_DROP_KG = float(os.getenv("MIN_DROP_KG", "1.0"))
MIN_PICKUP_KG = float(os.getenv("MIN_PICKUP_KG", "10.0"))
# A small group rides along with a bigger run if a stop is this close (km)
CLUB_MAX_KM = float(os.getenv("CLUB_MAX_KM", "30"))
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
