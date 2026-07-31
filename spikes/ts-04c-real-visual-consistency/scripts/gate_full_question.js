import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {compileFullQuestion} from '../src/full-question-compiler.js';
import {validateRequiredVisualRelations} from '../src/full-question-semantic-gate.js';

const root = path.resolve(decodeURIComponent(new URL('..', import.meta.url).pathname));
const inputName = 'model-deepseek-v4-flash-full-question-egg-saltwater-v01-network-attempt-2.json';
const input = JSON.parse(fs.readFileSync(path.join(root, 'results', inputName), 'utf8'));
const relationFixtureName = 'full-question-egg-saltwater-v01.visual-relations.json';
const relationFixturePath = path.join(root, 'fixtures', relationFixtureName);
const relationFixtureBytes = fs.readFileSync(relationFixturePath);
const relationFixture = JSON.parse(relationFixtureBytes);
const outputPath = path.join(root, 'results', 'full-question-local-gate-egg-saltwater-v01.json');
let compiled = null;
let error = null;
const semanticViolations = [];
try {
  compiled = compileFullQuestion(input.candidate);
  if (relationFixture.question_id !== compiled.question_id) throw new Error('relation fixture question binding mismatch');
  semanticViolations.push(...validateRequiredVisualRelations(compiled, relationFixture.relations));
} catch (caught) {
  error = String(caught.message || caught);
}
if (!error && semanticViolations.length) error = 'semantic visual gate failed';
const output = {
  artifact_kind: 'full_question_local_compile_gate',
  source_result: inputName,
  source_kind: 'candidate_output',
  relation_requirements: {
    fixture: relationFixtureName,
    fixture_kind: relationFixture.fixture_kind,
    evidence_status: relationFixture.evidence_status,
    sha256: createHash('sha256').update(relationFixtureBytes).digest('hex'),
  },
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
