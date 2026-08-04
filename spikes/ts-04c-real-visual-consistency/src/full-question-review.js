import result from '../results/model-deepseek-v4-flash-full-question-egg-saltwater-v01-network-attempt-2.json' with {type: 'json'};
import {compileFullQuestion, evaluateFullQuestionSegment} from './full-question-compiler.js';
import {renderFullQuestionFrame} from './full-question-renderer.js';

const lesson = compileFullQuestion(result.candidate);
const params = new URLSearchParams(location.search);
const fixedPhone = params.get('viewport') === 'phone';
const viewport = fixedPhone || window.innerWidth <= 520 ? 'phone' : 'tablet';
if (fixedPhone) document.documentElement.dataset.viewport = 'phone';

const canvas = document.querySelector('#canvas');
canvas.width = viewport === 'phone' ? 760 : 1000;
canvas.height = viewport === 'phone' ? 980 : 680;
const ctx = canvas.getContext('2d');
const play = document.querySelector('#play');
const progress = document.querySelector('#progress');
const segmentTitle = document.querySelector('#segment-title');
const caption = document.querySelector('#caption');
const segmentCount = document.querySelector('#segment-count');
const time = document.querySelector('#time');
const answer = document.querySelector('#answer');
const tabs = [...document.querySelectorAll('[data-segment]')];
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

let segmentIndex = 0;
let elapsed = 0;
let playing = false;
let lastFrame = 0;

function activeSegment() { return lesson.segments[segmentIndex]; }

function draw() {
  const segment = activeSegment();
  const frame = evaluateFullQuestionSegment(segment, elapsed, reducedMotion);
  const measurement = renderFullQuestionFrame(ctx, frame, {viewport});
  segmentTitle.textContent = segment.title;
  caption.textContent = segment.narration;
  segmentCount.textContent = `${segmentIndex + 1} / ${lesson.segments.length}`;
  time.textContent = `${(elapsed / 1000).toFixed(1)}s`;
  progress.max = String(segment.duration_ms);
  progress.value = String(elapsed);
  answer.hidden = segmentIndex !== lesson.segments.length - 1 || elapsed < segment.duration_ms * 0.72;
  tabs.forEach((tab, index) => tab.setAttribute('aria-current', index === segmentIndex ? 'step' : 'false'));
  window.__TS04C_FULL_QUESTION_MEASUREMENT__ = {...measurement, segment_id: segment.segment_id, elapsed_ms: elapsed, playback_state: playing ? 'playing' : 'paused'};
}

function stop(label = '播放') {
  playing = false;
  lastFrame = 0;
  play.textContent = label;
  play.setAttribute('aria-label', label);
}

function nextSegment() {
  if (segmentIndex >= lesson.segments.length - 1) {
    stop('重播');
    return false;
  }
  segmentIndex += 1;
  elapsed = 0;
  lastFrame = 0;
  draw();
  return true;
}

function tick(now) {
  if (!playing) return;
  if (!lastFrame) lastFrame = now;
  elapsed += now - lastFrame;
  lastFrame = now;
  if (elapsed >= activeSegment().duration_ms) {
    elapsed = activeSegment().duration_ms;
    draw();
    if (!nextSegment()) return;
  }
  draw();
  requestAnimationFrame(tick);
}

play.addEventListener('click', () => {
  if (playing) { stop('继续'); draw(); return; }
  if (segmentIndex === lesson.segments.length - 1 && elapsed >= activeSegment().duration_ms) {
    segmentIndex = 0; elapsed = 0;
  }
  playing = true;
  lastFrame = 0;
  play.textContent = '暂停';
  play.setAttribute('aria-label', '暂停');
  draw();
  requestAnimationFrame(tick);
});

progress.addEventListener('input', () => { elapsed = Number(progress.value); lastFrame = 0; draw(); });
tabs.forEach((tab, index) => tab.addEventListener('click', () => { segmentIndex = index; elapsed = 0; stop(); draw(); }));
document.querySelector('#question').textContent = lesson.question;
answer.textContent = lesson.answer_summary;
draw();
