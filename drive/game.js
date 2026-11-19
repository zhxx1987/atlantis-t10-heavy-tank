import {loadPyodide} from './runtime/pyodide.mjs';
import {Vector3,Quaternion} from '/AtlantisGallery/atlantis-renderer/vendor/tidewater/src/engine/index.js';

const style=document.createElement('link');
style.rel='stylesheet';style.href='./game.css';document.head.append(style);
const hud=document.createElement('div');
hud.id='drive-ui';
hud.innerHTML='<strong>T-10</strong>　<span id="speed">Loading driving scene…</span><button hidden>Start driving</button><small>W/S drive · A/D steer · Space brake · Mouse look · Left click flash effect · H hatches · Esc release</small>';
document.body.append(hud);
document.body.classList.add('drive');
const label=hud.querySelector('span'),button=hud.querySelector('button');
const text=async url=>{const r=await fetch(url);if(!r.ok)throw Error(url+' '+r.status);return r.text()};
try{
  const [py,core,rig]=await Promise.all([loadPyodide({indexURL:new URL('./runtime/',import.meta.url).href}),text('./drive_core.py'),text('./rig.json').then(JSON.parse)]);
  py.runPython(core);
  const advance=py.runPython(`import json
driver=Driver()
def advance(dt,throttle,steer,brake,dx,dy,click):
    driver.mouse(dx,dy)
    if click: driver.fire()
    remaining=min(.10,dt)
    while remaining>1e-8:
        h=min(1./120,remaining)
        driver.step(h,throttle,steer,brake)
        remaining-=h
    eye,aim=driver.camera((driver.x,driver.y,0))
    return json.dumps([driver.x,driver.y,driver.heading,driver.left,driver.right,*driver.travel,driver.turret,driver.elevation,driver.recoil,driver.flash,driver.shots,eye,aim,driver.hatch])
advance`);
  while(!window.sceneViewer?.loaded){
    const err=document.querySelector('#error')?.textContent;
    if(err)throw Error(err);
    await new Promise(r=>setTimeout(r,60));
  }
  const v=window.sceneViewer.viewer;
  v.controls.enabled=false;
  const root=v.assetRoots.get('T10').root, glow=v.assetRoots.get('Flash').root;
  function live(node){
    if(!node)throw Error('Missing model node');
    if(!node.matrixAutoUpdate)node.matrix.decompose(node.position,node.quaternion,node.scale);
    node.matrixAutoUpdate=true;return node;
  }
  live(root);live(glow);
  const named=name=>live(root.getObjectByName(name));
  const turret=named('Turret'),mantlet=named('Mantlet'),barrel=named('Barrel');
  const covers=['PortHatch','StarboardHatch','DriverCover'].map(named);
  const driverBase=covers[2].position.clone();
  window.t10Snapshot=()=>py.runPython("json.dumps(Driver.restore(json.loads(json.dumps(driver.snapshot()))).snapshot())");
  const wheels=['L','R'].map(side=>['drive_'+side,'idler_'+side,...Array.from({length:7},(_,i)=>'Road_'+side+'_'+i),...Array.from({length:3},(_,i)=>'Return_'+side+'_'+i)].map(named));
  const tracks=['L','R'].map(side=>Array.from({length:rig.count},(_,i)=>named('Track_'+side+'_'+String(i).padStart(3,'0'))));
  const keys=new Set(),audio=new Audio('./effect.wav');
  let dx=0,dy=0,click=false,last=performance.now(),heard=0,active=false,frames=0;
  let audioStarts=0;audio.addEventListener('playing',()=>audioStarts++);
  const length=rig.distance.at(-1);
  const pitch=length/rig.count;
  const axle=new Vector3(0,1,0);
  const pinA=new Vector3(),pinB=new Vector3();
  function samplePin(dist,out){
    dist=((dist%length)+length)%length;
    let lo=0,hi=rig.distance.length-1;
    while(hi-lo>1){const m=(hi+lo)>>1;if(rig.distance[m]<=dist)lo=m;else hi=m;}
    const a=rig.contour[lo],b=rig.contour[lo+1],f=(dist-rig.distance[lo])/(rig.distance[lo+1]-rig.distance[lo]);
    out.set(a[0]+f*(b[0]-a[0]),0,a[1]+f*(b[1]-a[1]));
  }
  function animateTrack(links,travel){
    samplePin(-travel-pitch/2,pinA);
    for(let i=0;i<links.length;i++){
      samplePin((i+.5)*pitch-travel,pinB);
      const link=links[i];
      link.position.x=(pinA.x+pinB.x)/2;
      link.position.z=(pinA.z+pinB.z)/2;
      // Replace the complete bind rotation. Equivalent Euler decompositions of
      // the imported half-turn can also have nonzero X and Z components.
      link.quaternion.setFromAxisAngle(axle,-Math.atan2(pinB.z-pinA.z,pinB.x-pinA.x));
      pinA.copy(pinB);
    }
  }
  function clear(){keys.clear();click=false;dx=dy=0;}
  let edge=0;
  function steerMouse(e){
    if(e.target instanceof Node && hud.contains(e.target)){edge=0;return;}
    dx+=e.movementX;dy+=e.movementY;
    edge=e.clientX<12?-1:e.clientX>window.innerWidth-12?1:0;
  }
  function resetEdge(){edge=0;}
  function engaged(on){
    active=on;clear();edge=0;
    button.textContent=on?'Release driving controls':'Resume driving';
    if(on){
      v.canvas.focus();
      window.addEventListener('mousemove',steerMouse,true);
      document.addEventListener('mouseleave',resetEdge);
    }else{
      window.removeEventListener('mousemove',steerMouse,true);
      document.removeEventListener('mouseleave',resetEdge);
      button.blur();v.canvas.blur();
    }
  }
  button.hidden=false;
  button.onclick=()=>engaged(!active);
  window.addEventListener('blur',()=>engaged(false));
  const inputs=new Set(['KeyW','KeyS','KeyA','KeyD','Space','KeyH']);
  for(const kind of ['keydown','keyup'])window.addEventListener(kind,e=>{
    if(active&&e.code==='Tab'){e.preventDefault();return;}
    if(active&&e.code==='Escape'){engaged(false);return;}
    if(!active||!inputs.has(e.code))return;
    e.preventDefault();e.stopImmediatePropagation();
    if(kind==='keydown'&&e.repeat&&!keys.has(e.code))return;
    if(e.code==='KeyH'&&kind==='keydown'&&!e.repeat)py.runPython('driver.hatches_open = not driver.hatches_open');
    if(kind==='keydown')keys.add(e.code);else keys.delete(e.code);
  },true);
  v.canvas.addEventListener('mousedown',e=>{if(active&&e.button===0){click=true;e.preventDefault();}},true);
  const localTip=new Vector3(),q=new Quaternion();
  function drawable(node){
    let found=false;node.traverse(child=>{if(child.isMesh)found=true;});return found;
  }
  if(!drawable(tracks[0][0])||!drawable(barrel))throw Error('Moving assembly has no renderable mesh');
  v.beforeRender=()=>{
    const now=performance.now(),dt=(now-last)/1000;last=now;
    const s=JSON.parse(advance(dt,Number(keys.has('KeyW'))-Number(keys.has('KeyS')),Number(keys.has('KeyA'))-Number(keys.has('KeyD')),keys.has('Space')||!active,dx+edge*360*Math.min(dt,.1),dy,click));
    dx=dy=0;click=false;
    const [x,y,yaw,left,right,l,r,t,p,recoil,flash,shots,eye,aim,hatch]=s;
    root.position.set(x,0,-y);root.rotation.y=yaw;
    turret.rotation.z=t;mantlet.rotation.y=-p;barrel.position.x=-recoil;
    for(const cover of covers)cover.rotation.y=-hatch;
    covers[2].position.copy(driverBase);covers[2].position.x+=.27*(Math.cos(hatch)-1);covers[2].position.z+=.27*Math.sin(hatch);
    for(let side=0;side<2;side++){
      const travel=side?r:l;
      wheels[side].forEach((n,i)=>{n.rotation.y=travel/(i===0?.356:i===1?.369:i<9?.405:.153);});
      animateTrack(tracks[side],travel);
    }
    root.updateMatrixWorld(true);
    const wasVisible=glow.visible;
    glow.visible=flash>0;glow.position.copy(barrel.localToWorld(localTip.set(4.48,0,0)));
    glow.quaternion.copy(barrel.getWorldQuaternion(q));glow.scale.setScalar(.5+flash);
    glow.updateMatrixWorld(true);
    if(wasVisible!==glow.visible)v.invalidateVisibility();
    if(left||right||flash||dx||dy||active)v.invalidateObjectTransforms([root,glow]);
    if(shots>heard){heard=shots;audio.currentTime=0;audio.play().catch(()=>{});}
    v.camera.position.set(eye[0],eye[2],-eye[1]);v.controls.target.set(aim[0],aim[2],-aim[1]);
    v.controls.changed();
    label.textContent=((left+right)*1.8).toFixed(1)+' km/h';
    window.t10Telemetry={x,y,yaw,left,right,turret:t,elevation:p,recoil,flash,shots,active,hatch,audioStarts,frames:++frames,track:l,camera:'third-person',tip:glow.position.toArray()};
  };
}catch(err){label.textContent='Loading failed · '+(err.message||err);console.error(err);}

