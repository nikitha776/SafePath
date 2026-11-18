# SafePath — Indiranagar feasibility check

Checked: 22 October 2026. Live Geoapify requests succeeded using the locally configured key.

## Walking routes

All journeys start at Indiranagar Metro Station. These are provider estimates, not field-verified pedestrian journeys.

| Destination | Routing preference | Distance | Estimated time |
|---|---|---|---|
| Domlur Flyover | balanced | 2.417 km | 34.8 min |
| Domlur Flyover | short | 2.412 km | 35.1 min |
| Chinmaya Mission Hospital | balanced | 0.944 km | 15.1 min |
| Chinmaya Mission Hospital | short | 0.942 km | 15.2 min |

Both routing preferences returned geometry for each destination. Exact geometries differ, but substantial overlap has not been measured. Distinct geometry is not evidence of meaningfully different safety conditions. The current routing documentation does not expose an explicit alternative-count input; use tested balanced/short requests for now and investigate broader candidate generation later.

One initial Halasuru station query resolved broadly to Bengaluru, with confidence 0.25. It was rejected from the final sample and replaced with Chinmaya Mission Hospital (confidence 0.75). Added broad-result and confidence validation. All landmark matches still need visual/manual confirmation before use.

## Business coverage

Area: 1,500-meter radius around the resolved Indiranagar Metro location. Separate searches returned 100 commercial listings, 100 catering listings, and 47 pharmacy listings. This reached the commercial and catering caps, so the area inventory is incomplete.

After exact place-ID deduplication: **245 unique records**, of which **16 (6.5%)** include opening-hour schedules in the search response. Separate mapped records may still describe the same physical establishment.

A proximity-biased details check of the first ten unique records found schedules for two; this is not a representative coverage estimate. It does not establish the number of additional schedules obtainable by querying details for the entire sample.

Examples of returned schedule strings:

- Dhanya: `Mo-Sa 11:00-20:30`
- Adyar Ananda Bhavan: `08:00-23:00`

No schedule parsing or arrival-time availability calculation has been implemented. Schedules do not confirm live business operation.

## Assistance

The combined hospital/police area search returned 42 listings, including specialty facilities and potentially duplicate records. This is not a count of distinct emergency-capable facilities. Hours, entrances, contacts, and assistance capability remain unverified.

## Lighting

The OpenStreetMap Overpass endpoint did not return a usable response during this session; the requests were stopped. Lighting coverage remains unverified. This is a retrieval limitation, not evidence that lighting data is absent.

Follow-up: a direct OSM main-API download later succeeded for a smaller pilot box. It contains mapped lamp locations and some lit tags; see the companion osm-feasibility.md report for counts and limitations. Current lamp operation remains unverified.

## Recommendation

Proceed with a basic map and routing foundation, keeping evidence confidence separate from estimated concern. Sparse business schedules are a material limitation for the core innovation: add a route-corridor coverage audit, pagination, place deduplication, and targeted schedule verification before relying on time-aware rankings. Missing data must remain unknown.

Neon is not configured. No crime data or community reports were assessed, no safety scores were calculated, and no site was deployed in this step.

## Sources and reproducibility

- [Geoapify routing inputs](https://apidocs.geoapify.com/docs/routing/)
- [Geoapify Places](https://apidocs.geoapify.com/docs/places/)
- [Geoapify Place Details](https://apidocs.geoapify.com/docs/place-details/)
- [OpenStreetMap attribution and license](https://www.openstreetmap.org/copyright)

Local audit scripts are documented in the workspace README. Cached responses and the key are excluded from Git. This report contains no credentials.
