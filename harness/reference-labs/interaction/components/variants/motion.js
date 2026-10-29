import {animate} from 'motion';
export function run(el,target,duration,complete){const playback=animate(el,{opacity:target},{duration:duration/1000,ease:'easeOut',onComplete:complete});return()=>playback.stop();}
