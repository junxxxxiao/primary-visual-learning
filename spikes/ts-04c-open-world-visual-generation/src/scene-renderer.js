const COLORS = {
  ink: "#17212b", paper: "#fffdf7", "science-green": "#43b581", "math-blue": "#4c88ff",
  "signal-coral": "#ff786a", "focus-yellow": "#f4c84a", muted: "#7a848e"
};

const STATE_BEAT = {
  initial: 0, key_process: 0.5, final: 1, paused: 0.5, resumed: 0.5,
  post_interaction: 1, reduced_motion: 1
};

function cloneNodes(candidate) {
  return new Map(candidate.scene.nodes.map(node => [node.id, {
    ...node, visible: false, emphasized: false, content: node.content || "",
    geometry: { ...(node.geometry || {}) }
  }]));
}

function applyAction(nodes, action) {
  for (const id of action.target_ids || []) {
    const node = nodes.get(id);
    if (!node) continue;
    if (["show", "trace", "compare"].includes(action.type)) node.visible = true;
    if (action.type === "trace") node.trace_progress = 1;
    if (action.type === "hide") node.visible = false;
    if (action.type === "emphasize") { node.visible = true; node.emphasized = true; }
    if (["move", "scale", "rotate", "morph"].includes(action.type)) {
      node.visible = true;
      Object.assign(node.geometry, action.to || {});
    }
    if (action.type === "update_value") { node.visible = true; node.content = String(action.value ?? node.content); }
  }
}

function geometryValue(node, key) {
  const g = node.geometry || {};
  if (key === "x" || key === "y") return g[key] ?? 500;
  if (key === "width") return g.width || (g.radius ? g.radius * 2 : node.type === "text" || node.type === "formula" ? 160 : 40);
  if (key === "height") return g.height || (g.radius ? g.radius * 2 : node.type === "text" || node.type === "formula" ? 50 : 40);
  if (key === "scale") return g.scale || 1;
  if (key === "rotation_deg") return g.rotation_deg || 0;
  return g[key] || 0;
}

function applyTimelineAction(nodes, action, progress, options) {
  const continuousAction = ["move", "scale", "rotate", "morph", "trace"].includes(action.type);
  const effectiveProgress = options.reducedMotion && continuousAction && progress < 1 ? 0 : progress;
  if (action.type === "trace") {
    for (const id of action.target_ids || []) {
      const node = nodes.get(id);
      if (!node) continue;
      node.visible = true;
      node.trace_progress = effectiveProgress;
    }
    return;
  }
  if (!["move", "scale", "rotate", "morph"].includes(action.type) || effectiveProgress >= 1) {
    applyAction(nodes, action); return;
  }
  if (effectiveProgress <= 0) return;
  for (const id of action.target_ids || []) {
    const node = nodes.get(id);
    if (!node) continue;
    node.visible = true;
    for (const [key, target] of Object.entries(action.to || {})) {
      if (typeof target !== "number") continue;
      const start = geometryValue(node, key);
      node.geometry[key] = start + (target - start) * effectiveProgress;
    }
  }
}

export function timelineDuration(candidate) {
  return candidate.timeline.start_hold_ms + candidate.timeline.beats.reduce((total, beat) => total + beat.duration_ms, 0);
}

function timelineNodes(candidate, elapsedMs, options = {}) {
  const nodes = cloneNodes(candidate);
  const beats = candidate.timeline.beats;
  for (const action of beats[0].actions) if (action.type === "show" && action.start_ms === 0) applyAction(nodes, action);
  let remaining = Math.max(0, elapsedMs - candidate.timeline.start_hold_ms);
  if (elapsedMs < candidate.timeline.start_hold_ms) return { nodes, beatIndex: 0, beatElapsedMs: 0 };
  for (let beatIndex = 0; beatIndex < beats.length; beatIndex += 1) {
    const beat = beats[beatIndex];
    if (remaining >= beat.duration_ms) {
      for (const action of beat.actions) applyAction(nodes, action);
      remaining -= beat.duration_ms;
      continue;
    }
    const actions = [...beat.actions].sort((a, b) => a.start_ms - b.start_ms);
    for (const action of actions) {
      if (remaining < action.start_ms) continue;
      const progress = action.duration_ms === 0 ? 1 : Math.min(1, (remaining - action.start_ms) / action.duration_ms);
      applyTimelineAction(nodes, action, progress, options);
    }
    return { nodes, beatIndex, beatElapsedMs: remaining };
  }
  return { nodes, beatIndex: beats.length - 1, beatElapsedMs: beats.at(-1).duration_ms };
}

