# FoodLoop

Mobile-first installable app (PWA) that routes food waste by expiry date:
expired or spoiled food never goes to human-food or feed routes; it goes only
to certified compost or biogas. Businesses add expired or surplus lots, hub
operators plan and run bulk pickups, and every completed pickup gets a
tamper-evident (hash-chained) disposal record.

Roles: business owner, hub operator (pickup person), platform admin.

## Run locally
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    DEMO_MODE=1 uvicorn app.main:app --reload
Open http://localhost:8000 on a phone-sized window.
Demo mode seeds fictional data. Accounts (password `Demo@1234`):
admin@foodloop.local, business 9000000005 (verified) and 9000000006
(pending), hub 9000000007.
Reset demo data: `DEMO_MODE=1 python -m app.seed --reset --demo`.
Tests: `python -m pytest -q tests`.

## Deploy (real users)
1. `cp .env.example .env`, set SECRET_KEY (long random), DB_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD.
2. `docker compose up -d --build` (app on port 8000, Postgres, persistent uploads).
3. Put it behind HTTPS (Caddy, nginx, or a host like Render/Railway/Fly). HTTPS is
   required for the camera QR scanner, secure cookies and "Install app".
4. Sign in as the platform admin, add real facilities (Sites), then invite
   hub staff. Businesses sign up themselves and you verify them. Production starts empty; no demo data.
Without Docker: set the same env vars and run the Procfile command.

## Production safety
- `DEMO_MODE` is ignored when `ENV=production` or on Render (`RENDER=true`):
  no demo data, no "Try a demo account" button, no demo admin.
- On every production start, demo accounts that still use the public demo
  password are switched off, and `ADMIN_PASSWORD` may not be `Demo@1234`.
- The admin comes from `ADMIN_EMAIL` and `ADMIN_PASSWORD` and is created only
  when no admin exists. To reset an existing one, set `ADMIN_PASSWORD_RESET=1`
  for one deploy, then remove it.

## Before you call it live
- Phone OTP/SMS verification (today: password + admin verification of businesses).
- Lawyer-reviewed Terms and Privacy (in-app text is a draft).
- Real, certified facility partners; verify each one's certificate yourself.
- Alembic migrations, backups of Postgres and uploads, error monitoring.
- Rate limiter is in-memory: use Redis if you run several processes.
- Placeholders to replace with sourced figures: CO2e factor (0.5/kg), meal
  weight (0.4 kg), points and facility rates.
- The disposal record proves a record wasn't altered. It is not an FSSAI or
  pollution-board certificate.
