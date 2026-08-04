const COLORS = {
  green: '#43b581', blue: '#4c88ff', coral: '#ff786a', ink: '#17212b',
  paper: '#fffdf7', muted: '#7a848e', line: '#c9d0d6', paleGreen: '#dff4ea', paleBlue: '#e4eeff'
};

const INNER_BOUNDS = {x: 28, y: 24, width: 924, height: 632};
let textScale = 1;

export function resolveTeachingScene(sampleId) {
  if (sampleId === 'primary_sound.opening-explanation') return 'string-observation';
  if (sampleId === 'primary_sound.compare') return 'string-force-comparison';
  if (sampleId === 'primary_sound.separate') return 'string-causality';
  if (sampleId === 'primary_sound_pair.pair-opening-explanation') return 'sound-source-comparison';
  if (sampleId === 'primary_sound_pair.pair-reveal') return 'sound-wave-reveal';
  if (sampleId.startsWith('middle_perfect_square.')) return 'perfect-square-area';
  return 'unsupported';
}

function clamp(value, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function cubicBezierY(t) {
  const x1 = 0.77, y1 = 0, x2 = 0.175, y2 = 1;
  let u = t;
  for (let index = 0; index < 5; index += 1) {
    const inverse = 1 - u;
    const x = 3 * inverse * inverse * u * x1 + 3 * inverse * u * u * x2 + u * u * u;
    const derivative = 3 * inverse * inverse * x1 + 6 * inverse * u * (x2 - x1) + 3 * u * u * (1 - x2);
    if (Math.abs(derivative) > 0.0001) u = clamp(u - (x - t) / derivative);
  }
  const inverse = 1 - u;
  return 3 * inverse * u * u * y2 + u * u * u;
}

function reveal(ratio, start, end, reducedMotion) {
  if (reducedMotion) return ratio >= end ? 1 : 0;
  return cubicBezierY(clamp((ratio - start) / (end - start)));
}

function withAlpha(ctx, alpha, draw) {
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  draw();
  ctx.restore();
}

function roundedPanel(ctx, bounds, fill = '#ffffff', stroke = COLORS.line) {
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(bounds.x, bounds.y, bounds.width, bounds.height, 14);
  ctx.fill();
  ctx.stroke();
}

function fitText(ctx, text, bounds, options = {}) {
  const maxSize = (options.size || 24) * textScale;
  const minSize = (options.minSize || 14) * textScale;
  let size = maxSize;
  ctx.font = `${options.weight || 700} ${size}px system-ui, sans-serif`;
  while (size > minSize && ctx.measureText(text).width > bounds.width) {
    size -= 1;
    ctx.font = `${options.weight || 700} ${size}px system-ui, sans-serif`;
  }
  ctx.fillStyle = options.color || COLORS.ink;
  ctx.textAlign = options.align || 'center';
  ctx.textBaseline = 'middle';
  const x = options.align === 'left' ? bounds.x : bounds.x + bounds.width / 2;
  ctx.fillText(text, x, bounds.y + bounds.height / 2, bounds.width);
}

function addElement(elements, id, semantic, bounds, alpha = 1) {
  if (alpha <= 0) return;
  elements.push({id, semantic, bounds: {...bounds}, opacity: alpha});
}

function drawArrow(ctx, x, y1, y2, color) {
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(x, y1); ctx.lineTo(x, y2); ctx.stroke();
  for (const [y, direction] of [[y1, 1], [y2, -1]]) {
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 7, y + direction * 10); ctx.lineTo(x + 7, y + direction * 10); ctx.closePath(); ctx.fill();
  }
}

