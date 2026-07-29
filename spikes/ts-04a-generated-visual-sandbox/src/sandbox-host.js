export const SANDBOX_POLICY = Object.freeze({
  version: "ts04a-sandbox-policy/1.0",
  executionBudgetMs: 250,
  maxEvents: 32,
  allowedEvents: Object.freeze(["render_complete", "interaction"]),
  inputSchemaVersion: "visual-sandbox-input/1.0",
  outputSchemaVersion: "visual-sandbox-output/1.0"
});

const BLOCKED_INPUT_KEYS = new Set([
  "child_name", "child_id", "student_name", "student_id", "voice", "photo", "transcript", "conversation", "history", "cookie"
]);

function rejectSensitiveFields(value, depth = 0) {
  if (depth > 6) throw new TypeError("INPUT_TOO_DEEP");
  if (!value || typeof value !== "object") return;
  for (const [key, nestedValue] of Object.entries(value)) {
    if (BLOCKED_INPUT_KEYS.has(key.toLowerCase())) throw new TypeError("INPUT_FIELD_NOT_ALLOWED");
    rejectSensitiveFields(nestedValue, depth + 1);
  }
}

function validateInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("INVALID_INPUT");
  }
  const allowed = new Set(["scene_id", "width", "height", "parameters"]);
  for (const key of Object.keys(input)) {
    if (!allowed.has(key) || BLOCKED_INPUT_KEYS.has(key)) throw new TypeError("INPUT_FIELD_NOT_ALLOWED");
  }
  if (typeof input.scene_id !== "string" || !/^[a-z0-9][a-z0-9._-]{0,63}$/.test(input.scene_id)) {
    throw new TypeError("INVALID_SCENE_ID");
  }
  if (!Number.isInteger(input.width) || input.width < 1 || input.width > 2048) throw new TypeError("INVALID_WIDTH");
  if (!Number.isInteger(input.height) || input.height < 1 || input.height > 2048) throw new TypeError("INVALID_HEIGHT");
  if (!input.parameters || typeof input.parameters !== "object" || Array.isArray(input.parameters)) {
    throw new TypeError("INVALID_PARAMETERS");
  }
  rejectSensitiveFields(input.parameters);
  const serialized = JSON.stringify(input.parameters);
  if (serialized.length > 16_384) throw new TypeError("INPUT_TOO_LARGE");
  return JSON.parse(JSON.stringify(input));
}

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return `sha256:${Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("")}`;
}

