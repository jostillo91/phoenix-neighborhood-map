import {readFile} from 'node:fs/promises';

const data=JSON.parse(await readFile(new URL('../public/data/transit.json',import.meta.url)));
const entries=Object.values(data.areas);
if(entries.length!==2806)throw new Error(`Expected 2806 areas, got ${entries.length}`);
if(!data.metadata.source.includes('phoenixopendata.com'))throw new Error('Official feed source is missing');
if(!entries.every(a=>Number.isFinite(a.transit_access_score)&&a.transit_access_score>=0&&a.transit_access_score<=100))throw new Error('Transit scores are not bounded');
if(!entries.some(a=>a.transit_stops>0))throw new Error('No served areas found');
console.log(`PASS: ${entries.length} block groups have bounded scheduled transit access scores.`);

