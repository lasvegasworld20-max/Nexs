import React,{useEffect,useRef,useState,useImperativeHandle,forwardRef} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {makeTerrain,makeScenery,makeTower,tokenHeight,districtData,box,mat} from './geometry';
import {money} from '../lib/api';
import {TokenAvatar,Change} from '../components/Shared';

export const CityCanvas=forwardRef(({tokens,onSelect,district,layers,onCamera},ref)=>{
 const mount=useRef(),engine=useRef(),labels=useRef({}),onSelectRef=useRef(onSelect),onCameraRef=useRef(onCamera),[failed,setFailed]=useState(false);
 onSelectRef.current=onSelect;onCameraRef.current=onCamera;
 useImperativeHandle(ref,()=>({
  zoom:direction=>{const e=engine.current;if(e){e.camera.zoom=THREE.MathUtils.clamp(e.camera.zoom*(direction>0?1.2:1/1.2),.5,3.5);e.camera.updateProjectionMatrix();}},
  reset:()=>{const e=engine.current;if(e){e.controls.target.set(0,0,0);e.camera.position.set(115,140,145);e.camera.zoom=1;e.camera.updateProjectionMatrix();}},
  rotate:()=>{const e=engine.current;if(e){const v=e.camera.position.clone().sub(e.controls.target);v.applyAxisAngle(new THREE.Vector3(0,1,0),Math.PI/4);e.camera.position.copy(e.controls.target.clone().add(v));}},
  view:top=>{const e=engine.current;if(e){const target=e.controls.target.clone();e.camera.position.copy(target.add(top?new THREE.Vector3(0,210,1):new THREE.Vector3(115,140,145)));}},
  focus:(x,z)=>{const e=engine.current;if(e){const delta=new THREE.Vector3(x,0,z).sub(e.controls.target);e.camera.position.add(delta);e.controls.target.set(x,0,z);e.camera.zoom=1.45;e.camera.updateProjectionMatrix();}}
 }),[]);
 useEffect(()=>{
  if(!mount.current || !tokens.length)return;
  const host=mount.current;const scene=new THREE.Scene();scene.background=new THREE.Color('#0b1013');scene.fog=new THREE.FogExp2('#0b1013',.0022);
  let renderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});}catch{setFailed(true);return;}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));renderer.setSize(host.clientWidth,host.clientHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.4;
  renderer.domElement.setAttribute('data-testid','city-canvas');renderer.domElement.setAttribute('aria-label','Interactive 3D token city');host.prepend(renderer.domElement);
  const aspect=host.clientWidth/host.clientHeight,frustum=136;
  const camera=new THREE.OrthographicCamera(-frustum*aspect/2,frustum*aspect/2,frustum/2,-frustum/2,.1,1200);camera.position.set(115,140,145);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,0,0);controls.enableDamping=true;controls.dampingFactor=.09;controls.minZoom=.5;controls.maxZoom=3.5;controls.maxPolarAngle=Math.PI*.47;controls.minPolarAngle=.05;controls.mouseButtons={LEFT:THREE.MOUSE.PAN,MIDDLE:THREE.MOUSE.DOLLY,RIGHT:THREE.MOUSE.ROTATE};controls.touches={ONE:THREE.TOUCH.PAN,TWO:THREE.TOUCH.DOLLY_ROTATE};
  scene.add(new THREE.AmbientLight('#b8d4d2',2));const sun=new THREE.DirectionalLight('#e7f7e9',3);sun.position.set(-70,120,30);scene.add(sun);const fill=new THREE.DirectionalLight('#6ca8bf',1.8);fill.position.set(80,30,-80);scene.add(fill);
  const terrain=makeTerrain(scene);makeScenery(scene,tokens);const towers=tokens.map((t,i)=>makeTower(scene,t,i));
  const cars=[];for(let i=0;i<26;i++){const m=box(scene,0,.15,0,.35,.16,.8,new THREE.MeshBasicMaterial({color:i%3===0?'#ffb5a5':'#d5eddc'}));cars.push({m,axis:i%2,road:(i%9-4)*18,offset:i*9.3,speed:2.5+(i%4)});}
  const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let down=null;
  const pointerdown=e=>{down={x:e.clientX,y:e.clientY};};
  const pointerup=e=>{if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6)return;const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(towers.map(t=>t.group),true).find(h=>h.object.userData.tokenId);if(hit)onSelectRef.current(hit.object.userData.tokenId);};
  renderer.domElement.addEventListener('pointerdown',pointerdown);renderer.domElement.addEventListener('pointerup',pointerup);
  const resize=new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;camera.left=-frustum*w/h/2;camera.right=frustum*w/h/2;camera.updateProjectionMatrix();renderer.setSize(w,h);});resize.observe(host);
  engine.current={scene,camera,controls,terrain,towers};let frame=0,raf;const clock=new THREE.Clock();
  const animate=()=>{
   raf=requestAnimationFrame(animate);const elapsed=clock.getElapsedTime();controls.update();terrain.crystal.rotation.y=elapsed*.25;terrain.crystal.position.y=5+Math.sin(elapsed)*.25;
   cars.forEach(({m,axis,road,offset,speed})=>{const pos=(elapsed*speed+offset)%250-125;m.position.set(axis?road+.75:pos,.3,axis?pos:road+.75);m.rotation.y=axis?0:Math.PI/2;});
   towers.forEach(t=>{t.building.scale.y=THREE.MathUtils.lerp(t.building.scale.y,t.targetHeight/t.height,.025);});
   if(frame++%2===0){
    const occupied=[];const sorted=[...towers].sort((a,b)=>(b.token.market_cap||0)-(a.token.market_cap||0));
    sorted.forEach(t=>{const el=labels.current[t.token.id];if(!el)return;const pos=new THREE.Vector3(t.token.x,t.targetHeight+4,t.token.z).project(camera);const x=(pos.x*.5+.5)*host.clientWidth,y=(-pos.y*.5+.5)*host.clientHeight;const w=el.offsetWidth,h=el.offsetHeight;const rect={x:x-w/2,y:y-h,w:w+8,h:h+10};const collision=occupied.some(r=>rect.x<r.x+r.w&&rect.x+rect.w>r.x&&rect.y<r.y+r.h&&rect.y+rect.h>r.y);const outside=pos.z>1||x<w/2||x>host.clientWidth-w/2||y<110||y>host.clientHeight-110;
     el.style.transform=`translate(${x}px,${y}px) translate(-50%, -100%)`;el.style.visibility=collision||outside?'hidden':'visible';if(!collision&&!outside)occupied.push(rect);
    });
   }
   if(frame%60===0)onCameraRef.current?.({x:Math.round(controls.target.x),z:Math.round(controls.target.z),zoom:camera.zoom});
   renderer.render(scene,camera);
  };animate();
  return()=>{cancelAnimationFrame(raf);resize.disconnect();controls.dispose();renderer.domElement.removeEventListener('pointerdown',pointerdown);renderer.domElement.removeEventListener('pointerup',pointerup);scene.traverse(o=>{o.geometry?.dispose();if(o.material){(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>{m.map?.dispose();m.dispose();});}});renderer.dispose();renderer.domElement.remove();engine.current=null;};
 // World geometry persists while prices update independently.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[tokens.map(t=>t.id).join(',')]);
 useEffect(()=>{engine.current?.towers.forEach(t=>{const current=tokens.find(n=>n.id===t.token.id);if(current){t.targetHeight=tokenHeight(current.market_cap);t.token=current;}});},[tokens]);
 useEffect(()=>{if(engine.current)engine.current.terrain.territories.visible=layers.territories;},[layers]);
 return <div className="city-stage" ref={mount} data-testid="city-stage">
 {failed&&<div className="webgl-error" data-testid="webgl-error">3D rendering is unavailable in this browser. Explore tokens using search or the leaderboard.</div>}
 {layers.labels&&tokens.map(t=><button key={t.id} ref={e=>labels.current[t.id]=e} data-testid={`token-building-${t.id}`} className={`building-label ${district!=='all'&&district!==t.district?'dimmed':''}`} onClick={()=>onSelect(t.id)} style={{'--token-color':t.color}}><TokenAvatar token={t} size={27}/><span><strong>{t.symbol}</strong><small>{money(t.market_cap)}</small></span><Change value={t.change_24h} testId={`building-change-${t.id}`}/><span className="label-stem"/></button>)}
 </div>;
});