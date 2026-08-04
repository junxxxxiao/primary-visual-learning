# TS-07 Minimum-Cost Playback Timeline Audit Design

## Purpose

TS-07 will audit the existing mathematics and sound high-fidelity Demo instead of building another player.

The Demo already provides sufficient prototype evidence that fixed narration, subtitles, progressive visuals, current-segment progress, one-second lead-in, play/pause, seek, segment switching, reduced motion, audio fallback, and phone/tablet layouts can form a coherent child-facing experience. TS-07 will not repeat those product-flow or visual acceptance checks.

The remaining falsifiable question is narrower:

> In the existing Chrome Demo, do the real-audio timeline and its fallback preserve the required quantitative synchronization and position continuity under the smallest set of stress operations not covered by prior acceptance evidence?

This is a disposable audit slice. It does not turn `prototype/` into production code, select a production framework, or prove the full P0 chain because TS-04C is not merged into `origin/main` and its current recorded result is `fail`.

## Existing Evidence Accepted Without Retest

The audit accepts the following as fixed-Demo feasibility evidence:

- mathematics and sound use the same high-fidelity player implementation;
- repository narration files play in the browser;
- subtitles, visual reveals, and current-segment progress are projected from the active audio position;
- every segment presents its initial scene for one second before narration and animation advance;
- users can play, pause, resume, seek, and switch segments;
- seeking restores the visible text, diagram, and scene for the requested position;
- reduced motion preserves static information;
- the Demo has a visual clock fallback when narration cannot play;
- prior browser acceptance covered fixed phone, responsive phone, tablet/desktop layouts, overflow, controls, and complete mathematics and sound flows.

These observations prove only fixed-prototype feasibility. They are not reused as quantitative evidence and do not prove production reliability.

## Candidate And Authorization

- Candidate under test: the existing playback implementation in `prototype/sound-demo.html`.
- Browser: Google Chrome `150.0.7871.188` on the local macOS environment.
- Real media: `prototype/assets/audio/narration-math-1.wav`, PCM 44.1 kHz, 16-bit, mono, approximately 20.16 seconds.
- Invocation: local HTTP plus a same-origin audit harness driven through Playwright CLI.
- Fixed parameters: playback rate `1.0`; existing subtitle and visual cues; one pause/resume sample per run; seek targets 5, 10, and 15 seconds; ten repeated seek/switch operations; one forced media-failure handoff.
- Runs: one warm-up run followed by five measured real-audio runs and five measured degraded-clock runs.
- Viewport: one stable desktop audit viewport. Timing measurements are layout-independent, and prior phone/tablet acceptance is not repeated.
- Budget: zero external calls, zero new TTS calls, zero Token use, and zero external cost.
- Data boundary: repository audio and synthetic audit commands only; no child data, textbook files, credentials, or production logs.
- User confirmation: on 2026-08-04 the user approved the browser/audio candidate, then explicitly reduced TS-07 to minimum-cost testing that excludes questions already answered by the Demo.

## Approaches

### Selected: Black-Box Audit Of The Existing Demo

A same-origin audit page loads the real Demo, drives its public controls, observes the real audio element and rendered cue state, and emits measurements. The audit does not copy playback logic and does not change child-facing behavior.

This has the lowest cost and strongest relevance because the candidate under measurement is the artifact that already demonstrated feasibility.

### Rejected: Build A New Standalone Timeline Runtime

A new reducer, media adapter, and player would produce cleaner interfaces but would mostly repeat behavior already present in the Demo. Passing it would not prove the existing experience meets the timing gates.

### Rejected: Repeat Full Demo Acceptance

Re-running all mathematics/sound flows, phone/tablet layouts, reduced motion, overlays, and screenshots would consume time without answering a new technical question. Existing acceptance remains prototype evidence and its stated limitations remain unchanged.

## Public Audit Seam

The only new public seam is:

```text
window.ts07Audit.run(config) -> Promise<AuditResult>
```

The audit interacts with the Demo through rendered controls and browser media state. It may read:

- `HTMLAudioElement.currentTime`, duration, paused, ended, and error state;
- current subtitle text and visibility;
- current segment progress fill;
- visible visual cue state already rendered by the Demo;
- the Demo's explicit visual-fallback state;
- monotonic observation timestamps.

It must not call private Demo functions, duplicate cue calculations, mutate internal state directly, or determine correctness from screenshots alone.

The only fault-injection exception is replacing the browser audio element's source with a same-origin missing URL after playback has advanced. This exercises the Demo's existing public media-error listener without calling a private function or changing repository files.

## Four Measurements

### Cue Synchronization

