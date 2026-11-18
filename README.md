# SafePath

A safety-aware navigation project, starting with walking routes in Indiranagar, Bengaluru.

## Stack

- Next.js 16 App Router, React, TypeScript, Tailwind CSS
- MapLibre GL JS with Geoapify raster tiles
- Python 3.12 + FastAPI
- Neon PostgreSQL + PostGIS (production branch connected and migrated)
- Geoapify for search/routing; cached OpenStreetMap infrastructure stored in PostGIS

## Start locally

From `/home/nikitha07/Projects/SafePath`:

```sh
npm run dev
```

Open http://localhost:3000. The FastAPI service runs on http://127.0.0.1:8000 and its API documentation is at http://127.0.0.1:8000/docs. Stop both services with Ctrl+C. Ports 3000 and 8000 should be free before starting.

The frontend proxies `/api/*` to the backend. Optional `API_BASE_URL` in the frontend environment overrides the backend address. External API requests consume Geoapify credits, including map tiles. This is a local development application: rate limiting, authentication and shared tile caching are required before deployment.

## Fresh installation

Node.js 20.9+ and Python 3.12 are required. This checkout already has installed dependencies.

```sh
npm ci
npm --prefix frontend ci
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock
cp .env.example .env
```

Add `GEOAPIFY_API_KEY` to the root `.env`. It is read by the Python backend only. Never prefix provider keys with `NEXT_PUBLIC_`. The existing private key and pilot data were copied into this project without displaying the key.

## What works now

- Active-city landmark/address search, rejecting low-confidence and overly broad matches
- Real walking routes for balanced and shortest-distance preferences
- Exact geometry deduplication and graceful partial provider failures
- Interactive map, route selection, distance and duration
- Backend-only provider credentials and map tile proxy with cache headers
- PostGIS evidence cache with spatial index and source timestamps
- Neon-backed evidence API and switchable mapped-streetlight overlay
- Selected-route shop, petrol, pharmacy, hospital and police pins with category filters and click-to-view details

The active Bengaluru sample runs from Indiranagar Metro Station to Chinmaya Mission Hospital; the Vijayawada configuration is retained. Confirm all matched locations before travel. A routing candidate is not a safety recommendation. Different geometries may overlap substantially. Departure-time schedule analysis is available. Safety scoring, navigation, community reports and SOS are not implemented yet. The mapped-light overlay is infrastructure evidence, not an operational lighting assessment.

## Neon setup

Connected to project `rapid-king-66728186`, organization `org-orange-frog-83556943`, branch `production`. `neon.ts` declares Postgres-only infrastructure. The local `.neon` link and private `.env` are ignored by Git.

The global Neon installation was unavailable, so commands use `npx neon@latest`. The PostgreSQL and parent Neon skills are installed in `.agents/skills/`. Authentication completed successfully.

```sh
npx neon@latest deploy
npm run db:migrate
npm run db:import-osm
```

`deploy` reconciles Neon backend services and pulls their credentials; it does not publish the frontend. Keep `GEOAPIFY_API_KEY`, `DATABASE_URL` (pooled app traffic), and `DATABASE_URL_UNPOOLED` (direct migrations) in the root `.env` or `.env.local`; process environment wins and `.env.local` overrides `.env`. No secrets use `NEXT_PUBLIC_`.

FastAPI uses Psycopg 3 through SQLAlchemy with a bounded reusable connection pool, connection checks, SSL and timeouts. Alembic uses the direct URL and no application pool. The initial migration passed on a temporary child of production before being applied to production; that temporary branch was deleted.

The cached sample imported 103 road ways and 123 lamp nodes. The default evidence bounding box contains 109 lamps. Records retain source URLs, original download timestamps and source-update times where supplied; importing does not make observations fresh. The importer is idempotent and does not overwrite a newer cached observation with older data. Download metadata alone does not confirm lamp operation.

Endpoints:

