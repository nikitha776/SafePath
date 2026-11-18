# SafePath — Neon setup and verification

Completed 22 October 2026 in `/home/nikitha07/Projects/SafePath`.

## Target and deployed service

- Organization: `org-orange-frog-83556943`
- Project: `rapid-king-66728186`
- Branch: `production` (`br-rough-brook-a1d4gbys`)
- CLI: 8.10.3, via the npx-installed package
- Managed service wired: PostgreSQL only, with PostGIS 3.6
- Frontend and FastAPI remain local; the database is hosted by Neon.

## What changed

Created the root `neon.ts` policy and private `.neon` link. Neon deploy populated `DATABASE_URL`, `DATABASE_URL_UNPOOLED` and `NEON_BRANCH` in the existing `.env`; the Geoapify key was preserved. All credentials remain backend-only, ignored by Git, and absent from the compiled browser bundle.

Installed the `neon` and `neon-postgres` agent skills locally. Preserved the existing SQLAlchemy/Psycopg architecture. Added support for `.env.local`, pooled application queries, direct migration connections, SSL, bounded pools and connection timeouts.

Validated the initial Alembic migration on temporary branch `br-patient-mountain-a1819s3z` before applying it to production. Both migrations passed, and the temporary branch was deleted and its removal confirmed. Added the idempotent OSM importer and imported 103 road records and 123 mapped streetlights. Original source and fetch timestamps are retained.

Added `/api/database/health` and `/api/evidence`, plus a switchable streetlight overlay. The default pilot bounding box returns all 103 intersecting road records and 109 lamp points. No operating-status or safety guarantee is inferred.

## Deployment output

`neon config plan` and `neon deploy` were run through the npx-installed CLI. The verified deploy output was:

```text
→ Applying to branch production (br-rough-brook-a1d4gbys)

Utilized services: Postgres
No changes — branch production already matches the policy.
Pulled 3 Neon variables into .env
  Postgres        DATABASE_URL, DATABASE_URL_UNPOOLED
  Branch          NEON_BRANCH
```

“No changes” refers to Neon service policy. Alembic separately applied the application's PostGIS schema.

## Verification output

`npm run build` exited 0 after the final code/configuration changes:

```text
▲ Next.js 16.4.2 (Turbopack)
✓ Compiled successfully in 3.8s
  Finished TypeScript in 1167ms
✓ Generating static pages using 5 workers (4/4) in 374ms

Route (app)
┌ ○ /
└ ○ /_not-found
```

`npm test`:

```text
6 passed, 1 warning in 0.67s
```

`npm run db:verify` exercised the real pooled connection and rolled probe writes back:

```text
PostgreSQL read/write + PostGIS geography query: PASS
Probe cleanup (rollback): PASS
Applied migration: 0001_osm_evidence
Persistent cached OSM evidence: {"street_lamp": 123, "road": 103}
Geometry validity and SRID: PASS
```

The app was started after the successful build using `npm run dev`:

```text
Uvicorn running on http://127.0.0.1:8000
Local: http://127.0.0.1:3000
✓ Ready in 293ms
```

`npm run test:services` then exercised the real Next.js → FastAPI → Neon flow and existing mapping integration:

```text
Next.js → FastAPI → Neon health: HTTP 200
Next.js → FastAPI → PostGIS evidence: HTTP 200 {"road": 103, "street_lamp": 109}
Source attribution and fetch timestamps: PASS
Geoapify location search: HTTP 200
Geoapify walking routes: HTTP 200, 2 candidate(s)
```

Browser verification showed two walking candidates, 109 mapped streetlights, map points, and a working show/hide control. A screenshot is included alongside this report.

## Failures and recovery

1. `npm i -g neon@latest` failed with ENOENT in the global npm installation path. Used the npx-installed CLI instead.
2. The first init attempt could not create the Neon CLI configuration directory. Granted access to the necessary directory, then retried.
3. Automatic multi-agent plugin installation failed because the child npm command attempted to use the read-only default npm cache. Completed init with `--no-agent-setup`, then installed the required project skills separately using a writable npm cache. No MCP plugin is required for this app's database connection.
4. Initial npm fetch/install attempts were slow; subsequent CLI commands used the cached npx installation.
5. A Next.js multiple-lockfile warning was resolved by explicitly setting the frontend Turbopack root. The final build completed without that warning.
6. Unit tests emit a Starlette TestClient deprecation warning about httpx. All six tests pass; the live application and PostgreSQL/Geoapify end-to-end checks pass. This warning concerns the test harness.

No setup, migration, database verification, or end-to-end failure remains unresolved. Production hosting of the frontend/FastAPI, authentication, and route safety scoring are outside this PostgreSQL wiring step.

## Reproduce

From the project root:

```sh
npm run build
npm test
npm run db:verify
npm run dev
# In another terminal:
npm run test:services
```

Keep credentials in the ignored environment files; there is no need to paste a connection string into chat.
