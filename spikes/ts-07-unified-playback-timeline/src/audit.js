(function installTs07Audit(global) {
  'use strict';

  function percentile(values, percentileValue) {
    if (!values.length) return null;
    const sorted = [...values].sort((left, right) => left - right);
    if (sorted.length === 1) return sorted[0];
    const index = (sorted.length - 1) * percentileValue;
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    if (lower === upper) return sorted[lower];
    return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
  }

  function summarize(values) {
    return {
      count: values.length,
      p50_ms: percentile(values, 0.5),
      p80_ms: percentile(values, 0.8),
      p95_ms: percentile(values, 0.95),
      max_ms: values.length ? Math.max(...values) : null
    };
  }

  function linearSlope(values) {
    if (values.length < 2) return 0;
    const xMean = (values.length - 1) / 2;
    const yMean = values.reduce((sum, value) => sum + value, 0) / values.length;
    let numerator = 0;
    let denominator = 0;
    values.forEach((value, index) => {
      numerator += (index - xMean) * (value - yMean);
      denominator += (index - xMean) ** 2;
    });
    return denominator ? numerator / denominator : 0;
  }

  function evaluate(config) {
    const thresholds = config.thresholds || {};
    const measurements = config.measurements || {};
    const subtitle = measurements.subtitleCueDeviationsMs || [];
    const visual = measurements.visualCueDeviationsMs || [];
    const pauseResume = measurements.pauseResumeErrorsMs || [];
    const seekErrors = measurements.seekErrorsMs || [];
    const switchOffsets = measurements.switchOffsetsMs || [];
    const switchErrors = switchOffsets.map(Math.abs);
    const handoffs = measurements.fallbackHandoffs || [];
    const fallbackTransitionCounts = measurements.fallbackTransitionCounts || [];
    const durationMs = config.durationMs || 1000;
    const handoffErrors = handoffs.map(item => Math.abs(item.afterRatio - item.beforeRatio) * durationMs);
    const metrics = {
      subtitle_cues: summarize(subtitle),
      visual_cues: summarize(visual),
      pause_resume: summarize(pauseResume),
      seek: {
        ...summarize(seekErrors),
        final_error_ms: seekErrors.length ? seekErrors[seekErrors.length - 1] : null,
        cumulative_drift_ms: seekErrors.length > 1 ? seekErrors[seekErrors.length - 1] - seekErrors[0] : 0,
        rendered_state_consistent: measurements.seekRenderedStateConsistent !== false
      },
      switch: {
        ...summarize(switchErrors),
        drift_slope_ms_per_operation: linearSlope(switchErrors),
        rendered_state_consistent: measurements.switchRenderedStateConsistent !== false,
        segment_consistent: measurements.switchSegmentConsistent !== false
      },
      fallback_handoffs: {
        ...summarize(handoffErrors),
        monotonic: measurements.fallbackMonotonic !== false,
        state_rollback: measurements.fallbackStateRollback === true,
        transition_counts: fallbackTransitionCounts,
        exactly_one_transition: fallbackTransitionCounts.length === 0 || fallbackTransitionCounts.every(count => count === 1)
      }
    };
    const violations = [];
    if (metrics.subtitle_cues.p95_ms !== null && metrics.subtitle_cues.p95_ms >= thresholds.cueP95MsExclusive) {
      violations.push('cue.subtitle_p95_exceeded');
    }
    if (metrics.visual_cues.p95_ms !== null && metrics.visual_cues.p95_ms >= thresholds.cueP95MsExclusive) {
      violations.push('cue.visual_p95_exceeded');
    }
    if (metrics.pause_resume.p95_ms !== null && metrics.pause_resume.p95_ms >= thresholds.pauseResumeP95MsExclusive) {
      violations.push('transport.pause_resume_p95_exceeded');
    }
    if (metrics.seek.max_ms !== null && metrics.seek.max_ms >= thresholds.seekFinalErrorMsExclusive) {
      violations.push('transport.seek_final_error_exceeded');
    }
    if (!metrics.seek.rendered_state_consistent) violations.push('transport.seek_state_inconsistent');
    if (metrics.switch.max_ms !== null && metrics.switch.max_ms >= thresholds.seekFinalErrorMsExclusive) {
      violations.push('transport.switch_error_exceeded');
    }
    if (metrics.switch.drift_slope_ms_per_operation > 0) {
      violations.push('transport.switch_drift_increasing');
    }
    if (!metrics.switch.rendered_state_consistent) violations.push('transport.switch_state_inconsistent');
    if (!metrics.switch.segment_consistent) violations.push('transport.switch_segment_inconsistent');
    if (metrics.fallback_handoffs.p95_ms !== null && metrics.fallback_handoffs.p95_ms >= thresholds.handoffErrorMsExclusive) {
      violations.push('fallback.handoff_error_exceeded');
    }
    if (!metrics.fallback_handoffs.monotonic) violations.push('fallback.not_monotonic');
    if (metrics.fallback_handoffs.state_rollback) violations.push('fallback.state_rollback');
    if (!metrics.fallback_handoffs.exactly_one_transition) violations.push('fallback.transition_count_invalid');
    return { pass: violations.length === 0, violationCodes: violations, metrics };
  }

  function sleep(milliseconds) {
    return new Promise(resolve => setTimeout(resolve, milliseconds));
  }

  async function waitFor(predicate, timeoutMs, label) {
    const startedAt = performance.now();
    while (performance.now() - startedAt < timeoutMs) {
      const value = predicate();
      if (value) return value;
      await sleep(20);
    }
    throw new Error(`Timed out waiting for ${label}`);
  }

  function nextFrame(targetWindow) {
    return new Promise(resolve => targetWindow.requestAnimationFrame(() => resolve()));
  }

  async function loadDemo(frame, runId) {
    const loaded = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Timed out loading Demo frame')), 10000);
      frame.addEventListener('load', () => {
        clearTimeout(timeout);
        resolve();
      }, { once: true });
    });
    frame.src = `/prototype/sound-demo.html?screen=intro&preset=math&ts07_run=${encodeURIComponent(runId)}`;
    await loaded;
    const targetWindow = frame.contentWindow;
    const document = frame.contentDocument;
    const audio = document.querySelector('#demo-audio');
    await waitFor(() => audio && audio.readyState >= 1, 5000, 'audio metadata');
    await waitFor(() => !audio.paused && audio.currentTime > 0.01, 5000, 'audio playback');
    return { targetWindow, document, audio };
  }

  function activeSubtitle(document) {
    return document.querySelector('.concept-screen.active .runtime-subtitle')?.textContent.trim() || '';
  }

  function visibleVisualIds(document, cues) {
    return cues
      .filter(cue => document.querySelector(`.concept-screen.active ${cue.selector}`)?.classList.contains('is-visible'))
      .map(cue => cue.id);
  }

  function activeProgressRatio(document, segment = 1) {
    const fill = document.querySelector(`.concept-screen.active [data-player-kind="math"] [data-player-segment="${segment}"] .player-fill`);
    return Number.parseFloat(fill?.style.width || '0') / 100;
  }

  function renderedState(document, fixture) {
    return {
      subtitle: activeSubtitle(document),
      visualIds: visibleVisualIds(document, fixture.visual_cues),
      progressRatio: activeProgressRatio(document)
    };
  }

  function expectedState(fixture, ratio) {
    let subtitle = fixture.subtitle_cues[0].text;
    fixture.subtitle_cues.forEach(cue => {
      if (ratio >= cue.ratio) subtitle = cue.text;
    });
    return {
      subtitle,
      visualIds: fixture.visual_cues.filter(cue => ratio >= cue.ratio).map(cue => cue.id)
    };
  }

  function sameIds(left, right) {
    return left.length === right.length && left.every((value, index) => value === right[index]);
  }

  function playerToggle(document) {
    return document.querySelector('.concept-screen.active [data-player-toggle]');
  }

  function clickSeek(context, targetMs) {
    const button = context.document.querySelector('.concept-screen.active [data-player-kind="math"] [data-player-segment="1"]');
    if (!button) throw new Error('Current segment seek control is missing');
    const durationMs = context.audio.duration * 1000;
    const ratio = Math.max(0, Math.min(0.99, targetMs / durationMs));
    const rect = button.getBoundingClientRect();
    button.dispatchEvent(new context.targetWindow.MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      clientX: rect.left + rect.width * ratio,
      clientY: rect.top + rect.height / 2
    }));
  }

  function clickSwitchOperation(context, segmentFixture, operation) {
    const button = context.document.querySelector(`.concept-screen.active [data-player-kind="math"] [data-player-segment="${operation.segment}"]`);
    if (!button) throw new Error(`Segment ${operation.segment} control is missing`);
    const ratio = Math.max(0, Math.min(0.99, operation.target_ms / segmentFixture.expected_duration_ms));
    const rect = button.getBoundingClientRect();
    button.dispatchEvent(new context.targetWindow.MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      clientX: rect.left + rect.width * ratio,
      clientY: rect.top + rect.height / 2
    }));
  }

  async function collectSwitchRun(frame, fixture, runId) {
    const context = await loadDemo(frame, runId);
    const { targetWindow, document, audio } = context;
    const observations = [];
    for (const operation of fixture.switch_operations) {
      const segmentFixture = fixture.switch_segments[String(operation.segment)];
      clickSwitchOperation(context, segmentFixture, operation);
      await waitFor(() => {
        const activeSegment = Number(document.querySelector('.concept-screen.active [data-player-kind="math"] [data-player-segment].active')?.dataset.playerSegment);
        return activeSegment === operation.segment &&
          audio.currentSrc.endsWith(segmentFixture.audio_path) &&
          !audio.paused &&
          Math.abs(audio.currentTime * 1000 - operation.target_ms) < 750;
      }, 5000, `segment ${operation.segment} at ${operation.target_ms}ms`);
      await nextFrame(targetWindow);
      await nextFrame(targetWindow);
      const observedMs = audio.currentTime * 1000;
      const actualRatio = audio.currentTime / audio.duration;
      const actualVisualIds = visibleVisualIds(document, segmentFixture.visual_cues);
      const expected = expectedState(segmentFixture, operation.target_ms / segmentFixture.expected_duration_ms);
      const activeSegment = Number(document.querySelector('.concept-screen.active [data-player-kind="math"] [data-player-segment].active')?.dataset.playerSegment);
      const progressRatio = activeProgressRatio(document, operation.segment);
      observations.push({
        segment: operation.segment,
        target_ms: operation.target_ms,
        observed_ms: observedMs,
        offset_ms: observedMs - operation.target_ms,
        error_ms: Math.abs(observedMs - operation.target_ms),
        segment_consistent: activeSegment === operation.segment,
        state_consistent: activeSubtitle(document) === expected.subtitle &&
          sameIds(actualVisualIds, expected.visualIds) &&
          Math.abs(progressRatio - actualRatio) < 0.02
      });
    }
    if (!audio.paused) playerToggle(document).click();
    return { run_id: runId, observations };
  }

  async function collectRealRun(frame, fixture, runId, includeSeek) {
    const context = await loadDemo(frame, runId);
    const { targetWindow, document, audio } = context;
    const durationMs = audio.duration * 1000;
    const subtitleObservations = [];
    const visualObservations = [];
    const seenSubtitles = new Set();
    const seenVisuals = new Set();
    let pauseResumeErrorMs = null;
    let pauseStateStable = true;

    while (audio.currentTime / audio.duration < 0.9) {
      const currentMs = audio.currentTime * 1000;
      const subtitle = activeSubtitle(document);
      fixture.subtitle_cues.forEach(cue => {
        if (subtitle === cue.text && !seenSubtitles.has(cue.id)) {
          seenSubtitles.add(cue.id);
          subtitleObservations.push({
            cue_id: cue.id,
            expected_ms: cue.ratio * durationMs,
            observed_ms: currentMs,
            deviation_ms: Math.abs(currentMs - cue.ratio * durationMs)
          });
        }
      });
      fixture.visual_cues.forEach(cue => {
        const visible = document.querySelector(`.concept-screen.active ${cue.selector}`)?.classList.contains('is-visible');
        if (visible && !seenVisuals.has(cue.id)) {
          seenVisuals.add(cue.id);
          visualObservations.push({
            cue_id: cue.id,
            expected_ms: cue.ratio * durationMs,
            observed_ms: currentMs,
            deviation_ms: Math.abs(currentMs - cue.ratio * durationMs)
          });
        }
      });

      if (pauseResumeErrorMs === null && audio.currentTime >= 2) {
        const toggle = playerToggle(document);
        toggle.click();
        await waitFor(() => audio.paused, 1000, 'pause');
        const pausedPosition = audio.currentTime;
        const pausedState = renderedState(document, fixture);
        await sleep(350);
        const heldPosition = audio.currentTime;
        const heldState = renderedState(document, fixture);
        toggle.click();
        await waitFor(() => !audio.paused, 1000, 'resume');
        const resumedPosition = audio.currentTime;
        pauseResumeErrorMs = Math.max(
          Math.abs(heldPosition - pausedPosition),
          Math.abs(resumedPosition - pausedPosition)
        ) * 1000;
        pauseStateStable = pausedState.subtitle === heldState.subtitle &&
          sameIds(pausedState.visualIds, heldState.visualIds) &&
          Math.abs(pausedState.progressRatio - heldState.progressRatio) < 0.002;
      }
      await nextFrame(targetWindow);
    }

    if (!audio.paused) playerToggle(document).click();
    const seekObservations = [];
    if (includeSeek) {
      for (const targetMs of fixture.seek_targets_ms) {
        clickSeek(context, targetMs);
        await waitFor(
          () => !audio.paused && Math.abs(audio.currentTime * 1000 - targetMs) < 750,
          5000,
          `seek to ${targetMs}ms`
        );
        await nextFrame(targetWindow);
        await nextFrame(targetWindow);
        const actualMs = audio.currentTime * 1000;
        const actualRatio = audio.currentTime / audio.duration;
        const actualState = renderedState(document, fixture);
        const expected = expectedState(fixture, targetMs / durationMs);
        const stateConsistent = actualState.subtitle === expected.subtitle &&
          sameIds(actualState.visualIds, expected.visualIds) &&
          Math.abs(actualState.progressRatio - actualRatio) < 0.02;
        seekObservations.push({
          target_ms: targetMs,
          observed_ms: actualMs,
          error_ms: Math.abs(actualMs - targetMs),
          state_consistent: stateConsistent
        });
      }
      if (!audio.paused) playerToggle(document).click();
    }

    return {
      run_id: runId,
      duration_ms: durationMs,
      subtitle_observations: subtitleObservations,
      visual_observations: visualObservations,
      pause_resume_error_ms: pauseResumeErrorMs,
      pause_state_stable: pauseStateStable,
      seek_observations: seekObservations
    };
  }

  async function collectFallbackRun(frame, fixture, runId) {
    const context = await loadDemo(frame, runId);
    const { targetWindow, document, audio } = context;
    await waitFor(() => audio.currentTime >= 10, 14000, 'fallback injection position');
    const durationMs = audio.duration * 1000;
    const beforeRatio = audio.currentTime / audio.duration;
    const beforeState = renderedState(document, fixture);
    let errorCount = 0;
    let fallbackTransitionCount = 0;
    document.addEventListener('playbackclockchange', event => {
      if (event.detail?.from === 'audio' && event.detail?.to === 'visual-fallback') fallbackTransitionCount += 1;
    });
    audio.addEventListener('error', () => { errorCount += 1; });
    audio.src = `/prototype/assets/audio/__ts07_missing_${encodeURIComponent(runId)}.wav`;
    audio.load();
    await waitFor(() => errorCount > 0, 3000, 'media error');
    await nextFrame(targetWindow);
    await nextFrame(targetWindow);
    const afterRatio = activeProgressRatio(document);
    const afterState = renderedState(document, fixture);
    await sleep(250);
    const laterRatio = activeProgressRatio(document);
    const beforeSubtitleIndex = fixture.subtitle_cues.findIndex(cue => cue.text === beforeState.subtitle);
    const afterSubtitleIndex = fixture.subtitle_cues.findIndex(cue => cue.text === afterState.subtitle);
    const stateRollback = afterSubtitleIndex < beforeSubtitleIndex || afterState.visualIds.length < beforeState.visualIds.length;
    return {
      run_id: runId,
      duration_ms: durationMs,
      error_count: errorCount,
      fallback_transition_count: fallbackTransitionCount,
      before_ratio: beforeRatio,
      after_ratio: afterRatio,
      later_ratio: laterRatio,
      handoff_error_ms: Math.abs(afterRatio - beforeRatio) * durationMs,
      monotonic: afterRatio >= beforeRatio && laterRatio >= afterRatio,
      state_rollback: stateRollback
    };
  }

  async function sha256Url(url) {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Unable to hash ${url}: HTTP ${response.status}`);
    const digest = await crypto.subtle.digest('SHA-256', await response.arrayBuffer());
    return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
  }

  async function runCandidate(config) {
    const fixtureUrl = config.fixtureUrl || './fixtures/audit-cues.json';
    const fixture = await fetch(fixtureUrl, { cache: 'no-store' }).then(response => response.json());
    const frame = config.frame;
    if (!(frame instanceof HTMLIFrameElement)) throw new Error('Candidate mode requires a Demo iframe');
    const realRunCount = config.realRunCount ?? 5;
    const switchRunCount = config.switchRunCount ?? 0;
    const fallbackRunCount = config.fallbackRunCount ?? 5;
    const startedAt = new Date().toISOString();

    const warmup = await collectRealRun(frame, fixture, 'warmup', false);
    const realRuns = [];
    for (let index = 0; index < realRunCount; index += 1) {
      realRuns.push(await collectRealRun(frame, fixture, `real-${index + 1}`, true));
    }
    const switchRuns = [];
    for (let index = 0; index < switchRunCount; index += 1) {
      switchRuns.push(await collectSwitchRun(frame, fixture, `switch-${index + 1}`));
    }
    const fallbackRuns = [];
    for (let index = 0; index < fallbackRunCount; index += 1) {
      fallbackRuns.push(await collectFallbackRun(frame, fixture, `fallback-${index + 1}`));
    }

    const measurements = {
      subtitleCueDeviationsMs: realRuns.flatMap(run => run.subtitle_observations.map(item => item.deviation_ms)),
      visualCueDeviationsMs: realRuns.flatMap(run => run.visual_observations.map(item => item.deviation_ms)),
      pauseResumeErrorsMs: realRuns.map(run => run.pause_resume_error_ms),
      seekErrorsMs: realRuns.flatMap(run => run.seek_observations.map(item => item.error_ms)),
      seekRenderedStateConsistent: realRuns.every(run => run.pause_state_stable && run.seek_observations.every(item => item.state_consistent)),
      switchOffsetsMs: switchRuns.flatMap(run => run.observations.map(item => item.offset_ms)),
      switchRenderedStateConsistent: switchRuns.every(run => run.observations.every(item => item.state_consistent)),
      switchSegmentConsistent: switchRuns.every(run => run.observations.every(item => item.segment_consistent)),
      fallbackHandoffs: fallbackRuns.map(run => ({ beforeRatio: run.before_ratio, afterRatio: run.after_ratio })),
      fallbackTransitionCounts: fallbackRuns.map(run => run.fallback_transition_count),
      fallbackMonotonic: fallbackRuns.every(run => run.monotonic),
      fallbackStateRollback: fallbackRuns.some(run => run.state_rollback)
    };
    const thresholds = {
      cueP95MsExclusive: fixture.thresholds.cue_p95_ms_exclusive,
      pauseResumeP95MsExclusive: fixture.thresholds.pause_resume_p95_ms_exclusive,
      seekFinalErrorMsExclusive: fixture.thresholds.seek_final_error_ms_exclusive,
      handoffErrorMsExclusive: fixture.thresholds.handoff_error_ms_exclusive
    };
    const evaluation = evaluate({ thresholds, measurements, durationMs: warmup.duration_ms });
    const hashes = {};
    for (const url of [
      '/prototype/sound-demo.html',
      fixture.candidate.audio_path,
      ...(fixture.candidate.additional_audio_paths || []),
      fixtureUrl,
      './src/audit.js'
    ]) hashes[url] = await sha256Url(url);

    return {
      result_version: 'ts-07-browser-audit/1.0',
      evidence_kind: 'candidate_output',
      started_at: startedAt,
      completed_at: new Date().toISOString(),
      candidate: {
        implementation: 'prototype/sound-demo.html',
        approved_browser: config.approvedBrowser || 'Google Chrome 150.0.7871.188',
        browser_user_agent: navigator.userAgent,
        platform: navigator.platform,
        playback_rate: fixture.candidate.playback_rate,
        external_requests: 0,
        tokens_or_equivalent: 0,
        cost_cny: 0
      },
      fixture_version: fixture.fixture_version,
      hashes,
      warmup: { duration_ms: warmup.duration_ms },
      raw: { real_runs: realRuns, switch_runs: switchRuns, fallback_runs: fallbackRuns },
      metrics: evaluation.metrics,
      violation_codes: evaluation.violationCodes,
      pass: evaluation.pass
    };
  }

  async function run(config = {}) {
    if (config.mode === 'evaluate') return evaluate(config);
    if (config.mode === 'candidate') return runCandidate(config);
    throw new Error(`Unsupported audit mode: ${config.mode || 'missing'}`);
  }

  global.ts07Audit = Object.freeze({ run });
})(window);