- `/api/database/health`: real connection, PostGIS and cache checks
- `/api/evidence`: bounded spatial query returning GeoJSON and provenance

## Validation

```sh
npm test
npm run build
npm run db:verify
# With npm run dev running:
npm run test:services
```

Backend tests cover invalid coordinates, duplicate candidates, partial mapping-service failures, broad search matches, and preventing provider-key echo. Live smoke checks verified search, two walking candidates, and PNG tiles. Browser checks verified rendered map tiles, route lines, and switching the selected route. The production build and all ten API tests pass. Live database verification checks read/write, PostGIS geography queries, rollback cleanup, applied migration, stored records and geometry validity. End-to-end checks call the database/evidence and Geoapify endpoints through the Next.js proxy; the browser also verified loading and toggling mapped lights.

## Existing feasibility work

- `docs/pilot-reports/`: completed Geoapify and direct OSM reports
- `scripts/check_pilot.py`: bounded Geoapify audit
- `scripts/check_osm.py`: direct Overpass audit
- `scripts/check_osm_sample.py`: small cached OSM main-API fallback audit
- `work/pilot-data/`: ignored cached API results and OSM XML

Public Overpass endpoints timed out during the audit, but a small main-API sample succeeded. Use cached extracts or a managed ingestion service for production, rather than making public OSM/Overpass requests for each journey. Missing lighting/hour data means unknown. Mapped lamps and schedules do not confirm current operation.

## Next milestone

Measure evidence coverage along complete walking-route corridors, expand the cached pilot area, and evaluate business schedules at estimated segment arrival times. Keep confidence separate from any future concern score.

Map data © OpenStreetMap contributors, ODbL: https://www.openstreetmap.org/copyright. Mapping services by Geoapify: https://www.geoapify.com/.

## Places along a selected route

`POST /api/route-places` accepts active-city `LineString` or `MultiLineString` geometry and a corridor width (default 100 meters, allowed 50–300). Geoapify performs separate category searches; the backend additionally checks approximate point-to-segment distance without connecting disjoint legs. It deduplicates exact OSM identifiers/place IDs and gives specific facility categories priority over shops. Different OSM elements can still describe the same physical establishment.

Pins use a green shopping bag for shops, amber petrol pump for fuel, purple cross for pharmacies, rose H for hospitals, and blue shield for police. The on-map legend explains the symbols. Category controls in the scrollable journey panel show available counts and hide/show each group. Dense pins are decluttered in screen space, prioritizing assistance categories; zooming in reveals overlapping places without moving their true coordinates. Results refresh when the selected route changes. Aborted requests cannot restore stale pins.

Popups show the mapped name, address, approximate straight-line distance from the route, and schedule when available. They do not claim live opening, accessible entrances or emergency capability. Provider-supplied names/addresses are rendered as text, not HTML.

Each category search is capped at 100 records; the UI explicitly flags possible truncation and individual category failures. Complete results are cached in bounded memory for five minutes. No travel history or new database schema is introduced by this feature. The current hospital pilot route returned 100 shop records, 12 pharmacies, six hospitals and one police listing; no petrol record was found within that route's 100-meter corridor. These are mapped records, not a complete census.

Validation: the production build passed, ten API tests passed, two live walking-route corridors were checked, and browser checks verified marker popups, category toggles and refreshing pins after selecting a different route.

## Visual theme

The interface uses a charcoal-and-grey night palette with a subtle CSS grey-cloud background and Geoapify Dark Matter raster tiles. Place pins are compact 20 × 24 pixels (previously 29 × 33), with 12-pixel symbols. Collision spacing and popup offsets match the smaller pins. Streetlight dots are also slightly smaller. Category colors remain semantic, while the route uses a muted mint highlight for visibility on the dark map. The production build and live dark-tile request passed; browser checks verified route rendering and clickable pin popups.

## City configuration