During uninterrupted real-audio playback, observe each existing subtitle change and visual reveal. Compare the audio position at observation with the independently frozen expected cue position.

Report subtitle and visual deviation separately with sample count, P50, P80, P95, and maximum. The gate for both is P95 `< 250ms`.

### Pause And Resume Continuity

Pause through the visible player control, wait while the page remains active, and confirm that audio position, visible cue state, and progress do not advance. Resume through the same control and compare the resumed semantic position with the paused position.

Report position error P50, P80, P95, and maximum. The gate is P95 `< 250ms`, with zero cue rollback or clearing.

### Repeated Seek And Switch Drift

Use the visible current-segment controls to seek to 5, 10, and 15 seconds and repeat a fixed seek/switch pattern ten times. After every operation, compare requested and observed audio positions plus the rendered subtitle, visual state, and progress.

The gate is no increasing cumulative drift, final-position error `< 250ms`, and 100% consistent rendered state. The audit does not replay or test child interactions because the existing mathematics candidate has no enabled child interaction during playback.

### Audio-Failure Handoff

Force one reproducible media failure after playback has advanced, observe the last real-audio position, and verify that the existing visual fallback continues from that position rather than restarting or launching an unrelated timeline.

The gate is exactly one real-to-fallback transition, handoff error `< 250ms`, monotonic continuation, and no subtitle, visual, or progress rollback.

## Fixtures And Independence

Expected cue positions are frozen literals extracted once from the current authored cue table and stored in an audit fixture. The measurement code cannot import or recompute expected values from the implementation under test.

One deliberately wrong cue fixture and one deliberately discontinuous handoff fixture are `adversarial_fixture` self-tests. They must fail before candidate measurements are accepted. These synthetic self-tests prove only that the audit detects the target failures and do not enter the Chrome candidate denominator.

The real Demo observations are `candidate_output`. They record browser version, audio hash, Demo source hash, fixture hash, audit source hash, execution time, raw observations, aggregate metrics, failures, external usage, and cost.

## Files

```text
spikes/ts-07-unified-playback-timeline/
  README.md
  decisions.md
  audit-harness.html
  fixtures/audit-cues.json
  schemas/audit-result.schema.json
  src/audit.js
  tests/audit-self-test.html
  results/browser-candidate.json
  results/summary.json
```

The harness is an engineering audit surface, not a C-end page. It reuses the Demo and existing audio by reference and adds no product UI, duplicated player, generated narration, or production dependency.

## Evidence And Status Boundary

- Audit self-tests passing can establish only `harness_ready`.
- Completing the approved Chrome runs with hashes and raw observations can establish `candidate_run_complete`.
- TS-07 cannot advance to `human_review_complete`, `conditional_pass`, or `pass` until required review is recorded.
- Existing Demo acceptance evidence remains explicitly labeled as prototype evidence rather than candidate timing measurements.
- TS-04C remains a failed and unmerged dependency, so this audit cannot establish complete P0 readiness.
- Safari, WeChat WebView, real phones, background throttling, network buffering, low-end devices, long lessons, and production session isolation remain unverified.
- The audit does not change the PRD, current prototype behavior, high-fidelity design, architecture decision, data handling, or privacy boundary.

## Approved Fallback Remediation

On 2026-08-04 the user approved a minimal shared-player fix after the first candidate run consistently reproduced fallback reset.

- The existing player records the last valid `audio.currentTime / audio.duration` ratio and decoded duration while real audio is healthy.
- A media error hands that snapshot to the existing visual fallback instead of resetting `visualFallbackRatio` to zero.
- The fallback advances against the decoded segment duration. The existing 9-second default remains only for audio that never exposes valid metadata.
- Pausing and resuming an active fallback keeps its current ratio and duration; it does not reuse an older audio snapshot.
- The change stays in the one shared player used by mathematics, sound, and the vacuum topic. No preset receives a local timer or override.
- The formal retest runs only five fallback candidates because the normal-audio path is untouched and already has sealed round-one evidence. One sound-main and one vacuum-topic smoke check confirm shared coverage without entering the formal denominator.
- The existing visible-control and media-error boundary remains the public verification seam. No private playback function becomes a test API.

## Implementation Sequence

1. Freeze the existing cue expectations and hashes without changing the Demo.
2. Add the minimal same-origin audit seam and result schema.
3. Prove the audit fails the two adversarial self-tests.
4. Run one warm-up and five measured Chrome real-audio runs.
5. Run five measured forced-fallback runs.
6. Generate raw evidence, summary metrics, and a bounded decision.
7. Run only the new slice checks, relevant shared schema checks, source/hash checks, and the final `origin/main` ancestry check.
