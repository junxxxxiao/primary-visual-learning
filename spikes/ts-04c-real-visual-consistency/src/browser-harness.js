import { VisualSandbox } from "../../ts-04a-generated-visual-sandbox/src/sandbox-host.js";

const STATES = [
  ["initial", "initial"],
  ["key-process", "key_process"],
  ["final", "final"],
  ["paused", "paused"],
  ["resumed", "resumed"],
  ["post-interaction", "post_interaction"],
  ["reduced-motion", "reduced_motion"],
  ["static-fallback", "static_fallback"]
];
const VIEWPORTS = {
  phone: { width: 390, height: 632 },
  tablet: { width: 1024, height: 728 }
};
const statusNode = document.getElementById("status");
const resultNode = document.getElementById("result");
const root = document.getElementById("sandbox-root");

function requiredMeasurement(payload) {
  const required = ["layout_mode", "canvas_inner_bounds", "local_safe_regions", "readability_limits", "container_metrics", "elements", "motion_envelopes"];
  return payload?.type === "layout_measurement" && required.every(key => Object.hasOwn(payload, key));
}

async function runCandidate(entry, sample) {
  const sandbox = new VisualSandbox(root);
  const runs = [];
  const profiles = {};
  let codeHash = null;

  for (const [viewport, dimensions] of Object.entries(VIEWPORTS)) {
    const states = [];
    const localSafeRegions = {};
    for (const [stateId, kind] of STATES) {
      const result = await sandbox.run({
        code: entry.candidate.scene_code,
        input: {
          scene_id: entry.candidate.scene_metadata.scene_id,
          width: dimensions.width,
          height: dimensions.height,
          parameters: { state: kind, viewport: { kind: viewport, ...dimensions } }
        }
      });
      codeHash ||= result.code_hash;
      const layoutEvent = result.events.find(event => event.name === "interaction" && requiredMeasurement(event.payload));
      const renderComplete = result.events.some(event => event.name === "render_complete");
      const measurement = layoutEvent?.payload || null;
      if (measurement) {
        const elements = measurement.elements.map(element => {
          const bounds = element.bounds;
          const fontSize = Number(element.font_size) || 0;
          const interactive = Boolean(element.interactive);
          const normalized = {
            element_id: element.element_id,
            bounds,
            font_size: fontSize,
            min_graphic_size: fontSize > 0 ? 0 : (Number(element.min_graphic_size) || Math.min(bounds.width, bounds.height)),
            interactive,
            touch_size: interactive ? (Number(element.touch_size) || Math.min(bounds.width, bounds.height)) : 0,
            local_safe_region: element.local_safe_region ?? null
          };
          if (element.local_safe_region && typeof element.local_safe_region === "object") {
            const regionId = `${stateId}-${element.element_id}`;
            localSafeRegions[regionId] = element.local_safe_region;
            normalized.local_safe_region = regionId;
          } else if (typeof element.local_safe_region === "string") {
            const region = measurement.local_safe_regions?.[element.local_safe_region];
            if (region) localSafeRegions[element.local_safe_region] = region;
            else normalized.local_safe_region = null;
          }
          return normalized;
        });
        states.push({ state_id: stateId, kind, elements, motion_envelopes: measurement.motion_envelopes });
      }
      runs.push({
        viewport,
        state_id: stateId,
        status: result.status,
        reason: result.reason,
        runtime_error_message: result.runtime_error_message,
        duration_ms: result.duration_ms,
        code_hash: result.code_hash,
        render_complete: renderComplete,
        layout_measurement: Boolean(measurement),
        render_stats: result.render_stats,
        timing: result.timing
      });
    }
    if (states.length) profiles[viewport] = {
      layout_mode: viewport === "phone" ? "vertical-responsive" : "tablet-responsive",
      canvas_inner_bounds: { x: 0, y: 0, width: dimensions.width, height: dimensions.height },
      local_safe_regions: localSafeRegions,
      readability_limits: viewport === "phone"
        ? { min_font_size: 16, min_graphic_size: 24, min_touch_size: 44 }
        : { min_font_size: 18, min_graphic_size: 28, min_touch_size: 44 },
      container_metrics: {
        client_width: dimensions.width,
        client_height: dimensions.height,
        scroll_width: dimensions.width,
        scroll_height: dimensions.height,
        overflow: "visible",
        clip: false,
        mask: false
      },
      states
    };
  }
  sandbox.destroyAll();
  return {
    sample_id: entry.sample_id,
    source_input_hash: sample.input_hash,
    runs,
    scene_declaration: {
      schema_version: "visual-scene/1.0",
      scene_id: entry.candidate.scene_metadata.scene_id,
      scene_version: entry.candidate.scene_metadata.scene_version,
      learning_goal: entry.candidate.scene_metadata.learning_goal,
      knowledge_version: sample.input_hash,
      teaching_contract_version: "compact-generated-scene/0.2",
      layout_contract_version: "visual-layout/v1",
      code_hash: codeHash,
      test_version: "ts04c-browser-harness/0.1",
      teaching: { status: "ready", facts: entry.candidate.scene_metadata.teaching.facts },
      viewport_profiles: profiles
    }
  };
}

async function main() {
  const params = new URLSearchParams(location.search);
  const resultFile = params.get("result");
  if (!resultFile || !/^[a-zA-Z0-9._-]+\.json$/.test(resultFile)) throw new Error("invalid result query");
  const [modelResult, fixture] = await Promise.all([
    fetch(`./results/${resultFile}`, { cache: "no-store" }).then(response => response.json()),
    fetch("./fixtures/calibration-inputs.json", { cache: "no-store" }).then(response => response.json())
  ]);
  const samples = Object.fromEntries(fixture.samples.map(sample => [sample.sample_id, sample]));
  const candidates = [];
  for (const entry of modelResult.candidates) {
    statusNode.textContent = `running ${entry.sample_id}`;
    candidates.push(await runCandidate(entry, samples[entry.sample_id]));
  }
  const browserRunLabel = params.get("browserRun") || "browser-round-1";
  const payload = { run_label: modelResult.run_label, browser_run_label: browserRunLabel, model_result_file: resultFile, candidates };
  const response = await fetch("/api/ts04c-browser-result", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }).then(value => value.json());
  window.__TS04C_BROWSER_RESULT__ = response;
  resultNode.textContent = JSON.stringify(response, null, 2);
  statusNode.textContent = response.pass ? "pass" : "fail";
  document.documentElement.dataset.testState = response.pass ? "pass" : "fail";
}

main().catch(error => {
  const failure = { pass: false, runner_error: String(error.stack || error) };
  window.__TS04C_BROWSER_RESULT__ = failure;
  resultNode.textContent = JSON.stringify(failure, null, 2);
  statusNode.textContent = "error";
  document.documentElement.dataset.testState = "error";
});
