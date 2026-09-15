import type {AreaData, Area} from './geo';

export type CrimeCategory = 'violent-crime' | 'property-crime';
export type CrimeMeasure = 'rate' | 'count';
export type CrimeSource = {
 city: string; status: string; geography: string; url: string; period: string;
 note: string; counts?: Record<string,number>; mapped?: Record<string,number>;
 months?: Record<string,number>; population?: number;
};
export type CrimeData = {
 geography: AreaData;
 cityGeography: AreaData;
 metadata: {retrieved:string; period:string; populationSource:string; populationMethod:string;
 sources:CrimeSource[]; audit:Record<string,unknown>; citywideDefinition:string;
 regionalAgencies:any[]; cautions:string[]};
};
export function crimeValue(area:Area, category:CrimeCategory, measure:CrimeMeasure):number|null {
 return area[`${category}_${measure}`] ?? null;
}
export function crimeDisplayData(data:CrimeData, category:CrimeCategory, measure:CrimeMeasure, city:string):AreaData {
 return {...data.geography,features:data.geography.features.map(f=>({...f,properties:{...f.properties,
  [category]:city==='all'||f.properties.city===city?crimeValue(f.properties,category,measure):null,
 }}))};
}
export const crimeNumber=(n:number|null|undefined, decimals=0)=>n==null?'Unavailable':n.toLocaleString('en-US',{maximumFractionDigits:decimals,minimumFractionDigits:decimals});

