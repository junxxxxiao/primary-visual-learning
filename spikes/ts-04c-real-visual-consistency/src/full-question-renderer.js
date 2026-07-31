const COLORS = {
  ink: '#17212b', muted: '#65717c', paper: '#fffdf7', line: '#b9c3cc', water: '#a8d9f4',
  saltwater: '#74c6d4', egg: '#f2c66d', eggLine: '#ad7932', coral: '#ef6558', blue: '#397be5',
  green: '#2f9b72', paleGreen: '#def3e9', paleCoral: '#ffe8e5', white: '#ffffff', salt: '#f8fbff'
};

function viewportLayout(canvas, viewport) {
  if (viewport === 'phone') return {width: 760, height: 980, left: 56, top: 72, right: 704, bottom: 910};
  return {width: 1000, height: 680, left: 60, top: 60, right: 940, bottom: 620};
}

function mapObject(object, layout, viewport) {
  if (viewport !== 'phone') return {...object};
  const sourceWidth = 880;
  const sourceHeight = 560;
  const xScale = (layout.right - layout.left) / sourceWidth;
  const yScale = (layout.bottom - layout.top) / sourceHeight;
  return {
    ...object,
    x: layout.left + (object.x - 60) * xScale,
    y: layout.top + (object.y - 60) * yScale,
    width: object.width * xScale,
    height: object.height * (object.kind === 'tank' ? 1.28 : Math.min(1.08, yScale)),
  };
}

function roundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, Math.min(radius, width / 2, height / 2));
}

function fitText(ctx, text, bounds, options = {}) {
  let size = options.size || 24;
  const min = options.min || 14;
  ctx.font = `${options.weight || 700} ${size}px system-ui, sans-serif`;
  while (size > min && ctx.measureText(text).width > bounds.width) {
    size -= 1;
    ctx.font = `${options.weight || 700} ${size}px system-ui, sans-serif`;
  }
  ctx.fillStyle = options.color || COLORS.ink;
  ctx.textAlign = options.align || 'center';
  ctx.textBaseline = 'middle';
  const x = options.align === 'left' ? bounds.x : bounds.x + bounds.width / 2;
  ctx.fillText(text, x, bounds.y + bounds.height / 2, bounds.width);
  return size;
}

