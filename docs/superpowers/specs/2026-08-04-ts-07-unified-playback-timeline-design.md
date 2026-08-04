# TS-07 Unified Playback Timeline Design

## Purpose

TS-07 answers one falsifiable question:

> Can one problem-isolated browser runtime use a single authoritative timeline to keep real narration audio, subtitles, visual cues, and current-segment progress synchronized through play, pause, resume, seek, segment changes, background recovery, responsive layout changes, reduced motion, and audio failure?

This is a disposable technical slice, not production application code. It validates the playback runtime candidate only. It does not prove visual generation quality, learning efficacy, production reliability, or the complete P0 chain because TS-04C is not merged into `origin/main` and its current recorded decision is `fail`.

## Authorization And Candidate

- Candidate implementation: a browser-native unified timeline using `HTMLAudioElement.currentTime` as the authoritative clock while real audio is available and `performance.now()` as the continuity-preserving fallback clock after an explicit media failure.
- Browser and version: Google Chrome `150.0.7871.188` on the local macOS environment.
- Invocation: local HTTP browser harness driven through Playwright CLI; no hosted service or production endpoint.
- Fixed media: repository file `prototype/assets/audio/narration-math-1.wav`, PCM 44.1 kHz, 16-bit, mono, approximately 20.16 seconds.
- Fixed parameters: playback rate `1.0`; four subtitle cues; five visual cues; seeks to 5, 10, and 15 seconds; ten repeated switch/seek cycles; phone review viewport `390 x 844`; tablet viewport `768 x 1024`.
- Budget: zero external requests, zero new TTS requests, zero Token usage, and zero external cost.
- Data boundary: repository audio and synthetic timeline fixtures only; no child data, textbook files, credentials, production logs, or external services.
- User confirmation: on 2026-08-04 the user approved this candidate, environment, media, budget, and evidence boundary.

## Considered Approaches

### Audio-Authoritative Timeline

This is the selected approach. While audio is healthy, its decoded playback position is the only business time. All other outputs project from that position. On failure, the runtime records the last semantic position and continues with a monotonic fallback clock without creating a second lesson state.

This approach measures the behavior users actually experience, keeps the implementation small, and directly exercises browser media lifecycle behavior. Its precision is limited by browser media updates, so the runtime samples on animation frames and never treats `timeupdate` frequency as the clock.

### Web Audio Timeline

An `AudioContext` could offer a finer-grained clock, but it would add decoding, buffer management, autoplay, suspension, and lifecycle behavior that TS-07 does not need to answer its first question. It would also make the spike less representative of the repository's existing pre-generated file playback.

### Page-Timer Timeline

Using `performance.now()` during normal playback would simplify tests, but the audio would become a follower and could drift from the page timer under buffering or background throttling. That would weaken the candidate evidence, so this approach is rejected except as the declared media-failure fallback.

## Public Test Seams

Tests observe behavior only through two approved public interfaces:

```text
dispatchLessonCommand(session, command, clockSample) -> { session, events }
window.ts07Harness.runScenario(config) -> Promise<ScenarioResult>
```

`dispatchLessonCommand` is the state-transition seam. It accepts an immutable lesson session, a versioned command, and an explicit clock sample. It returns the next session and emitted events. Unit tests do not inspect private helpers or mutate internal adapter state.

`window.ts07Harness.runScenario` is the real-browser seam. It performs one fixed scenario through the same command interface used by the controls and returns machine-readable observations, spans, percentiles, boundary results, and pass/fail codes. Browser checks do not infer correctness from screenshots alone.

## Runtime Model

The slice has four focused components:

1. Lesson runtime: owns session identity, active segment, playback state, semantic timeline position, scene state, interaction state, capabilities, and snapshot version.
2. Clock adapters: sample either the real audio position or the monotonic fallback while presenting the same clock-sample contract to the runtime.
3. Cue projector: derives subtitle, visual cue, reduced-motion equivalent, and progress exclusively from `timeline_position`.
4. Measurement harness: executes fixed scenarios, records StageTiming-compatible spans and cue observations, computes metrics, and emits machine-readable results.

The session identity tuple is `session_id + question_id + lesson_plan_version`. Commands, media callbacks, animation frames, and restored snapshots must match the tuple before they can change state.

## State And Commands

The runtime uses these playback states:

```text
preparing
ready
playing
paused
seeking
switching
completed
degraded
failed
```

The command set is closed and versioned:

```text
prepare
play
pause
resume
seek
switch_segment
enter_background
return_foreground
media_failed
set_reduced_motion
set_viewport
tick
```

Every accepted transition records the command, identity tuple, previous and next state, previous and next timeline positions, clock source, monotonic observation time, and rejection reason when applicable. Unsupported commands and stale identities fail before mutation.

## Timeline Rules

- A segment always starts at semantic position `0` and holds its complete initial visual state for 1,000ms before narration, progress, and animated cues advance.
- During healthy playback, audio remains paused throughout the lead-in and `timeline_position` then follows the sampled audio position directly.
- Pausing snapshots the exact semantic position and projected scene. No cue can advance while paused.
- Resuming continues from the snapshot position; it cannot clear the scene, restart the segment, or replay already revealed cues.
- Seeking rebuilds subtitle, complete visual scene, and progress deterministically from the target semantic position.
- Child interaction results are a separate overlay on the generated scene state. Seeking can restore whether an interaction result was already retained but cannot synthesize or replay the child action.
- Segment switching creates a complete initial scene, waits the same 1,000ms lead-in, and then advances. Returning to a prior segment follows the same rule rather than resuming a hidden independent timer.
- Background entry pauses browser playback and records a semantic snapshot. Foreground return restores that snapshot before resuming.
- Responsive viewport changes only alter layout projection. Session identity, segment, position, cues, and interaction state remain unchanged.
- Reduced motion replaces motion with equivalent static states at the same cue boundaries. It cannot remove labels, relationships, or conclusions.
- A real-audio error emits `media_failed`, freezes the last audio-backed position, changes the clock source to fallback, and continues from that exact position in `degraded` state.

