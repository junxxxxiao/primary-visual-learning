const COLORS = {
  "science-green": "#237a57",
  "math-blue": "#2463a8",
  "signal-coral": "#d85f4a",
  "focus-yellow": "#d9a514"
};

function trustedProgram(api, input, spec, colors) {
  const canvas = api.canvas;
  const ctx = canvas.getContext("2d");
  const width = input.width;
  const height = input.height;
  const phone = input.parameters.viewport.kind === "phone";
  const state = input.parameters.state;
  const padding = phone ? 20 : 32;
  const titleSize = phone ? 20 : 24;
  const labelSize = phone ? 16 : 18;
  const primary = colors[spec.color_tokens.primary];
  const accent = colors[spec.color_tokens.accent];
  const background = "#f7faf8";
  const ink = "#17231d";
  const elements = [];
  const addText = (id, text, x, y, maxWidth, size = labelSize) => {
    ctx.fillStyle = ink;
    ctx.font = `600 ${size}px sans-serif`;
    ctx.textBaseline = "top";
    ctx.fillText(text, x, y, maxWidth);
    elements.push({ element_id: id, bounds: { x, y, width: maxWidth, height: size * 1.4 }, font_size: size, min_graphic_size: 0, interactive: false, touch_size: 0, local_safe_region: null });
  };
  const addBox = (id, x, y, boxWidth, boxHeight, color) => {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, boxWidth, boxHeight);
    elements.push({ element_id: id, bounds: { x, y, width: boxWidth, height: boxHeight }, font_size: 0, min_graphic_size: Math.min(boxWidth, boxHeight), interactive: false, touch_size: 0, local_safe_region: null });
  };
  const drawWave = (id, x, y, waveWidth, waveHeight, amplitude, color) => {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    for (let step = 0; step <= waveWidth; step += 4) {
      const pointY = y + waveHeight / 2 + Math.sin(step / 18) * amplitude;
      if (step === 0) ctx.moveTo(x + step, pointY);
      else ctx.lineTo(x + step, pointY);
    }
    ctx.stroke();
    elements.push({ element_id: id, bounds: { x, y, width: waveWidth, height: waveHeight }, font_size: 0, min_graphic_size: Math.min(waveWidth, waveHeight), interactive: false, touch_size: 0, local_safe_region: null });
  };

  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);
  addText("title", spec.title, padding, padding, width - padding * 2, titleSize);
  const contentTop = padding + titleSize * 2.2;
  const contentHeight = height - contentTop - padding;
  const fallback = state === "static_fallback";
  const labels = fallback ? spec.static_fallback.steps : spec.labels;
  const sceneType = fallback ? "sequence" : spec.scene_type;
  const visibleCount = state === "initial" ? Math.min(1, labels.length) : labels.length;

  if (sceneType === "comparison") {
    const gap = phone ? 18 : 28;
    const extraCount = Math.max(0, visibleCount - 2);
    const extraHeight = extraCount ? extraCount * labelSize * 1.8 + gap : 0;
    const panelAreaHeight = contentHeight - extraHeight;
    const panelWidth = phone ? width - padding * 2 : (width - padding * 2 - gap) / 2;
    const panelHeight = phone ? (panelAreaHeight - gap) / 2 : panelAreaHeight;
    for (let index = 0; index < Math.min(2, visibleCount); index += 1) {
      const x = phone ? padding : padding + index * (panelWidth + gap);
      const y = phone ? contentTop + index * (panelHeight + gap) : contentTop;
      addBox(`panel-${index}`, x, y, panelWidth, panelHeight, index ? "#e9f1fb" : "#e8f4ee");
      drawWave(`signal-${index}`, x + 24, y + 52, panelWidth - 48, Math.max(80, panelHeight - 110), index ? 32 : 16, index ? accent : primary);
      addText(`dsl-content-${index}`, labels[index], x + 20, y + 18, panelWidth - 40);
    }
    for (let index = 2; index < visibleCount; index += 1) {
      addText(`dsl-content-${index}`, labels[index], padding, contentTop + panelAreaHeight + gap + (index - 2) * labelSize * 1.8, width - padding * 2);
    }
  } else if (sceneType === "wave") {
    const extraCount = Math.max(0, visibleCount - 2);
    const extraHeight = extraCount ? extraCount * labelSize * 1.8 + 12 : 0;
    const waveAreaHeight = contentHeight - extraHeight;
    const waveHeight = Math.max(80, (waveAreaHeight - 70) / 2);
    drawWave("wave-before", padding, contentTop + 30, width - padding * 2, waveHeight, 18, primary);
    if (visibleCount > 1) drawWave("wave-after", padding, contentTop + waveHeight + 50, width - padding * 2, waveHeight, 38, accent);
    addText("dsl-content-0", labels[0], padding, contentTop, width - padding * 2);
    if (visibleCount > 1) addText("dsl-content-1", labels[1], padding, contentTop + waveHeight + 20, width - padding * 2);
    for (let index = 2; index < visibleCount; index += 1) {
      addText(`dsl-content-${index}`, labels[index], padding, contentTop + waveAreaHeight + 12 + (index - 2) * labelSize * 1.8, width - padding * 2);
    }
  } else if (sceneType === "area_model") {
    const modelSize = Math.min(width - padding * 2, contentHeight * 0.62);
    const x = padding;
    const y = contentTop + 16;
    addBox("area-model", x, y, modelSize, modelSize * 0.68, "#dceafa");
    ctx.strokeStyle = primary;
    ctx.lineWidth = 4;
    ctx.strokeRect(x, y, modelSize, modelSize * 0.68);
    for (let index = 0; index < visibleCount; index += 1) addText(`dsl-content-${index}`, labels[index], x, y + modelSize * 0.68 + 28 + index * (labelSize * 1.8), width - padding * 2);
  } else {
    const gap = phone ? 14 : 24;
    const itemHeight = Math.min(110, (contentHeight - gap * (labels.length - 1)) / labels.length);
    for (let index = 0; index < visibleCount; index += 1) {
      const x = padding;
      const y = contentTop + index * (itemHeight + gap);
      addBox(`step-${index}`, x, y, width - padding * 2, itemHeight, index % 2 ? "#e9f1fb" : "#e8f4ee");
      addText(`dsl-content-${index}`, labels[index], x + 20, y + (itemHeight - labelSize * 1.4) / 2, width - padding * 2 - 40);
    }
  }

  const interaction = spec.interaction !== "none" && state === "post_interaction";
  if (interaction) {
    const size = phone ? 48 : 52;
    addBox("interaction-control", width - padding - size, height - padding - size, size, size, accent);
    const control = elements[elements.length - 1];
    control.interactive = true;
    control.touch_size = size;
  }
  api.emit("interaction", {
    type: "layout_measurement",
    layout_mode: phone ? "vertical-responsive" : "tablet-responsive",
    canvas_inner_bounds: { x: 0, y: 0, width, height },
    local_safe_regions: {},
    readability_limits: phone ? { min_font_size: 16, min_graphic_size: 24, min_touch_size: 44 } : { min_font_size: 18, min_graphic_size: 28, min_touch_size: 44 },
    container_metrics: { client_width: width, client_height: height, scroll_width: width, scroll_height: height, overflow: "visible", clip: false, mask: false },
    elements,
    motion_envelopes: []
  });
  api.emit("render_complete", { state });
}

export function compileScene(spec) {
  return `(${trustedProgram.toString()})(api,input,${JSON.stringify(spec)},${JSON.stringify(COLORS)});`;
}

export function renderScenePreview(canvas, spec, viewport, state) {
  canvas.width = viewport.width;
  canvas.height = viewport.height;
  let measurement = null;
  trustedProgram({
    canvas,
    emit(name, payload) {
      if (name === "interaction" && payload?.type === "layout_measurement") measurement = payload;
    }
  }, {
    width: viewport.width,
    height: viewport.height,
    parameters: { state, viewport }
  }, spec, COLORS);
  return measurement;
}