function frameDocument() {
  const policy = JSON.stringify(SANDBOX_POLICY);
  return `<!doctype html><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval'; worker-src blob:; connect-src 'none'; img-src 'none'; media-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<canvas id="surface"></canvas>
<script>
(() => {
  "use strict";
  const POLICY = ${policy};
  let initialized = false;
  addEventListener("message", event => {
    if (initialized || event.source !== parent || event.data?.type !== "sandbox-init" || !event.ports[0]) return;
    initialized = true;
    const port = event.ports[0];
    const sessionId = event.data.sessionId;
    const runToken = event.data.runToken;
    const input = event.data.input;
    const code = event.data.code;
    const canvas = document.getElementById("surface");
    canvas.width = input.width;
    canvas.height = input.height;
    const offscreen = canvas.transferControlToOffscreen();
    const workerSource = \`
      "use strict";
      const nativePostMessage = self.postMessage.bind(self);
      const disabled = ["fetch", "XMLHttpRequest", "WebSocket", "WebSocketStream", "WebTransport", "EventSource", "importScripts", "Worker", "SharedWorker", "BroadcastChannel", "RTCPeerConnection", "indexedDB", "caches"];
      for (const name of disabled) {
        try { Object.defineProperty(self, name, { value: undefined, writable: false, configurable: false }); } catch (_) {}
      }
      self.onmessage = event => {
        const { code, input, canvas, runToken } = event.data;
        const send = (kind, detail = {}) => nativePostMessage({ kind, runToken, ...detail });
        const emit = (name, payload = {}) => {
          let serialized;
          try { serialized = JSON.stringify(payload); } catch (_) { return send("policy-violation"); }
          if (!payload || typeof payload !== "object" || Array.isArray(payload) || serialized.length > 8192) {
            return send("policy-violation");
          }
          send("candidate-event", { name, payload });
        };
        const api = Object.freeze({
          canvas,
          emit
        });
        send("worker-ready");
        try {
          const run = new Function("api", "input", '"use strict";' + code);
          Promise.resolve(run(api, Object.freeze(input))).then(
            () => send("completed"),
            error => send("runtime-error", { message: String(error?.message || error) })
          );
        } catch (error) {
          send("runtime-error", { message: String(error?.message || error) });
        }
      };
    \`;
    const blobUrl = URL.createObjectURL(new Blob([workerSource], { type: "text/javascript" }));
    const worker = new Worker(blobUrl);
    URL.revokeObjectURL(blobUrl);
    let terminal = false;
    let acceptedEvents = 0;
    const finish = (status, reason) => {
      if (terminal) return;
      terminal = true;
      clearTimeout(timer);
      const terminationStartedAt = performance.now();
      worker.terminate();
      const terminationDurationMs = performance.now() - terminationStartedAt;
      port.postMessage({ type: "terminal", sessionId, status, reason, acceptedEvents, terminationDurationMs });
      port.close();
    };
    let timer = setTimeout(() => finish("terminated", "worker_boot_budget"), POLICY.executionBudgetMs);
    worker.onerror = () => finish("runtime_error", "worker_crash");
    worker.onmessage = messageEvent => {
      const message = messageEvent.data;
      if (!message || message.runToken !== runToken) return;
      if (message.kind === "worker-ready") {
        clearTimeout(timer);
        timer = setTimeout(() => finish("terminated", "execution_budget"), POLICY.executionBudgetMs);
        port.postMessage({ type: "worker_ready", sessionId });
        return;
      }
      if (message.kind === "candidate-event") {
        if (!POLICY.allowedEvents.includes(message.name)) return;
        if (acceptedEvents >= POLICY.maxEvents) return finish("terminated", "event_limit");
        acceptedEvents += 1;
        port.postMessage({ type: "event", sessionId, name: message.name, payload: message.payload });
        return;
      }
      if (message.kind === "completed") return finish("completed", "clean_exit");
      if (message.kind === "policy-violation") return finish("terminated", "output_violation");
      if (message.kind === "runtime-error") return finish("runtime_error", "generated_code_error");
    };
    worker.postMessage({ code, input, runToken, canvas: offscreen }, [offscreen]);
  }, { once: true });
})();
</script>`;
}

export class VisualSandbox {
  constructor(root = document.body) {
    this.root = root;
    this.activeFrames = new Set();
  }

