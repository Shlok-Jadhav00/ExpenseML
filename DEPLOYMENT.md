# ExpenseML private beta deployment

This checklist prepares a fresh Neon PostgreSQL database, a Render FastAPI
service, and a Vercel frontend. It does not deploy services or copy the local
SQLite database. Replace every placeholder before using it.

## Environment variables

### Render

Set these in the Render service dashboard:

- `APP_ENV=production`
- `DATABASE_URL`: Neon pooled or direct PostgreSQL URL
- `CORS_ORIGINS`: the exact Vercel origin, for example `https://expenseml.vercel.app`
- `COOKIE_SECURE=true`
- `SESSION_SAMESITE=lax`
- `BETA_MODE=true`
- `BETA_ALLOWED_EMAILS`: comma-separated invited email addresses
- `SESSION_MAX_AGE_SECONDS=604800`
- `SESSION_IDLE_TIMEOUT_SECONDS=86400`

Never commit `DATABASE_URL`, allowlists, passwords, API keys, or `.env` files.

### Vercel

The frontend uses same-origin relative API paths. No backend URL is required
in the frontend environment. Replace `YOUR-RENDER-SERVICE` in `vercel.json`
with the actual Render service hostname before deployment.

## Neon

Create a new empty PostgreSQL database for beta users. Copy its connection URL
to Render as `DATABASE_URL`. The application creates missing tables and applies
only additive schema changes at startup. It never imports `data/expenses.db`.

## Backup and restoration

For PostgreSQL, create an encrypted, access-controlled custom-format backup:

```powershell
pg_dump --format=custom --file=expenseml-beta-YYYYMMDD.dump "$env:DATABASE_URL"
```

Restore into a separately verified database, not directly over the live beta:

```powershell
createdb expenseml_beta_restore
pg_restore --clean --if-exists --dbname="$env:RESTORE_DATABASE_URL" expenseml-beta-YYYYMMDD.dump
```

Verify user counts, transaction counts, login, account deletion, and isolation
in the restored database before any cutover. Store backups outside GitHub with
restricted access and test a restoration before beta launch and periodically
afterward. The local SQLite database remains local and is not part of this
procedure.

## Launch checklist

1. Create the empty Neon database and configure Render variables.
2. Replace the Render hostname placeholder in `vercel.json`.
3. Deploy the frontend to Vercel and copy its exact HTTPS origin into
   Render's `CORS_ORIGINS`.
4. Confirm Render `/health` is healthy.
5. Register one invited account through the Vercel domain. Confirm the
   HttpOnly, Secure session cookie, CSRF token flow, login, logout, and expiry.
6. Confirm an unapproved email is rejected while `BETA_MODE=true`.
7. Test two independent invited accounts: each can see only its own records.
8. Test optional research consent, then withdraw it and verify the user's
   consent flag is immediately false.
9. Test account deletion and confirm that the user's transactions and sessions
   are removed.
10. Create and verify the first encrypted database backup.

The Vercel-domain checks require the services to be deployed and cannot be
completed from this local workspace. Do not treat a local test as proof that
the production cookie or rewrite configuration works.
