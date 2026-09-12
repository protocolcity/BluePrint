/**
 * LiveTail — EventSource log tail with idle placard (pc-294, pc-304).
 * props: {
 *   url?: string,          // EventSource URL; omitted → idle
 *   worker?: string,       // display name
 *   active?: bool,         // false → idle placard, no EventSource
 *   maxLines?: number,     // default 500
 *   idleLabel?: string,
 * }
 *
 * Stream protocols:
 * - default `message` events: data is a plain line (kit greenfield)
 * - WorkForce shift-out (proxied at /api/worker-out/<name>/stream):
 *   named events chunk|end|idle|waiting|ping with JSON payloads;
 *   chunk carries { text } appended raw (may span lines)
 */
import { esc, ensureSuiteUiCss } from "./util.js";

export function mountLiveTail(el, props) {
  ensureSuiteUiCss();
  props = props || {};
  var url = props.url ? String(props.url) : "";
  var worker = props.worker ? String(props.worker) : "";
  var active = props.active !== false && !!url;
  var maxLines = Math.max(50, Math.min(2000, Number(props.maxLines) || 500));
  var idleLabel =
    props.idleLabel ||
    (worker
      ? worker + " is not streaming"
      : "Waiting for ready work…");

  var es = null;
  var state = "idle";
  var lines = [];
  var rawBuf = "";

  el.className = "suite-live-tail";
  el.setAttribute("role", "log");
  el.setAttribute("aria-live", "polite");
  el.setAttribute("aria-relevant", "additions");

  function renderIdle() {
    state = "idle";
    el.classList.remove("is-streaming", "is-error");
    el.classList.add("is-idle");
    el.innerHTML =
      '<p class="suite-live-tail__idle dim">' + esc(idleLabel) + "</p>";
  }

  function renderShell() {
    el.classList.remove("is-idle");
    el.innerHTML =
      '<pre class="suite-live-tail__pre" tabindex="0"></pre>' +
      '<p class="suite-live-tail__status dim" aria-live="polite"></p>';
  }

  function setStatus(msg, kind) {
    var st = el.querySelector(".suite-live-tail__status");
    if (st) {
      st.textContent = msg || "";
      st.classList.toggle("is-err", kind === "error");
    }
  }

  function paintPre() {
    var pre = el.querySelector(".suite-live-tail__pre");
    if (!pre) return;
    if (rawBuf) {
      pre.textContent = rawBuf;
    } else {
      pre.textContent = lines.join("\n");
    }
    pre.scrollTop = pre.scrollHeight;
  }

  function capRaw() {
    if (!rawBuf) return;
    var all = rawBuf.split("\n");
    if (all.length > maxLines) {
      rawBuf = all.slice(all.length - maxLines).join("\n");
    }
  }

  function appendLine(text) {
    lines.push(String(text));
    if (lines.length > maxLines) {
      lines = lines.slice(lines.length - maxLines);
    }
    paintPre();
  }

  function appendRaw(text) {
    rawBuf += String(text == null ? "" : text);
    capRaw();
    paintPre();
  }

  function parseJson(data) {
    try {
      return JSON.parse(data || "{}");
    } catch (e) {
      return null;
    }
  }

  function finishStream(statusMsg, asError) {
    state = asError ? "error" : "idle";
    el.classList.remove("is-streaming");
    if (asError) el.classList.add("is-error");
    else el.classList.remove("is-error");
    setStatus(statusMsg || "", asError ? "error" : "");
    teardownEs();
  }

  function connect() {
    if (!active || !url) {
      renderIdle();
      return;
    }
    if (typeof EventSource === "undefined") {
      renderShell();
      state = "error";
      el.classList.add("is-error");
      setStatus("EventSource not available", "error");
      return;
    }
    renderShell();
    state = "streaming";
    el.classList.add("is-streaming");
    setStatus(worker ? "Streaming · " + worker : "Streaming…");
    try {
      es = new EventSource(url);
    } catch (e) {
      state = "error";
      el.classList.remove("is-streaming");
      el.classList.add("is-error");
      setStatus("Could not open stream", "error");
      return;
    }
    /* Plain message protocol (kit default). */
    es.onmessage = function (ev) {
      appendLine(ev && ev.data != null ? ev.data : "");
    };
    /* WorkForce shift-out named events (pc-280 / pc-304). */
    es.addEventListener("chunk", function (ev) {
      var j = parseJson(ev && ev.data);
      if (j && typeof j.text === "string") {
        appendRaw(j.text);
      } else if (ev && ev.data) {
        appendRaw(ev.data);
      }
    });
    es.addEventListener("waiting", function (ev) {
      var j = parseJson(ev && ev.data);
      setStatus((j && j.msg) || "Waiting for shift output…");
    });
    es.addEventListener("ping", function () {
      /* heartbeat — keep streaming state */
    });
    es.addEventListener("idle", function (ev) {
      var j = parseJson(ev && ev.data);
      finishStream((j && j.msg) || "Not on shift", false);
      if (!rawBuf && !lines.length) {
        renderIdle();
      }
    });
    es.addEventListener("end", function (ev) {
      var j = parseJson(ev && ev.data);
      finishStream(
        (j && j.reason) || (j && j.msg) || "Stream ended",
        false
      );
    });
    es.onerror = function () {
      /* Browser auto-reconnects; close to avoid spam (same as person_v1 pc-289). */
      finishStream("Stream interrupted — pulse fallback", true);
    };
  }

  function teardownEs() {
    if (es) {
      try {
        es.close();
      } catch (e) {
        /* ignore */
      }
      es = null;
    }
  }

  connect();

  return {
    update: function (next) {
      teardownEs();
      return mountLiveTail(el, next);
    },
    destroy: function () {
      teardownEs();
      lines = [];
      rawBuf = "";
      el.innerHTML = "";
      el.className = "suite-live-tail";
      el.removeAttribute("role");
      el.removeAttribute("aria-live");
      el.removeAttribute("aria-relevant");
    },
    /** Test/debug: current stream state (idle|streaming|error). */
    getState: function () {
      return state;
    },
  };
}
