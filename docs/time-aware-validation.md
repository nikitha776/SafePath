# Departure-time business analysis — 22 October 2026

Implemented in the web planner for the active Bengaluru pilot. The mobile prototype continues using its compatible raw places endpoint; mobile departure-time controls are not part of this change.

## Validation

- `npm test`: **35 passed**. Includes exact closing boundaries, overnight Friday→Saturday schedules, split hours, midnight rollover, timezone conversion, conditional/missing/invalid schedules, spaced weekday lists, closing during travel, immutable raw POI caching, and disconnected route legs.
- `npm run build`: compiled successfully; TypeScript and static generation passed.
- Live checks through Next.js → FastAPI → Geoapify: both real sample candidate routes analyzed successfully at 10:00 and 23:00 IST.
- Browser checks: entering a departure time, comparing both route summaries, and changing departure without rerouting all worked. Aarthi diagnostics (scheduled 09:00–17:00) displayed expected closed at 23:08 and expected open at 10:08; unknown-hours popups were also verified.

## Live sample

| Route | Departure (IST) | Expected open businesses | Expected closed | Hours unknown | Total businesses |
|---|---|---:|---:|---:|---:|
| Balanced | 10:00 | 5 | 2 | 105 | 112 |
| Balanced | 23:00 | 0 | 7 | 105 | 112 |
| Shortest | 10:00 | 5 | 2 | 104 | 111 |
| Shortest | 23:00 | 0 | 7 | 104 | 111 |

Only about **6%** of the sampled businesses had usable hours. Zero expected open among known schedules does **not** mean no businesses are open: most hours are unknown. Shop results hit the provider limit, so these are partial listings. Duplicate physical establishments may exist under different OSM elements.

## Method and limits

Arrival uses the closest projected point on the route and the proportion of route length traveled, multiplied by the provider's total walking duration. Stops, detours to an entrance and variations in walking pace are excluded. There are no inferred connectors between disconnected geometry legs. The earliest closest encounter is used for repeated locations.

Schedules use pinned `opening-hours-py==2.1.4` in Asia/Kolkata. Spacing between comma-separated weekday selectors is normalized to prevent the parser from treating each day as a separate all-day rule. Holiday/school-holiday, solar and appointment-dependent schedules stay unknown where local context is missing. Published hours may be stale and are not confirmed live availability. Hospital and police schedules are individually labelled but excluded from commercial-activity counts. This does not establish observed street activity, assistance access or route safety.
