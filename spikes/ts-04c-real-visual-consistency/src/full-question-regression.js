import result from '../results/model-deepseek-v4-flash-full-question-egg-saltwater-v01-network-attempt-2.json' with {type: 'json'};
import {compileFullQuestion, evaluateFullQuestionSegment} from './full-question-compiler.js';
import {renderFullQuestionFrame} from './full-question-renderer.js';

const lesson = compileFullQuestion(result.candidate);
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('2d', {willReadFrequently: true});
const runs = [];
const states = [
  {name: 'initial', ratio: 0, reduced: false},
  {name: 'key_process', ratio: 0.5, reduced: false},
  {name: 'final', ratio: 1, reduced: false},
  {name: 'paused', ratio: 0.5, reduced: false},
  {name: 'resumed', ratio: 0.5, reduced: false},
  {name: 'post_interaction', ratio: 1, reduced: false},
  {name: 'reduced_motion', ratio: 1, reduced: true},
];

for (const viewport of ['phone', 'tablet']) {
  canvas.width = viewport === 'phone' ? 760 : 1000;
  canvas.height = viewport === 'phone' ? 980 : 680;
  for (const segment of lesson.segments) {
    for (const state of states) {
      const elapsed = segment.duration_ms * state.ratio;
      const frame = evaluateFullQuestionSegment(segment, elapsed, state.reduced);
      const measurement = renderFullQuestionFrame(ctx, frame, {viewport});
      const violations = [];
      for (const element of measurement.elements) {
        const bounds = element.bounds;
        if (bounds.x < 0 || bounds.y < 0 || bounds.x + bounds.width > canvas.width || bounds.y + bounds.height > canvas.height) {
          violations.push({element_id: element.id, code: 'canvas_bounds_exceeded', bounds});
        }
      }
      const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      let foreground = 0;
      for (let index = 0; index < pixels.length; index += 64) {
        if (pixels[index] < 245 || pixels[index + 1] < 245 || pixels[index + 2] < 240) foreground += 1;
      }
      if (foreground < 100) violations.push({code: 'scene_blank', foreground});
      runs.push({viewport, segment_id: segment.segment_id, state: state.name, result: violations.length ? 'fail' : 'pass', violations, foreground});
    }
  }
}

window.__TS04C_FULL_QUESTION_REGRESSION__ = {
  status: runs.every(run => run.result === 'pass') ? 'pass' : 'fail',
  run_count: runs.length,
  failures: runs.filter(run => run.result === 'fail'),
  runs,
};
document.querySelector('#result').textContent = JSON.stringify(window.__TS04C_FULL_QUESTION_REGRESSION__, null, 2);
