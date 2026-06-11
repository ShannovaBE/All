# Shannova Compliance Engineering Report

Date: 2026-06-01

## Scope Completed

This work covered the first three launch-blocking priorities from the compliance review:

1. Secret exposure cleanup
2. Canonical codebase cleanup
3. Structured audit logging foundation

The canonical working copy is now:

- Backend: `backend/`
- Frontend: `frontend/`

Older sibling folders outside this production-final directory were treated as reference snapshots and were not pushed as part of this cleanup.

## 1. Secret Exposure Cleanup

Completed:

- Removed canonical local secret files:
  - `backend/.env`
  - `backend/Beta/kaggle.json`
  - `frontend/.env.local`
- Removed generated local user-store data:
  - `backend/backend/users_store/`
  - `backend/users_store/`
- Added safe templates:
  - `backend/.env.example`
  - `frontend/.env.example`
- Added a root `.gitignore` that blocks:
  - `.env` and `.env.*`
  - `kaggle.json`
  - service-account/key JSON files
  - local SQLite DBs
  - Python and Node runtime folders
  - Next.js build output
  - model/output/test-data artifacts that should not be committed
- Removed the already-exposed public GitHub file `Beta/kaggle.json` from `ShannovaBE/All` main in commit `721b2f11c18c81c88b7bbd69c21e4836ccd91394`.

Required manual follow-up:

- Rotate the exposed Kaggle credential in the Kaggle account.
- Rotate any Google/service-account credentials that were copied locally or may have been shared.
- Consider history-rewrite/removal for any previously committed secrets if the public repository will remain public.

## 2. Canonical Codebase Cleanup

Completed:

- Treated `shannova-production-final` as the canonical app root.
- Added a root ignore policy so future pushes exclude local runtime files and generated artifacts.
- Kept production frontend and backend together for a clean GitHub branch push.
- Left older duplicate folders outside this app root untouched.

Important note:

- This branch intentionally excludes large generated artifacts and local runtime folders. The product code, configs, migrations, tests, and report are the intended push scope.

## 3. Audit Logging Foundation

Completed:

- Added `backend/audit.py`.
- Added `AuditEvent` model to `backend/models.py`.
- Added Alembic migration:
  - `backend/alembic/versions/3f9a2c1b8d71_create_audit_events.py`
- Added structured audit calls for sensitive actions, including:
  - dataset upload
  - dataset metadata reads
  - dataset listing
  - dataset download URL generation
  - dataset deletion
  - dataset description updates
  - user registration
  - user login attempts
  - account reads
  - review reads/submissions
  - admin review listing/moderation/deletion
  - plan updates
  - user deletion
- Audit events include:
  - `actor_id`
  - `action`
  - `resource`
  - `timestamp`
  - `ip`
  - `purpose`
  - `result`
  - redacted metadata
- Audit writes are fail-open: they emit structured JSON logs and attempt database persistence, but do not break the user-facing operation if audit storage is temporarily unavailable.

## Test Results

Passed:

- `python3 -m compileall -q audit.py main.py models.py db.py auth reviews metadata users tests`
- `../backend/.venv_test/bin/python -m unittest discover -s tests -v`
  - 23 tests run
  - 22 passed
  - 1 skipped: pipeline fast-path test skipped because that test venv does not include the pipeline/pandas dependency set
- `npm run lint` in `frontend/`

Secret scan:

- Canonical app contains only `.env.example` placeholders after excluding generated/model/test-data artifacts.
- Public GitHub `Beta/kaggle.json` now returns 404.

## Remaining Launch-Blocking Work

Recommended next priorities:

1. Apply the latest Alembic migrations against the deployed production database.
2. Configure the scheduled retention workflow secrets in GitHub Actions.
3. Review and merge the latest compliance branch into the production branch.

## Follow-Up Implementation: Access Control, DSR, And Provenance

Date: 2026-06-01

Completed after the first compliance foundation pass:

1. API-level licence and KYB access control
   - Added backend policy helpers for plan rank, sensitivity level, KYB requirements, permitted uses, and restricted accounts.
   - Dataset downloads now require `X-User-Id` and enforce owner/admin bypass, buyer licence tier, KYB status, dataset restriction state, and purpose.
   - Seller upload now requires a known, unrestricted, KYB-verified user.
   - Added admin KYB status endpoint: `PATCH /admin/users/{user_id}/kyb`.
   - Users now carry `kyb_status` and `restricted` state in their safe public payload.

2. Data Subject Rights APIs
   - Added `GET /users/{user_id}/export?format=json` for JSON user data export.
   - Added `GET /users/{user_id}/export?format=csv` for CSV export.
   - Added `PATCH /users/{user_id}/restrict` to restrict or unrestrict processing for a user.
   - Restriction requests propagate to owned dataset records by setting their `restriction_status`.
   - Existing `DELETE /users/{user_id}` remains the erasure path and now sits beside export/restriction coverage.

3. Provenance and compliance evidence
   - Added durable dataset fields:
     - `provenance`
     - `compliance_evidence`
     - `access_policy`
     - `restriction_status`
   - Added migration:
     - `backend/alembic/versions/4a6e8f0c2b19_add_dataset_compliance_fields.py`
   - Upload now stores source, uploader, file hash, storage provider, object key, MIME source, pipeline version, transformations, stats, PII evidence, category evidence, quality evidence, access policy, and listing decision.

Additional tests added:

- `backend/tests/test_access_controls.py`
- `backend/tests/test_dsr_export.py`

Validation after this pass:

- `python3 -m compileall -q audit.py main.py models.py db.py auth reviews metadata users tests`
- `../backend/.venv_test/bin/python -m unittest discover -s tests -v`
  - 31 tests run
  - 30 passed
  - 1 skipped: pipeline fast-path test skipped because that test venv does not include the pipeline/pandas dependency set
