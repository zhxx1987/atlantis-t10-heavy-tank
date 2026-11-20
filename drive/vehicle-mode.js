// One mode boundary for every Gallery vehicle. The renderer stays owned by Gallery.
export function vehicleMode(viewer,onChange){
 const canvas=viewer.canvas,stage=viewer.container,abort=new AbortController();
 let active=false,locked=false,disposed=false;
 const previous=canvas.style.cursor,stageCursor=stage.style.cursor;
 const style=document.createElement('style');style.textContent='html.gallery-vehicle-operating,html.gallery-vehicle-operating *{cursor:none!important}';document.head.append(style);
 function set(value){
  if(disposed||active===value)return;
  active=value;locked=false;
  canvas.dataset.vehicleMode=value?'vehicle':'viewport';
  canvas.style.cursor=value?'none':previous;stage.style.cursor=value?'none':stageCursor;
  stage.classList.toggle('vehicle-operating',value);document.documentElement.classList.toggle('gallery-vehicle-operating',value);viewer.controls.enabled=!value;
  if(value){canvas.tabIndex=0;canvas.focus({preventScroll:true});}
  else if(document.pointerLockElement===canvas)document.exitPointerLock();
  onChange(value);
  if(value){try{Promise.resolve(canvas.requestPointerLock?.()).catch(()=>{});}catch{}}
 }
 const listen=(target,event,callback)=>target.addEventListener(event,callback,{signal:abort.signal});
 listen(window,'keydown',e=>{if(e.code==='Escape'&&active){e.preventDefault();set(false);}});
 listen(window,'blur',()=>set(false));
 listen(document,'visibilitychange',()=>{if(document.hidden)set(false);});
 listen(document,'pointerlockchange',()=>{
  if(document.pointerLockElement===canvas){if(active)locked=true;else document.exitPointerLock();}
  else if(active&&locked)set(false);
 });
 canvas.dataset.vehicleMode='viewport';
 return {set,get active(){return active;},dispose(){set(false);disposed=true;abort.abort();canvas.style.cursor=previous;stage.style.cursor=stageCursor;stage.classList.remove('vehicle-operating');document.documentElement.classList.remove('gallery-vehicle-operating');style.remove();}};
}
