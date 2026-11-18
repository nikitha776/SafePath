# Prototype mapped-condition assessment — 23 October 2026

This change extends `/api/route-activity`; existing business schedules and raw `/api/route-places` remain compatible. The web interface shows separate mapped concern and evidence-confidence fields, a coloured outer evidence band on the selected route, comparison explanations and a per-section evidence list under **Evidence**.

## Checks

- Backend tests: 43 passing, including geometry subdivision, disconnected legs, schedule changes, explicit unlit/access tags versus missing data, stale/partial-source ranking gates, DB failure and gaps without mapped support.
- Frontend comparison checks: 7 passing (`npm --prefix frontend run test:assessment`): insufficient data, missing/non-finite scores/times, meaningful differences, one-candidate fallback and substantial travel-time trade-offs.
- Production frontend build passes, including TypeScript and static generation.
- Both real Bengaluru sample routes return HTTP 200 with 10 sections of at most 100 m each. At 23:00 IST, confidence coverage indices are 10%; mapped lighting coverage is approximately 26% / 27%. Neither route passes the ranking gates. Both return null route concern scores and **Insufficient evidence**.
- Browser visual verification could not be completed: the existing preview tab was on an error-page URL blocked by the browser's protocol policy. That page was not bypassed. API and build checks completed; reopen/refresh the normal HTTP preview to inspect the UI.

## Method

Sections preserve route vertices and disjoint geometry legs. Time at the section midpoint is derived from proportion of route length and total provider walking duration, excluding stops and assistance/access detours. Published business schedules are reevaluated at each section's passage time. Nearby businesses are within 100 m straight-line of the section; hospital/police listings use 200 m.

Infrastructure is read from Neon within 150 m of the route (maximum 2000 records). Sections are sampled at intervals no greater than 20 m. A road centerline within 15 m supplies road/foot/access tags. A mapped lamp within 20 m or `lit=yes` supplies a mapped-lighting proxy; `lit=no` is kept distinct and takes precedence. None confirms lamp operation or measured illumination. Tags from nearby roads may not represent the exact walking surface. A fixed 18:00–06:00 IST window marks nighttime; this is not calculated sunset or weather visibility.

The prototype confidence value is an **evidence-coverage index**, not a statistical confidence or probability of harm: 45% usable local business schedules, 40% lighting evidence coverage and 15% road evidence coverage, weighted by section length. Incomplete/truncated sources reduce it; missing infrastructure prevents strong confidence. Infrastructure older than 180 days or missing fetch dates reduces it further. Fetch age does not establish current conditions.

Concern contributions use only evaluable schedule, explicit lighting and access indicators (45/35/20 provisional weights, normalized over available indicators). Missing evidence is never converted to darkness or danger. Explicit adverse mapped tags can be highlighted even where overall confidence remains limited. A route concern score is withheld unless ranking gates pass.

Ranking gates require at least 60% schedule coverage, 60% mapped lighting coverage, 60% confidence index, 80% scored route length, complete sources and recent infrastructure fetches. The UI additionally requires a concern-index difference of at least 10 points and declines an automatic preference if the candidate takes over 50% or 10 minutes longer than the fastest. These thresholds and weights are provisional, unvalidated design choices, not an empirically calibrated safety model.

A mapped-support gap means no scheduled-open business within 100 m and no hospital/police listing within 200 m. Unknown schedules or incomplete listings can cause such a gap. It does not establish an isolated/deserted road. Assistance opening, access and response are unverified. Historical crime, observed footfall, actual connectivity/isolation and verified current lighting remain unavailable. The UI describes those limits and declines unsupported rankings.
