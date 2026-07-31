import fs from 'node:fs';
import path from 'node:path';
import {compileFullQuestion} from '../src/full-question-compiler.js';

const root = path.resolve(decodeURIComponent(new URL('..', import.meta.url).pathname));
const inputName = 'model-deepseek-v4-flash-full-question-egg-saltwater-v01-network-attempt-2.json';
const input = JSON.parse(fs.readFileSync(path.join(root, 'results', inputName), 'utf8'));
const outputPath = path.join(root, 'results', 'full-question-local-gate-egg-saltwater-v01.json');
let compiled = null;
let error = null;
const semanticViolations = [];
try {
  compiled = compileFullQuestion(input.candidate);
  for (const segment of compiled.segments) {
    const objects = segment.scene.objects;
    const forceUp = objects.find(object => object.kind === 'arrow' && object.style === 'force-up');
    const forceDown = objects.find(object => object.kind === 'arrow' && object.style === 'force-down');
    const declaresGreater = objects.some(object => object.kind === 'meter' && object.label.includes('浮力>重力'));
    if (declaresGreater && (!forceUp || !forceDown || forceUp.height <= forceDown.height)) {
      semanticViolations.push({segment_id: segment.segment_id, code: 'visual.force_magnitude_contradiction', detail: '“浮力>重力”要求浮力箭头长于重力箭头。'});
    }
    if (segment.narration.includes('两者平衡') || segment.narration.includes('浮力与重力平衡')) {
      if (!forceUp || !forceDown || forceUp.height !== forceDown.height) {
        semanticViolations.push({segment_id: segment.segment_id, code: 'visual.force_balance_missing', detail: '平衡结论必须显示等长的浮力与重力箭头。'});
      }
    }
  }
} catch (caught) {
  error = String(caught.message || caught);
}
if (!error && semanticViolations.length) error = 'semantic visual gate failed';
const output = {
  artifact_kind: 'full_question_local_compile_gate',
  source_result: inputName,
  source_kind: 'candidate_output',
  status: compiled && !semanticViolations.length ? 'pass' : 'fail',
  question_id: input.candidate?.question_id || null,
  metrics: compiled ? {
    segment_count: compiled.segments.length,
    total_duration_ms: compiled.total_duration_ms,
    object_count: compiled.segments.reduce((sum, segment) => sum + segment.scene.objects.length, 0),
    timeline_action_count: compiled.segments.reduce((sum, segment) => sum + segment.scene.timeline.length, 0),
  } : null,
  semantic_violations: semanticViolations,
  error,
};
fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(JSON.stringify({output: outputPath, status: output.status, metrics: output.metrics, error}));
if (!compiled || semanticViolations.length) process.exitCode = 1;
