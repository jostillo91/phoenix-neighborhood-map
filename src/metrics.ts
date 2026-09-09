export const metrics = [
 { id: "overall", label: "Overall score", short:"Overall", note: "Five measures. One transparent, experimental indicator", direction:"Higher scores indicate stronger measured conditions." },
 { id: "income", label: "Income", short:"Income", note: "Median annual household income", direction:"Higher income earns a higher score." },
 { id: "poverty", label: "Poverty", short:"Poverty", note: "Share of people below the poverty threshold", direction:"Lower poverty earns a higher score." },
 { id: "vacancy", label: "Vacancy", short:"Vacancy", note: "Share of housing units that are vacant", direction:"Lower vacancy earns a higher score." },
 { id: "value", label: "Housing value", short:"Housing value", note: "Median value of owner-occupied homes", direction:"Higher home values earn a higher score; this is not an affordability measure." },
 { id: "affordability", label: "Affordability", short:"Affordability", note: "Renters spending 30% or more of income on gross rent", direction:"Lower rent burden earns a higher score." },
];
export const bands = [{min:80,label:"Excellent",range:"80–100",color:"#127d72"},{min:65,label:"Good",range:"65–79",color:"#65b5aa"},{min:50,label:"Average",range:"50–64",color:"#efcc76"},{min:35,label:"Below average",range:"35–49",color:"#e99162"},{min:0,label:"Distressed",range:"0–34",color:"#bb5264"}];
export const color = (n:number|null)=>n==null?"#98a1aa":bands.find(b=>n>=b.min)?.color||"#98a1aa";
export const rating = (n:number|null)=>n==null?"Insufficient data":bands.find(b=>n>=b.min)?.label;
export const weights:Record<string,number>={income:25,poverty:25,vacancy:20,value:15,affordability:15};
export const fmt=(n:number|null,key:string)=>n==null?"Not available":(key==='income'||key==='value')?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n):`${n.toFixed(1)}%`;
export const paint=(key:string):any=>['case',['==',['get',key],null],'#98a1aa',['step',['get',key],'#bb5264',35,'#e99162',50,'#efcc76',65,'#65b5aa',80,'#127d72']];
