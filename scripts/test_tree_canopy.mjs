import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../public/data/", import.meta.url);
const canopy = JSON.parse(await readFile(new URL("tree-canopy.json", root), "utf8"));
const neighborhoods = JSON.parse(await readFile(new URL("neighborhoods.geojson", root), "utf8"));

assert.equal(Object.keys(canopy.areas).length, neighborhoods.features.length);
assert.equal(neighborhoods.features.length, 2806);
assert.match(canopy.metadata.source, /USDA Forest Service/);
assert.equal(canopy.metadata.year, 2025);
assert.equal(canopy.metadata.spatialResolution, "30 meters");
assert.equal(canopy.metadata.anchorsPercent.length, 3);
let scored = 0;
let rawValues = [];
for (const feature of neighborhoods.features) {
  const area = canopy.areas[feature.properties.id];
  assert.ok(area);
  assert.ok(Number.isInteger(area.tree_canopy_valid_pixels));
  if (area.tree_canopy_score == null) continue;
  scored += 1;
  assert.ok(Number.isInteger(area.tree_canopy_score));
  assert.ok(area.tree_canopy_score >= 0 && area.tree_canopy_score <= 100);
  assert.equal(typeof area.tree_canopy_pct, "number");
  assert.ok(area.tree_canopy_pct >= 0 && area.tree_canopy_pct <= 100);
  assert.ok(area.tree_canopy_valid_pixels > 0);
  rawValues.push(area.tree_canopy_pct);
}
assert.equal(scored, canopy.metadata.scoredBlockGroups);
assert.equal(canopy.metadata.unscoredBlockGroups, 2806 - scored);
assert.ok(rawValues.some(value => value === 0));
assert.ok(rawValues.some(value => value > 5));
console.log(`PASS: ${scored} block groups have bounded NLCD tree-canopy scores; ${2806 - scored} remain unscored.`);

