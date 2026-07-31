import fixture from "../fixtures/hybrid-preview-scenes.json" with {type: "json"};
import {compileHybridScene, evaluateHybridFrame} from "./hybrid-scene-compiler.js";

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const title = document.getElementById("title");
const caption = document.getElementById("caption");
const status = document.getElementById("status");
const progress = document.getElementById("progress");
const play = document.getElementById("play");
const time = document.getElementById("time");
const tabs = [...document.querySelectorAll("[data-scene]")];

const scenes = fixture.scenes.map(scene => ({...scene, compiled: compileHybridScene(scene)}));
const DURATION_MS = 5200;
let sceneIndex = 0;
let playing = false;
let elapsed = 0;
let lastFrame = 0;

function mapScene(point) {
  return {x: 70 + point.x * 0.84, y: 54 + point.y * 0.56};
}

function mapMath(point) {
  const plot = {left: 258, top: 144, width: 486, height: 360, xMin: -2.5, xMax: 5.5, yMin: -4, yMax: 8};
  return {
    x: plot.left + ((point.x - plot.xMin) / (plot.xMax - plot.xMin)) * plot.width,
    y: plot.top + ((plot.yMax - point.y) / (plot.yMax - plot.yMin)) * plot.height,
  };
}

function drawArrow(start, end, color) {
  const angle = Math.atan2(end.y - start.y, end.x - start.x);
  const size = 13;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(end.x, end.y);
  ctx.lineTo(end.x - size * Math.cos(angle - 0.48), end.y - size * Math.sin(angle - 0.48));
  ctx.lineTo(end.x - size * Math.cos(angle + 0.48), end.y - size * Math.sin(angle + 0.48));
  ctx.closePath(); ctx.fill();
}

function drawLabel(text, x, y, maxWidth = 120) {
  ctx.fillStyle = "#17212b";
  ctx.font = "700 18px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x, y, maxWidth);
}

function drawRoundedBox(node) {
  const center = mapScene(node);
  const width = node.width * 0.84;
  const height = node.height * 0.56;
  const colors = {
    lamp: "#f4c84a", toy: "#43b581", shadow: "#17212b", wall: "#9aa5af", axis: "#ffffff", point: "#ff786a",
  };
  if (node.style === "wall") {
    ctx.fillStyle = colors.wall;
    ctx.fillRect(center.x - width / 2, center.y - height / 2, width, height);
    drawLabel("墙", center.x, center.y - height / 2 - 18);
    return;
  }
  if (node.style === "point") {
    ctx.fillStyle = colors.point;
    ctx.beginPath(); ctx.arc(center.x, center.y, 8, 0, Math.PI * 2); ctx.fill();
    drawLabel(node.label, center.x + 62, center.y - 18, 140);
    return;
  }
  ctx.fillStyle = colors[node.style] || "#43b581";
  ctx.strokeStyle = "#17212b";
  ctx.lineWidth = 3;
  ctx.beginPath(); ctx.roundRect(center.x - width / 2, center.y - height / 2, width, height, 8); ctx.fill(); ctx.stroke();
  if (node.style === "shadow") ctx.fillStyle = "rgba(23,33,43,.82)";
  drawLabel(node.label, center.x, center.y, width - 8);
}

function drawShadowScene(frame, ratio) {
  for (const connector of frame.connectors) {
    const start = mapScene(connector.from);
    const end = mapScene(connector.to);
    ctx.strokeStyle = "rgba(255,120,106,.88)";
    ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke();
  }
  for (const node of frame.nodes) drawRoundedBox(node);
  const shadow = frame.nodes.find(node => node.id === "shadow");
  const shadowCenter = mapScene(shadow);
  ctx.fillStyle = "#17212b";
  ctx.font = "800 21px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(`影子高度 ${(shadow.height / 10).toFixed(0)} cm`, shadowCenter.x, shadowCenter.y + shadow.height * 0.56 / 2 + 30);
  ctx.fillStyle = "#ff786a";
  ctx.font = "800 22px system-ui, sans-serif";
  ctx.fillText(ratio < 0.5 ? "先看边界光线" : "靠近后，边界张开，影子变大", canvas.width / 2, 52);
}

