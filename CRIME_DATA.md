# Crime data layer

Reviewed September 13, 2026. Crime is an informational overlay and is excluded from the Economic & Housing Score.

## Citywide comparison

The Citywide view uses Arizona Department of Public Safety Crime Insight 2025 agency totals for Valley police agencies. Violent crime is DPS's victim-based total for murder, aggravated assault, robbery, and sexual assaults. Property crime is burglary + larceny + motor-vehicle theft. Rates are calculated as reported cases divided by the ACS 2020–2024 place population multiplied by 1,000.

These are agency averages, not neighborhood measurements. DPS data can be revised and its monthly submissions were not independently audited here. Sheriff totals are shown only as agency context because they cover broader service areas and cannot be assigned to individual towns.

## Neighborhood detail

Neighborhood detail is available for Phoenix, Mesa, Tempe, Chandler, and Glendale for January–December 2025. Phoenix reports are assigned to Phoenix police grids. Glendale reports use the source's `BEAT_GIS` field and the city's official police-beat polygons. Mesa, Tempe, and Chandler reports are assigned to portions of Census tracts using approximate source coordinates or block locations. Reports are deduplicated by report and category.

Mesa withholds locations for sensitive offenses, so mapped violent crime understates the agency total. Tempe's general-offense feed does not include a separate ASU Police feed. Chandler uses primary-offense reports and excludes unfounded reports. Glendale's public table has no point geometry, so reports without a matching beat cannot be placed. Glendale transitioned to NIBRS on July 1, 2022; the map uses the complete 2025 calendar year. Each city has different definitions and location precision; neighborhood totals must be compared within the same city and source.

Rates use area-weighted ACS population estimates. A rate is withheld when estimated population is below 500, spatial coverage is below 95%, or the ACS population margin of error exceeds 50% of the estimate. This guard does not capture interpolation uncertainty. Missing coverage never means zero crime.

The public `public/data/crime.json` file contains aggregate geometry and audit metadata only. Incident addresses and IDs are not published.

Run `python scripts/add_glendale_crime.py --refresh` after the base crime build to refresh Glendale's 2025 reports, official beat polygons, and area-weighted ACS population estimates. The ignored `.data-cache/glendale-crime/` directory retains the minimum source fields needed for reproducibility.