  async run({ code, input, budgetMs = SANDBOX_POLICY.executionBudgetMs }) {
    const traceStartedAt = new Date().toISOString();
    const traceStart = performance.now();
    if (typeof code !== "string" || code.length === 0 || code.length > 65_536) throw new TypeError("INVALID_CODE");
    const cleanInput = validateInput(input);
    const codeHash = await sha256(code);
    const sessionId = crypto.randomUUID();
    const runToken = crypto.randomUUID();
    const createStartedAt = performance.now();
    const iframe = document.createElement("iframe");
    iframe.sandbox = "allow-scripts";
    iframe.allow = "camera 'none'; microphone 'none'; clipboard-read 'none'; clipboard-write 'none'; geolocation 'none'";
    iframe.referrerPolicy = "no-referrer";
    iframe.srcdoc = frameDocument();
    this.root.append(iframe);
    this.activeFrames.add(iframe);

    const events = [];
    const channel = new MessageChannel();
    const marks = { frameLoadedAt: null, workerReadyAt: null, terminalAt: null };
    let settled = false;
    const cleanup = () => {
      channel.port1.close();
      iframe.remove();
      this.activeFrames.delete(iframe);
    };

    return new Promise(resolve => {
      const finish = (status, reason, acceptedEvents = events.length, terminationDurationMs = 0) => {
        if (settled) return;
        settled = true;
        marks.terminalAt = performance.now();
        const destroyStartedAt = performance.now();
        cleanup();
        const destroyEndedAt = performance.now();
        const offset = value => Math.max(0, value - traceStart);
        const span = (spanId, stage, startedAt, endedAt, outcome = "success") => ({
          span_id: spanId,
          parent_span_id: null,
          stage,
          started_offset_ms: Number(offset(startedAt).toFixed(3)),
          ended_offset_ms: Number(offset(endedAt).toFixed(3)),
          duration_ms: Number(Math.max(0, endedAt - startedAt).toFixed(3)),
          latency_scope: "system_work",
          outcome,
          retry_index: 0,
          cache_status: "not_applicable",
          provider: null,
          model: null,
          input_units: null,
          output_units: null,
          cost_amount: 0,
          cost_currency: "CNY",
          error_code: outcome === "success" ? null : reason
        });
        const spans = [];
        if (marks.frameLoadedAt !== null) spans.push(span("sandbox-create", "sandbox.create", createStartedAt, marks.frameLoadedAt));
        if (marks.frameLoadedAt !== null && marks.workerReadyAt !== null) spans.push(span("sandbox-worker-boot", "sandbox.worker_boot", marks.frameLoadedAt, marks.workerReadyAt));
        if (marks.workerReadyAt !== null) {
          const executionOutcome = status === "completed"
            ? "success"
            : reason === "execution_budget" || reason === "worker_boot_budget" || reason === "host_watchdog"
              ? "timeout"
              : "failure";
          spans.push(span("sandbox-execute", "sandbox.execute", marks.workerReadyAt, marks.terminalAt, executionOutcome));
        }
        const terminationEndedAt = marks.terminalAt;
        const terminationStartedAt = Math.max(traceStart, terminationEndedAt - terminationDurationMs);
        spans.push(span("sandbox-terminate", "sandbox.terminate", terminationStartedAt, terminationEndedAt));
        spans.push(span("sandbox-destroy", "sandbox.destroy", destroyStartedAt, destroyEndedAt));
        const milestones = [];
        if (marks.frameLoadedAt !== null) milestones.push({ name: "sandbox_frame_loaded", offset_ms: Number(offset(marks.frameLoadedAt).toFixed(3)), latency_scope: "diagnostic" });
        if (marks.workerReadyAt !== null) milestones.push({ name: "sandbox_worker_ready", offset_ms: Number(offset(marks.workerReadyAt).toFixed(3)), latency_scope: "diagnostic" });
        milestones.push({ name: "sandbox_terminal", offset_ms: Number(offset(marks.terminalAt).toFixed(3)), latency_scope: "system_output" });
        resolve({
          status,
          reason,
          events,
          accepted_event_count: acceptedEvents,
          duration_ms: Math.round(marks.terminalAt - traceStart),
          code_hash: codeHash,
          policy_version: SANDBOX_POLICY.version,
          input_schema_version: SANDBOX_POLICY.inputSchemaVersion,
          output_schema_version: SANDBOX_POLICY.outputSchemaVersion,
          timing: {
            schema_version: "stage-timing/1.0",
            trace_id: sessionId,
            slice_id: "TS-04A",
            clock: "monotonic",
            trace_started_at: traceStartedAt,
            milestones,
            spans
          }
        });
      };
      const hostTimer = setTimeout(() => finish("terminated", "host_watchdog"), budgetMs + 750);
      channel.port1.onmessage = event => {
        const message = event.data;
        if (!message || message.sessionId !== sessionId) return;
        if (message.type === "event") events.push({ name: message.name, payload: message.payload });
        if (message.type === "worker_ready") marks.workerReadyAt = performance.now();
        if (message.type === "terminal") {
          clearTimeout(hostTimer);
          finish(message.status, message.reason, message.acceptedEvents, message.terminationDurationMs);
        }
      };
      iframe.addEventListener("load", () => {
        marks.frameLoadedAt = performance.now();
        iframe.contentWindow.postMessage({
          type: "sandbox-init", sessionId, runToken, code, input: cleanInput
        }, "*", [channel.port2]);
      }, { once: true });
    });
  }

  destroyAll() {
    for (const iframe of this.activeFrames) iframe.remove();
    this.activeFrames.clear();
  }
}
