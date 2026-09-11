export const metrics = [
 { id: "overall", label: "Overall score", short:"Overall", note: "Five measures. One transparent, experimental indicator", direction:"Higher scores indicate stronger measured conditions." },
 { id: "income", label: "Income", short:"Income", note: "Median annual household income", direction:"Higher income earns a higher score." },
 { id: "poverty", label: "Poverty", short:"Poverty", note: "Share of people below the poverty threshold", direction:"Lower poverty earns a higher score." },
 { id: "vacancy", label: "Vacancy", short:"Vacancy", note: "Share of housing units that are vacant", direction:"Lower vacancy earns a higher score." },
 { id: "value", label: "Housing value", short:"Housing value", note: "Median value of owner-occupied homes", direction:"Higher home values earn a higher score; this is not an affordability measure." },
 { id: "affordability", label: "Affordability", short:"Affordability", note: "Renters spending 30% or more of income on gross rent", direction:"Lower rent burden earns a higher score." },
 { id: "heat", label: "Summer Heat", short:"Summer Heat", note: "Relative summer daytime land surface temperature", direction:"Higher scores mean hotter relative summer surface exposure; this is not an air-temperature forecast." },
 { id: "tree-canopy", label: "Tree Canopy", short:"Tree Canopy", note: "Mean percentage of each block group's land covered by tree canopy", direction:"Higher scores mean more relative tree canopy coverage." },
];
export const bands = [{min:80,label:"Excellent",range:"80–100",color:"#127d72"},{min:65,label:"Good",range:"65–79",color:"#65b5aa"},{min:50,label:"Average",range:"50–64",color:"#efcc76"},{min:35,label:"Below average",range:"35–49",color:"#e99162"},{min:0,label:"Distressed",range:"0–34",color:"#bb5264"}];
export const heatBands = [{min:80,label:"Very hot",range:"80–100",color:"#b42318"},{min:65,label:"Hot",range:"65–79",color:"#e35d2f"},{min:50,label:"Warm",range:"50–64",color:"#f2b84b"},{min:35,label:"Moderate",range:"35–49",color:"#8bc7b5"},{min:0,label:"Cooler",range:"0–34",color:"#2878a8"}];
export const canopyBands = [{min:80,label:"Very leafy",range:"80–100",color:"#1f5f3a"},{min:65,label:"Leafy",range:"65–79",color:"#3e874b"},{min:50,label:"Moderate",range:"50–64",color:"#79a85c"},{min:35,label:"Sparse",range:"35–49",color:"#b8c686"},{min:0,label:"Very sparse",range:"0–34",color:"#d8cfb0"}];
export const metricBands=(key:string)=>key==='heat'?heatBands:key==='tree-canopy'?canopyBands:bands;
export const color = (n:number|null,key:string='overall')=>n==null?"#98a1aa":metricBands(key).find(b=>n>=b.min)?.color||"#98a1aa";
export const rating = (n:number|null)=>n==null?"Insufficient data":bands.find(b=>n>=b.min)?.label;
export const heatRating = (n:number|null)=>n==null?"Insufficient data":heatBands.find(b=>n>=b.min)?.label;
export const canopyRating = (n:number|null)=>n==null?"Insufficient data":canopyBands.find(b=>n>=b.min)?.label;
export const weights:Record<string,number>={income:25,poverty:25,vacancy:20,value:15,affordability:15};
export const fmt=(n:number|null,key:string)=>n==null?"Not available":key==='heat'?`${n.toFixed(1)}°F`:(key==='income'||key==='value')?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n):`${n.toFixed(1)}%`;
export const paint=(key:string):any=>{const b=metricBands(key);return ['case',['==',['get',key],null],'#98a1aa',['step',['get',key],b[4].color,b[3].min,b[3].color,b[2].min,b[2].color,b[1].min,b[1].color,b[0].min,b[0].color]];};