- `npm run lint` in `frontend/`

Notes:

- Access policy is intentionally conservative. Medical uploads default to `special_category`; PII redaction escalates non-special datasets to `sensitive`; sensitive and special-category access requires KYB.
- The product now has retention enforcement, stronger password hashing, and CI checks. The user store has also been moved to the database in the latest follow-up pass.

## Follow-Up Implementation: Retention, Password Hashing, And CI

Date: 2026-06-08

Completed in this pass:

1. Retention automation
   - Added durable dataset retention fields:
     - `retention_policy`
     - `retention_expires_at`
   - Added migration:
     - `backend/alembic/versions/5d2b7c9a10ef_add_dataset_retention_fields.py`
   - Upload now assigns a default retention policy and expiry using `DEFAULT_RETENTION_DAYS`.
   - Added `backend/retention.py` with a retention sweep that finds expired active datasets and restricts them.
   - Added admin endpoint:
     - `POST /admin/retention/run`
   - Retention is intentionally non-destructive by default. It locks expired datasets with `restriction_status=retention_expired`; object deletion only runs when `RETENTION_DELETE_OBJECTS=true`.

2. Password hashing hardening
   - Replaced unsalted SHA-256 password storage with versioned PBKDF2-SHA256 hashes.
   - Added constant-time password verification.
   - Preserved legacy SHA-256 login compatibility.
   - Successful login with a legacy hash automatically upgrades the stored password hash to PBKDF2.
   - Added `PASSWORD_PBKDF2_ITERATIONS` to `backend/.env.example`.

3. CI and secret scanning
   - Added GitHub Actions workflow:
     - `.github/workflows/compliance-checks.yml`
   - CI runs:
     - secret scan
     - backend dependency install
     - backend compile
     - backend unit tests
     - frontend dependency install
     - frontend lint
   - Added local/CI secret scan script:
     - `scripts/secret_scan.sh`

Additional tests added:

- `backend/tests/test_password_hashing.py`
- `backend/tests/test_retention.py`

Validation after this pass:

- `python3 -m compileall -q audit.py main.py models.py db.py auth reviews metadata users tests retention.py`
- `.venv_test/bin/python -m unittest discover -s tests -v`
  - 37 tests run
  - 36 passed
  - 1 skipped: pipeline fast-path test skipped because that test venv does not include the pipeline/pandas dependency set
- `sh scripts/secret_scan.sh`
- `npm run lint` in `frontend/`

Remaining production work from this pass was completed in the next follow-up, except for executing migrations against the real deployed database, which requires production credentials.

## Follow-Up Implementation: Scheduled Retention, Dependency Audits, And Database Users

Date: 2026-06-08

Completed in this pass:

1. Scheduled retention
   - Added scheduled GitHub Actions workflow:
     - `.github/workflows/retention-sweep.yml`
   - The workflow runs daily and can be triggered manually.
   - It calls `POST /admin/retention/run` with `dry_run=false`.
   - Required GitHub secrets:
     - `SHANNOVA_RETENTION_URL`
     - `SHANNOVA_RETENTION_ADMIN_USER_ID`
   - Added command-line runner:
     - `backend/scripts/run_retention_sweep.py`

2. Dependency vulnerability scanning
   - Updated `.github/workflows/compliance-checks.yml` to run:
     - `pip-audit` for backend dependencies
     - `npm audit --omit=dev --audit-level=high` for frontend production dependencies
   - Upgraded frontend Next.js from `15.5.6` to `15.5.19` to clear critical/high npm audit findings.
   - Current frontend production audit exits cleanly at the high threshold. NPM still reports a moderate transitive PostCSS advisory inside Next, with no non-breaking npm fix available.

3. Database-backed users
   - Added SQLAlchemy `User` model.
   - Replaced the file-backed `backend/users_store/users.json` runtime store with database-backed CRUD in `backend/users/store.py`.
   - Added Alembic migration:
     - `backend/alembic/versions/6e3f8a2b4c11_create_users_table.py`
   - Preserved the existing public user payload and auth function API.
   - Kept PBKDF2 password hashing and legacy SHA-256 upgrade-on-login.
   - Added one-time migration helper for old local/dev JSON users:
     - `backend/scripts/_one_time/migrate_users_json_to_db.py`

4. Migration verification
   - Made older migrations dialect-aware so CI can smoke-test a fresh SQLite database.
   - CI now runs:
     - `DATABASE_URL=sqlite:///./ci_migration_check.db alembic upgrade head`

Additional tests updated:

- `backend/tests/test_password_hashing.py`
  - Now verifies PBKDF2, legacy hash upgrade, failed-login non-upgrade, and database-backed user CRUD.

Validation after this pass:

- `python3 -m compileall -q audit.py main.py models.py db.py auth reviews metadata users tests retention.py scripts`
- `.venv_test/bin/python -m unittest discover -s tests -v`
  - 38 tests run
  - 37 passed
  - 1 skipped: pipeline fast-path test skipped because that test venv does not include the pipeline/pandas dependency set
- `DATABASE_URL=sqlite:///./ci_migration_check.db alembic upgrade head`
- `sh scripts/secret_scan.sh`
- `npm run lint` in `frontend/`
- `npm audit --omit=dev --audit-level=high` in `frontend`
- `pip-audit -r` against an audit-safe backend requirements file
  - No known Python dependency vulnerabilities found outside the custom-index Torch CPU wheel line

Remaining production-only action:

- Run `alembic upgrade head` against the deployed production database using production credentials.
- Configure the two retention workflow secrets in GitHub Actions after the production API URL/admin user are confirmed.
