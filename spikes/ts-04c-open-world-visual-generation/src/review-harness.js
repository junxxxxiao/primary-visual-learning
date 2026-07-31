import { renderTimelineScene, timelineDuration } from "./scene-renderer.js";

const VIEWPORTS = { phone: { kind: "phone", width: 390, height: 632 }, tablet: { kind: "tablet", width: 1024, height: 728 } };
const fixture = await fetch("./results/candidates-v4-flash-v03-example-guided.json", { cache: "no-store" }).then(response => response.json());
const candidateSelect = document.getElementById("candidate");
const canvas = document.getElementById("canvas");
const play = document.getElementById("play");
const progress = document.getElementById("progress");
const time = document.getElementById("time");
const beat = document.getElementById("beat");
const narration = document.getElementById("narration");
const severe = document.getElementById("severe");
const notes = document.getElementById("notes");
const reviews = JSON.parse(localStorage.getItem("ts04c-v03-reviews") || "{}");
const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
let viewport = "phone";
let elapsed = 0;
let playing = false;
let lastFrame = 0;
let reducedMotion = reducedMotionQuery.matches;
let activeSampleId = fixture.entries[0].sample_id;

for (const [index, entry] of fixture.entries.entries()) {
  const option = document.createElement("option");
  option.value = String(index); option.textContent = `${index + 1}. ${entry.question}`;
  candidateSelect.append(option);
}

function entry() { return fixture.entries[Number(candidateSelect.value || 0)]; }
function formatTime(ms) { const seconds = Math.floor(ms / 1000); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`; }
function saveReview() {
  const selected = document.querySelector("[data-rating][aria-pressed='true']");
  reviews[activeSampleId] = { sample_id: activeSampleId, rating: selected?.dataset.rating || null, severe_error: severe.checked, notes: notes.value };
  localStorage.setItem("ts04c-v03-reviews", JSON.stringify(reviews));
}
function loadReview() {
  const review = reviews[entry().sample_id] || {};
  document.querySelectorAll("[data-rating]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.rating === review.rating)));
  severe.checked = Boolean(review.severe_error); notes.value = review.notes || "";
}
function render() {
  const current = entry().candidate;
  const duration = timelineDuration(current);
  progress.max = String(duration); progress.value = String(Math.min(elapsed, duration));
  const frame = renderTimelineScene(canvas, current, elapsed, VIEWPORTS[viewport], { reducedMotion });
  beat.textContent = `${frame.beat_index + 1} / ${current.timeline.beats.length}`;
  narration.textContent = current.timeline.beats[frame.beat_index].narration;
  time.textContent = `${formatTime(elapsed)} / ${formatTime(duration)}`;
}
function resetPlayback() { playing = false; elapsed = 0; lastFrame = 0; play.textContent = "▶"; play.title = "播放"; play.setAttribute("aria-label", "播放"); render(); }
function tick(now) {
  if (!playing) return;
  if (!lastFrame) lastFrame = now;
  elapsed += now - lastFrame; lastFrame = now;
  if (elapsed >= timelineDuration(entry().candidate)) { elapsed = timelineDuration(entry().candidate); playing = false; play.textContent = "▶"; }
  render();
  if (playing) requestAnimationFrame(tick);
}

reducedMotionQuery.addEventListener("change", event => {
  reducedMotion = event.matches;
  render();
});

play.addEventListener("click", () => {
  playing = !playing; lastFrame = 0; play.textContent = playing ? "❚❚" : "▶";
  play.title = playing ? "暂停" : "播放"; play.setAttribute("aria-label", play.title);
  if (playing) { if (elapsed >= timelineDuration(entry().candidate)) elapsed = 0; requestAnimationFrame(tick); }
});
progress.addEventListener("input", () => { elapsed = Number(progress.value); lastFrame = 0; render(); });
candidateSelect.addEventListener("change", () => { saveReview(); activeSampleId = entry().sample_id; resetPlayback(); loadReview(); });
document.querySelectorAll("[data-viewport]").forEach(button => button.addEventListener("click", () => {
  viewport = button.dataset.viewport;
  document.querySelectorAll("[data-viewport]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
  render();
}));
document.querySelectorAll("[data-rating]").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll("[data-rating]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
  saveReview();
}));
severe.addEventListener("change", saveReview); notes.addEventListener("change", saveReview);
document.getElementById("next").addEventListener("click", () => {
  saveReview(); candidateSelect.value = String((Number(candidateSelect.value) + 1) % fixture.entries.length); activeSampleId = entry().sample_id; resetPlayback(); loadReview();
});
document.getElementById("export").addEventListener("click", () => {
  saveReview();
  const payload = { artifact_kind: "human_review_draft", prompt_profile: fixture.prompt_profile, reviews: fixture.entries.map(item => reviews[item.sample_id] || { sample_id: item.sample_id, rating: null, severe_error: false, notes: "" }) };
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  link.download = "ts04c-v03-human-review-draft.json"; link.click(); URL.revokeObjectURL(link.href);
});

loadReview(); render();
