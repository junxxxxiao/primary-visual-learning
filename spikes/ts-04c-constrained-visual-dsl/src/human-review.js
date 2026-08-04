import { renderScenePreview } from "./compiler.js";

const RUN_LABEL = "official-dsl-calibration-round-1";
const DRAFT_KEY = `ts04c-v2-human-review:${RUN_LABEL}`;
const STATES = [
  ["initial", "起始"],
  ["key_process", "关键过程"],
  ["final", "最终"],
  ["paused", "暂停"],
  ["resumed", "恢复"],
  ["post_interaction", "交互后"],
  ["reduced_motion", "减少动画"],
  ["static_fallback", "静态降级"]
];
const VIEWPORTS = {
  phone: { kind: "phone", width: 390, height: 632 },
  tablet: { kind: "tablet", width: 1024, height: 728 }
};

const nodes = {
  alias: document.getElementById("reviewer-alias"),
  role: document.getElementById("reviewer-role"),
  reset: document.getElementById("reset-draft"),
  sampleList: document.getElementById("sample-list"),
  progressCount: document.getElementById("progress-count"),
  progressBar: document.getElementById("progress-bar"),
  samplePosition: document.getElementById("sample-position"),
  sceneTitle: document.getElementById("scene-title"),
  sampleId: document.getElementById("sample-id"),
  previous: document.getElementById("previous-sample"),
  next: document.getElementById("next-sample"),
  stateTabs: document.getElementById("state-tabs"),
  visitedCount: document.getElementById("visited-count"),
  phoneCanvas: document.getElementById("phone-canvas"),
  tabletCanvas: document.getElementById("tablet-canvas"),
  learningGoal: document.getElementById("learning-goal"),
  narration: document.getElementById("narration"),
  candidateLabels: document.getElementById("candidate-labels"),
  claims: document.getElementById("claims"),
  form: document.getElementById("review-form"),
  critical: document.getElementById("critical-error"),
  notes: document.getElementById("review-notes"),
  completion: document.getElementById("completion-message"),
  draft: document.getElementById("draft-message"),
  submit: document.getElementById("submit-review"),
  dialog: document.getElementById("result-dialog"),
  resultTitle: document.getElementById("result-title"),
  resultMessage: document.getElementById("result-message"),
  closeDialog: document.getElementById("close-dialog")
};

let candidates = [];
let sourceById = new Map();
let currentIndex = 0;
let currentState = "initial";
let draft = { reviewer_alias: "reviewer-01", reviewer_role: "product_visual", reviews: {} };

function blankReview() {
  return { teaching: null, visual: null, state_integrity: null, critical_error: false, notes: "", visited_states: [] };
}

function reviewFor(sampleId) {
  draft.reviews[sampleId] ||= blankReview();
  return draft.reviews[sampleId];
}

function isComplete(review) {
  return [review.teaching, review.visual, review.state_integrity].every(Boolean) && review.visited_states.length === STATES.length;
}

function saveDraft() {
  draft.reviewer_alias = nodes.alias.value.trim();
  draft.reviewer_role = nodes.role.value;
  localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  nodes.draft.textContent = "草稿已保存在本浏览器";
  updateProgress();
}

function restoreDraft() {
  try {
    const stored = JSON.parse(localStorage.getItem(DRAFT_KEY));
    if (stored?.reviews) draft = stored;
  } catch (_error) {
    localStorage.removeItem(DRAFT_KEY);
  }
  nodes.alias.value = draft.reviewer_alias || "reviewer-01";
  nodes.role.value = draft.reviewer_role || "product_visual";
}

function updateProgress() {
  const completed = candidates.filter(entry => isComplete(reviewFor(entry.spec.sample_id))).length;
  const percent = candidates.length ? completed / candidates.length * 100 : 0;
  nodes.progressCount.textContent = `${completed} / ${candidates.length} 已完成`;
  nodes.progressBar.style.width = `${percent}%`;
  nodes.completion.textContent = completed === candidates.length ? "全部场景已完成，可以提交" : `还需完成 ${candidates.length - completed} 个场景`;
  nodes.submit.disabled = completed !== candidates.length || !/^[A-Za-z0-9._-]{1,40}$/.test(nodes.alias.value.trim());
  renderSampleList();
}

function renderSampleList() {
  nodes.sampleList.replaceChildren();
  candidates.forEach((entry, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `sample-button${isComplete(reviewFor(entry.spec.sample_id)) ? " done" : ""}`;
    button.setAttribute("aria-current", String(index === currentIndex));
    const number = document.createElement("span");
    number.className = "sample-number";
    number.textContent = String(index + 1).padStart(2, "0");
    const copy = document.createElement("span");
    copy.className = "sample-copy";
    const title = document.createElement("strong");
    title.textContent = entry.spec.title;
    const meta = document.createElement("span");
    meta.textContent = entry.spec.scene_type;
    copy.append(title, meta);
    button.append(number, copy);
    button.addEventListener("click", () => selectSample(index));
    nodes.sampleList.append(button);
  });
}

function renderStates() {
  const review = reviewFor(candidates[currentIndex].spec.sample_id);
  nodes.stateTabs.replaceChildren();
  for (const [state, label] of STATES) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `state-tab${review.visited_states.includes(state) ? " visited" : ""}`;
    button.role = "tab";
    button.setAttribute("aria-selected", String(state === currentState));
    button.textContent = label;
    button.addEventListener("click", () => {
      currentState = state;
      markVisited();
      renderScene();
    });
    nodes.stateTabs.append(button);
  }
  nodes.visitedCount.textContent = `已查看 ${review.visited_states.length} / ${STATES.length}`;
}

