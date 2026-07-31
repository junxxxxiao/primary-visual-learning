# TS-06A Progressive Segment Runtime Design

## Purpose

TS-06A answers one falsifiable question:

> Can a deterministic offline runtime accept independently prepared lesson segments, preserve session and manifest isolation, overlap visual and audio preparation, and produce correct playback, cancellation, timeout, and fallback events without bypassing knowledge, visual, or cache admission gates?

This slice validates protocol and orchestration behavior only. It does not call a model, TTS provider, browser renderer, or external service. Passing its deterministic fixtures advances the slice only to `harness_ready`; it is not candidate evidence for latency, quality, cost, or production readiness.

## Scope

The slice owns:

- versioned lesson manifest, segment envelope, and segment event contracts;
- deterministic virtual-time scheduling;
- segment admission and playback ordering;
- visual and audio preparation overlap;
- cancellation, timeout, stale-response, cache, and fallback behavior;
- StageTiming-compatible traces and aggregate metrics;
- gold and adversarial fixtures that prove the harness detects known violations.

The slice does not own:

- lesson content generation or educational quality (TS-03);
- visual generation, rendering, safety, or layout correctness (TS-04A/B/C);
- real TTS, subtitles, media clocks, cue drift, pause, resume, or seek (TS-07);
- real provider concurrency, billing, throughput, or production recovery (TS-06/TS-12);
- UI or a browser playback demo.

## Considered Approaches

### Static event validation

Schema validation and event-list replay would be small, but it could not prove critical-path timing, concurrent readiness, cancellation races, or timeout transitions.

### Deterministic virtual-time runtime

This is the selected approach. A virtual clock and fixture-defined work completions make concurrency and failure behavior reproducible without external dependencies. It is sufficient to test protocol semantics while keeping provider performance outside the evidence boundary.

### Browser-integrated demo

A browser player would look closer to the product, but it would mix TS-07 playback and TS-04C rendering into this slice and make failures harder to attribute.

## Contracts

### `lesson-manifest/1.0`

The manifest identifies one problem-level lesson session and fixes the ordered segment set. It includes:

- `session_id`, `lesson_id`, `manifest_version`, and `manifest_hash`;
- `knowledge_package_hash` and verification status;
- ordered segment descriptors with stable `segment_id`, `segment_version`, and ordinal;
- dependency identifiers for segments that cannot be admitted independently;
- creation metadata and an explicit synthetic fixture marker for this slice.

The hash is computed over a canonical representation excluding the hash field itself. A manifest version change creates a new identity; events from the previous version become stale.

### `segment-envelope/1.0`

Each envelope is independently validatable and contains:

- the full session, lesson, manifest, and segment identity tuple;
- segment ordinal and dependency list;
- narration text and ordered cue declarations;
- visual artifact reference and its TS-04B admission result reference;
- audio artifact reference and readiness status;
- cache identity and knowledge provenance references;
- static fallback reference;
- envelope hash and production timestamp represented in virtual time.

The offline harness treats visual, audio, and provenance references as opaque synthetic artifacts. It validates identity, readiness, and gate outcomes but does not claim those upstream gates actually ran.

### `segment-event/1.0`

Events use a closed event type set:

```text
lesson_open
manifest_ready
segment_ready
visual_ready
audio_ready
segment_admitted
segment_playable
segment_started
segment_completed
lesson_complete
fallback
cancelled
```

Every event includes an event ID, trace ID, identity tuple, virtual monotonic offset, attempt number, cache status, and event-specific payload. Events are idempotent by event ID and semantic identity. Unknown event types or invalid identity tuples fail before state mutation.

## Runtime Model

The runtime has four focused components:

1. Contract validator: validates schemas, hashes, identity tuples, and allowed transitions.
2. Virtual clock: executes fixture work items in deterministic time and stable tie-break order.
3. Segment orchestrator: owns session state, readiness joins, admission, playback order, cancellation, and fallback.
4. Metrics reporter: emits StageTiming traces and computes wall-clock milestones from the shared monotonic clock.

A segment becomes `playable` only when its envelope, visual readiness, audio readiness, provenance identity, and admission result all pass. Readiness events may arrive in any order. Playback remains ordered by manifest ordinal even if later segments become ready first. Only one terminal result is allowed per segment and per lesson.

Parallel preparation uses a join rather than summed durations:

```text
segment_playable = max(segment_ready, visual_ready, audio_ready, admission_ready)
```

The reporter must derive end-to-end latency from milestone offsets. It must never add overlapping span durations to claim wall-clock latency.