`frontend/src/config/cities.json` is the public configuration shared by frontend, backend and OSM import. `activeCity` currently selects `bengaluru`; `vijayawada` remains available. Change it and restart both servers (rebuild for production). This controls map center, sample journey, search bounds, route/POI validation, and evidence query bounds. These pilot bounds are approximate service coverage, not municipal boundaries.

OSM cache import expects `work/pilot-data/<activeCity>_osm_sample.xml`, downloaded from the OSM map API using the configured `evidenceBounds` in west,south,east,north order. Import with `npm run db:import-osm`. It retains existing city records; spatial queries isolate the active sample. The sample does not cover the entire city, and missing lighting data means unknown. Historical Bengaluru feasibility reports/scripts remain labelled as historical pilot work.

## Android mobile app

The Expo + React Native app is in `mobile/`. It shares the Vijayawada configuration and FastAPI services while retaining the web frontend. See `mobile/README.md` for development APK, USB backend forwarding and location-permission testing. Run `npm run mobile` from the root to start its development server.

## Time-aware business activity

The web planner accepts a departure date/time in **Asia/Kolkata (IST)**. All candidate routes request `POST /api/route-activity` with the route geometry, `duration_seconds` and an offset-aware ISO `departure_time`. The API reuses the normalized 5-minute POI cache but reevaluates schedules on every departure change. Existing `/api/route-places` remains compatible with the mobile prototype.

Arrival at each listing is approximated by its closest projected position along the ordered route geometry, multiplied by the route's total walking duration. It assumes average pace, excludes stops/access detours and artificial connectors between disjoint geometry legs, and selects the earliest closest encounter on looping routes. It is not live navigation or measured segment timing.

`opening-hours-py==2.1.4` handles OSM weekly, split and overnight schedules in IST. Closing instants are excluded. Missing, malformed, comment-only/by-appointment schedules remain unknown. Holiday/school-holiday and solar expressions remain unknown because validated local context is not available. Raw schedules may be stale; every label is an expectation, not a real-time confirmation.

Summaries show expected open/closed/unknown counts for shops, fuel and pharmacies, plus usable-hours coverage. Hospitals and police listings are evaluated individually but excluded from commercial-activity totals. Listing truncation/provider failures remain visible. These counts do not prove street activity, accessible assistance or safety, and the pilot does not rank routes by safety.

Validation: `npm test` covers schedule boundaries, overnight/day rollover, timezone conversion, closing during travel, missing/conditional hours, cache isolation across departure changes and disconnected-leg progress. On 22 October 2026 the live sample had usable hours for only 7 of 112 businesses (6%); other hours remained unknown.

## Prototype section assessment

Each `/api/route-activity` response now includes an `assessment` with sections of up to 100 metres, estimated passage times, business schedules at section arrival, mapped lighting coverage, explicit foot/access restrictions, hospital/police listing proximity, and coverage-based evidence confidence. Cached infrastructure is queried within 150 metres of the route; database failures preserve business results and return an assessment with missing infrastructure.

The web UI separates mapped concern from evidence confidence, shows an outer section-evidence band, and exposes per-section reasons under **Evidence**. Unknown evidence never becomes an unlit/unsafe condition. A mapped-support gap describes listing proximity, not an observed isolated street. Infrastructure operation and assistance availability remain unverified.

Comparison is a conservative prototype heuristic, not a calibrated probability of harm. It declines ranking for sparse schedules, missing/stale infrastructure or incomplete listings. Where complete evidence passes the documented thresholds, it compares only mapped conditions, requires a meaningful score difference and accounts for travel-time tradeoffs. Crime, real-time footfall, verified current illumination and a validated risk model remain absent. The present Bengaluru sample does not meet the gates and displays **Insufficient evidence to rank**.

Run `npm test`, `npm --prefix frontend run test:assessment`, and `npm run build` to validate the implementation. See `docs/route-assessment-validation.md` for methods and live results.
