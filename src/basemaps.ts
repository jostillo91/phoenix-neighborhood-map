export type Basemap = 'standard' | 'satellite' | 'hybrid';
export function readBasemap(hash:string):Basemap {
 const value=new URLSearchParams(hash.replace(/^#/, '')).get('basemap');
 return value==='satellite'||value==='hybrid'?value:'standard';
}
export const imageryAttribution='USDA, <a href="https://www.usgs.gov/programs/national-geospatial-program/the-national-map">USGS The National Map</a>: Orthoimagery · Census data';
export const imageryTiles={
 satellite:'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',
 hybrid:'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}'
};
