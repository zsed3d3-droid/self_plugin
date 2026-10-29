import {gsap} from 'gsap';
export function run(el,target,duration,complete){const tween=gsap.to(el,{opacity:target,duration:duration/1000,ease:'power1.out',overwrite:true,onComplete:complete});return()=>tween.kill();}
