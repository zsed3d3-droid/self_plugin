import 'animate.css';
export function run(el,target,duration,complete){
  const name=target?'animate__fadeIn':'animate__fadeOut';
  el.style.setProperty('--animate-duration',duration+'ms');
  el.classList.remove('animate__animated','animate__fadeIn','animate__fadeOut');
  void el.offsetWidth;
  el.classList.add('animate__animated',name);
  let done=false;
  let timer;
  const finish=event=>{if(event.target!==el||done)return;done=true;clearTimeout(timer);el.removeEventListener('animationend',finish);el.style.opacity=String(target);el.classList.remove('animate__animated',name);complete();};
  el.addEventListener('animationend',finish);
  // Reduced-motion may complete before listeners observe animationend; finite fallback.
  timer=setTimeout(()=>finish({target:el}),duration+60);
  return()=>{done=true;clearTimeout(timer);const current=getComputedStyle(el).opacity;el.removeEventListener('animationend',finish);el.classList.remove('animate__animated',name);el.style.opacity=current;};
}
