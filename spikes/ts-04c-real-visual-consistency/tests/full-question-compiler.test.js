import assert from 'node:assert/strict';
import fs from 'node:fs';
import {compileFullQuestion, evaluateFullQuestionSegment} from '../src/full-question-compiler.js';

const result = JSON.parse(fs.readFileSync(new URL('../results/model-deepseek-v4-flash-full-question-egg-saltwater-v01-network-attempt-2.json', import.meta.url), 'utf8'));
const compiled = compileFullQuestion(result.candidate);
assert.equal(compiled.segments.length, 4);
assert.equal(compiled.total_duration_ms, 32000);

for (const segment of compiled.segments) {
  const initial = evaluateFullQuestionSegment(segment, 0);
  const beforeNarration = evaluateFullQuestionSegment(segment, 999);
  const final = evaluateFullQuestionSegment(segment, segment.duration_ms);
  assert.deepEqual(initial.objects, beforeNarration.objects, `${segment.segment_id} must hold its start frame for 1s`);
  assert.equal(final.objects.length, segment.scene.objects.length);
}

const broken = structuredClone(result.candidate);
broken.segments[0].scene.objects[0].x = 20;
assert.throws(() => compileFullQuestion(broken), /source bounds exceed safe region/);
const movingOutside = structuredClone(result.candidate);
movingOutside.segments[0].scene.timeline.push({target_id: 'egg1', property: 'x', from: 500, to: 920, start_ms: 1000, end_ms: 2000});
assert.throws(() => compileFullQuestion(movingOutside), /motion envelope exceeds safe region/);
console.log(JSON.stringify({pass: true, segments: compiled.segments.length, total_duration_ms: compiled.total_duration_ms}));
