type Polygon={type:'Polygon';coordinates:number[][][]};
type MultiPolygon={type:'MultiPolygon';coordinates:number[][][][]};
type Geometry=Polygon|MultiPolygon;
type Feature<P>={type:'Feature';properties:P;geometry:Geometry};
type FeatureCollection<F>={type:'FeatureCollection';features:F[]};
export type Area = { id:string; name:string; tract:string; coverage:number; [key:string]:any };
export type AreaFeature = Feature<Area>;
export type AreaData = FeatureCollection<AreaFeature>;
export function bounds(feature:AreaFeature):[number,number,number,number]{
 const points:number[][]=(feature.geometry.type==='Polygon'?feature.geometry.coordinates:feature.geometry.coordinates.flat()).flat();
 let west=Infinity,south=Infinity,east=-Infinity,north=-Infinity;
 for(const [x,y] of points){west=Math.min(west,x);east=Math.max(east,x);south=Math.min(south,y);north=Math.max(north,y);}
 return [west,south,east,north];
}
function ringContains(point:number[],ring:number[][]):boolean{
 const [x,y]=point;let inside=false;
 for(let i=0,j=ring.length-1;i<ring.length;j=i++){
  const [ax,ay]=ring[i],[bx,by]=ring[j];
  const cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax);
  if(Math.abs(cross)<1e-12&&x>=Math.min(ax,bx)&&x<=Math.max(ax,bx)&&y>=Math.min(ay,by)&&y<=Math.max(ay,by))return true;
  if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;
 }
 return inside;
}
export function contains(feature:AreaFeature,point:number[]):boolean{
 const polygons:number[][][][]=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
 return polygons.some(p=>ringContains(point,p[0])&&!p.slice(1).some(h=>ringContains(point,h)));
}
export function createAreaIndex(data:AreaData){
 const entries=data.features.map(f=>({f,b:bounds(f)}));
 return {byId:new Map(data.features.map(f=>[f.properties.id,f])),at:(point:number[])=>entries.find(({f,b})=>point[0]>=b[0]&&point[0]<=b[2]&&point[1]>=b[1]&&point[1]<=b[3]&&contains(f,point))?.f};
}
export function readShare(hash:string){
 const p=new URLSearchParams(hash.replace(/^#/,''));const area=p.get('area');const metric=p.get('metric')||'overall';
 return {area:area&&/^04013\d{7}$/.test(area)?area:null,metric:['overall','income','poverty','vacancy','value','affordability','heat','tree-canopy','transit','violent-crime','property-crime'].includes(metric)?metric:'overall'};
}

