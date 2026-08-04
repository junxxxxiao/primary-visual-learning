import { renderScene, RUNTIME_STATES } from "./scene-renderer.js";

const VIEWPORTS = { phone: { kind: "phone", width: 390, height: 632 }, tablet: { kind: "tablet", width: 1024, height: 728 } };
const PROFILES = {
  "v02-repaired": {
    fixture: "./results/candidates-v4-flash-v02-repaired.json",
    runLabel: "v4-flash-v02-repaired-browser-round-1",
    schemaVersion: "open-visual-scene/0.2"
  },
  "v03-example-guided": {
    fixture: "./results/candidates-v4-flash-v03-example-guided.json",
    runLabel: "v4-flash-v03-example-guided-browser-round-1",
    schemaVersion: "open-visual-scene/0.3"
  }
};
const status = document.getElementById("status");
const result = document.getElementById("result");
const canvas = document.getElementById("canvas");

async function main() {
  const profileKey = new URLSearchParams(window.location.search).get("profile") || "v02-repaired";
  const profile = PROFILES[profileKey];
  if (!profile) throw new Error(`Unknown browser profile: ${profileKey}`);
  const fixture = await fetch(profile.fixture, { cache: "no-store" }).then(response => response.json());
  if (fixture.schema_version !== profile.schemaVersion || fixture.candidate_count !== 10) throw new Error("Browser fixture does not match the selected profile");
  const candidates = [];
  for (const entry of fixture.entries) {
    status.textContent = `running ${entry.sample_id}`;
    const runs = [];
    for (const viewport of Object.values(VIEWPORTS)) {
      for (const state of RUNTIME_STATES) {
        const started = performance.now();
        const measurement = renderScene(canvas, entry.candidate, state, viewport);
        const screenViolations = measurement.elements.filter(element => {
          const b = element.bounds;
          return b.x < 0 || b.y < 0 || b.x + b.width > viewport.width || b.y + b.height > viewport.height;
        });
        runs.push({
          viewport: viewport.kind, state_id: state, duration_ms: Math.round(performance.now() - started),
          rendered_element_count: measurement.elements.length,
          logical_violations: measurement.logical_violations,
          screen_violations: screenViolations,
          pixel_stats: measurement.pixel_stats,
          canvas: { width: canvas.width, height: canvas.height, scroll_width: canvas.scrollWidth, scroll_height: canvas.scrollHeight }
        });
      }
    }
    candidates.push({ sample_id: entry.sample_id, source_attempt: entry.source_attempt, runs });
  }
  const response = await fetch("/api/ts04c-v3-browser-result", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
    profile_key: profileKey, run_label: profile.runLabel, schema_version: profile.schemaVersion,
    prompt_profile: fixture.prompt_profile || null, candidates
  }) }).then(value => value.json());
  window.__TS04C_V3_RESULT__ = response;
  result.textContent = JSON.stringify(response, null, 2);
  status.textContent = response.pass ? "pass" : "fail";
  document.documentElement.dataset.testState = response.pass ? "pass" : "fail";
}

main().catch(error => {
  const failure = { pass: false, runner_error: String(error.stack || error) };
  window.__TS04C_V3_RESULT__ = failure; result.textContent = JSON.stringify(failure, null, 2);
  status.textContent = "error"; document.documentElement.dataset.testState = "error";
});
