# Changelog

## Unreleased

### Added

- Private-beta registration controlled by a server-side email allowlist.
- Mandatory beta privacy-notice acknowledgment.
- Optional, separate ML research consent with version and timestamp tracking.
- Immediate research-consent withdrawal that excludes the user from future research evaluation.
- PostgreSQL support for production deployments while preserving local SQLite development.
- Vercel rewrites, Render service configuration, and Neon deployment guidance.
- PostgreSQL backup and restoration procedure.

### Changed

- Production startup now requires an explicit PostgreSQL `DATABASE_URL`.
- Production CORS and cookie settings are environment-driven.
- Protected application data requires privacy-notice acknowledgment.
- Database changes use additive migrations and do not import local SQLite records.
- Forecast errors no longer expose internal exception details.

### Verification

- Backend tests: 42 passed.
- Deployment and multi-user security tests: 11 passed.
- Frontend production build: passed.
- Backend and ML source compilation: passed.
