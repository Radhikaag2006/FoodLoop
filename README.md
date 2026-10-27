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

## Dispatch: who drives which run
`DISPATCH_MODE` decides how planned runs are given to drivers. It is an
optimisation solver (Google OR-Tools), not machine learning.

| Mode | What happens |
|------|--------------|
| `rules` (default) | One run at a time to the nearest eligible driver, as before. |
| `solver` | New runs wait `DISPATCH_BATCH_SECONDS` (default 120), then all waiting runs are assigned together to minimise total driving. Stops inside a run are ordered with 2-opt. If the solver fails it falls back to `rules`. |
| `shadow` | `rules` decide; the solver's answer and km are stored for comparison (admin Overview, Dispatch). |

Hard rules in every mode: driver active and available, vehicle capacity at
least the run's kg, a driver who declined a run never gets it back. A decline
re-plans that run and the other runs still waiting for a yes.

Settings (env): `DISPATCH_MODE`, `DISPATCH_BATCH_SECONDS`,
`SOLVER_TIME_LIMIT_S` (5), `UNASSIGNED_PENALTY_KM` (1000),
`DISPATCH_LOAD_KM` (5, extra cost per run a driver already holds),
`OSRM_URL` (optional road distances; any error falls back to straight line x
`ROAD_FACTOR`), `OSRM_TIMEOUT_S`, `AVG_SPEED_KMH`.
Admin: Overview shows the reason for each assignment; `POST
/api/admin/dispatch/run` gives out waiting runs immediately.
`trip_log` records each offer and what happened (logged only, for later analysis).
Compare methods on random scenarios: `python scripts/sim_dispatch.py`.

## Deploy (real users)
1. `cp .env.example .env`, set SECRET_KEY (long random), DB_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD.
2. `docker compose up -d --build` (app on port 8000, Postgres, persistent uploads).
3. Put it behind HTTPS (Caddy, nginx, or a host like Render/Railway/Fly). HTTPS is
   required for the camera QR scanner, secure cookies and "Install app".
4. Sign in as the platform admin, add real facilities (Sites), then invite
   hub staff. Businesses sign up themselves and you verify them. Production starts empty; no demo data.
Without Docker: set the same env vars and run the Procfile command.

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
