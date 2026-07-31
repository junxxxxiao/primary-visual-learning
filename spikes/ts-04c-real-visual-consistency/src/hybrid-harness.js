import fixture from "../fixtures/hybrid-scene-v01.json" with {type: "json"};
import {compileHybridScene, evaluateHybridFrame} from "./hybrid-scene-compiler.js";

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const progress = document.getElementById("progress");
const status = document.getElementById("status");
const adapter = document.getElementById("adapter");
const compiled = compileHybridScene(fixture);
adapter.textContent = compiled.motion_canvas_adapter_source;

function map(point) {
  return {x: 30 + point.x * 0.7, y: 30 + point.y * 0.56};
}

function draw(frame) {
  ctx.fillStyle = "#fffdf7"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  const nodes = new Map(frame.nodes.map(node => [node.id, node]));
  for (const node of frame.nodes) {
    const center = map(node); const width = node.width * 0.7; const height = node.height * 0.56;
    ctx.fillStyle = node.id === "flashlight" ? "#f4c84a" : "#43b581";
    ctx.strokeStyle = "#17212b"; ctx.lineWidth = 2;
    ctx.fillRect(center.x - width / 2, center.y - height / 2, width, height); ctx.strokeRect(center.x - width / 2, center.y - height / 2, width, height);
    ctx.fillStyle = "#17212b"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(node.id, center.x, center.y);
  }
  for (const line of frame.connectors) {
    const start = map(line.from); const end = map(line.to);
    ctx.strokeStyle = "#ff786a"; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke();
    if (line.marker_end === "arrow") {
      const angle = Math.atan2(end.y - start.y, end.x - start.x); const size = 12;
      ctx.fillStyle = "#ff786a"; ctx.beginPath(); ctx.moveTo(end.x, end.y); ctx.lineTo(end.x - size * Math.cos(angle - .5), end.y - size * Math.sin(angle - .5)); ctx.lineTo(end.x - size * Math.cos(angle + .5), end.y - size * Math.sin(angle + .5)); ctx.fill();
    }
  }
  for (const line of frame.function_lines) {
    const start = map({x: line.points[0].x * 70 + 500, y: 520 - line.points[0].y * 35});
    const end = map({x: line.points[1].x * 70 + 500, y: 520 - line.points[1].y * 35});
    ctx.strokeStyle = line.id === "line-one" ? "#4c88ff" : "#7a848e"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke();
  }
}

function render() {
  const frame = evaluateHybridFrame(compiled, Number(progress.value));
  draw(frame);
  status.textContent = `连接线随节点重算；函数线由公式确定。进度 ${(Number(progress.value) * 100).toFixed(0)}%`;
}

progress.addEventListener("input", render);
render();
