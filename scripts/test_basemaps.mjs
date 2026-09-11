import assert from 'node:assert/strict';
import {readBasemap,imageryTiles} from '../src/basemaps.ts';
assert.equal(readBasemap(''),'standard');
assert.equal(readBasemap('#metric=heat&basemap=satellite'),'satellite');
assert.equal(readBasemap('#area=040131141001&basemap=hybrid&metric=overall'),'hybrid');
assert.equal(readBasemap('#basemap=invalid'),'standard');
assert.ok(Object.values(imageryTiles).every(url=>url.startsWith('https://basemap.nationalmap.gov/')));
console.log('Basemap deep-link parsing and HTTPS source checks passed.');
