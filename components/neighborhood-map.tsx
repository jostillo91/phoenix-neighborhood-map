"use client";
import {useEffect,useRef,useState,forwardRef,useImperativeHandle} from 'react';
import type {Map as GLMap} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import 'leaflet/dist/leaflet.css';
import {color,paint,metrics} from '@/src/metrics';
import {bounds,type AreaData,type AreaFeature,type Area} from '@/src/geo';
import {LocateFixed,Plus,Minus} from 'lucide-react';
import {Tooltip,TooltipContent,TooltipTrigger,TooltipProvider} from '@/components/ui/tooltip';
export type MapHandle={focus:(f:AreaFeature)=>void;point:(point:[number,number])=>void;reset:()=>void};
const base='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_';
const attribution='Tiles © Esri, HERE, Garmin, <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, GIS community · Census data';
export const NeighborhoodMap=forwardRef<MapHandle,{data:AreaData;metric:string;selected:string|null;compared:string[];onSelect:(p:Area)=>void;onReady:()=>void}>(function NeighborhoodMap({data,metric,selected,compared,onSelect,onReady},ref){
 const container=useRef<HTMLDivElement>(null),gl=useRef<GLMap|null>(null),leaf=useRef<any>(null),layers=useRef<any>(null),marker=useRef<any>(null),library=useRef<any>(null);
 const selectedRef=useRef(selected),comparedRef=useRef(compared),metricRef=useRef(metric),onSelectRef=useRef(onSelect);
 selectedRef.current=selected;comparedRef.current=compared;metricRef.current=metric;onSelectRef.current=onSelect;
 const [ready,setReady]=useState(false),[error,setError]=useState(''),[hover,setHover]=useState<Area|null>(null);
 const layerStyle=(f:AreaFeature)=>{const id=f.properties.id;const chosen=id===selectedRef.current;const a=comparedRef.current[0]===id;const b=comparedRef.current[1]===id;return {fillColor:color(f.properties[metricRef.current],metricRef.current),fillOpacity:.7,color:a?'#5244bb':b?'#087caa':chosen?'#172f44':'#fff',weight:chosen||a||b?4:.65,opacity:chosen||a||b?1:.65};};
 useImperativeHandle(ref,()=>({focus(f){const b=bounds(f);gl.current?.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:65,maxZoom:13,duration:550});leaf.current?.fitBounds([[b[1],b[0]],[b[3],b[2]]],{padding:[50,50],maxZoom:14});},point(p){gl.current?.flyTo({center:p,zoom:13});leaf.current?.setView([p[1],p[0]],14);marker.current?.remove();if(gl.current&&library.current)marker.current=new library.current.Marker({color:'#172f44'}).setLngLat(p).addTo(gl.current);else if(leaf.current&&library.current)marker.current=library.current.circleMarker([p[1],p[0]],{radius:7,color:'#fff',weight:3,fillColor:'#172f44',fillOpacity:1}).addTo(leaf.current);},reset(){gl.current?.flyTo({center:[-112.04,33.47],zoom:9.25});leaf.current?.setView([33.47,-112.04],10);marker.current?.remove();}}),[]);
 useEffect(()=>{let disposed=false;let observer:ResizeObserver|undefined;
  async function init(){try{
   const c=document.createElement('canvas'),context=c.getContext('webgl2'),supported=!!context;context?.getExtension('WEBGL_lose_context')?.loseContext();
   if(!supported){
    const L=await import('leaflet');if(disposed)return;library.current=L;
    const m=L.map(container.current!,{zoomControl:false,minZoom:7,maxZoom:16,preferCanvas:false}).setView([33.47,-112.04],10);leaf.current=m;
    L.tileLayer(base+'Base/MapServer/tile/{z}/{y}/{x}',{attribution,maxZoom:16}).on('tileerror',()=>setError('Background tiles are unavailable. You can still explore Census areas.')).addTo(m);
    layers.current=L.geoJSON(data,{style:f=>f?layerStyle(f as AreaFeature):{},onEachFeature:(f:any,l:any)=>{
     l.on('click',()=>{setHover(null);onSelectRef.current(f.properties);});
     l.on('mouseover',()=>{if(matchMedia('(hover:hover)').matches){setHover(f.properties);l.setStyle({weight:2.5,color:'#172f44',opacity:1});}});
     l.on('mouseout',()=>{setHover(null);l.setStyle(layerStyle(f));});
     // Label rendered geography for assistive technology and inspection.
     l.on('add',()=>{const el=l.getElement();if(el){el.setAttribute('data-geoid',f.properties.id);el.setAttribute('aria-label',`Block group ${f.properties.id}`);}});
    }}).addTo(m);
    m.createPane('cityLabels');m.getPane('cityLabels')!.style.zIndex='450';m.getPane('cityLabels')!.style.pointerEvents='none';
    L.tileLayer(base+'Reference/MapServer/tile/{z}/{y}/{x}',{pane:'cityLabels',maxZoom:16}).addTo(m);
    observer=new ResizeObserver(()=>m.invalidateSize());observer.observe(container.current!);setReady(true);onReady();return;
   }
   const M=await import('maplibre-gl');if(disposed)return;library.current=M;
   const m=new M.Map({container:container.current!,center:[-112.04,33.47],zoom:9.25,minZoom:7,maxZoom:16,attributionControl:{compact:true},style:{version:8,sources:{base:{type:'raster',tiles:[base+'Base/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution}},layers:[{id:'background',type:'background',paint:{'background-color':'#e9eef0'}},{id:'base',type:'raster',source:'base'}]}});gl.current=m;
   m.on('error',(e:any)=>{if(!disposed)setError(e.sourceId==='base'?'Background tiles are unavailable. Census areas remain usable.':'A map layer could not load. Please refresh to retry.');});
   m.on('load',()=>{if(disposed)return;
    m.addSource('labels',{type:'raster',tiles:[base+'Reference/MapServer/tile/{z}/{y}/{x}'],tileSize:256});m.addLayer({id:'labels',type:'raster',source:'labels'});
    m.addSource('areas',{type:'geojson',data,promoteId:'id'});
    m.addLayer({id:'areas-fill',type:'fill',source:'areas',paint:{'fill-color':paint(metricRef.current),'fill-opacity':.7}});
    m.addLayer({id:'areas-lines',type:'line',source:'areas',paint:{'line-color':'#fff','line-width':.65,'line-opacity':.65}});
    m.addLayer({id:'hover',type:'line',source:'areas',paint:{'line-color':'#172f44','line-width':2},filter:['==',['get','id'],'']});
    for(const [id,col,width] of [['selection-halo','#fff',7],['selection','#172f44',4],['compare-a','#5244bb',4],['compare-b','#087caa',4]] as const)m.addLayer({id,type:'line',source:'areas',paint:{'line-color':col,'line-width':width},filter:['==',['get','id'],'']});
    m.on('click','areas-fill',e=>{const p=e.features?.[0]?.properties;if(p){setHover(null);onSelectRef.current(p as Area);}});
    m.on('mousemove','areas-fill',e=>{m.getCanvas().style.cursor='pointer';if(matchMedia('(hover:hover)').matches){const p=e.features?.[0]?.properties;setHover(p as Area);m.setFilter('hover',['==',['get','id'],p?.id||'']);}});
    m.on('mouseleave','areas-fill',()=>{m.getCanvas().style.cursor='';setHover(null);m.setFilter('hover',['==',['get','id'],'']);});
    setReady(true);onReady();
   });observer=new ResizeObserver(()=>m.resize());observer.observe(container.current!);
  }catch(e){if(!disposed)setError('The map could not start. Please refresh to try again.');}}
  init();return()=>{disposed=true;observer?.disconnect();gl.current?.remove();gl.current=null;leaf.current?.remove();leaf.current=null;};
 },[data]);
 useEffect(()=>{if(!ready)return;const m=gl.current;if(m?.getLayer('areas-fill')){m.setPaintProperty('areas-fill','fill-color',paint(metric));for(const id of ['selection','selection-halo'])m.setFilter(id,['==',['get','id'],selected||'']);m.setFilter('compare-a',['==',['get','id'],compared[0]||'']);m.setFilter('compare-b',['==',['get','id'],compared[1]||'']);}if(layers.current){layers.current.setStyle(layerStyle);layers.current.eachLayer((l:any)=>{if(l.feature.properties.id===selected||compared.includes(l.feature.properties.id))l.bringToFront();});}},[ready,metric,selected,compared]);
 return <><div ref={container} className="map-canvas" aria-label="Interactive neighborhood map" data-ready={ready}/>{!ready&&!error&&<div className="map-message" role="status">Drawing 2,806 Census areas…</div>}{error&&<div className="map-error" role="status">{error}<button onClick={()=>setError('')} aria-label="Dismiss map notice">×</button></div>}<TooltipProvider delayDuration={350}><div className="map-tools">{[{label:'Zoom in',icon:<Plus size={19}/>,action:()=>{gl.current?.zoomIn();leaf.current?.zoomIn();}},{label:'Zoom out',icon:<Minus size={19}/>,action:()=>{gl.current?.zoomOut();leaf.current?.zoomOut();}},{label:'Show Phoenix Valley',icon:<LocateFixed size={19}/>,action:()=>{gl.current?.flyTo({center:[-112.04,33.47],zoom:9.25});leaf.current?.setView([33.47,-112.04],10);}}].map(b=><Tooltip key={b.label}><TooltipTrigger asChild><button aria-label={b.label} disabled={!ready} onClick={b.action}>{b.icon}</button></TooltipTrigger><TooltipContent side="left">{b.label}</TooltipContent></Tooltip>)}</div></TooltipProvider>{hover&&<div className="hover-readout"><strong>Tract {hover.tract} · BG {hover.id.slice(-1)}</strong><span>{metrics.find(m=>m.id===metric)?.label}: {hover[metric]??'No data'}{hover[metric]!=null?' / 100':''}</span></div>}</>;
});
