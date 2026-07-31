const OPERATORS = {
  gt: (left, right) => left > right,
  eq: (left, right) => left === right,
  lt: (left, right) => left < right,
};

function selectMeasuredObject(segment, selector) {
  const matches = segment.scene.objects.filter(object => (
    object.kind === selector.kind && object.style === selector.style
  ));
  if (matches.length !== 1) return null;
  const value = matches[0][selector.measure];
  return Number.isFinite(value) ? value : null;
}

export function validateRequiredVisualRelations(candidate, requirements) {
  const violations = [];
  for (const requirement of requirements) {
    const segment = candidate.segments[requirement.segment_ordinal - 1];
    const leftValue = segment ? selectMeasuredObject(segment, requirement.left) : null;
    const rightValue = segment ? selectMeasuredObject(segment, requirement.right) : null;
    const compare = OPERATORS[requirement.operator];
    if (!segment || !compare || leftValue === null || rightValue === null || !compare(leftValue, rightValue)) {
      const operandMissing = !segment || leftValue === null || rightValue === null;
      violations.push({
        relation_id: requirement.relation_id,
        claim_refs: [...requirement.claim_refs],
        segment_id: segment?.segment_id ?? null,
        code: operandMissing
          ? 'visual.required_relation_operand_missing'
          : 'visual.required_relation_mismatch',
        operator: requirement.operator,
        left_value: leftValue,
        right_value: rightValue,
      });
    }
  }
  return violations;
}
