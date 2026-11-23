# Student Gig & Skill Marketplace (IT 109)

FastAPI + PostgreSQL (Supabase) + Upstash Redis + Supabase Storage + Google OAuth +
PayMongo sandbox + PSGC + Google SMTP, with a Nuxt 3 frontend.

* Phase 1 (done): `backend/` and `database/`
* Phase 2 (done): `frontend/` (see `frontend/README.md` for setup)
* Phase 3 (next): five diagrams, PDF documentation, pitch deck

## 1. Folder structure

```
student-gig-marketplace/
├── database/schema.sql            # run once in Supabase SQL Editor
└── backend/
    ├── requirements.txt
    ├── .env.example               # copy to .env (never commit .env)
    └── app/
        ├── main.py                # app, CORS, security headers, global rate limit
        ├── config.py              # reads environment variables
        ├── db.py                  # Postgres pool, parameterized queries only
        ├── cache.py               # Upstash Redis + in-memory fallback, invalidation
        ├── ratelimit.py           # fixed-window rate limiter
        ├── security.py            # JWT, RBAC dependencies, reCAPTCHA check
        ├── validators.py          # RegEx rules + XSS text cleaning
        ├── schemas.py             # request validation models
        ├── routers/               # auth, profiles, gigs, bids, contracts, webhooks, admin
        └── services/              # email, storage, paymongo, escrow, bidcounts
```

## 2. Setup steps

1. **Supabase**: create a project. SQL Editor > paste `database/schema.sql` > Run.
   Copy the pooler connection URI to `DATABASE_URL`, and the project URL and
   service role key to `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`.
2. **Upstash** (optional): create a free Redis database, copy the REST URL and token.
   Leave blank to use the in-memory cache.
3. **Google Cloud Console**: create OAuth client (Web). Authorized redirect URI:
   `http://localhost:8000/auth/google/callback`. Create a reCAPTCHA v2 checkbox key pair
   (Google publishes test keys for development).
4. **PayMongo**: use test keys only (`sk_test_...`). Create a webhook for
   `checkout_session.payment.paid` pointing to `https://<public-url>/webhooks/paymongo`
   (use ngrok on localhost) and put its secret in `PAYMONGO_WEBHOOK_SECRET`.
   Without a public URL, the client's "Sync payment" button calls
   `POST /contracts/{id}/sync-payment`, which asks PayMongo directly.
5. **Gmail SMTP**: enable 2-step verification, create an App Password, use it as `SMTP_PASSWORD`.
6. Run:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env                                   # then fill it in
   uvicorn app.main:app --reload
   ```
   Open http://localhost:8000/docs for the interactive API.
7. Log in once with Google, then make yourself admin in the SQL Editor:
   `update users set role = 'admin' where email = 'you@gmail.com';`

## 3. Transaction workflow and endpoints

| Step | Actor | Endpoint | Result |
|---|---|---|---|
| 1 | Client | `POST /gigs` (CAPTCHA) | gig `pending_approval` |
| 2 | Admin | `POST /admin/gigs/{id}/approve` | gig `approved`, listing cache invalidated |
| 3 | Freelancer | `POST /gigs/{id}/bids` (CAPTCHA) | bid `pending`, bid-count cache invalidated |
| 4 | Client | `POST /bids/{id}/accept` | contract `pending_payment`, gig `awarded` |
| 5 | Client | `POST /contracts/{id}/pay` | returns PayMongo checkout URL |
| 6 | PayMongo | `POST /webhooks/paymongo` | payment `paid`, contract `funded` |
| 7 | Freelancer | `POST /contracts/{id}/submit` | external link saved, contract `submitted` |
| 8 | Client | `POST /contracts/{id}/approve` | contract `approved`, payout `pending` created |
| 9 | Admin | `PUT /admin/payouts/{id}` | manual record, payout `paid`, contract `paid_out` |

Other endpoints: `GET /gigs` (public, cached), `GET/PUT/DELETE /gigs/{id}`, `GET /gigs/mine`,
`GET /gigs/{id}/bids`, `GET /bids/mine`, `PUT/DELETE /bids/{id}`, `GET /contracts`,
`GET /contracts/{id}`, `POST /contracts/{id}/cancel`, `GET/POST /contracts/{id}/thread`,
`GET/PUT /profiles/me`, `GET /profiles/{id}`, `POST/PUT/DELETE /portfolio`,
`GET /psgc/...`, `GET /dashboard/{client|freelancer|admin}`, `GET /payouts/mine`,
`GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/gigs`, `GET /admin/payouts`.

## 4. Requirement checklist

| Requirement | Where |
|---|---|
| Google OAuth 2.0 | `routers/auth.py` |
| RBAC (backend) | `security.require_roles` on every route; ownership checks in routers |
| Rate limiting | global 120/min/IP in `main.py` + per-route limits (`ratelimit.py`) |
| SQL injection prevention | parameterized queries only (`db.py`), whitelisted ORDER BY |
| XSS prevention | `validators.clean_text`, CSP headers, escaped email HTML |
| RegEx validation | `validators.py`, `schemas.py` |
| CAPTCHA | reCAPTCHA v2 on login, gig create, bid create (`security.py`) |
| Caching + invalidation | `cache.py`, `routers/gigs.py`, `services/bidcounts.py` |
| Object storage | `services/storage_service.py` (Supabase Storage) |
| PayMongo sandbox + webhook | `services/paymongo_service.py`, `routers/webhooks.py` |
| Manual payouts | `routers/admin.py` `PUT /admin/payouts/{id}` |
| PSGC address | `routers/profiles.py` `/psgc/*` |
| SMTP emails | `services/email_service.py` |
| Secrets | `.env` via `config.py`; `.env.example` has no real values |

## 5. Known limits of this phase

* The code was compiled and its pure logic tested (validators, schemas, webhook
  signature, cache TTL/invalidation, rate limiter). It has **not** been run against
  real Supabase, Upstash, Google, PayMongo or SMTP; the build sandbox had no package
  installs or outside network access. Expect to fix small integration issues on first run.
* Add `.env` to `.gitignore` before your first commit.