function drawTank(ctx, object) {
  const left = object.x - object.width / 2;
  const top = object.y - object.height / 2;
  const liquidTop = top + object.height * 0.16;
  ctx.fillStyle = object.style === 'saltwater' ? COLORS.saltwater : COLORS.water;
  ctx.globalAlpha *= 0.72;
  ctx.fillRect(left + 6, liquidTop, object.width - 12, object.height * 0.82);
  ctx.globalAlpha /= 0.72;
  ctx.strokeStyle = COLORS.ink;
  ctx.lineWidth = 5;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(left, top);
  ctx.lineTo(left, top + object.height);
  ctx.lineTo(left + object.width, top + object.height);
  ctx.lineTo(left + object.width, top);
  ctx.stroke();
  ctx.strokeStyle = object.style === 'saltwater' ? COLORS.green : COLORS.blue;
  ctx.lineWidth = 3;
  ctx.beginPath();
  for (let x = left + 8; x <= left + object.width - 8; x += 4) {
    const y = liquidTop + Math.sin((x - left) / 28) * 3;
    x === left + 8 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  fitText(ctx, object.label, {x: left + 20, y: top + object.height - 48, width: object.width - 40, height: 34}, {size: 22, color: COLORS.ink});
}

function drawEgg(ctx, object) {
  ctx.fillStyle = COLORS.egg;
  ctx.strokeStyle = COLORS.eggLine;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.ellipse(object.x, object.y, object.width / 2, object.height / 2, 0, 0, Math.PI * 2);
  ctx.fill(); ctx.stroke();
  fitText(ctx, object.label, {x: object.x - object.width / 2 + 8, y: object.y - 16, width: object.width - 16, height: 32}, {size: 20, min: 13});
}

function hash(value) {
  let result = 0;
  for (const character of value) result = (result * 31 + character.charCodeAt(0)) >>> 0;
  return result;
}

function drawParticles(ctx, object) {
  const count = 32;
  const left = object.x - object.width / 2;
  const top = object.y - object.height / 2;
  let seed = hash(object.id);
  ctx.fillStyle = COLORS.salt;
  ctx.strokeStyle = COLORS.blue;
  ctx.lineWidth = 1;
  for (let index = 0; index < count; index += 1) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const x = left + 12 + (seed % 1000) / 1000 * (object.width - 24);
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const y = top + 12 + (seed % 1000) / 1000 * (object.height - 24);
    ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
}

function drawArrow(ctx, object) {
  const up = object.style === 'force-up';
  const startY = object.y + (up ? object.height / 2 : -object.height / 2);
  const endY = object.y + (up ? -object.height / 2 : object.height / 2);
  const color = up ? COLORS.blue : COLORS.coral;
  ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = Math.max(7, object.width * 0.45); ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(object.x, startY); ctx.lineTo(object.x, endY); ctx.stroke();
  const direction = up ? -1 : 1;
  ctx.beginPath();
  ctx.moveTo(object.x, endY + direction * 2);
  ctx.lineTo(object.x - 14, endY - direction * 22);
  ctx.lineTo(object.x + 14, endY - direction * 22);
  ctx.closePath(); ctx.fill();
  fitText(ctx, object.label, {x: object.x + 24, y: object.y - 18, width: 104, height: 36}, {size: 22, align: 'left', color});
}

function drawLabel(ctx, object) {
  const bounds = {x: object.x - object.width / 2, y: object.y - object.height / 2, width: object.width, height: object.height};
  const highlight = object.style === 'highlight';
  roundedRect(ctx, bounds.x, bounds.y, bounds.width, bounds.height, 8);
  ctx.fillStyle = highlight ? COLORS.paleGreen : COLORS.white;
  ctx.strokeStyle = highlight ? COLORS.green : COLORS.line;
  ctx.lineWidth = 2; ctx.fill(); ctx.stroke();
  fitText(ctx, object.label, {x: bounds.x + 18, y: bounds.y + 6, width: bounds.width - 36, height: bounds.height - 12}, {size: 25, color: highlight ? COLORS.green : COLORS.ink});
}

function drawMeter(ctx, object) {
  const left = object.x - object.width / 2;
  const top = object.y - object.height / 2;
  const barWidth = Math.max(18, object.width * 0.24);
  const baseY = top + object.height - 44;
  const buoyancyHeight = object.height * 0.58;
  const weightHeight = object.height * 0.4;
  for (const [x, height, color] of [[left + object.width * 0.3, buoyancyHeight, COLORS.blue], [left + object.width * 0.7, weightHeight, COLORS.coral]]) {
    ctx.fillStyle = color;
    roundedRect(ctx, x - barWidth / 2, baseY - height, barWidth, height, 6); ctx.fill();
  }
  fitText(ctx, '浮', {x: left, y: baseY + 4, width: object.width / 2, height: 28}, {size: 17, color: COLORS.blue});
  fitText(ctx, '重', {x: left + object.width / 2, y: baseY + 4, width: object.width / 2, height: 28}, {size: 17, color: COLORS.coral});
  fitText(ctx, object.label, {x: left - 22, y: top - 36, width: object.width + 44, height: 30}, {size: 20, min: 13, color: COLORS.green});
}

function drawObject(ctx, object) {
  ctx.save();
  ctx.globalAlpha = Math.max(0, Math.min(1, object.opacity));
  ctx.translate(object.x, object.y);
  ctx.scale(object.scale, object.scale);
  ctx.translate(-object.x, -object.y);
  if (object.kind === 'tank') drawTank(ctx, object);
  else if (object.kind === 'ellipse') drawEgg(ctx, object);
  else if (object.kind === 'particles') drawParticles(ctx, object);
  else if (object.kind === 'arrow') drawArrow(ctx, object);
  else if (object.kind === 'label') drawLabel(ctx, object);
  else if (object.kind === 'meter') drawMeter(ctx, object);
  ctx.restore();
}

export function renderFullQuestionFrame(ctx, frame, options = {}) {
  const viewport = options.viewport === 'phone' ? 'phone' : 'tablet';
  const layout = viewportLayout(ctx.canvas, viewport);
  const objects = frame.objects.map(object => mapObject(object, layout, viewport));
  ctx.save();
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.lineJoin = 'round';
  for (const object of objects.filter(item => item.kind === 'tank')) drawObject(ctx, object);
  for (const object of objects.filter(item => item.kind !== 'tank' && item.kind !== 'label')) drawObject(ctx, object);
  for (const object of objects.filter(item => item.kind === 'label')) drawObject(ctx, object);
  ctx.restore();
  const elements = objects.filter(object => object.opacity > 0).map(object => {
    const scale = object.scale;
    const bounds = {x: object.x - object.width * scale / 2, y: object.y - object.height * scale / 2, width: object.width * scale, height: object.height * scale};
    if (object.kind === 'arrow') {
      bounds.width += 128;
      bounds.x -= 14;
    }
    if (object.kind === 'meter') {
      bounds.x -= 22;
      bounds.y -= 40;
      bounds.width += 44;
      bounds.height += 40;
    }
    return {id: object.id, kind: object.kind, bounds};
  });
  return {viewport, canvas_inner_bounds: {x: 0, y: 0, width: layout.width, height: layout.height}, elements};
}
