# Phoenix Valley Neighborhood Conditions Map

A responsive, interactive map of economic and housing conditions across **all 2,806 Census block groups in Maricopa County, Arizona**. Includes Phoenix, Tempe, Mesa, Scottsdale, Chandler, Gilbert, Glendale, Peoria, Avondale, Goodyear, Tolleson, Surprise, and nearby county communities. Rural county areas are also included. Pinal County and the portions of municipalities extending into it are outside this first release.

**Deployment:** [Open the public map](https://phoenix-neighborhood-map.jostillo.chatgpt.site).

[Download the portable application source](https://phoenix-neighborhood-map.jostillo.chatgpt.site/phoenix-neighborhood-map-source.zip).

**GitHub status (September 9, 2026):** The existing Sites source checkout was updated in place. The connected GitHub account is `jostillo91`, but `jostillo91/phoenix-neighborhood-map` returns 404 and repository searches did not locate this project. GitHub synchronization is blocked until the owner supplies the existing repository URL and grants the connection access. No replacement repository was created and no unrelated repository was modified.

## Interface

The map fills the available desktop workspace, with category controls on the left and selected-area details on the right. On phones it occupies the viewport below the header, with collapsible bottom controls and a separate expandable details sheet. Overall score, every category score, raw statistics, GEOID, missing-data coverage, and methodological caveats remain visible in the appropriate panel.

Search accepts addresses, cities, ZIP codes, neighborhoods, and landmarks. Selecting a result zooms to its point, marks it, and finds the containing polygon using bounding-box filtering plus polygon/hole/multipolygon containment. City and ZIP results represent a point, not a city-wide average. Generalized Census boundaries and approximate geocoding can misclassify locations near edges; this is not parcel-level verification.

Compare Areas saves A then B (click or search), outlines them in purple/blue, and displays all scores, raw values, and B-minus-A differences. A third distinct selection replaces B. Clear comparison returns to normal exploration. Percentage differences use percentage points. Missing values never become zero.

Selecting an area or metric updates `#area=040131141001&metric=poverty`. Copy area link shares that state; refreshing restores the area, metric, and focus. Comparison pairs and raw search queries are not stored in the URL. There is no pathname router.

### Search service and privacy

Explicitly submitted queries go directly to the public [Photon API](https://github.com/komoot/photon) using OpenStreetMap data. No secret key or backend is required. Results are biased/bounded to the Valley. Search uses a 40-query memory cache, a 1.5-second per-browser throttle, a 15-second timeout, and no autocomplete. The public demo permits reasonable use but can throttle traffic and offers no availability guarantee; per-browser throttling is not an aggregate service quota. For broad public traffic, switch to a supported hosted or self-hosted Photon deployment before scaling. `public/search-config.json` controls the endpoint without changing the component. Only explicitly submitted queries are sent; the app has no analytics or persistent address history. Photon/OSM attribution appears with results. [API documentation](https://github.com/komoot/photon/blob/master/docs/api-v1.md).

## Stack and architecture

React 19, TypeScript, Vite 8, MapLibre GL JS, GeoJSON. A dynamically loaded Leaflet renderer supports browsers without WebGL2. Both renderers read the same bundled data and use the same thresholds. The published application is a **static Vite build**: no backend, API key, database, or user login is needed. The Sites preview scaffold uses Vinext for supervised development; `vite.static.config.ts` is the independent static production configuration. Its unused scaffold helpers are not part of the deployed app.

## Data sources and dates

All scoring data: **U.S. Census Bureau, 2020–2024 ACS 5-year estimates**, in 2024 dollars where applicable. Retrieved **September 8, 2026**. These are estimates over a five-year period, not September 2026 conditions.

The script streams the official [2024 table-based Summary File](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/) and retains only Maricopa County block-group rows. This is the Bureau's public bulk-download interface; no API access key is needed.

| Category | Official download | Raw statistic | Weight | Better direction |
|---|---|---|---:|---|
| Income | [B19013](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b19013.dat) | E001: median household income | 25% | Higher |
| Poverty | [C17002](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c17002.dat) | 100 × (E002 + E003) / E001: people below poverty threshold / people with poverty status determined | 25% | Lower |
| Vacancy | [B25002](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25002.dat) | 100 × E003 / E001: vacant / all housing units | 20% | Lower |
| Housing value | [B25077](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25077.dat) | E001: median value of owner-occupied housing | 15% | Higher |
| Affordability | [B25070](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25070.dat) | 100 × (E007+E008+E009+E010) / (E001−E011): renters spending at least 30% of income on gross rent, excluding ratios not computed | 15% | Lower burden |

Variable suffixes above use the Summary File convention (for example `B19013_E001`). The API equivalent is `B19013_001E`. Gross rent includes contract rent plus applicable tenant-paid utility and fuel costs.

Geography: [2024 Census Arizona block groups, 1:500,000 cartographic boundaries](https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_04_bg_500k.zip), filtered to state 04/county 013. Coordinates are rounded to five decimal places. The shipped GeoJSON is about 2.27 MB uncompressed; no giant national source files are committed.

Basemap: Esri [World Light Gray Base](https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer) and [Reference](https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer). Credits: Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community. These live contextual tiles do not affect scores and require internet access. Their content date varies.

`public/data/metadata.json` records exact URLs, retrieval date, national-file SHA-256 hashes, geographic-file hash, weights, formulas, normalization anchors, and coverage. `source-estimates.json` retains county source cells including published margins of error for independent auditing. Protected demographic tables are neither downloaded nor scored.

## Scoring methodology

**This is an experimental composite indicator, not an official judgment of whether neighborhoods or residents are good or bad.** No race, ethnicity, religion, or other protected demographic characteristic is used.

### Normalization

For each metric, using all valid county block groups with equal weight per area:

1. Compute P05, P50 (median), and P95 using linear interpolation between sorted observations.
2. Clip the raw value to [P05, P95].
3. Map [P05, P50] linearly to [0, 50], and [P50, P95] linearly to [50, 100].
4. Reverse poverty, vacancy, and rent burden: `score = 100 − normalized_value`.

Thus 50 means the **typical county area (median)**, not the national average or a precise quality threshold. Percentile clipping limits the influence of extreme values. This is piecewise linear scaling, not percentile rank. If an anchor coincides with the median, an exact median observation receives 50; division by zero is avoided.

For `L=P05`, `M=P50`, `H=P95`, and clipped `x`:

```
N(x) = 50 * (x-L)/(M-L)               when x < M
N(x) = 50                             when x = M
N(x) = 50 + 50 * (x-M)/(H-M)          when x > M
```

### Overall formula

```
overall = 0.25*income + 0.25*poverty + 0.20*vacancy
        + 0.15*housing_value + 0.15*affordability
```

Overall uses unrounded normalized values. Display scores round half-up to whole numbers. Therefore averaging the displayed category numbers can differ by one point from the displayed overall score.

Missing/invalid values, negative Census sentinels, nonfinite values, and zero/invalid denominators become null. **Missing never becomes zero.** The overall score requires both income and poverty plus at least 75% of intended weight. Available weights are divided by their sum. Partial coverage is disclosed on the area card. An area without an overall score can still have individual category scores.

**Coverage:** 2,646 overall scores; 160 areas lack sufficient data. Missing category counts: income 158, poverty 37, vacancy 39, housing value 279, affordability 252.

| Display score | Label | Color |
|---|---|---|
| 80–100 | Excellent | Deep teal |
| 65–79 | Good | Light teal |
| 50–64 | Average | Gold |
| 35–49 | Below average | Orange |
| 0–34 | Distressed | Rose |
| Missing | Insufficient data | Gray |

The same bands apply to every active metric. A high poverty score means **low poverty**, and a high affordability score means **low rent burden**. The labels describe relative indicator scores, not people.

## Limitations

- This is primarily an **economic and housing** indicator. Income, poverty, and home values are correlated, so it still favors economic resources. Vacancy and rent burden add different information but do not eliminate that bias.
- High home values can reduce access to housing. They are not direct evidence of safety, upkeep, resident well-being, or affordability.
- Vacancies include seasonal/recreational units, normal turnover, and construction; vacancy does not prove neglect.
- Rent burden applies only to renters with a computed ratio, not owners, all households, or prospective movers. Small renter samples can create unstable estimates.
- Block-group ACS estimates may have large sampling error. Raw published margins of error are retained in the audit file; composite uncertainty is not modeled. Differences of a few score points should not be treated as meaningful rankings. Income/value margins are also present in GeoJSON.
- Sentinels are treated as missing. Censored or unavailable medians are not invented as exact values.
- The county-wide reference includes rural areas, uninhabited land, group quarters, student areas, and seasonal communities. Land area is not population; large polygons are visually prominent but receive no extra statistical weight.
- Generalized cartographic polygons are unsuitable for individual property decisions. A block group is not necessarily a locally recognized neighborhood.
- No crime data is included: a compatible county-wide incident series was not established. No schools, transit, heat, parks, building conditions, or amenities are scored.
- Basemap providers can change availability or terms. Data and scores are bundled independently.

## Local development

Node 22.13 or newer:

```bash
npm ci
npm run dev:static
```

Open the URL printed by Vite. For production:

```bash
npm run build
```

Serve the `dist/` directory with any static host. The app has no nested routes. For hosting under a repository subpath, set `BASE_PATH=/your-repository-name/` during the build. Data and asset URLs honor that base.

## Regenerate data

Python 3.9+ (tested with Python 3.11):

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell alternative: .venv\Scripts\Activate.ps1
pip install -r scripts/requirements.txt
python scripts/prepare_data.py
python scripts/test_scoring.py
python scripts/verify_data.py
```

Use `python scripts/prepare_data.py --refresh` to re-download official files. `.data-cache/` contains only county table rows and the Arizona boundary ZIP and is ignored by Git. Full national tables are streamed and discarded. Regeneration overwrites the three processed files in `public/data/`; review changes before committing. The year is deliberately pinned to 2024 to prevent accidental cross-vintage joins. Changing years requires reviewing variable definitions, geographic compatibility, counts, and tests.

## Deployment

The app is published as static files through Sites. There is no deployed server code or database.

The current deployment remains at the original Sites URL. Improvements do not create or switch to a new public site.

An optional GitHub Pages workflow remains available if the owner later requests that hosting change. After connecting the **existing** repository and pushing its source, choose GitHub Actions in Settings → Pages, then run the included deployment workflow. It computes the repository base path and publishes `dist/`. Do not create a replacement repository for this update.

## Validation

- Unit checks: clipping, median mapping, reversed directions, invalid data, missing-weight gates.
- Dataset integrity: all 2,806 IDs unique, geographic coverage and bounds, complete table joins, independent arithmetic checks for all raw rates and overall scores.
- TypeScript application checks and static production build.
- Browser QA results are documented in `TESTING.md`.

## Phase 2

See [the complete dataset assessment](PHASE2_DATASETS.md), also [readable on the public site](https://phoenix-neighborhood-map.jostillo.chatgpt.site/phase2-data.html). It covers source, coverage, update frequency, granularity, block-group joins, and limitations for violent/property crime, heat, parks, groceries, transit, and walkability. No candidate changes the current formula. Highest-value next feature: a separately labeled summer surface-heat overlay.