function drawAxisBox() {
  const origin = mapMath({x: 0, y: 0});
  const xStart = mapMath({x: -2.5, y: 0});
  const xEnd = mapMath({x: 5.5, y: 0});
  const yStart = mapMath({x: 0, y: -4});
  const yEnd = mapMath({x: 0, y: 8});
  ctx.strokeStyle = "rgba(201,208,214,.5)";
  ctx.lineWidth = 1;
  [-2, 2, 4].forEach(x => {
    const top = mapMath({x, y: 8}); const bottom = mapMath({x, y: -4});
    ctx.beginPath(); ctx.moveTo(top.x, top.y); ctx.lineTo(bottom.x, bottom.y); ctx.stroke();
  });
  [-2, 2, 4, 6].forEach(y => {
    const left = mapMath({x: -2.5, y}); const right = mapMath({x: 5.5, y});
    ctx.beginPath(); ctx.moveTo(left.x, left.y); ctx.lineTo(right.x, right.y); ctx.stroke();
  });
  ctx.strokeStyle = "#17212b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(xStart.x, xStart.y);
  ctx.lineTo(xEnd.x, xEnd.y);
  ctx.moveTo(yStart.x, yStart.y);
  ctx.lineTo(yEnd.x, yEnd.y);
  ctx.stroke();
  drawArrow(xStart, xEnd, "#17212b");
  drawArrow(yStart, yEnd, "#17212b");
  ctx.fillStyle = "#17212b";
  ctx.font = "800 18px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("x", xEnd.x + 22, xEnd.y + 4);
  ctx.fillText("y", yEnd.x - 10, yEnd.y - 18);
  ctx.font = "700 14px system-ui, sans-serif";
  [{x: 2, y: 0, text: "2"}, {x: 0, y: 5, text: "5"}].forEach(tick => {
    const p = mapMath(tick);
    ctx.fillText(tick.text, tick.x === 0 ? origin.x - 18 : p.x, tick.x === 0 ? p.y + 5 : origin.y + 20);
  });
  drawLabel("同一坐标系", origin.x + 110, mapMath({x: 0, y: -4}).y + 28, 180);
}

function drawLineScene(frame, ratio) {
  drawAxisBox();
  frame.function_lines.forEach((line, index) => {
    const start = mapMath(line.points[0]);
    const end = mapMath(line.points[1]);
    const visibleEnd = {x: start.x + (end.x - start.x) * ratio, y: start.y + (end.y - start.y) * ratio};
    const color = index === 0 ? "#4c88ff" : "#7a848e";
    ctx.strokeStyle = color;
    ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(visibleEnd.x, visibleEnd.y); ctx.stroke();
    if (ratio > 0.55) drawLabel(line.label, end.x + (index === 0 ? 58 : 68), end.y + (index === 0 ? -20 : 18), 150);
  });
  if (ratio > 0.78 && frame.derived.first_intersection) {
    const p = mapMath(frame.derived.first_intersection);
    ctx.fillStyle = "#ff786a";
    ctx.beginPath(); ctx.arc(p.x, p.y, 9, 0, Math.PI * 2); ctx.fill();
    drawLabel("交点 (2,5)", p.x + 68, p.y - 18, 140);
  }
  ctx.fillStyle = "#ff786a";
  ctx.font = "800 22px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(ratio < 0.55 ? "先用公式画出两条线" : "交点同时满足两个公式", canvas.width / 2, 52);
}

function draw() {
  const scene = scenes[sceneIndex];
  const ratio = Number(progress.value);
  const frame = evaluateHybridFrame(scene.compiled, ratio);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#fffdf7"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (scene.id === "shadow-preview") drawShadowScene(frame, ratio);
  else drawLineScene(frame, ratio);
  title.textContent = scene.title;
  caption.textContent = scene.caption;
  status.textContent = ratio < 1 ? "播放中：每条关系由本地程序重算。" : "本段完成：最终画面保持可检查。";
  time.textContent = `${(ratio * DURATION_MS / 1000).toFixed(1)}s`;
}

function tick(now) {
  if (!playing) return;
  if (!lastFrame) lastFrame = now;
  elapsed += now - lastFrame;
  lastFrame = now;
  if (elapsed >= DURATION_MS) { elapsed = DURATION_MS; playing = false; play.textContent = "重播"; }
  progress.value = String(elapsed / DURATION_MS);
  draw();
  if (playing) requestAnimationFrame(tick);
}

function resetScene(nextIndex) {
  sceneIndex = nextIndex;
  elapsed = 0; lastFrame = 0; playing = false; progress.value = "0"; play.textContent = "播放";
  tabs.forEach((tab, index) => tab.setAttribute("aria-pressed", String(index === sceneIndex)));
  draw();
}

play.addEventListener("click", () => {
  if (elapsed >= DURATION_MS) elapsed = 0;
  playing = !playing;
  play.textContent = playing ? "暂停" : "播放";
  lastFrame = 0;
  if (playing) requestAnimationFrame(tick);
});
progress.addEventListener("input", () => { elapsed = Number(progress.value) * DURATION_MS; lastFrame = 0; draw(); });
tabs.forEach((tab, index) => tab.addEventListener("click", () => resetScene(index)));
draw();