function drawWave(ctx, bounds, amplitude, cycles, color, progress = 1) {
  const endX = bounds.x + bounds.width * progress;
  ctx.strokeStyle = color;
  ctx.lineWidth = 5;
  ctx.lineCap = 'round';
  ctx.beginPath();
  for (let x = bounds.x; x <= endX; x += 3) {
    const phase = ((x - bounds.x) / bounds.width) * Math.PI * 2 * cycles;
    const y = bounds.y + bounds.height / 2 + Math.sin(phase) * amplitude;
    x === bounds.x ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function drawStringPanel(ctx, elements, panel, id, label, amplitude, alpha, detailAlpha) {
  withAlpha(ctx, alpha, () => {
    roundedPanel(ctx, panel);
    fitText(ctx, label, {x: panel.x + 18, y: panel.y + 14, width: 120, height: 32}, {size: 21, align: 'left', color: id === 'heavy' ? COLORS.coral : COLORS.ink});
    const string = {x: panel.x + 42, y: panel.y + 68, width: panel.width - 84, height: Math.max(116, panel.height - 112)};
    ctx.strokeStyle = COLORS.muted; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(string.x, string.y + string.height / 2); ctx.lineTo(string.x + string.width, string.y + string.height / 2); ctx.stroke();
    ctx.fillStyle = COLORS.ink;
    for (const x of [string.x, string.x + string.width]) ctx.fillRect(x - 5, string.y + 10, 10, string.height - 20);
    drawWave(ctx, string, amplitude * detailAlpha, 4, COLORS.green);
    addElement(elements, `${id}-string`, 'string', string, alpha);
    if (detailAlpha > 0) {
      const arrowX = string.x + string.width / 2;
      drawArrow(ctx, arrowX, string.y + string.height / 2 - amplitude, string.y + string.height / 2 + amplitude, COLORS.green);
      fitText(ctx, amplitude < 40 ? '振幅小 · 声音较轻' : '振幅大 · 声音更响', {x: panel.x + 20, y: panel.y + panel.height - 43, width: panel.width - 40, height: 28}, {size: 19, color: COLORS.green});
      addElement(elements, `${id}-amplitude`, 'amplitude', {x: arrowX - 12, y: string.y + string.height / 2 - amplitude - 12, width: 24, height: amplitude * 2 + 24}, detailAlpha);
      addElement(elements, `${id}-loudness`, 'loudness', {x: panel.x + 20, y: panel.y + panel.height - 57, width: panel.width - 40, height: 36}, detailAlpha);
    }
  });
}

function renderStringForce(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const fixedAlpha = reveal(ratio, 0, 0.2, options.reducedMotion);
  const stringAlpha = reveal(ratio, 0.2, 0.55, options.reducedMotion);
  const detailAlpha = reveal(ratio, 0.55, 0.78, options.reducedMotion);
  const conclusionAlpha = reveal(ratio, 0.78, 1, options.reducedMotion);
  withAlpha(ctx, Math.max(0.18, fixedAlpha), () => {
    fitText(ctx, '同一根弦：长度、松紧、粗细都不变', {x: phone ? 80 : 180, y: 26, width: phone ? 820 : 620, height: 42}, {size: 25});
    if (!phone) { ctx.fillStyle = COLORS.coral; ctx.fillRect(382, 69, 216, 5); }
  });
  addElement(elements, 'fixed-conditions', 'controlled-conditions', {x: 180, y: 26, width: 620, height: 48}, Math.max(0.18, fixedAlpha));
  const panels = phone
    ? [{x: 72, y: 92, width: 836, height: 220}, {x: 72, y: 330, width: 836, height: 220}]
    : [{x: 52, y: 104, width: 420, height: 408}, {x: 508, y: 104, width: 420, height: 408}];
  drawStringPanel(ctx, elements, panels[0], 'light', '轻轻拨', 26, stringAlpha, detailAlpha);
  drawStringPanel(ctx, elements, panels[1], 'heavy', '用力拨', 58, stringAlpha, detailAlpha);
  withAlpha(ctx, conclusionAlpha, () => {
    const bounds = {x: 170, y: phone ? 555 : 548, width: 640, height: phone ? 95 : 66};
    roundedPanel(ctx, bounds, COLORS.paleBlue, COLORS.blue);
    if (phone) {
      fitText(ctx, '往返次数接近 → 频率接近', {x: bounds.x + 20, y: bounds.y + 10, width: bounds.width - 40, height: 32}, {size: 18, color: COLORS.blue});
      fitText(ctx, '所以音调基本不变', {x: bounds.x + 20, y: bounds.y + 52, width: bounds.width - 40, height: 32}, {size: 18, color: COLORS.blue});
    } else fitText(ctx, '往返次数接近 → 频率接近 → 音调基本不变', {x: bounds.x + 20, y: bounds.y + 10, width: bounds.width - 40, height: 46}, {size: 24, color: COLORS.blue});
    addElement(elements, 'frequency-conclusion', 'frequency-pitch', bounds, conclusionAlpha);
  });
}

function renderStringObservation(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const stringAlpha = Math.max(0.18, reveal(ratio, 0.15, 0.65, options.reducedMotion));
  const observationAlpha = reveal(ratio, 0.65, 1, options.reducedMotion);
  fitText(ctx, '先观察：同一根琴弦怎样振动', {x: 130, y: 28, width: 720, height: 44}, {size: 27});
  const panel = phone ? {x: 72, y: 108, width: 836, height: 330} : {x: 170, y: 120, width: 640, height: 360};
  drawStringPanel(ctx, elements, panel, 'observation', '琴弦', 48, stringAlpha, stringAlpha);
  withAlpha(ctx, observationAlpha, () => {
    const bounds = {x: 160, y: phone ? 500 : 510, width: 660, height: 66};
    roundedPanel(ctx, bounds, COLORS.paleGreen, COLORS.green);
    fitText(ctx, '琴弦往复振动，波峰和波谷不断重复', {x: bounds.x + 20, y: bounds.y + 10, width: bounds.width - 40, height: 46}, {size: 23, color: COLORS.green});
    addElement(elements, 'observation-note', 'repeated-vibration', bounds, observationAlpha);
  });
}

function renderStringCausality(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const amplitudeAlpha = reveal(ratio, 0.12, 0.52, options.reducedMotion);
  const frequencyAlpha = reveal(ratio, 0.42, 0.78, options.reducedMotion);
  const conclusionAlpha = reveal(ratio, 0.78, 1, options.reducedMotion);
  fitText(ctx, '同一次拨动，分别看两个变化', {x: 150, y: 28, width: 680, height: 44}, {size: 27});
  const left = phone ? {x: 72, y: 105, width: 836, height: 190} : {x: 52, y: 120, width: 420, height: 300};
  const right = phone ? {x: 72, y: 320, width: 836, height: 190} : {x: 508, y: 120, width: 420, height: 300};
  for (const [panel, color, title, semantic, text] of [[left, COLORS.green, '振幅变大', 'amplitude-cause', '振幅变大 → 响度变大'], [right, COLORS.blue, '频率基本不变', 'frequency-cause', '相同时间内次数接近 → 音调基本不变']]) {
    const alpha = semantic === 'amplitude-cause' ? amplitudeAlpha : frequencyAlpha;
    withAlpha(ctx, alpha, () => {
      roundedPanel(ctx, panel, '#ffffff', color);
      fitText(ctx, title, {x: panel.x + 20, y: panel.y + 14, width: panel.width - 40, height: 34}, {size: 24, color});
      const wave = {x: panel.x + 42, y: panel.y + 62, width: panel.width - 84, height: 70};
      drawWave(ctx, wave, semantic === 'amplitude-cause' ? 30 : 18, 4, color);
      fitText(ctx, text, {x: panel.x + 24, y: panel.y + panel.height - 48, width: panel.width - 48, height: 30}, {size: 19, color});
      addElement(elements, semantic, semantic, panel, alpha);
    });
  }
  withAlpha(ctx, conclusionAlpha, () => {
    const bounds = {x: 160, y: phone ? 540 : 470, width: 660, height: 70};
    roundedPanel(ctx, bounds, COLORS.paleBlue, COLORS.blue);
    fitText(ctx, '力度主要改变振幅和响度，不是音调', {x: bounds.x + 20, y: bounds.y + 10, width: bounds.width - 40, height: 48}, {size: 23, color: COLORS.blue});
    addElement(elements, 'causality-conclusion', 'causality', bounds, conclusionAlpha);
  });
}

function drawRubberBandSource(ctx, elements, panel, id, label, amplitude, alpha) {
  withAlpha(ctx, alpha, () => {
    roundedPanel(ctx, panel);
    fitText(ctx, label, {x: panel.x + 18, y: panel.y + 12, width: panel.width - 36, height: 32}, {size: 21, color: id === 'strong' ? COLORS.coral : COLORS.ink});
    const rig = {x: panel.x + 72, y: panel.y + 64, width: panel.width - 144, height: 126};
    ctx.strokeStyle = COLORS.ink; ctx.lineWidth = 9; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(rig.x, rig.y); ctx.lineTo(rig.x, rig.y + rig.height); ctx.moveTo(rig.x + rig.width, rig.y); ctx.lineTo(rig.x + rig.width, rig.y + rig.height); ctx.stroke();
    drawWave(ctx, {x: rig.x, y: rig.y + 10, width: rig.width, height: rig.height - 20}, amplitude, 1, COLORS.green);
    addElement(elements, `${id}-source`, 'sound-source', rig, alpha);
  });
}

function renderSoundSources(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const sourceAlpha = Math.max(0.18, reveal(ratio, 0, 0.3, options.reducedMotion));
  const comparisonAlpha = reveal(ratio, 0.3, 0.72, options.reducedMotion);
  const conclusionAlpha = reveal(ratio, 0.72, 1, options.reducedMotion);
  fitText(ctx, '同一根橡皮筋，比较轻拨和重拨', {x: 150, y: 24, width: 680, height: 44}, {size: 26});
  const panels = phone
    ? [{x: 70, y: 82, width: 840, height: 210}, {x: 70, y: 310, width: 840, height: 210}]
    : [{x: 54, y: 90, width: 420, height: 304}, {x: 506, y: 90, width: 420, height: 304}];
  drawRubberBandSource(ctx, elements, panels[0], 'light', '轻拨', 18, sourceAlpha);
  drawRubberBandSource(ctx, elements, panels[1], 'strong', '重拨', 45, sourceAlpha);
  withAlpha(ctx, comparisonAlpha, () => {
    const waveY = phone ? [245, 473] : [422, 422];
    panels.forEach((panel, index) => {
      const waveBounds = {x: panel.x + 70, y: waveY[index], width: panel.width - 140, height: 86};
      drawWave(ctx, waveBounds, index ? 34 : 15, 4, index ? COLORS.coral : COLORS.green);
      fitText(ctx, index ? '振幅更大 · 更响' : '振幅较小 · 较轻', {x: waveBounds.x, y: waveBounds.y + 72, width: waveBounds.width, height: 30}, {size: 18, color: index ? COLORS.coral : COLORS.green});
      addElement(elements, `${index ? 'strong' : 'light'}-wave`, 'waveform', waveBounds, comparisonAlpha);
      addElement(elements, `${index ? 'strong' : 'light'}-amplitude`, 'amplitude', {x: waveBounds.x, y: waveBounds.y, width: waveBounds.width, height: waveBounds.height + 28}, comparisonAlpha);
    });
  });
  withAlpha(ctx, conclusionAlpha, () => {
    const bounds = {x: 170, y: phone ? 548 : 566, width: 640, height: phone ? 100 : 64};
    roundedPanel(ctx, bounds, COLORS.paleBlue, COLORS.blue);
    if (phone) {
      fitText(ctx, '波峰数量和间距接近', {x: bounds.x + 20, y: bounds.y + 10, width: bounds.width - 40, height: 32}, {size: 18, color: COLORS.blue});
      fitText(ctx, '所以音调基本不变', {x: bounds.x + 20, y: bounds.y + 55, width: bounds.width - 40, height: 32}, {size: 18, color: COLORS.blue});
    } else fitText(ctx, '波峰数量和间距接近 → 音调基本不变', {x: bounds.x + 20, y: bounds.y + 9, width: bounds.width - 40, height: 46}, {size: 23, color: COLORS.blue});
    addElement(elements, 'pair-frequency-conclusion', 'frequency-pitch', bounds, conclusionAlpha);
  });
}

function renderSoundWaveReveal(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const sourceAlpha = Math.max(0.18, reveal(ratio, 0, 0.25, options.reducedMotion));
  const amplitudeAlpha = reveal(ratio, 0.25, 0.62, options.reducedMotion);
  const pitchAlpha = reveal(ratio, 0.62, 0.9, options.reducedMotion);
  fitText(ctx, '重拨时，先看振幅，再看音调', {x: 140, y: 28, width: 700, height: 44}, {size: 27});
  const panel = phone ? {x: 70, y: 100, width: 840, height: 250} : {x: 130, y: 112, width: 720, height: 290};
  drawRubberBandSource(ctx, elements, panel, 'strong', '重拨：摆动更宽', 45, sourceAlpha);
  withAlpha(ctx, amplitudeAlpha, () => {
    const wave = {x: panel.x + 72, y: phone ? 380 : 435, width: panel.width - 144, height: 72};
    drawWave(ctx, wave, 34, 4, COLORS.coral);
    fitText(ctx, '振幅更大 → 声音更响', {x: wave.x, y: wave.y + 62, width: wave.width, height: 30}, {size: 20, color: COLORS.coral});
    addElement(elements, 'reveal-amplitude', 'amplitude', wave, amplitudeAlpha);
  });
  withAlpha(ctx, pitchAlpha, () => {
    const bounds = {x: 160, y: phone ? 545 : 540, width: 660, height: 68};
    roundedPanel(ctx, bounds, COLORS.paleBlue, COLORS.blue);
    fitText(ctx, '波峰间距接近 → 音调基本不变', {x: bounds.x + 20, y: bounds.y + 10, width: bounds.width - 40, height: 46}, {size: 23, color: COLORS.blue});
    addElement(elements, 'reveal-pitch', 'frequency-pitch', bounds, pitchAlpha);
  });
}

function region(ctx, elements, id, semantic, bounds, label, fill, alpha) {
  withAlpha(ctx, alpha, () => {
    ctx.fillStyle = fill; ctx.strokeStyle = COLORS.ink; ctx.lineWidth = 3;
    ctx.fillRect(bounds.x, bounds.y, bounds.width, bounds.height); ctx.strokeRect(bounds.x, bounds.y, bounds.width, bounds.height);
    fitText(ctx, label, bounds, {size: Math.min(34, Math.max(18, Math.min(bounds.width, bounds.height) / 3))});
  });
  addElement(elements, id, semantic, bounds, alpha);
}

function renderPerfectSquare(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const originalAlpha = Math.max(0.18, reveal(ratio, 0, 0.25, options.reducedMotion));
  const rectanglesAlpha = reveal(ratio, 0.25, 0.6, options.reducedMotion);
  const cornerAlpha = reveal(ratio, 0.6, 0.78, options.reducedMotion);
  const formulaAlpha = reveal(ratio, 0.78, 1, options.reducedMotion);
  fitText(ctx, '把四块面积拼成一个完整正方形', {x: 150, y: 26, width: 680, height: 44}, {size: 27});
  const square = phone ? {x: 290, y: 92, width: 400, height: 400} : {x: 82, y: 132, width: 430, height: 430};
  const a = square.width * 0.27;
  const x = square.width - a;
  region(ctx, elements, 'region-x2', 'area-x2', {x: square.x, y: square.y, width: x, height: x}, 'x²', COLORS.paleBlue, originalAlpha);
  region(ctx, elements, 'region-ax-right', 'area-ax', {x: square.x + x, y: square.y, width: a, height: x}, 'ax', COLORS.paleGreen, rectanglesAlpha);
  region(ctx, elements, 'region-ax-bottom', 'area-ax', {x: square.x, y: square.y + x, width: x, height: a}, 'ax', COLORS.paleGreen, rectanglesAlpha);
  region(ctx, elements, 'region-a2', 'area-a2', {x: square.x + x, y: square.y + x, width: a, height: a}, 'a²', '#ffe8e5', cornerAlpha);
  withAlpha(ctx, formulaAlpha, () => {
    const formula = phone ? {x: 180, y: 535, width: 620, height: 76} : {x: 558, y: 206, width: 350, height: 168};
    roundedPanel(ctx, formula, '#ffffff', COLORS.blue);
    if (phone) {
      fitText(ctx, '(x + a)²', {x: formula.x + 18, y: formula.y + 6, width: formula.width - 36, height: 30}, {size: 22, color: COLORS.blue});
      fitText(ctx, '= x² + 2ax + a²', {x: formula.x + 18, y: formula.y + 38, width: formula.width - 36, height: 30}, {size: 22, color: COLORS.blue});
    } else fitText(ctx, '(x + a)² = x² + 2ax + a²', {x: formula.x + 18, y: formula.y + 20, width: formula.width - 36, height: 42}, {size: 27, color: COLORS.blue});
    if (!phone) fitText(ctx, '四块没有重叠，也没有空缺', {x: formula.x + 18, y: formula.y + 82, width: formula.width - 36, height: 42}, {size: 20});
    addElement(elements, 'formula-equality', 'formula', formula, formulaAlpha);
  });
}

function renderSquareBound(ctx, ratio, options, elements) {
  const phone = options.viewport === 'phone';
  const formulaAlpha = Math.max(0.18, reveal(ratio, 0, 0.25, options.reducedMotion));
  const nonnegativeAlpha = reveal(ratio, 0.25, 0.6, options.reducedMotion);
  const shrinkProgress = reveal(ratio, 0.6, 0.86, options.reducedMotion);
  const maximumAlpha = reveal(ratio, 0.78, 1, options.reducedMotion);
  fitText(ctx, '平方项越小，面积越接近上界', {x: 170, y: 28, width: 640, height: 44}, {size: 27});
  const formula = phone ? {x: 120, y: 100, width: 740, height: 92} : {x: 90, y: 126, width: 500, height: 112};
  withAlpha(ctx, formulaAlpha, () => {
    roundedPanel(ctx, formula, '#ffffff', COLORS.blue);
    fitText(ctx, 'A = C - k(x - h)²', {x: formula.x + 24, y: formula.y + 18, width: formula.width - 48, height: 54}, {size: 32, color: COLORS.blue});
    addElement(elements, 'area-upper-bound-formula', 'upper-bound-formula', formula, formulaAlpha);
  });

  const startSize = phone ? 250 : 220;
  const endSize = phone ? 46 : 40;
  const size = startSize + (endSize - startSize) * shrinkProgress;
  const center = phone ? {x: 490, y: 365} : {x: 745, y: 296};
  const square = {x: center.x - size / 2, y: center.y - size / 2, width: size, height: size};
  withAlpha(ctx, Math.max(formulaAlpha, nonnegativeAlpha), () => {
    ctx.fillStyle = '#ffe8e5'; ctx.strokeStyle = COLORS.coral; ctx.lineWidth = 4;
    ctx.fillRect(square.x, square.y, square.width, square.height); ctx.strokeRect(square.x, square.y, square.width, square.height);
  });
  addElement(elements, 'square-term', 'square-term', square, Math.max(formulaAlpha, nonnegativeAlpha));
  withAlpha(ctx, nonnegativeAlpha, () => {
    const label = phone ? {x: 170, y: 515, width: 640, height: 52} : {x: 612, y: 452, width: 266, height: 52};
    fitText(ctx, '(x - h)² ≥ 0', label, {size: 28, color: COLORS.coral});
    addElement(elements, 'square-nonnegative', 'nonnegative', label, nonnegativeAlpha);
  });
  withAlpha(ctx, maximumAlpha, () => {
    const bound = phone ? {x: 160, y: 580, width: 660, height: 68} : {x: 150, y: 420, width: 420, height: 154};
    roundedPanel(ctx, bound, COLORS.paleBlue, COLORS.blue);
    if (phone) {
      fitText(ctx, '平方项 = 0 时，A 最大 = C', {x: bound.x + 20, y: bound.y + 10, width: bound.width - 40, height: 46}, {size: 23, color: COLORS.blue});
    } else {
      fitText(ctx, 'C - k(x-h)² ≤ C', {x: bound.x + 24, y: bound.y + 20, width: bound.width - 48, height: 44}, {size: 27, color: COLORS.blue});
      fitText(ctx, 'x = h 时，A 最大 = C', {x: bound.x + 24, y: bound.y + 82, width: bound.width - 48, height: 40}, {size: 22});
    }
    addElement(elements, 'maximum-conclusion', 'maximum', bound, maximumAlpha);
  });
}

function renderUnsupported(ctx, candidate, elements) {
  const bounds = {x: 170, y: 220, width: 640, height: 210};
  roundedPanel(ctx, bounds, '#ffffff', COLORS.coral);
  fitText(ctx, '当前题目暂不支持动态教学图解', {x: bounds.x + 36, y: bounds.y + 50, width: bounds.width - 72, height: 44}, {size: 27});
  fitText(ctx, candidate.caption || '请使用静态讲解继续', {x: bounds.x + 52, y: bounds.y + 114, width: bounds.width - 104, height: 54}, {size: 19, weight: 500, color: COLORS.muted});
  addElement(elements, 'unsupported-fallback', 'unsupported', bounds);
}

export function renderTeachingScene(ctx, candidate, ratio, options = {}) {
  const scene = resolveTeachingScene(candidate.sample_id || '');
  const settings = {reducedMotion: options.reducedMotion === true, viewport: options.viewport === 'phone' ? 'phone' : 'tablet'};
  const elements = [];
  textScale = settings.viewport === 'phone' ? 2 : 1;
  ctx.save();
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.lineJoin = 'round';
  if (scene === 'string-observation') renderStringObservation(ctx, clamp(ratio), settings, elements);
  else if (scene === 'string-force-comparison') renderStringForce(ctx, clamp(ratio), settings, elements);
  else if (scene === 'string-causality') renderStringCausality(ctx, clamp(ratio), settings, elements);
  else if (scene === 'sound-source-comparison') renderSoundSources(ctx, clamp(ratio), settings, elements);
  else if (scene === 'sound-wave-reveal') renderSoundWaveReveal(ctx, clamp(ratio), settings, elements);
  else if (scene === 'perfect-square-area' && candidate.sample_id.endsWith('.justify')) renderSquareBound(ctx, clamp(ratio), settings, elements);
  else if (scene === 'perfect-square-area') renderPerfectSquare(ctx, clamp(ratio), settings, elements);
  else renderUnsupported(ctx, candidate, elements);
  ctx.restore();
  textScale = 1;
  return {
    scene,
    supported: scene !== 'unsupported',
    viewport: settings.viewport,
    reduced_motion: settings.reducedMotion,
    ratio: clamp(ratio),
    canvas_inner_bounds: {...INNER_BOUNDS},
    elements
  };
}
