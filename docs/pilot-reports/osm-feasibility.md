# SafePath — direct OpenStreetMap check

Checked 22 October 2026. No Geoapify API or API key was used for these requests.

## Access results

- Private.coffee Overpass: timed out with no response body after 25 seconds.
- overpass-api.de: connection timed out after 8 seconds.
- OSM main map API: succeeded for a small bounding box near Indiranagar Metro.

Overpass remains unavailable from this session. Main-API success establishes that direct OSM access works; the timeout does not establish whether the issue lies with the service or the connection path. A failed data request is not evidence of missing map data.

## Sample and findings

Requested box: longitude 77.636–77.640, latitude 12.976–12.980, approximately 430 × 440 meters. This is smaller than the earlier Geoapify 1.5-kilometer-radius sample. OSM map responses include intersecting ways and referenced objects beyond the box, so returned counts are not a strictly clipped area census.

| Indicator | Result |
|---|---:|
| Business records returned | 98 |
| Business records with opening-hour schedules | 10 |
| Highway ways returned | 103 |
| Highway ways tagged lit=yes | 10 |
| Highway ways without a lit tag | 93 |
| Street-lamp nodes strictly inside the requested box | 109 |
| Hospital/police records returned | 5 |

123 street-lamp nodes were returned overall; 14 were outside the box and excluded from the strictly bounded lamp count. Business and assistance counts are OSM element counts, not verified distinct physical establishments. Highway ways include infrastructure that may not be walkable; these counts do not measure illuminated route length.

Example schedules returned: Tadka Singh `12:00-22:30`; Adyar Ananda Bhavan `08:00-23:00`; Dhanya `Mo-Sa 11:00-20:30`. Schedules have not been parsed or verified in person. Missing hours remain unknown. A street-lamp location or lit=yes tag does not prove that a lamp works or that an entire road is illuminated.

## Implication for SafePath

Direct OSM data offers useful infrastructure evidence, especially mapped lamp locations. Use Geoapify for search/routing and supplement it with a cached OSM extract in Neon/PostGIS. The evidence overlaps: Geoapify and direct OSM must not be treated as independent confirmation of the same record.

We cannot claim that OSM has better opening-hours coverage than Geoapify from these tests because areas, categories, limits, and timestamps differ. Next, compare the same route corridors and match exact OSM element IDs, then deduplicate physical establishments and assess missing data.

Public Overpass availability is unsuitable as a dependency on every route request; evaluate a managed service or periodic extracts for production. The successful small main-API download is a diagnostic fallback, not the proposed city-scale ingestion mechanism.

## Reproducibility

The workspace contains `scripts/check_osm.py` for the larger Overpass check and `scripts/check_osm_sample.py` for the cached small-sample audit. The latter only downloads again when the cached XML is absent or `--refresh` is supplied. Raw data and summaries are stored in ignored `work/pilot-data/` files.

- [Exact successful OSM request](https://api.openstreetmap.org/api/0.6/map?bbox=77.636,12.976,77.640,12.980)
- [Overpass API and public endpoints](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [OpenStreetMap API documentation](https://wiki.openstreetmap.org/wiki/API_v0.6)
- © [OpenStreetMap contributors — attribution and ODbL license](https://www.openstreetmap.org/copyright).
