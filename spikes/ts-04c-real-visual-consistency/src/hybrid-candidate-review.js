import result from '../results/hybrid-dsl-local-gate-v01-flash-calibration-round-1.json' with {type:'json'};
import {renderTeachingScene} from './teaching-scene-renderer.js';

const candidates = result.compiled_candidates.map(item => ({...item, compiled:item.scene}));
const canvas = document.querySelector('#canvas');
const ctx = canvas.getContext('2d');
const select = document.querySelector('#scene');
const progress = document.querySelector('#progress');
const play = document.querySelector('#play');
const title = document.querySelector('#title');
const caption = document.querySelector('#caption');
const time = document.querySelector('#time');
const status = document.querySelector('#status');
const reducedMotionQuery = matchMedia('(prefers-reduced-motion: reduce)');
let active = 0, playing = false, elapsed = 0, last = 0;
let reducedMotion = reducedMotionQuery.matches;
const duration = 5200;

for (const [index,item] of candidates.entries()) {
  const option = document.createElement('option');
  option.value = String(index); option.textContent = `${index+1}. ${item.title}`; select.append(option);
}

function viewportKind(){return window.innerWidth<=480?'phone':'tablet';}
function draw(){const item=candidates[active],ratio=Number(progress.value);const measurement=renderTeachingScene(ctx,item,ratio,{reducedMotion,viewport:viewportKind()});title.textContent=item.title;caption.textContent=item.caption;time.textContent=`${(ratio*duration/1000).toFixed(1)}s`;status.textContent=measurement.supported?'校准预览':'暂不支持动态预览';window.__TS04C_TEACHING_MEASUREMENT__=measurement;}
function tick(now){if(!playing)return;if(!last)last=now;elapsed+=now-last;last=now;progress.value=String(Math.min(1,elapsed/duration));draw();if(elapsed>=duration){playing=false;play.textContent='重播';return;}requestAnimationFrame(tick);}
play.addEventListener('click',()=>{if(playing){playing=false;play.textContent='继续';return;}if(Number(progress.value)>=1){elapsed=0;progress.value='0';}else elapsed=Number(progress.value)*duration;playing=true;last=0;play.textContent='暂停';requestAnimationFrame(tick);});
progress.addEventListener('input',()=>{elapsed=Number(progress.value)*duration;draw();});
select.addEventListener('change',()=>{active=Number(select.value);elapsed=0;progress.value='0';playing=false;play.textContent='播放';draw();});
reducedMotionQuery.addEventListener('change',event=>{reducedMotion=event.matches;draw();});
window.addEventListener('resize',draw);
draw();
