import assert from 'node:assert/strict';
import {renderTeachingScene, resolveTeachingScene} from '../src/teaching-scene-renderer.js';

function recordingContext() {
  const context = {
    canvas: {width: 980, height: 680}, globalAlpha: 1,
    save() {}, restore() {}, clearRect() {}, fillRect() {}, strokeRect() {}, beginPath() {},
    roundRect() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {}, fillText() {},
    measureText(text) { return {width: String(text).length * 16}; }
  };
  return context;
}

function render(sampleId, ratio = 1, options = {}) {
  return renderTeachingScene(recordingContext(), {sample_id: sampleId, caption: 'fallback'}, ratio, options);
}

function assertInBounds(measurement) {
  const canvas = {x: 0, y: 0, width: 980, height: 680};
  for (const element of measurement.elements) {
    const bounds = element.bounds;
    assert.ok(bounds.x >= canvas.x && bounds.y >= canvas.y, `${element.id} starts outside canvas`);
    assert.ok(bounds.x + bounds.width <= canvas.width, `${element.id} exceeds canvas width`);
    assert.ok(bounds.y + bounds.height <= canvas.height, `${element.id} exceeds canvas height`);
  }
}

assert.equal(resolveTeachingScene('primary_sound.compare'), 'string-force-comparison');
assert.equal(resolveTeachingScene('primary_sound.opening-explanation'), 'string-observation');
assert.equal(resolveTeachingScene('primary_sound.separate'), 'string-causality');
assert.equal(resolveTeachingScene('primary_sound_pair.pair-reveal'), 'sound-wave-reveal');
assert.equal(resolveTeachingScene('middle_perfect_square.complete'), 'perfect-square-area');
assert.equal(resolveTeachingScene('unknown.sample'), 'unsupported');
for (const sampleId of [
  'primary_sound.opening-explanation', 'primary_sound.compare', 'primary_sound.separate',
  'primary_sound_pair.pair-opening-explanation', 'primary_sound_pair.pair-reveal',
  'middle_perfect_square.complete', 'middle_perfect_square.justify'
]) assert.notEqual(resolveTeachingScene(sampleId), 'unsupported', `${sampleId} must resolve to a concrete component`);

for (const viewport of ['phone', 'tablet']) {
  const sound = render('primary_sound.opening-explanation', 1, {viewport});
  const soundSemantics = new Set(sound.elements.map(element => element.semantic));
  for (const semantic of ['string', 'repeated-vibration']) assert.ok(soundSemantics.has(semantic), `sound opening misses ${semantic}`);
  assertInBounds(sound);

  const comparison = render('primary_sound.compare', 1, {viewport});
  const comparisonSemantics = new Set(comparison.elements.map(element => element.semantic));
  for (const semantic of ['amplitude', 'loudness', 'frequency-pitch']) assert.ok(comparisonSemantics.has(semantic), `sound comparison misses ${semantic}`);
  assertInBounds(comparison);

  const causality = render('primary_sound.separate', 1, {viewport});
  const causalitySemantics = new Set(causality.elements.map(element => element.semantic));
  for (const semantic of ['amplitude-cause', 'frequency-cause', 'causality']) assert.ok(causalitySemantics.has(semantic), `sound separation misses ${semantic}`);
  assertInBounds(causality);

  const pair = render('primary_sound_pair.pair-opening-explanation', 1, {viewport});
  const pairSemantics = new Set(pair.elements.map(element => element.semantic));
  for (const semantic of ['sound-source', 'waveform', 'amplitude', 'frequency-pitch']) assert.ok(pairSemantics.has(semantic), `sound pair misses ${semantic}`);
  assertInBounds(pair);

  const pairReveal = render('primary_sound_pair.pair-reveal', 1, {viewport});
  const pairRevealSemantics = new Set(pairReveal.elements.map(element => element.semantic));
  for (const semantic of ['sound-source', 'amplitude', 'frequency-pitch']) assert.ok(pairRevealSemantics.has(semantic), `sound pair reveal misses ${semantic}`);
  assertInBounds(pairReveal);

  const math = render('middle_perfect_square.complete', 1, {viewport});
  assert.deepEqual(math.elements.filter(element => element.id.startsWith('region-')).map(element => element.id).sort(), ['region-a2', 'region-ax-bottom', 'region-ax-right', 'region-x2']);
  assertInBounds(math);

  const justification = render('middle_perfect_square.justify', 1, {viewport});
  const justificationSemantics = new Set(justification.elements.map(element => element.semantic));
  for (const semantic of ['square-term', 'nonnegative', 'upper-bound-formula', 'maximum']) assert.ok(justificationSemantics.has(semantic), `justification misses ${semantic}`);
  assert.equal(justification.elements.some(element => element.id.startsWith('region-')), false, 'justification must not reuse area decomposition');
  assert.ok(justification.elements.find(element => element.id === 'square-term').bounds.width <= 46, 'square term must shrink to zero proxy at the final state');
  const normalMiddle = render('middle_perfect_square.justify', 0.72, {viewport, reducedMotion: false});
  const reducedMiddle = render('middle_perfect_square.justify', 0.72, {viewport, reducedMotion: true});
  assert.ok(normalMiddle.elements.find(element => element.id === 'square-term').bounds.width < reducedMiddle.elements.find(element => element.id === 'square-term').bounds.width, 'reduced motion must hold the square before the snap boundary');
  assertInBounds(justification);

  for (const sampleId of ['primary_sound.compare', 'primary_sound_pair.pair-reveal', 'middle_perfect_square.justify']) {
    const normal = render(sampleId, 1, {viewport, reducedMotion: false});
    const reduced = render(sampleId, 1, {viewport, reducedMotion: true});
    assert.deepEqual(reduced.elements, normal.elements, `${sampleId} final measurement differs in reduced motion`);
  }
}

const unsupported = render('unknown.sample');
assert.equal(unsupported.supported, false);
assert.equal(unsupported.elements[0].semantic, 'unsupported');
assertInBounds(unsupported);

console.log(JSON.stringify({pass: true, scene_families: 6, viewports: 2}));