function stateNodes(candidate, state) {
  const nodes = cloneNodes(candidate);
  const beats = candidate.timeline.beats;
  if (state === "initial") {
    for (const action of beats[0].actions) if (action.type === "show") applyAction(nodes, action);
    return nodes;
  }
  const ratio = STATE_BEAT[state] ?? 1;
  const limit = Math.max(1, Math.ceil(beats.length * ratio));
  for (const beat of beats.slice(0, limit)) for (const action of beat.actions) applyAction(nodes, action);
  return nodes;
}

function logicalBounds(node, schemaVersion) {
  const g = node.geometry || {};
  if (Array.isArray(g.points) && g.points.length) {
    const xs = g.points.map(point => point.x), ys = g.points.map(point => point.y);
    return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs) || 2, height: Math.max(...ys) - Math.min(...ys) || 2 };
  }
  const centerAnchored = ["open-visual-scene/0.3", "open-visual-scene/0.4"].includes(schemaVersion);
  let width = (g.width || (g.radius ? g.radius * 2 : node.type === "text" || node.type === "formula" ? 160 : 40)) * (centerAnchored ? (g.scale || 1) : 1);
  let height = (g.height || (g.radius ? g.radius * 2 : node.type === "text" || node.type === "formula" ? 50 : 40)) * (centerAnchored ? (g.scale || 1) : 1);
  if (centerAnchored && (g.rotation_deg || 0) % 180) {
    const diagonal = Math.hypot(width, height);
    width = diagonal; height = diagonal;
  }
  return { x: (g.x ?? 500) - width / 2, y: (g.y ?? 500) - height / 2, width, height };
}

function screenBounds(bounds, transform) {
  return {
    x: transform.ox + bounds.x * transform.scale,
    y: transform.oy + bounds.y * transform.scale,
    width: Math.max(2, bounds.width * transform.scale),
    height: Math.max(2, bounds.height * transform.scale)
  };
}

function screenBox(node, transform) {
  const scale = geometryValue(node, "scale");
  return {
    centerX: transform.ox + geometryValue(node, "x") * transform.scale,
    centerY: transform.oy + geometryValue(node, "y") * transform.scale,
    width: geometryValue(node, "width") * scale * transform.scale,
    height: geometryValue(node, "height") * scale * transform.scale,
    rotationDeg: geometryValue(node, "rotation_deg")
  };
}

function screenPoints(points, transform) {
  return points.map(point => ({
    x: transform.ox + point.x * transform.scale,
    y: transform.oy + point.y * transform.scale
  }));
}

export function partialPolylinePoints(points, progress) {
  if (!points.length) return [];
  const fraction = Math.min(1, Math.max(0, progress));
  if (points.length === 1 || fraction === 0) return [points[0]];
  const lengths = points.slice(1).map((point, index) => Math.hypot(point.x - points[index].x, point.y - points[index].y));
  const targetLength = lengths.reduce((total, length) => total + length, 0) * fraction;
  const partial = [points[0]];
  let traversed = 0;
  for (let index = 0; index < lengths.length; index += 1) {
    const length = lengths[index];
    if (traversed + length <= targetLength || length === 0) {
      partial.push(points[index + 1]);
      traversed += length;
      continue;
    }
    const segmentProgress = (targetLength - traversed) / length;
    partial.push({
      x: points[index].x + (points[index + 1].x - points[index].x) * segmentProgress,
      y: points[index].y + (points[index + 1].y - points[index].y) * segmentProgress
    });
    break;
  }
  return partial;
}

function colorFor(node) {
  if (node.style_token && COLORS[node.style_token]) return COLORS[node.style_token];
  const id = node.id.toLowerCase();
  if (id.includes("water") || id.includes("line") || id.includes("ray")) return COLORS["math-blue"];
  if (id.includes("honey") || id.includes("oil") || id.includes("light")) return COLORS["focus-yellow"];
  if (id.includes("conclusion") || id.includes("result")) return COLORS["signal-coral"];
  return COLORS["science-green"];
}

