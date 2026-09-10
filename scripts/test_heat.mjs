import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../public/data/", import.meta.url);
const heat = JSON.parse(await readFile(new URL("heat.json", root), "utf8"));
const neighborhoods = JSON.parse(await readFile(new URL("neighborhoods.geojson", root), "utf8"));

assert.equal(Object.keys(heat.areas).length, neighborhoods.features.length);
assert.equal(neighborhoods.features.length, 2806);
assert.equal(heat.metadata.source.includes("USGS Landsat Collection 2 Level-2"), true);
assert.deepEqual(heat.metadata.summerMonths, [6, 7, 8]);
assert.equal(heat.metadata.minSceneObservations, 2);
assert.equal(heat.metadata.anchorsFahrenheit.length, 3);
let scored = 0;
for (const feature of neighborhoods.features) {
  const area = heat.areas[feature.properties.id];
  assert.ok(area);
  assert.ok(Number.isInteger(area.heat_observations));
  assert.ok(area.heat_observations >= 0);
  if (area.heat_score == null) continue;
  scored += 1;
  assert.ok(Number.isInteger(area.heat_score));
  assert.ok(area.heat_score >= 0 && area.heat_score <= 100);
  assert.equal(typeof area.heat_temp_f, "number");
  assert.equal(typeof area.heat_temp_c, "number");
  assert.ok(area.heat_observations >= 2);
  assert.ok(area.heat_pixels > 0);
}
assert.equal(scored, heat.metadata.scoredBlockGroups);
assert.equal(heat.metadata.unscoredBlockGroups, 2806 - scored);
console.log(`PASS: ${scored} block groups have bounded Landsat heat scores; ${2806 - scored} remain unscored.`);