## Fixtures

The real-media candidate fixture uses `narration-math-1.wav` and a synthetic manifest with four subtitle cues and five visual cues distributed across its measured duration. Cue expectations are fixed literals in the fixture and are not computed by the implementation under test.

Gold fixtures cover normal playback, pause and resume, seeks to 5/10/15 seconds, segment switching and return, background and foreground recovery, phone/tablet layout changes, reduced motion, and real-audio failure followed by fallback continuation.

Adversarial fixtures cover stale session callbacks, stale lesson-plan callbacks, unsupported commands, duplicate delayed media events, ticks while paused, seek bounds, conflicting clocks, and attempts to replay child interactions after seek.

All fixture content is synthetic and labeled `gold_fixture` or `adversarial_fixture`. Only observations produced by Chrome with the approved runtime and real repository audio are candidate measurements. Synthetic fixture expectations do not enter a candidate capability denominator.

## Metrics And Gates

Each browser observation records expected semantic cue time, observed authoritative time, wall-clock observation time, clock source, viewport, motion mode, and absolute deviation.

The candidate gates are:

- normal subtitle cue deviation P95 `< 250ms`;
- normal visual cue deviation P95 `< 250ms`;
- pause/resume position error P95 `< 250ms`;
- ten switch/seek cycles produce no increasing cumulative drift and maximum final-position error `< 250ms`;
- seek rebuild matches the expected subtitle, complete visual state, and current-segment progress at 5, 10, and 15 seconds in 100% of cases;
- child actions are automatically replayed in 0 cases;
- stale identity events mutate the active session in 0 cases;
- phone and tablet runs preserve the same semantic state and have no horizontal overflow;
- reduced-motion runs preserve 100% of declared cue information;
- audio failure continues on the same session and semantic position with one explicit clock-source transition and no second business timeline;
- every scenario emits machine-readable `pass` or `fail` with violation codes and StageTiming-compatible spans.

Percentiles are calculated from raw per-observation measurements and reported with sample counts, P50, P80, P95, and maximum. Real-audio and degraded paths are reported separately. Harness self-tests and Chrome candidate results are never combined into one denominator.

## Browser And Layout Verification

The harness is served over local HTTP. It presents a restrained test surface containing the current segment label, subtitle, visual cue states, progress, clock source, play control, and seek control. The surface exists to expose runtime behavior, not to become a product page or replace the current prototype.

Chrome runs both fixed review viewports:

- phone: `390 x 844`;
- tablet: `768 x 1024`.

For both viewports the runner records viewport dimensions, document `scrollWidth/clientWidth`, critical control bounding boxes, timeline state before and after layout changes, and scenario results. Screenshots are supporting evidence only. Numeric runtime observations and boundary results determine pass/fail.

## Result Artifacts

The slice will contain:

```text
spikes/ts-07-unified-playback-timeline/
  README.md
  decisions.md
  browser-harness.html
  fixtures/
  schemas/
  src/
  tests/
  results/summary.json
  results/browser-candidate.json
```

`results/summary.json` separates harness self-test results from candidate measurements. The candidate record includes browser version, operating system, audio hash, runtime code hash, execution time, sample counts, percentiles, failure examples, external usage, cost, and any unavailable field marked `unverified`.

## Evidence And Decision Boundary

Passing deterministic tests may establish only `harness_ready`. Completing the approved Chrome runs with traceable real audio may establish `candidate_run_complete`. TS-07 cannot advance to `human_review_complete`, `conditional_pass`, or `pass` until the required review is recorded.

Even if all TS-07 candidate gates pass, the decision must state that:

- TS-04C is not in the branch baseline and its current candidate decision is `fail`;
- synthetic visual cues validate timeline projection but not generated-scene quality;
- no production framework, media library, persistence mechanism, or deployment architecture is selected;
- the PRD, current prototype, and high-fidelity design are not changed by this isolated slice;
- real mobile Safari, WeChat WebView, low-end devices, network buffering, long lessons, and production concurrency remain unverified;
- no child data, credentials, external requests, or new paid media generation are involved.

## Implementation Sequence

1. Add schemas and fixed fixtures for sessions, commands, cue manifests, scenario results, and StageTiming spans.
2. Implement one public state-transition seam through red/green cycles for identity rejection, play/pause/resume, seek rebuild, switching, background recovery, reduced motion, viewport changes, and degradation.
3. Add the real browser harness using the same command seam and the fixed repository audio.
4. Add independent harness self-tests for known good and adversarial fixtures.
5. Run Chrome candidate scenarios for real audio and degraded clocks on phone and tablet.
6. Generate raw candidate evidence, aggregate metrics, `summary.json`, and `decisions.md` without overstating the allowed status.
7. Run slice tests, shared schema/provenance tests, link checks relevant to the new directory, and the final `origin/main` ancestry check.