## Failure Semantics

- Duplicate event: accepted as an idempotent no-op only when the payload hash matches; conflicting duplicates fail.
- Out-of-order readiness: retained until prerequisites arrive; it cannot start playback early.
- Missing event: the configured virtual deadline produces a machine-readable timeout and fallback.
- Cross-session or manifest mismatch: rejected before state mutation.
- Superseded manifest: all later events for the old version are stale and ignored with an audit result.
- Cancellation: cancels pending work and prevents later responses from becoming playable or cache-admitted.
- Late response after cancellation or fallback: recorded as stale, with no playback or valid cache write.
- Failed visual/provenance admission: prevents `segment_admitted` and uses the declared static fallback.
- Lesson hard deadline: a trace still not playable at 45,000ms emits exactly one fallback terminal event.

## Fixture Matrix

Gold fixtures cover:

- full-plan serial preparation;
- first-segment-independent preparation;
- segment streaming with serial visual and audio work;
- segment streaming with visual and audio work in parallel;
- cache hit for a valid versioned segment;
- later segment ready before the current segment;
- successful segment fallback followed by continuation where allowed.

Adversarial fixtures cover:

- duplicate and conflicting duplicate events;
- readiness and completion events in invalid order;
- missing audio, visual, envelope, or admission result;
- cross-session and cross-manifest contamination;
- manifest hash and segment version mismatch;
- cancellation followed by a late provider result;
- timeout followed by a late result;
- attempted cache write after rejection or cancellation;
- overlapping spans whose durations would be incorrectly summed;
- a trace reaching the 45-second hard deadline.

All fixtures are synthetic `gold_fixture` or `adversarial_fixture`. None are `candidate_output`, and none count toward a candidate evaluation denominator.

## Metrics and Gates

The harness reports:

- `question_confirmed -> manifest_ready`;
- `question_confirmed -> first_segment_ready`;
- `question_confirmed -> first_visual_ready`;
- `question_confirmed -> first_audio_ready`;
- `question_confirmed -> first_meaningful_content`;
- `question_confirmed -> first_segment_playable`;
- `question_confirmed -> interactive_ready`;
- `question_confirmed -> fallback_ready`;
- accepted, rejected, duplicate, stale, cancelled, degraded, and cache events;
- scheduled concurrency and critical-path wall-clock duration.

Harness gates are:

- 100% of valid gold fixtures reach their expected terminal state;
- 100% of known invalid transitions and identity violations are rejected before state mutation;
- zero cross-session or superseded-manifest events affect playback or valid cache state;
- every accepted segment starts at most once and only in manifest order;
- every cancellation, timeout, and hard-deadline fixture produces exactly the expected terminal event;
- no rejected, cancelled, stale, or degraded candidate writes a valid cache entry;
- parallel wall-clock metrics equal the virtual critical path rather than the sum of overlapping spans;
- every fixture produces a schema-valid StageTiming trace and machine-readable pass/fail result.

The product targets of first meaningful content P80 under 8 seconds, a fresh interactive scene P80 under 30 seconds, and 45-second fallback coverage remain TS-06 candidate gates. TS-06A may test their calculation and deadline mechanics with synthetic times, but may not claim those performance targets are met.

## Files and Execution

The slice will contain:

```text
spikes/ts-06a-progressive-segment-runtime/
  README.md
  decisions.md
  fixtures/
  schemas/
  src/
  tests/
  results/summary.json
```

It will run with the repository's existing Python standard-library pattern and the available JSON Schema validator if already used by adjacent slices. The main command will execute all deterministic fixtures, validate emitted artifacts, and rewrite `results/summary.json` reproducibly.

## Evidence and Decision

The decision record will state:

- status `harness_ready` when all offline gates pass;
- no candidate provider, model, service version, Token usage, external cost, or real latency was tested;
- synthetic fixtures prove only the protocol and harness behavior;
- PRD and high-fidelity behavior remain unchanged;
- the architecture may adopt the contracts only after TS-03/04C/07 candidate integrations validate them;
- no child data, textbook content, credentials, production logs, or external requests are involved.

## Implementation Sequence

1. Add schemas and canonical examples.
2. Implement validation, virtual clock, state transitions, and metrics.
3. Add gold and adversarial fixtures.
4. Add unit and end-to-end harness tests.
5. Generate deterministic results and record the `harness_ready` decision.
6. Run slice tests, shared provenance tests, and repository link/status checks relevant to the new directory.
