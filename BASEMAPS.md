# Basemaps

Standard preserves Esri World Light Gray Base and Reference, with its existing Esri/HERE/Garmin/OpenStreetMap/GIS community attribution. Satellite uses [USGSImageryOnly](https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer). Hybrid uses [USGSImageryTopo](https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer), which combines imagery with roads and place names in a single tile service. Both USGS services are HTTPS and require no API key. Attribution credits USDA and USGS The National Map; Hybrid also credits US Topo roads and place names.

USGS documents the CONUS orthoimagery as public domain, largely USDA NAIP. These are reference images, not live satellite observations: the service describes 2017–2021 CONUS imagery and a June 2024 imagery refresh. Dates/resolution vary geographically. Basemap images are unrelated to the dates or values of the thematic datasets. Map zoom remains capped at 16, matching the documented service scale.

The existing Leaflet SVG layer remains intact. Standard retains 0.7 fill opacity; imagery modes use 0.5. Hybrid's embedded labels stay below the Census polygons. Standard's existing transparent city labels retain their separate pane. Only the active basemap's tile layers remain attached. Selection/comparison borders retain their existing styles.

The touch-friendly native Basemap selector is below the zoom controls. Its state is stored as `basemap=standard|satellite|hybrid` in the existing hash and survives metric/area changes and refresh. Invalid or absent values default to Standard. Basemap changes do not recreate the map or reset search, selection, comparisons or camera position.

Checks: existing scoring/data/geography/heat/canopy tests, TypeScript and production build; `node --experimental-strip-types scripts/test_basemaps.mjs` checks URL parsing. Browser QA checks actual loaded tiles, visible overlays, and active layer cleanup across all three basemaps. Third-party availability is outside the application's control; tile errors show a notice while Census overlays remain usable.
