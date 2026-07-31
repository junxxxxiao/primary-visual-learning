import fs from 'node:fs';
import path from 'node:path';
import {compileHybridScene} from '../src/hybrid-scene-compiler.js';

const root = path.resolve(decodeURIComponent(new URL('..', import.meta.url).pathname));
const inputName = 'model-deepseek-v4-flash-official-hybrid-dsl-v01-flash-calibration-round-1.json';
const inputPath = path.join(root, 'results', inputName);
const result = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const checks = [];
const compiledCandidates = [];

for (const candidate of result.candidates) {
  try {
    const compiled = compileHybridScene(candidate.scene);
    checks.push({sample_id: candidate.sample_id, compile_pass: true, node_count: compiled.nodes.length, connector_count: compiled.connectors.length, function_line_count: compiled.function_lines.length});
    compiledCandidates.push({sample_id: candidate.sample_id, title: candidate.title, caption: candidate.caption, scene: compiled});
  } catch (error) {
    checks.push({sample_id: candidate.sample_id, compile_pass: false, error: String(error.message || error)});
  }
}

const output = {
  artifact_kind: 'hybrid_dsl_local_compile_gate',
  source_result: inputName,
  source_kind: 'candidate_output',
  status: checks.every(item => item.compile_pass) ? 'pass' : 'fail',
  metrics: {contract_pass: result.metrics.contract_pass, compile_pass: {numerator: checks.filter(item => item.compile_pass).length, denominator: 10}},
  checks,
  compiled_candidates: compiledCandidates,
};
const outputPath = path.join(root, 'results', 'hybrid-dsl-local-gate-v01-flash-calibration-round-1.json');
fs.writeFileSync(outputPath, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify({output: outputPath, contract_pass: result.metrics.contract_pass, compile_pass: output.metrics.compile_pass}));
