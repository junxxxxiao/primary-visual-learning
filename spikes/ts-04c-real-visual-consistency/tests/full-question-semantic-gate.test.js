import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateRequiredVisualRelations} from '../src/full-question-semantic-gate.js';

const result = JSON.parse(fs.readFileSync(
  new URL('../results/model-deepseek-v4-flash-full-question-egg-saltwater-v01-network-attempt-2.json', import.meta.url),
  'utf8',
));
const relationFixture = JSON.parse(fs.readFileSync(
  new URL('../fixtures/full-question-egg-saltwater-v01.visual-relations.json', import.meta.url),
  'utf8',
));

const candidate = structuredClone(result.candidate);
candidate.segments[2].narration = '这段文案不包含任何用于门禁的比较关键词。';
candidate.segments[2].scene.objects.find(object => object.kind === 'meter').label = '受力比较';

const requirements = relationFixture.relations.slice(0, 1);

assert.deepEqual(validateRequiredVisualRelations(candidate, requirements), [{
  relation_id: 'buoyancy-overcomes-weight',
  claim_refs: ['motion-follows-force-balance'],
  segment_id: 'seg3-compare',
  code: 'visual.required_relation_mismatch',
  operator: 'gt',
  left_value: 120,
  right_value: 120,
}]);

const missingOperands = validateRequiredVisualRelations(candidate, relationFixture.relations.slice(1));
assert.deepEqual(missingOperands, [{
  relation_id: 'buoyancy-balances-weight',
  claim_refs: ['motion-follows-force-balance'],
  segment_id: 'seg4-conclusion',
  code: 'visual.required_relation_operand_missing',
  operator: 'eq',
  left_value: null,
  right_value: null,
}]);

const compliant = structuredClone(candidate);
compliant.segments[2].scene.objects.find(object => object.style === 'force-up').height = 160;
compliant.segments[3].scene.objects.push(
  {id: 'balance-up', kind: 'arrow', style: 'force-up', width: 20, height: 100, x: 460, y: 300, label: '浮力'},
  {id: 'balance-down', kind: 'arrow', style: 'force-down', width: 20, height: 100, x: 540, y: 300, label: '重力'},
);
assert.deepEqual(validateRequiredVisualRelations(compliant, relationFixture.relations), []);

console.log(JSON.stringify({pass: true, cases: 3}));
