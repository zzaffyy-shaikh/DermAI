# DermAI — Security Review

Snapshot of the security posture, what's fixed, and what to do before a public deployment.

## Fixed / in place
- **Passwords** hashed with PBKDF2-HMAC-SHA256 (200k iterations) + per-user salt; never stored or logged in plaintext. Constant-time comparison on verify.
- **Auth** via opaque bearer tokens (DB-backed); `/auth/logout` deletes the token.
- **RBAC** enforced on every protected route via `require_role(...)` (patient / doctor / admin).
- **Authorization checks**: patients can only read their own sessions/reports; doctor/admin endpoints are role-gated.
- **Doctor data scoping** (QA-hardened): a doctor can only read a patient's medical history / report if that patient has a consultation case with them — no blanket access to all patient records. Admins may access all.
- **Verification gate**: doctors *and* management start unverified and are blocked from their panels until approved by a verified admin.
- **Input validation** (QA-hardened): blank/whitespace usernames rejected; age constrained to 0–120.
- **CORS**: `allow_credentials=False` (we use bearer tokens, not cookies).
- **Google sign-in** verifies the ID token server-side against our client ID (audience check) — the client cannot forge identity.
- **Input validation** via Pydantic on all JSON bodies.
- **`.gitignore`** keeps `.env`, `dermai.db`, and generated reports out of version control.
- **Startup warnings** if dev-auth is on, the default admin password is unchanged, or CORS is open.

## Must do before production
1. **Disable dev auth:** set `DERMAI_AUTH_MODE` to anything other than `dev` (this turns off the `X-Role`/`X-User-Id` header bypass used for local testing).
2. **Change the admin password:** `DERMAI_SEED_ADMIN_PASSWORD=<strong>` (and delete/rotate the seeded `admin` if exposed).
3. **Rotate the Gemini API key** — it was committed in `.env.example`. Generate a new one, put it only in `.env` (gitignored), and remove it from `.env.example`.
4. **Restrict CORS:** set `DERMAI_CORS_ORIGINS` to your real frontend origin(s), not `*`.
5. **Serve over HTTPS** (TLS terminated by nginx/Caddy or the platform). Bearer tokens and report links must not travel over plain HTTP in production.
6. **Restrict the Google OAuth client** to your production origins in Google Cloud Console.

## Recommended hardening (next)
- **Token expiry / rotation** — tokens currently don't expire; add an `expires_at` and reject stale tokens.
- **Rate limiting** on `/auth/*` (e.g. slowapi) to slow brute force.
- **Report links**: `/report/{id}?token=` puts the token in the URL (can leak via logs/history). Prefer the `Authorization` header (the app already supports it); keep the query param only for convenience.
- **Upload limits**: cap image size / validate content-type to prevent large-upload abuse.
- **Audit logging** for doctor/admin actions (consults, verifications, history edits).
- **Medical data**: encrypt the DB at rest and document consent/retention (GDPR/HIPAA-style) since this stores health data.
