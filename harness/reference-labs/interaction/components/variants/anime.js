import {animate} from 'animejs';
export function run(el,target,duration,complete){const playback=animate(el,{opacity:target,duration,ease:'outQuad',onComplete:complete});return()=>playback.cancel();}
