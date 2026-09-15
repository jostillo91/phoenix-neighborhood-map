export const metrics = [
 { id: "overall", label: "Economic & Housing Score", short:"Economic & housing", note: "Five economic and housing measures; does not measure safety", direction:"Higher scores indicate stronger measured economic and housing conditions, not greater safety." },
 { id: "income", label: "Income", short:"Income", note: "Median annual household income", direction:"Higher income earns a higher score." },
 { id: "poverty", label: "Poverty", short:"Poverty", note: "Share of people below the poverty threshold", direction:"Lower poverty earns a higher score." },
 { id: "vacancy", label: "Vacancy", short:"Vacancy", note: "Share of housing units that are vacant", direction:"Lower vacancy earns a higher score." },
 { id: "value", label: "Housing value", short:"Housing value", note: "Median value of owner-occupied homes", direction:"Higher home values earn a higher score; this is not an affordability measure." },
 { id: "affordability", label: "Affordability", short:"Affordability", note: "Renters spending 30% or more of income on gross rent", direction:"Lower rent burden earns a higher score." },
 { id: "heat", label: "Summer Heat", short:"Summer Heat", note: "Relative summer daytime land surface temperature", direction:"Higher scores mean hotter relative summer surface exposure; this is not an air-temperature forecast." },
 { id: "tree-canopy", label: "Tree Canopy", short:"Tree Canopy", note: "Mean percentage of each block group's land covered by tree canopy", direction:"Higher scores mean more relative tree canopy coverage." },
];
export const bands = [{min:80,label:"Much higher",range:"80–100",color:"#127d72"},{min:65,label:"Higher",range:"65–79",color:"#65b5aa"},{min:50,label:"Typical",range:"50–64",color:"#efcc76"},{min:35,label:"Lower",range:"35–49",color:"#e99162"},{min:0,label:"Much lower",range:"0–34",color:"#bb5264"}];
export const heatBands = [{min:80,label:"Very hot",range:"80–100",color:"#b42318"},{min:65,label:"Hot",range:"65–79",color:"#e35d2f"},{min:50,label:"Warm",range:"50–64",color:"#f2b84b"},{min:35,label:"Moderate",range:"35–49",color:"#8bc7b5"},{min:0,label:"Cooler",range:"0–34",color:"#2878a8"}];
export const canopyBands = [{min:80,label:"Very leafy",range:"80–100",color:"#1f5f3a"},{min:65,label:"Leafy",range:"65–79",color:"#3e874b"},{min:50,label:"Moderate",range:"50–64",color:"#79a85c"},{min:35,label:"Sparse",range:"35–49",color:"#b8c686"},{min:0,label:"Very sparse",range:"0–34",color:"#d8cfb0"}];
export function crimeBands(key:string,measure='rate') {
 const edges=measure==='count'?(key==='violent-crime'?[0,5,20,50,100]:[0,25,100,250,500]):(key==='violent-crime'?[0,2,5,10,20]:[0,10,25,50,100]);
 const colors=['#f4dfac','#edb963','#df8643','#be503c','#842e3b'];
 return edges.map((min,i)=>({min,color:colors[i],label:i===4?`${min}+`:`${min}–<${edges[i+1]}`,range:i===4?`${min}+`:`${min}–<${edges[i+1]}`})).reverse();
}
export const metricBands=(key:string,measure='rate')=>key==='violent-crime'||key==='property-crime'?crimeBands(key,measure):key==='heat'?heatBands:key==='tree-canopy'?canopyBands:bands;
export const color = (n:number|null,key:string='overall',measure='rate')=>n==null?"#98a1aa":metricBands(key,measure).find(b=>n>=b.min)?.color||"#98a1aa";
export const rating = (n:number|null)=>n==null?"Insufficient data":bands.find(b=>n>=b.min)?.label;
export const heatRating = (n:number|null)=>n==null?"Insufficient data":heatBands.find(b=>n>=b.min)?.label;
export const canopyRating = (n:number|null)=>n==null?"Insufficient data":canopyBands.find(b=>n>=b.min)?.label;
export const weights:Record<string,number>={income:25,poverty:25,vacancy:20,value:15,affordability:15};
export const fmt=(n:number|null,key:string)=>n==null?"Not available":key==='heat'?`${n.toFixed(1)}°F`:(key==='income'||key==='value')?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n):`${n.toFixed(1)}%`;
export const paint=(key:string):any=>{const b=metricBands(key);return ['case',['==',['get',key],null],'#98a1aa',['step',['get',key],b[4].color,b[3].min,b[3].color,b[2].min,b[2].color,b[1].min,b[1].color,b[0].min,b[0].color]];};

export const crimeMetrics = [
 {id:'violent-crime',label:'Violent crime',short:'Violent crime',note:'Reported violent offenses',direction:'Explore citywide agency statistics and available neighborhood reports.'},
 {id:'property-crime',label:'Property crime',short:'Property crime',note:'Reported property offenses',direction:'Explore burglary, theft and motor-vehicle theft reports.'},
];
export const isCrime=(key:string)=>crimeMetrics.some(m=>m.id===key);
export const mapMetrics=[...metrics,...crimeMetrics];
export function missingReason(area:Record<string,any>,key:string):string {
 if(isCrime(key))return area.local?'Rate unavailable: the population estimate is too small, incomplete or uncertain. Select reported counts to see available records.':'No statistic is available at this geography. Missing coverage does not mean zero crime.';
 if(area[key]!=null)return '';
 if(key==='heat')return 'Insufficient valid summer scene observations for a heat score.';
 if(key==='tree-canopy')return 'Insufficient valid source pixels for a tree canopy score.';
 const absent=metrics.filter(m=>Object.hasOwn(weights,m.id)&&area[m.id]==null).map(m=>m.label.toLowerCase());
 if(key!=='overall')return `No usable ${metrics.find(m=>m.id===key)?.label.toLowerCase()} estimate. The Census estimate may be unavailable or its denominator may be zero.`;
 return `No economic score. Unavailable measures: ${absent.join(', ')}. This score needs income, poverty, and at least 75% of the intended weight; this area has ${area.coverage}%. Available statistics are shown below.`;
}