function markVisited() {
  const review = reviewFor(candidates[currentIndex].spec.sample_id);
  if (!review.visited_states.includes(currentState)) review.visited_states.push(currentState);
  saveDraft();
}

function renderEvidence(source, spec) {
  nodes.learningGoal.textContent = source.learning_goal;
  nodes.narration.textContent = source.narration;
  nodes.candidateLabels.textContent = spec.labels.join(" · ");
  nodes.claims.replaceChildren();
  for (const claim of source.claims) {
    const row = document.createElement("div");
    row.className = "claim-row";
    const id = document.createElement("strong");
    id.textContent = claim.claim_id;
    const text = document.createElement("p");
    text.textContent = claim.text;
    const terms = document.createElement("span");
    terms.textContent = `核对词：${claim.supported_terms.join("、")}`;
    row.append(id, text, terms);
    nodes.claims.append(row);
  }
}

function renderForm() {
  const review = reviewFor(candidates[currentIndex].spec.sample_id);
  for (const field of ["teaching", "visual", "state_integrity"]) {
    for (const input of nodes.form.elements[field]) input.checked = input.value === review[field];
  }
  nodes.critical.checked = review.critical_error;
  nodes.notes.value = review.notes;
}

function renderScene() {
  const entry = candidates[currentIndex];
  const source = sourceById.get(entry.spec.sample_id);
  nodes.samplePosition.textContent = `场景 ${currentIndex + 1} / ${candidates.length}`;
  nodes.sceneTitle.textContent = entry.spec.title;
  nodes.sampleId.textContent = entry.spec.sample_id;
  nodes.previous.disabled = currentIndex === 0;
  nodes.next.disabled = currentIndex === candidates.length - 1;
  renderScenePreview(nodes.phoneCanvas, entry.spec, VIEWPORTS.phone, currentState);
  renderScenePreview(nodes.tabletCanvas, entry.spec, VIEWPORTS.tablet, currentState);
  renderEvidence(source, entry.spec);
  renderForm();
  renderStates();
  updateProgress();
}

function selectSample(index) {
  currentIndex = Math.max(0, Math.min(candidates.length - 1, index));
  currentState = "initial";
  markVisited();
  renderScene();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function submitReview() {
  nodes.submit.disabled = true;
  nodes.submit.textContent = "正在保存";
  const reviews = candidates.map(entry => ({ sample_id: entry.spec.sample_id, ...reviewFor(entry.spec.sample_id) }));
  try {
    const response = await fetch("/api/ts04c-v2-human-review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_label: RUN_LABEL,
        reviewer_role: nodes.role.value,
        reviewer_alias: nodes.alias.value.trim(),
        reviews
      })
    });
    if (!response.ok) throw new Error(`保存失败：HTTP ${response.status}`);
    const result = await response.json();
    nodes.resultTitle.textContent = result.threshold_pass ? "本份评审达到门槛" : "本份评审未达到门槛";
    nodes.resultMessage.textContent = `通过 ${result.pass_count} / 10，严重错误 ${result.critical_error_count} 个。结果已保存为 ${result.result_file}。还需结合另一评审角色的结果，才能推进切片状态。`;
    nodes.dialog.showModal();
  } catch (error) {
    nodes.resultTitle.textContent = "评审保存失败";
    nodes.resultMessage.textContent = String(error.message || error);
    nodes.dialog.showModal();
  } finally {
    nodes.submit.textContent = "提交本轮评审";
    updateProgress();
  }
}

async function main() {
  const [candidateResponse, sourceResponse] = await Promise.all([
    fetch("./results/candidate-specs-official-dsl-calibration-round-1.json", { cache: "no-store" }),
    fetch("../ts-04c-real-visual-consistency/fixtures/calibration-inputs.json", { cache: "no-store" })
  ]);
  if (!candidateResponse.ok || !sourceResponse.ok) throw new Error("评审数据加载失败");
  const candidateData = await candidateResponse.json();
  const sourceData = await sourceResponse.json();
  candidates = candidateData.specs;
  sourceById = new Map(sourceData.samples.map(sample => [sample.sample_id, sample]));
  restoreDraft();
  nodes.previous.addEventListener("click", () => selectSample(currentIndex - 1));
  nodes.next.addEventListener("click", () => selectSample(currentIndex + 1));
  nodes.alias.addEventListener("input", saveDraft);
  nodes.role.addEventListener("change", saveDraft);
  nodes.form.addEventListener("change", event => {
    const review = reviewFor(candidates[currentIndex].spec.sample_id);
    if (event.target.matches('input[type="radio"]')) review[event.target.name] = event.target.value;
    if (event.target === nodes.critical) review.critical_error = nodes.critical.checked;
    saveDraft();
  });
  nodes.notes.addEventListener("input", () => {
    reviewFor(candidates[currentIndex].spec.sample_id).notes = nodes.notes.value;
    saveDraft();
  });
  nodes.submit.addEventListener("click", submitReview);
  nodes.reset.addEventListener("click", () => {
    if (!window.confirm("清空当前浏览器中的全部评审草稿？")) return;
    localStorage.removeItem(DRAFT_KEY);
    draft = { reviewer_alias: "reviewer-01", reviewer_role: "product_visual", reviews: {} };
    nodes.alias.value = draft.reviewer_alias;
    nodes.role.value = draft.reviewer_role;
    currentIndex = 0;
    currentState = "initial";
    markVisited();
    renderScene();
  });
  nodes.closeDialog.addEventListener("click", () => nodes.dialog.close());
  markVisited();
  renderScene();
}

main().catch(error => {
  nodes.sceneTitle.textContent = "评审工具加载失败";
  nodes.sampleId.textContent = String(error.stack || error);
});