function drawArrowHead(ctx, points, color, lineWidth) {
  if (points.length < 2) return;
  const end = points.at(-1), previous = points.at(-2);
  const angle = Math.atan2(end.y - previous.y, end.x - previous.x);
  const size = Math.max(8, lineWidth * 3);
  ctx.beginPath();
  ctx.moveTo(end.x, end.y);
  ctx.lineTo(end.x - size * Math.cos(angle - Math.PI / 6), end.y - size * Math.sin(angle - Math.PI / 6));
  ctx.lineTo(end.x - size * Math.cos(angle + Math.PI / 6), end.y - size * Math.sin(angle + Math.PI / 6));
  ctx.closePath(); ctx.fillStyle = color; ctx.fill();
}

function drawShapeLabel(ctx, node, maxWidth) {
  if (!node.content) return;
  ctx.fillStyle = COLORS.ink;
  ctx.font = "700 14px system-ui, sans-serif";
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(node.content, 0, 0, Math.max(24, maxWidth - 10));
}

function drawNode(ctx, node, bounds, transform) {
  const b = screenBounds(bounds, transform);
  const color = colorFor(node);
  ctx.save();
  ctx.strokeStyle = COLORS.ink;
  ctx.fillStyle = color;
  ctx.lineWidth = node.emphasized ? 4 : 2;
  if (node.emphasized) { ctx.shadowColor = "rgba(23,33,43,.25)"; ctx.shadowBlur = 8; }
  if (node.type === "line" || node.type === "plot") {
    const logicalPoints = node.geometry.points || [
      { x: bounds.x, y: bounds.y + bounds.height / 2 },
      { x: bounds.x + bounds.width, y: bounds.y + bounds.height / 2 }
    ];
    const fullPoints = screenPoints(logicalPoints, transform);
    const points = node.trace_progress === undefined ? fullPoints : partialPolylinePoints(fullPoints, node.trace_progress);
    ctx.beginPath();
    points.forEach((point, index) => {
      index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = node.emphasized ? 5 : 3;
    ctx.stroke();
    if (node.marker_end === "arrow" && (node.trace_progress === undefined || node.trace_progress > 0)) {
      drawArrowHead(ctx, points, color, ctx.lineWidth);
    }
  } else {
    const box = screenBox(node, transform);
    ctx.translate(box.centerX, box.centerY);
    ctx.rotate((box.rotationDeg * Math.PI) / 180);
    const local = { x: -box.width / 2, y: -box.height / 2, width: box.width, height: box.height };
    if (node.type === "axis") {
      ctx.beginPath(); ctx.moveTo(local.x, 0); ctx.lineTo(local.x + local.width, 0);
      ctx.moveTo(0, local.y); ctx.lineTo(0, local.y + local.height); ctx.stroke();
    } else if (node.type === "particles") {
      for (let i = 0; i < 9; i += 1) {
        const x = local.x + ((i * 37) % 100) / 100 * local.width, y = local.y + ((i * 61) % 100) / 100 * local.height;
        ctx.beginPath(); ctx.arc(x, y, node.emphasized ? 6 : 4, 0, Math.PI * 2); ctx.fill();
      }
    } else if (node.type === "text" || node.type === "formula") {
      const fontSize = node.type === "formula" ? 20 : 16;
      ctx.font = `700 ${fontSize}px system-ui, sans-serif`;
      ctx.fillStyle = COLORS.ink;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(node.content || node.id.replaceAll("-", " "), 0, 0, Math.max(60, local.width));
    } else if (node.type === "shape") {
      ctx.beginPath();
      if (node.shape_kind === "ellipse") {
        ctx.ellipse(0, 0, local.width / 2, local.height / 2, 0, 0, Math.PI * 2);
      } else if (node.shape_kind === "polygon" && node.geometry.vertices?.length >= 3) {
        node.geometry.vertices.forEach((vertex, index) => {
          const x = vertex.x * local.width / 2, y = vertex.y * local.height / 2;
          index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        });
        ctx.closePath();
      } else {
        const radius = Math.min(12, local.width / 4, local.height / 4);
        ctx.roundRect(local.x, local.y, local.width, local.height, radius);
      }
      ctx.fill(); ctx.stroke(); drawShapeLabel(ctx, node, local.width);
    } else if (node.type !== "group") {
      const radius = Math.min(12, local.width / 4, local.height / 4);
      ctx.beginPath(); ctx.roundRect(local.x, local.y, local.width, local.height, radius); ctx.fill(); ctx.stroke();
    }
  }
  ctx.restore();
  return b;
}

function pixelStats(ctx, width, height) {
  const data = ctx.getImageData(0, 0, width, height).data;
  let nonBackground = 0;
  const colors = new Set();
  for (let i = 0; i < data.length; i += 16) {
    const key = `${data[i] >> 5}-${data[i + 1] >> 5}-${data[i + 2] >> 5}`;
    colors.add(key);
    if (!(data[i] > 245 && data[i + 1] > 243 && data[i + 2] > 235)) nonBackground += 1;
  }
  return { non_background_samples: nonBackground, quantized_color_count: colors.size };
}

export function renderScene(canvas, candidate, state, viewport) {
  const width = viewport.width, height = viewport.height;
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = COLORS.paper; ctx.fillRect(0, 0, width, height);
  const margin = viewport.kind === "phone" ? 20 : 28;
  const scale = Math.min((width - margin * 2) / 1000, (height - margin * 2) / 1000);
  const transform = { scale, ox: (width - 1000 * scale) / 2, oy: (height - 1000 * scale) / 2 };

  if (state === "static_fallback") {
    ctx.fillStyle = COLORS.ink; ctx.font = `800 ${viewport.kind === "phone" ? 17 : 20}px system-ui, sans-serif`;
    ctx.textAlign = "left"; ctx.textBaseline = "top";
    candidate.static_fallback.steps.forEach((step, index) => ctx.fillText(`${index + 1}. ${step}`, margin, margin + index * (viewport.kind === "phone" ? 52 : 58), width - margin * 2));
    return { elements: candidate.static_fallback.steps.map((_, index) => ({ id: `fallback-${index}`, bounds: { x: margin, y: margin + index * 52, width: width - margin * 2, height: 40 } })), logical_violations: [], pixel_stats: pixelStats(ctx, width, height) };
  }

  const nodes = stateNodes(candidate, state);
  const visible = [...nodes.values()].filter(node => node.visible).sort((a, b) => (a.layout?.priority || 1) - (b.layout?.priority || 1));
  const elements = [];
  const logicalViolations = [];
  for (const node of visible) {
    const logical = logicalBounds(node, candidate.schema_version);
    if (logical.x < 0 || logical.y < 0 || logical.x + logical.width > 1000 || logical.y + logical.height > 1000) logicalViolations.push({ id: node.id, bounds: logical });
    if (node.type !== "group") elements.push({ id: node.id, type: node.type, bounds: drawNode(ctx, node, logical, transform) });
  }
  return { elements, logical_violations: logicalViolations, pixel_stats: pixelStats(ctx, width, height) };
}

export function renderTimelineScene(canvas, candidate, elapsedMs, viewport, options = {}) {
  const width = viewport.width, height = viewport.height;
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = COLORS.paper; ctx.fillRect(0, 0, width, height);
  const margin = viewport.kind === "phone" ? 20 : 28;
  const scale = Math.min((width - margin * 2) / 1000, (height - margin * 2) / 1000);
  const transform = { scale, ox: (width - 1000 * scale) / 2, oy: (height - 1000 * scale) / 2 };
  const playback = timelineNodes(candidate, Math.min(elapsedMs, timelineDuration(candidate)), { reducedMotion: options.reducedMotion === true });
  const visible = [...playback.nodes.values()].filter(node => node.visible).sort((a, b) => (a.layout?.priority || 1) - (b.layout?.priority || 1));
  const elements = [];
  const logicalViolations = [];
  for (const node of visible) {
    const logical = logicalBounds(node, candidate.schema_version);
    if (logical.x < 0 || logical.y < 0 || logical.x + logical.width > 1000 || logical.y + logical.height > 1000) logicalViolations.push({ id: node.id, bounds: logical });
    if (node.type !== "group") elements.push({ id: node.id, type: node.type, bounds: drawNode(ctx, node, logical, transform) });
  }
  return {
    elements, logical_violations: logicalViolations, pixel_stats: pixelStats(ctx, width, height),
    beat_index: playback.beatIndex, beat_elapsed_ms: playback.beatElapsedMs, total_duration_ms: timelineDuration(candidate)
  };
}

export const RUNTIME_STATES = ["initial", "key_process", "final", "paused", "resumed", "post_interaction", "reduced_motion", "static_fallback"];
