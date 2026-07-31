import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {compileHybridScene, evaluateHybridFrame} from "../src/hybrid-scene-compiler.js";

const fixturePath = path.resolve("fixtures/hybrid-scene-v01.json");
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const compiled = compileHybridScene(fixture);

assert.equal(compiled.connectors[0].from.x, 180);
assert.equal(compiled.connectors[0].to.y, 380);
assert.deepEqual(compiled.function_lines[0].points, [{x: -2, y: -3}, {x: 3, y: 7}]);
assert.deepEqual(compiled.function_lines[1].points, [{x: 0, y: 7}, {x: 5, y: 2}]);
assert.equal(compiled.function_lines[0].label, "line-one");
assert.deepEqual(compiled.derived.first_intersection, {x: 2, y: 5});
assert.match(compiled.motion_canvas_adapter_source, /never eval'd/);
assert.match(compiled.motion_canvas_adapter_source, /functionLine/);
const middle = evaluateHybridFrame(compiled, 0.5);
assert.equal(middle.nodes.find(node => node.id === "flashlight").x, 240);
assert.equal(middle.connectors[0].from.x, 240);
assert.equal(middle.connectors[0].to.y, 380);

assert.throws(() => compileHybridScene({...fixture, connectors: [{id: "bad", from: {node_id: "missing", anchor: "center"}, to: {node_id: "shadow", anchor: "top"}}]}), /unknown node/);
assert.throws(() => compileHybridScene({...fixture, nodes: [{...fixture.nodes[0], kind: "javascript"}, fixture.nodes[1]]}), /not allowed/);

console.log(JSON.stringify({pass: true, connector_count: compiled.connectors.length, function_line_count: compiled.function_lines.length}));
