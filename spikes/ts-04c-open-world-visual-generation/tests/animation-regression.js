import { partialPolylinePoints, renderScene, renderTimelineScene, RUNTIME_STATES } from "../src/scene-renderer.js";

const VIEWPORT = { kind: "phone", width: 390, height: 390 };
const GATE_VIEWPORTS = [{ kind: "phone", width: 390, height: 632 }, { kind: "tablet", width: 1024, height: 728 }];
const PAPER = [255, 253, 247];
const canvas = document.getElementById("canvas");
const status = document.getElementById("status");
const result = document.getElementById("result");

function candidate(node, action) {
  return {
    schema_version: "open-visual-scene/0.3",
    scene: { nodes: [node] },
    timeline: { start_hold_ms: 1000, beats: [{ duration_ms: 2000, narration: "test", actions: [
      { type: "show", target_ids: [node.id], start_ms: 0, duration_ms: 0 }, action
    ] }] },
    static_fallback: { steps: ["test"] }
  };
}

function pixels() {
  return canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data.slice();
}

function foregroundStats(data) {
  let count = 0, xTotal = 0, yTotal = 0;
  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      const offset = (y * canvas.width + x) * 4;
      if (data[offset] === PAPER[0] && data[offset + 1] === PAPER[1] && data[offset + 2] === PAPER[2]) continue;
      count += 1; xTotal += x; yTotal += y;
    }
  }
  return { count, centerX: xTotal / count, centerY: yTotal / count };
}

