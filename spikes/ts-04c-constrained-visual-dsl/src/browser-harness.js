import { VisualSandbox } from "../../ts-04a-generated-visual-sandbox/src/sandbox-host.js";
import { compileScene } from "./compiler.js";

const STATES = [["initial","initial"],["key-process","key_process"],["final","final"],["paused","paused"],["resumed","resumed"],["post-interaction","post_interaction"],["reduced-motion","reduced_motion"],["static-fallback","static_fallback"]];
const VIEWPORTS = { phone: { width: 390, height: 632 }, tablet: { width: 1024, height: 728 } };
const statusNode = document.getElementById("status");
const resultNode = document.getElementById("result");
const root = document.getElementById("sandbox-root");

async function runSpec(entry) {
  const spec = entry.spec;
  const code = compileScene(spec);
  const sandbox = new VisualSandbox(root);
  const profiles = {};
  const runs = [];
  let codeHash = null;
  for (const [viewport, dimensions] of Object.entries(VIEWPORTS)) {
    const states = [];
    for (const [stateId, kind] of STATES) {
      const result = await sandbox.run({ code, input: { scene_id: spec.scene_id, width: dimensions.width, height: dimensions.height, parameters: { state: kind, viewport: { kind: viewport, ...dimensions } } } });
      codeHash ||= result.code_hash;
      const measurement = result.events.find(event => event.name === "interaction" && event.payload.type === "layout_measurement")?.payload;
      if (measurement) states.push({ state_id: stateId, kind, elements: measurement.elements, motion_envelopes: measurement.motion_envelopes });
      const expectedContentCount = kind === "static_fallback" ? spec.static_fallback.steps.length : (kind === "initial" ? Math.min(1, spec.labels.length) : spec.labels.length);
      const renderedContentCount = measurement?.elements.filter(element => element.element_id.startsWith("dsl-content-")).length || 0;
      runs.push({ viewport, state_id: stateId, status: result.status, reason: result.reason, duration_ms: result.duration_ms, render_complete: result.events.some(event => event.name === "render_complete"), layout_measurement: Boolean(measurement), expected_content_count: expectedContentCount, rendered_content_count: renderedContentCount, render_stats: result.render_stats, runtime_error_message: result.runtime_error_message, timing: result.timing });
    }
    profiles[viewport] = {
      layout_mode: viewport === "phone" ? "vertical-responsive" : "tablet-responsive",
      canvas_inner_bounds: { x: 0, y: 0, width: dimensions.width, height: dimensions.height },
      local_safe_regions: {},
      readability_limits: viewport === "phone" ? { min_font_size: 16, min_graphic_size: 24, min_touch_size: 44 } : { min_font_size: 18, min_graphic_size: 28, min_touch_size: 44 },
      container_metrics: { client_width: dimensions.width, client_height: dimensions.height, scroll_width: dimensions.width, scroll_height: dimensions.height, overflow: "visible", clip: false, mask: false },
      states
    };
  }
  sandbox.destroyAll();
  return {
    sample_id: spec.sample_id,
    runs,
    scene_declaration: {
      schema_version: "visual-scene/1.0", scene_id: spec.scene_id, scene_version: `${spec.scene_id}/dsl-0.1`, learning_goal: spec.title,
      knowledge_version: entry.source_input_hash, teaching_contract_version: "visual-dsl/0.1", layout_contract_version: "visual-layout/v1",
      code_hash: codeHash, test_version: "ts04c-v2-browser/0.1",
      teaching: { status: "ready", facts: spec.facts.map(factId => ({ fact_id: factId, expected: factId, visual: factId, narration: factId })) },
      viewport_profiles: profiles
    }
  };
}

async function main() {
  const params = new URLSearchParams(window.location.search);
  const fixtureName = params.get("fixture") || "specs.json";
  const runLabel = params.get("run_label") || "gold-harness-round-1";
  const fixtureKind = params.get("fixture_kind") || "gold_fixture";
  if (!/^[a-zA-Z0-9._-]+\.json$/.test(fixtureName) || !/^[a-zA-Z0-9._-]+$/.test(runLabel)) throw new Error("invalid harness parameter");
  if (!["gold_fixture", "candidate_output"].includes(fixtureKind)) throw new Error("invalid fixture kind");
  const fixturePath = fixtureKind === "gold_fixture" ? `./fixtures/${fixtureName}` : `./results/${fixtureName}`;
  const fixture = await fetch(fixturePath, { cache: "no-store" }).then(response => {
    if (!response.ok) throw new Error(`fixture load failed: ${response.status}`);
    return response.json();
  });
  const candidates = [];
  for (const entry of fixture.specs) {
    statusNode.textContent = `running ${entry.spec.sample_id}`;
    candidates.push(await runSpec(entry));
  }
  const response = await fetch("/api/ts04c-v2-browser-result", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_label: runLabel, fixture_kind: fixtureKind, candidates }) }).then(value => value.json());
  window.__TS04C_V2_RESULT__ = response;
  resultNode.textContent = JSON.stringify(response, null, 2);
  statusNode.textContent = response.pass ? "pass" : "fail";
  document.documentElement.dataset.testState = response.pass ? "pass" : "fail";
}

main().catch(error => { const failure = { pass: false, runner_error: String(error.stack || error) }; window.__TS04C_V2_RESULT__ = failure; resultNode.textContent = JSON.stringify(failure, null, 2); statusNode.textContent = "error"; document.documentElement.dataset.testState = "error"; });
