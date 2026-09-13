/* Shared client for the D2 change feed (GET /api/changes, text/event-stream).
   Reconnects with exponential backoff and drops the connection while the
   tab is hidden — a background tab should not hold one of the shared 8
   server slots against pages someone is actually looking at. */
export function connectChanges(onChanged, onState) {
  let source = null, backoff = 1000;
  function report(state) { if (onState) onState(state); }
  function stop() { if (source) { source.close(); source = null; } }
  function start() {
    if (source || document.hidden) return;
    report('connecting');
    source = new EventSource('/api/changes');
    source.addEventListener('changed', () => onChanged());
    source.onopen = () => { backoff = 1000; report('open'); };
    source.onerror = () => {
      stop();
      report('error');
      if (!document.hidden) setTimeout(start, backoff);
      backoff = Math.min(backoff * 2, 30000);
    };
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { stop(); report('paused'); } else { start(); }
  });
  start();
  return { stop };
}