function equalPixels(a, b) {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function renderAt(scene, elapsed, options) {
  renderTimelineScene(canvas, scene, elapsed, VIEWPORT, options);
  return pixels();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function testPartialPolylineHelper() {
  const source = [{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 3, y: 4 }, { x: 9, y: 4 }];
  const expectedEndpoints = [[0, 0], [3, 0.25], [3, 3.5], [9, 4]];
  [0, 0.25, 0.5, 1].forEach((progress, index) => {
    const partial = partialPolylinePoints(source, progress);
    const end = partial.at(-1);
    assert(Math.abs(end.x - expectedEndpoints[index][0]) < 0.001 && Math.abs(end.y - expectedEndpoints[index][1]) < 0.001, `wrong trace endpoint at ${progress}`);
  });
  assert(JSON.stringify(source) === JSON.stringify([{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 3, y: 4 }, { x: 9, y: 4 }]), "trace mutated source points");
}

function testRotation() {
  const scene = candidate(
    { id: "square", type: "shape", geometry: { x: 500, y: 500, width: 300, height: 300, rotation_deg: 0 } },
    { type: "rotate", target_ids: ["square"], start_ms: 0, duration_ms: 2000, to: { rotation_deg: 90 } }
  );
  const start = renderAt(scene, 1000);
  const middle = renderAt(scene, 2000);
  const end = renderAt(scene, 3000);
  assert(!equalPixels(start, middle), "45-degree rotation matches 0-degree pixels");
  assert(!equalPixels(middle, end), "45-degree rotation matches 90-degree pixels");
  const centers = [start, middle, end].map(frame => foregroundStats(frame));
  assert(Math.max(...centers.map(item => item.centerX)) - Math.min(...centers.map(item => item.centerX)) < 1, "rotation moved the horizontal center");
  assert(Math.max(...centers.map(item => item.centerY)) - Math.min(...centers.map(item => item.centerY)) < 1, "rotation moved the vertical center");
}

function testProgressiveTrace() {
  const scene = candidate(
    { id: "path", type: "line", geometry: { points: [{ x: 100, y: 200 }, { x: 400, y: 200 }, { x: 400, y: 700 }, { x: 900, y: 700 }] } },
    { type: "trace", target_ids: ["path"], start_ms: 0, duration_ms: 2000 }
  );
  const frames = [1000, 1500, 2000, 3000].map(elapsed => renderAt(scene, elapsed));
  const counts = frames.map(frame => foregroundStats(frame).count);
  assert(counts[0] === 0 && counts[0] < counts[1] && counts[1] < counts[2] && counts[2] < counts[3], `trace pixels are not monotonic: ${counts}`);
  renderScene(canvas, scene, "final", VIEWPORT);
  assert(equalPixels(frames[3], pixels()), "completed trace differs from full path");
}

function testReducedMotion() {
  const move = candidate(
    { id: "box", type: "shape", geometry: { x: 300, y: 500, width: 120, height: 80 } },
    { type: "move", target_ids: ["box"], start_ms: 0, duration_ms: 2000, to: { x: 700 } }
  );
  const moveStart = renderAt(move, 1000);
  const moveNormalMiddle = renderAt(move, 2000);
  const moveReducedMiddle = renderAt(move, 2000, { reducedMotion: true });
  assert(!equalPixels(moveStart, moveNormalMiddle), "normal move has no intermediate frame");
  assert(equalPixels(moveStart, moveReducedMiddle), "reduced move did not retain its pre-action frame");
  assert(equalPixels(renderAt(move, 3000), renderAt(move, 3000, { reducedMotion: true })), "reduced move final frame differs");

  const rotate = candidate(
    { id: "rectangle", type: "shape", geometry: { x: 500, y: 500, width: 240, height: 100, rotation_deg: 0 } },
    { type: "rotate", target_ids: ["rectangle"], start_ms: 0, duration_ms: 2000, to: { rotation_deg: 90 } }
  );
  const rotateStart = renderAt(rotate, 1000);
  assert(!equalPixels(rotateStart, renderAt(rotate, 2000)), "normal rotate has no intermediate frame");
  assert(equalPixels(rotateStart, renderAt(rotate, 2000, { reducedMotion: true })), "reduced rotate did not retain its pre-action frame");
  assert(equalPixels(renderAt(rotate, 3000), renderAt(rotate, 3000, { reducedMotion: true })), "reduced rotate final frame differs");

  const trace = candidate(
    { id: "line", type: "line", geometry: { points: [{ x: 100, y: 500 }, { x: 900, y: 500 }] } },
    { type: "trace", target_ids: ["line"], start_ms: 0, duration_ms: 2000 }
  );
  assert(foregroundStats(renderAt(trace, 2000, { reducedMotion: true })).count === 0, "reduced trace appeared before completion");
  assert(equalPixels(renderAt(trace, 3000), renderAt(trace, 3000, { reducedMotion: true })), "reduced trace final frame differs");
}

function testV04SemanticPrimitives() {
  const polygon = candidate(
    { id: "triangle", type: "shape", shape_kind: "polygon", content: "直角三角形", geometry: { x: 500, y: 500, width: 360, height: 280, vertices: [{ x: -1, y: 1 }, { x: -1, y: -1 }, { x: 1, y: 1 }] } },
    { type: "move", target_ids: ["triangle"], start_ms: 0, duration_ms: 2000, to: { x: 600 } }
  );
  polygon.schema_version = "open-visual-scene/0.4";
  const polygonPixels = renderAt(polygon, 1000);
  const polygonStats = foregroundStats(polygonPixels);
  assert(polygonStats.count > 1000, "v0.4 polygon or internal label did not render");

  const arrow = candidate(
    { id: "force", type: "line", marker_end: "arrow", geometry: { points: [{ x: 200, y: 500 }, { x: 800, y: 500 }] } },
    { type: "trace", target_ids: ["force"], start_ms: 0, duration_ms: 2000 }
  );
  arrow.schema_version = "open-visual-scene/0.4";
  const withoutArrow = structuredClone(arrow); delete withoutArrow.scene.nodes[0].marker_end;
  assert(!equalPixels(renderAt(arrow, 3000), renderAt(withoutArrow, 3000)), "v0.4 arrow marker did not change pixels");
}

async function testCandidateStateGate() {
  const fixture = await fetch("../results/candidates-v4-flash-v03-example-guided.json", { cache: "no-store" }).then(response => response.json());
  let runs = 0;
  for (const entry of fixture.entries) {
    for (const viewport of GATE_VIEWPORTS) {
      for (const state of RUNTIME_STATES) {
        const measurement = renderScene(canvas, entry.candidate, state, viewport);
        assert(measurement.elements.length > 0, `${entry.sample_id} ${viewport.kind}.${state} is empty`);
        assert(measurement.logical_violations.length === 0, `${entry.sample_id} ${viewport.kind}.${state} exceeds logical bounds`);
        assert(measurement.elements.every(element => {
          const b = element.bounds;
          return b.x >= 0 && b.y >= 0 && b.x + b.width <= viewport.width && b.y + b.height <= viewport.height;
        }), `${entry.sample_id} ${viewport.kind}.${state} exceeds screen bounds`);
        assert(measurement.pixel_stats.non_background_samples >= 20, `${entry.sample_id} ${viewport.kind}.${state} is blank`);
        assert(measurement.pixel_stats.quantized_color_count >= 2, `${entry.sample_id} ${viewport.kind}.${state} is single color`);
        runs += 1;
      }
    }
  }
  return runs;
}

async function main() {
  testPartialPolylineHelper();
  testRotation();
  testProgressiveTrace();
  testReducedMotion();
  testV04SemanticPrimitives();
  const stateRuns = await testCandidateStateGate();
  window.__TS04C_ANIMATION_RESULT__ = { pass: true, tests: 6, state_runs: stateRuns };
  status.textContent = "pass";
  document.documentElement.dataset.testState = "pass";
}

main().catch(error => {
  window.__TS04C_ANIMATION_RESULT__ = { pass: false, error: String(error.stack || error) };
  status.textContent = "fail";
  document.documentElement.dataset.testState = "fail";
}).finally(() => {
  result.textContent = JSON.stringify(window.__TS04C_ANIMATION_RESULT__, null, 2);
});
