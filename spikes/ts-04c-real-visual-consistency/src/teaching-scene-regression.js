import result from '../results/hybrid-dsl-local-gate-v01-flash-calibration-round-1.json' with {type:'json'};
import {renderTeachingScene} from './teaching-scene-renderer.js';

const canvas = document.querySelector('#canvas');
const ctx = canvas.getContext('2d', {willReadFrequently: true});
const selected = result.compiled_candidates.filter(item => item.sample_id === 'primary_sound.opening-explanation' || item.sample_id.startsWith('middle_perfect_square.'));
const viewport = innerWidth <= 480 ? 'phone' : 'tablet';
const runs = [];

function foregroundPixels() {
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let count = 0;
  for (let index = 0; index < data.length; index += 16) {
    if (!(data[index] > 250 && data[index + 1] > 248 && data[index + 2] > 240)) count += 1;
  }
  return count;
}

try {
  for (const candidate of selected) {
    for (const reducedMotion of [false, true]) {
      for (const ratio of reducedMotion ? [0.5, 1] : [0, 0.5, 1]) {
        const measurement = renderTeachingScene(ctx, candidate, ratio, {viewport, reducedMotion});
        const foreground = foregroundPixels();
        if (foreground < 20) throw new Error(`${candidate.sample_id} ${ratio} is blank`);
        if (measurement.elements.some(element => {
          const b = element.bounds;
          return b.x < 0 || b.y < 0 || b.x + b.width > canvas.width || b.y + b.height > canvas.height;
        })) throw new Error(`${candidate.sample_id} ${ratio} exceeds canvas`);
        runs.push({sample_id: candidate.sample_id, ratio, reduced_motion: reducedMotion, foreground});
      }
    }
  }
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth) throw new Error('horizontal overflow');
  window.__TS04C_TEACHING_REGRESSION__ = {pass: true, viewport, runs};
  document.documentElement.dataset.testState = 'pass';
} catch (error) {
  window.__TS04C_TEACHING_REGRESSION__ = {pass: false, viewport, error: String(error.stack || error), runs};
  document.documentElement.dataset.testState = 'fail';
}
document.querySelector('#result').textContent = JSON.stringify(window.__TS04C_TEACHING_REGRESSION__, null, 2);
