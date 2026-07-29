import { SANDBOX_POLICY, VisualSandbox } from "./sandbox-host.js";

const root = document.getElementById("sandbox-root");
const statusNode = document.getElementById("status");
const casesNode = document.getElementById("cases");
const metricsNode = document.getElementById("metrics");
const jsonNode = document.getElementById("result-json");
const hostState = { lesson_position: 37, saved: true };
const baseInput = { scene_id: "science.sound.demo", width: 320, height: 180, parameters: { color: "#4f8f78" } };

function percentile(values, percentileValue) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.max(0, Math.ceil((percentileValue / 100) * sorted.length) - 1);
  return Number(sorted[index].toFixed(3));
}

function summarize(values) {
  return {
    sample_count: values.length,
    p50_ms: percentile(values, 50),
    p80_ms: percentile(values, 80),
    p95_ms: percentile(values, 95),
    max_ms: values.length ? Number(Math.max(...values).toFixed(3)) : null
  };
}

function showMetrics(summary) {
  const metrics = [
    ["攻击夹具", `${summary.passed_cases}/${summary.total_cases}`],
    ["禁止能力成功访问", String(summary.forbidden_access_successes)],
    ["重复创建/销毁", `${summary.lifecycle_passes}/${summary.lifecycle_runs}`],
    ["残留 iframe", String(summary.residual_iframes)]
  ];
  metricsNode.replaceChildren(...metrics.map(([label, value]) => {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    wrapper.append(term, detail);
    return wrapper;
  }));
}

function showCases(results) {
  casesNode.replaceChildren(...results.map(result => {
    const item = document.createElement("li");
    item.dataset.pass = String(result.pass);
    item.innerHTML = `<strong>${result.pass ? "PASS" : "FAIL"}</strong> ${result.case_id} - ${result.actual_status}/${result.actual_reason}`;
    return item;
  }));
}

async function run() {
  const fixture = await fetch("./fixtures/attacks.json", { cache: "no-store" }).then(response => response.json());
  const sandbox = new VisualSandbox(root);
  const caseResults = [];

  for (const testCase of fixture.cases) {
    const observed = await sandbox.run({ code: testCase.code, input: baseInput });
    const pass = observed.status === testCase.expected_status
      && observed.reason === testCase.expected_reason
      && observed.accepted_event_count === testCase.expected_events;
    caseResults.push({
      case_id: testCase.id,
      pass,
      expected_status: testCase.expected_status,
      actual_status: observed.status,
      expected_reason: testCase.expected_reason,
      actual_reason: observed.reason,
      expected_events: testCase.expected_events,
      accepted_events: observed.accepted_event_count,
      duration_ms: observed.duration_ms,
      timing: observed.timing,
      code_hash: observed.code_hash,
      policy_version: observed.policy_version
    });
  }

  const inputRejections = [];
  for (const input of [
    { ...baseInput, child_name: "synthetic-child" },
    { ...baseInput, parameters: { nested: { transcript: "synthetic voice text" } } },
    { ...baseInput, width: 99999 }
  ]) {
    try {
      await sandbox.run({ code: "api.emit('render_complete')", input });
      inputRejections.push(false);
    } catch (_) {
      inputRejections.push(true);
    }
  }

  let lifecyclePasses = 0;
  const lifecycleResults = [];
  for (let index = 0; index < 20; index += 1) {
    const result = await sandbox.run({ code: "api.emit('render_complete', { cycle: input.parameters.cycle });", input: { ...baseInput, parameters: { cycle: index } } });
    lifecycleResults.push(result);
    if (result.status === "completed" && result.accepted_event_count === 1 && sandbox.activeFrames.size === 0) lifecyclePasses += 1;
  }
  sandbox.destroyAll();

  const stageDurations = {};
  for (const result of [...caseResults, ...lifecycleResults]) {
    for (const timingSpan of result.timing.spans) {
      const group = `${timingSpan.stage}.${timingSpan.outcome}`;
      stageDurations[group] ||= [];
      stageDurations[group].push(timingSpan.duration_ms);
    }
  }
  const completedDurations = caseResults.filter(result => result.actual_status === "completed").map(result => result.duration_ms);
  const budgetTerminationDurations = caseResults.filter(result => result.actual_reason === "execution_budget").map(result => result.duration_ms);
  const summary = {
    protocol_version: "ts04a-browser-protocol/1.1",
    fixture_version: fixture.fixture_version,
    policy_version: SANDBOX_POLICY.version,
    browser_user_agent: navigator.userAgent,
    run_at: new Date().toISOString(),
    total_cases: caseResults.length,
    passed_cases: caseResults.filter(result => result.pass).length,
    forbidden_access_successes: caseResults.filter(result => result.case_id.includes("access") && !result.pass).length,
    input_schema_rejections: inputRejections.filter(Boolean).length,
    input_schema_rejection_target: inputRejections.length,
    lifecycle_runs: 20,
    lifecycle_passes: lifecyclePasses,
    residual_iframes: root.querySelectorAll("iframe").length,
    host_state_preserved: hostState.lesson_position === 37 && hostState.saved === true,
    code_hashes_present: caseResults.every(result => /^sha256:[a-f0-9]{64}$/.test(result.code_hash)),
    timing_contract_version: "stage-timing/1.0",
    timing_summary: {
      completed_total: summarize(completedDurations),
      execution_budget_termination_total: summarize(budgetTerminationDurations),
      lifecycle_total: summarize(lifecycleResults.map(result => result.duration_ms)),
      stages: Object.fromEntries(Object.entries(stageDurations).map(([stage, values]) => [stage, summarize(values)]))
    },
    case_results: caseResults
  };
  summary.pass = summary.passed_cases === summary.total_cases
    && summary.forbidden_access_successes === 0
    && summary.input_schema_rejections === summary.input_schema_rejection_target
    && summary.lifecycle_passes === summary.lifecycle_runs
    && summary.residual_iframes === 0
    && summary.host_state_preserved
    && summary.code_hashes_present;

  showMetrics(summary);
  showCases(caseResults);
  statusNode.textContent = summary.pass ? "全部候选门槛通过" : "存在未通过门槛";
  statusNode.dataset.state = summary.pass ? "pass" : "fail";
  jsonNode.textContent = JSON.stringify(summary, null, 2);
  document.documentElement.dataset.testState = summary.pass ? "pass" : "fail";
  window.__TS04A_RESULT__ = summary;
}

run().catch(error => {
  statusNode.textContent = `验证运行失败：${error.message}`;
  statusNode.dataset.state = "fail";
  document.documentElement.dataset.testState = "error";
  jsonNode.textContent = JSON.stringify({ pass: false, runner_error: String(error.stack || error) }, null, 2);
});
