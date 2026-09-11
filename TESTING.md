# MVP validation — September 8, 2026

## Automated checks

- Four scoring unit tests pass: missing/sentinel handling, denominators, clipping/reversal, and minimum-coverage gates.
- Integrity script verifies all 2,806 unique block groups, complete joins, coordinates in the expected regional bounds, raw rate arithmetic, and every overall score.
- Application TypeScript check passes (`npm run typecheck`).
- Static Vite production build passes.

## Browser checks

Desktop viewport: 1363 × 936. Mobile CSS tested inside a 390 × 844 viewport iframe in the supervised preview (not physical-device testing).

- Bundled dataset loads, polygons render, basemap and city labels render.
- Clicking a Phoenix block group opens the matching Census ID and profile.
- Checked ID `040131141001` against exported GeoJSON: overall 44; income 34 ($76,705); poverty 33 (17.1%); vacancy 72 (2.7%); value 53 ($466,000); affordability 32 (69.2%).
- All six category tabs update the active tab, score heading, score, and category description. The legend title follows the active category and retains the documented score bands.
- Methodology dialog opens and closes with accessible title/description.
- Mobile category controls and map render without horizontal layout overflow; area selection and category switching checked.

## Material limits

The available cloud test browser does not provide WebGL2. Its checks therefore exercise the Leaflet SVG fallback, which uses the same GeoJSON, raw values, and color bands as MapLibre. The MapLibre path compiles and passes TypeScript checks but could not be visually exercised in this browser. No claim of successful hardware-accelerated browser QA is made.

Early preview errors (an import incompatibility and a basemap requiring an API key) were repaired before publication. Final browser console review excludes errors from the browser's own extension and earlier hot-reload sessions.

Publication is verified using the hosting service's terminal deployment status and an HTTP request when available; the cloud browser cannot navigate to live Sites URLs.

# UX update validation — September 9, 2026

The existing checkout, deployment setup, source history, GeoJSON, and scoring pipeline were inspected before editing. Git diff confirms no changes to scoring scripts or public/data.

## Automated

`npm test` passed scoring tests, full data integrity, new point-in-polygon/share-state tests, TypeScript, and production build. Geography checks cover polygon interiors, boundaries, holes, multipolygons, out-of-county points, invalid URL parameters, and the real Phoenix City Hall point mapping to GEOID 040131141001.

## Supervised browser preview

- Desktop 1363 × 936: map loads, polygons and base labels render, selected-area sidebar and category controls leave the central map usable.
- Phone-sized iframe 390 × 844: map fills the viewport below the header; bottom layer/legend control opens and closes; details expand and scroll; comparison fits with vertical scrolling. This tests responsive CSS, not a physical phone.
- Real Photon network requests worked in the browser (including CORS): `200 W Washington St Phoenix`, `Phoenix City Hall`, `Tempe`, `85281`, and `Downtown Phoenix`. Address/landmark/ZIP/neighborhood results were selected and correctly opened containing block groups. City/ZIP point results carry a warning against treating their block-group score as a whole-place average.
- Phoenix City Hall: GEOID 040131141001, overall 44, category/raw values match the audited dataset. ZIP 85281 point selected 040133201001, overall 44.
- Clicked rendered polygons 040133184001 and 040133184002; the details changed to their IDs. Hover readout and strong selected borders were observed. Zoom-in/out buttons worked.
- All six desktop metric tabs updated the active metric and matching legend. Phone Poverty tab worked. Overall remains distinct from the active map metric in details.
- Desktop comparison: Phoenix City Hall versus Tempe's point (040133187002). Missing income/overall displayed as dashes; no invalid difference or zero replacement. Valid poverty difference was -33 score points / +44.7 raw percentage points.
- Phone comparison: 040133201001 versus 040131141001. Both overall 44; income delta -13 score points / -$12,345; all categories and raw values fit the table. Clearing comparison restored normal exploration.
- Share URL `#area=040133187002&metric=overall` restored the selected missing-data area and map focus after refresh.
- A nonsense search returned the helpful “No Valley results found” empty state.
- Console review found no application errors in the inspected final sessions. The browser's own metadata extension logged errors unrelated to this application. One browser action timeout was retried successfully after inspecting current state.

## Remaining verification limits

The cloud browser lacks WebGL2, so visual interaction checks exercise the Leaflet fallback. MapLibre is typechecked/built but still needs a WebGL-capable device smoke test. The Sites browser policy permits internal preview QA and prohibits navigating the cloud browser to the live Sites URL. The public URL HTTP check returned 403 in this environment; therefore live browser interactions and live refresh are not claimed. Hosting publication is verified separately by the hosting service's terminal status.

Search is a best-effort public Photon demo without an SLA. Generalized boundaries and approximate result points remain a limitation near borders. No high-volume service load test was performed.

# Tree Canopy layer validation — September 10, 2026

## Automated

- The reproducible NLCD pipeline produced `public/data/tree-canopy.json` for all 2,806 existing Census block-group GEOIDs.
- 2,806 block groups received valid raw canopy percentages and bounded 0–100 scores; 0 remain unscored.
- Raw values are bounded to 0–100 percent and include both very low-canopy urban areas and greener outlying areas.
- Existing scoring, heat, geography, share-state, TypeScript, and production-build checks pass; the new canopy dataset has its own integrity test.

## Browser checks

- The Tree Canopy selector uses the existing Leaflet SVG rendering path and recolors the same block-group polygons with a dry-to-deep-green scale.
- Tree Canopy legend, raw percentage details, 0–100 score, comparison row, `#metric=tree-canopy` deep link, and refresh restoration are covered by the production browser check.
- Existing Overall, Income, Poverty, Vacancy, Housing value, Affordability, and Summer Heat layers remain selectable and retain visible polygon paths.

## Data limits

The source is the USDA Forest Service/MRLC NLCD Tree Canopy Cover CONUS v2025-6 product at 30 m resolution. Its product-level water and non-tree-agriculture masks are respected, and non-processing/background pixels are excluded from the denominator. The 2025 source year differs from the 2022–2024 Summer Heat composite. Canopy percentage is not canopy height or an individual-tree inventory, and the relationship to heat is descriptive rather than causal.

