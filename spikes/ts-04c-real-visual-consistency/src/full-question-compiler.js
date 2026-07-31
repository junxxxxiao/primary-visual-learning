const SOURCE_BOUNDS = {left: 60, top: 60, right: 940, bottom: 620};
const OBJECT_KINDS = new Set(['tank', 'ellipse', 'particles', 'arrow', 'label', 'meter']);
const PROPERTIES = new Set(['opacity', 'x', 'y', 'scale']);

function finite(value, label) {
  if (!Number.isFinite(value)) throw new Error(`${label} must be finite`);
}

function compileObject(object, segmentId) {
  if (!object || !/^[a-z0-9][a-z0-9._-]{0,95}$/.test(object.id || '')) throw new Error(`${segmentId}: invalid object id`);
  if (!OBJECT_KINDS.has(object.kind)) throw new Error(`${segmentId}: unsupported object kind ${object.kind}`);
  for (const key of ['x', 'y', 'width', 'height']) finite(object[key], `${segmentId}.${object.id}.${key}`);
  const bounds = {
    left: object.x - object.width / 2,
    right: object.x + object.width / 2,
    top: object.y - object.height / 2,
    bottom: object.y + object.height / 2,
  };
  if (bounds.left < SOURCE_BOUNDS.left || bounds.right > SOURCE_BOUNDS.right || bounds.top < SOURCE_BOUNDS.top || bounds.bottom > SOURCE_BOUNDS.bottom) {
    throw new Error(`${segmentId}.${object.id}: source bounds exceed safe region`);
  }
  return {...object, source_bounds: bounds};
}

function compileSegment(segment) {
  const objects = segment.scene.objects.map(object => compileObject(object, segment.segment_id));
  const objectIds = new Set(objects.map(object => object.id));
  if (objectIds.size !== objects.length) throw new Error(`${segment.segment_id}: duplicate object id`);
  const timeline = segment.scene.timeline.map(action => {
    if (!objectIds.has(action.target_id)) throw new Error(`${segment.segment_id}: unknown timeline target ${action.target_id}`);
    if (!PROPERTIES.has(action.property)) throw new Error(`${segment.segment_id}: unsupported property ${action.property}`);
    if (action.start_ms < 1000 || action.end_ms <= action.start_ms || action.end_ms > segment.duration_ms) throw new Error(`${segment.segment_id}: invalid timeline range`);
    finite(action.from, `${segment.segment_id}.${action.target_id}.from`);
    finite(action.to, `${segment.segment_id}.${action.target_id}.to`);
    const target = objects.find(object => object.id === action.target_id);
    if (action.property === 'x' && (action.to - target.width / 2 < SOURCE_BOUNDS.left || action.to + target.width / 2 > SOURCE_BOUNDS.right)) {
      throw new Error(`${segment.segment_id}.${target.id}: x motion envelope exceeds safe region`);
    }
    if (action.property === 'y' && (action.to - target.height / 2 < SOURCE_BOUNDS.top || action.to + target.height / 2 > SOURCE_BOUNDS.bottom)) {
      throw new Error(`${segment.segment_id}.${target.id}: y motion envelope exceeds safe region`);
    }
    if (action.property === 'scale') {
      const maxScale = Math.max(action.from, action.to);
      if (target.x - target.width * maxScale / 2 < SOURCE_BOUNDS.left || target.x + target.width * maxScale / 2 > SOURCE_BOUNDS.right || target.y - target.height * maxScale / 2 < SOURCE_BOUNDS.top || target.y + target.height * maxScale / 2 > SOURCE_BOUNDS.bottom) {
        throw new Error(`${segment.segment_id}.${target.id}: scale motion envelope exceeds safe region`);
      }
    }
    return {...action};
  });
  return {...segment, scene: {objects, timeline}};
}

export function compileFullQuestion(candidate) {
  if (!candidate || candidate.schema_version !== 'full-question-lesson/0.1') throw new Error('unsupported full-question schema');
  if (!Array.isArray(candidate.segments) || candidate.segments.length !== 4) throw new Error('exactly four segments are required');
  const segments = candidate.segments.map(compileSegment);
  const segmentIds = new Set(segments.map(segment => segment.segment_id));
  if (segmentIds.size !== segments.length) throw new Error('duplicate segment id');
  return {...candidate, segments, total_duration_ms: segments.reduce((sum, segment) => sum + segment.duration_ms, 0)};
}

function ease(value) {
  const t = Math.min(1, Math.max(0, value));
  return t * t * (3 - 2 * t);
}

export function evaluateFullQuestionSegment(segment, elapsedMs, reducedMotion = false) {
  const objects = new Map(segment.scene.objects.map(object => [object.id, {...object, opacity: 1, scale: 1}]));
  for (const action of segment.scene.timeline) {
    const object = objects.get(action.target_id);
    let value;
    if (reducedMotion) value = elapsedMs >= action.end_ms ? action.to : action.from;
    else if (elapsedMs <= action.start_ms) value = action.from;
    else if (elapsedMs >= action.end_ms) value = action.to;
    else value = action.from + (action.to - action.from) * ease((elapsedMs - action.start_ms) / (action.end_ms - action.start_ms));
    object[action.property] = value;
  }
  return {objects: [...objects.values()], elapsed_ms: Math.min(segment.duration_ms, Math.max(0, elapsedMs))};
}

export const fullQuestionSourceBounds = SOURCE_BOUNDS;
