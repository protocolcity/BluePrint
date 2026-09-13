/* Work-order content is untrusted text, never executable markup. */
(async () => {
  const {safeReturnTo} = await import('/js/reader-navigation.mjs');
  const {backLabel, date, paintOutline, setTrustedHtml} = await import('/js/nav-shell.mjs');

  function gateLabel(order) {
    if (order.gate_type === 'deferred') return 'Deferred';
    if (order.gate_type === 'tracking') return 'Tracking';
    if (order.gate_type === 'timer') return order.gate_expired ? 'Timer expired' : `Held until ${date(order.gate_until)}`;
    if (order.gate_type === 'human') return 'Needs a decision';
    if (order.blocked_on === 'open' || order.blocked_on === 'unknown') return 'Blocked on another order';
    return 'None';
  }

  function assignmentSummary(order) {
    const owner = (order.owner || '').trim();
    if (owner && owner !== 'Unassigned') return owner;
    if (order.needs_routing) return 'Needs routing';
    return 'Unassigned';
  }

  function lifecycleSummary(order) {
    if (order.status === 'in_progress' && order.live_with) return `Live · ${order.live_with}`;
    if (order.status === 'in_review' && order.parked_by) return `Parked · ${order.parked_by}`;
    return order.status_word || order.status;
  }

  function claimSummary(order) {
    if (order.status === 'in_progress' && order.live_with) return `Claim live with ${order.live_with}${order.since ? ` since ${date(order.since)}` : ''}`;
    if (order.status === 'in_review' && order.parked_by) return `Parked by ${order.parked_by}${order.since ? ` since ${date(order.since)}` : ''}`;
    return 'No active claim';
  }

  function paintFacts(order) {
    const facts = document.getElementById('facts');
    if (!facts) return;
    facts.replaceChildren();
    const rows = [
      ['Lifecycle', lifecycleSummary(order)],
      ['Gate', gateLabel(order)],
      ['Assignment', assignmentSummary(order)],
      ['Claim', claimSummary(order)],
      ['Updated', date(order.updated_at)],
    ];
    if (order.parent) rows.push(['Parent', order.parent]);
    if (order.blockers?.length) rows.push(['Blockers', order.blockers.join(', ')]);
    if (order.observed_at) rows.push(['Observed', date(order.observed_at)]);
    for (const [label, value] of rows) {
      const dt = document.createElement('dt');
      dt.textContent = label;
      const dd = document.createElement('dd');
      dd.textContent = value;
      facts.append(dt, dd);
    }
  }

  window.paintComment = function paintComment(comment) {
    const item = document.createElement('section');
    const heading = document.createElement('h3');
    heading.textContent = `${comment.author || 'Unknown author'} · ${date(comment.created_at)}`;
    const body = document.createElement('div');
    body.className = 'bp-md';
    if (comment.body_html) setTrustedHtml(body, comment.body_html);
    else body.textContent = comment.body || '';
    item.append(heading, body);
    return item;
  };

  const message = document.getElementById('message');
  const params = new URLSearchParams(location.search);
  const back = document.getElementById('reader-back');
  back.href = safeReturnTo(params.get('return_to'));
  back.textContent = backLabel(new URL(back.href, location.href).pathname);
  try {
    const query = new URLSearchParams({id: params.get('id') || '', project: params.get('project') || ''});
    const response = await fetch('/api/work-order?' + query);
    const order = await response.json();
    if (!response.ok) throw new Error(order.error || 'Unable to load work order.');
    document.getElementById('identity').textContent = `${order.project_name || order.project} · ${order.ext_id}`;
    document.getElementById('title').textContent = order.title;
    document.getElementById('state').textContent = `Priority ${order.priority}`;
    paintFacts(order);
    paintOutline(document.getElementById('description-outline'), order.description_outline);
    setTrustedHtml(document.getElementById('description'), order.description_html || order.description || 'No description provided.');
    window.bpOrder = order;
    if (order.references?.length) {
      const section = document.createElement('section');
      const heading = document.createElement('h2');
      heading.textContent = 'Source locations';
      section.append(heading);
      for (const reference of order.references) {
        const link = document.createElement('a');
        link.className = 'bp-paper-row';
        link.href = reference.href;
        link.textContent = `${reference.action} · ${reference.label}`;
        section.append(link);
        if (order.reveal_supported) {
          const button = document.createElement('button');
          button.type = 'button';
          button.textContent = 'Show in Finder';
          const status = document.createElement('span');
          status.setAttribute('role', 'status');
          button.addEventListener('click', async () => {
            button.disabled = true;
            try {
              const reveal = await fetch('/api/work-order/reveal', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-BluePrint-Action': 'work-order'},
                body: JSON.stringify({project: order.project, id: order.ext_id, path: reference.path}),
              });
              const result = await reveal.json();
              if (!reveal.ok || !result.ok) throw new Error(result.error || 'Reveal unavailable');
              status.textContent = 'Shown in Finder.';
            } catch (error) {
              status.textContent = error.message;
            } finally {
              button.disabled = false;
            }
          });
          section.append(button, status);
        }
      }
      document.getElementById('description').after(section);
    }
    window.dispatchEvent(new Event('bp-order-ready'));
    const comments = document.getElementById('comments');
    if (!order.comments.length) comments.textContent = 'No comments yet.';
    for (const comment of order.comments) comments.append(window.paintComment(comment));
    message.hidden = true;
    document.getElementById('order').hidden = false;
  } catch (error) {
    message.textContent = error.message;
  }
})();

(() => {
  const form = document.getElementById('note-form');
  const body = document.getElementById('note-body');
  const button = document.getElementById('note-submit');
  const status = document.getElementById('note-result');
  const params = new URLSearchParams(location.search);
  const draftKey = `bp-note-draft:${params.get('project') || ''}:${params.get('id') || ''}`;
  try {
    const saved = sessionStorage.getItem(draftKey);
    if (saved) body.value = saved;
  } catch (_) { /* Storage unavailable; draft is best-effort only. */ }
  body.addEventListener('input', () => {
    try { sessionStorage.setItem(draftKey, body.value); } catch (_) { /* ignore */ }
  });
  let saving = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (saving || !body.value.trim()) return;
    saving = true;
    button.disabled = true;
    body.disabled = true;
    status.textContent = 'Saving through WorkLane…';
    status.dataset.error = 'false';
    try {
      const identity = document.getElementById('identity').textContent.split(' · ');
      const response = await fetch('/api/work-order/note', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-BluePrint-Action': 'note'},
        body: JSON.stringify({project: params.get('project') || identity[0], id: params.get('id'), body: body.value}),
        signal: AbortSignal.timeout(20000),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'The note could not be saved.');
      const comment = result.comment;
      if (window.bpOrder) window.bpOrder.updated_at = result.task?.updated_at || comment.created_at;
      const comments = document.getElementById('comments');
      if (comments.textContent === 'No comments yet.') comments.replaceChildren();
      comments.append(window.paintComment(comment));
      body.value = '';
      try { sessionStorage.removeItem(draftKey); } catch (_) { /* ignore */ }
      status.textContent = 'Note saved to WorkLane.';
    } catch (error) {
      status.dataset.error = 'true';
      status.textContent = error.name === 'TimeoutError' || error.name === 'TypeError'
        ? 'The response was interrupted. Refresh the record before retrying; the note may already be saved.'
        : error.message;
    } finally {
      saving = false;
      button.disabled = false;
      body.disabled = false;
    }
  });
})();

(() => {
  const $ = id => document.getElementById(id);
  let saving = false;
  function configure() {
    const action = $('work-action').value;
    const order = window.bpOrder;
    if (!order) return;
    $('work-controls').hidden = ['done', 'canceled', 'cancelled'].includes(order.status);
    for (const [name, visible] of [['priority', action === 'priority'], ['reason', action === 'hold'], ['agent', action === 'assign'], ['reminder', action === 'reminder']]) {
      $('action-' + name).hidden = !visible;
      $(name + '-label').hidden = !visible;
    }
    $('action-reason').required = action === 'hold';
    const options = order.assignment_options || [];
    $('action-submit').disabled = saving || (action === 'assign' && !options.length) || (action === 'resume' && !order.gate_type);
    $('action-explanation').textContent = action === 'reminder'
      ? 'Adds a date to Calendar. It does not delay work or change assignment, and sends no outside notification.'
      : action === 'assign' && !options.length
        ? 'No local agent is registered for this project. Remote repository activity does not create an assignable agent.'
        : action === 'resume'
          ? (order.gate_type ? 'Clear the current hold. The assigned agent can resume when WorkLane considers this work ready.' : 'This work order has no hold to release.')
          : '';
  }
  window.addEventListener('bp-order-ready', () => {
    const order = window.bpOrder;
    $('action-priority').value = String(order.priority);
    try {
      const labels = typeof order.labels === 'string' ? JSON.parse(order.labels) : order.labels || [];
      $('action-reminder').value = (labels.find(label => label.startsWith('reminder:')) || '').slice(9);
    } catch (error) { /* ignore malformed labels */ }
    $('action-agent').replaceChildren(...(order.assignment_options || []).map(agent => new Option(agent.name, agent.id)));
    configure();
  });
  $('work-action').addEventListener('change', configure);
  $('action-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (saving || !window.bpOrder) return;
    const order = window.bpOrder;
    const action = $('work-action').value;
    const value = action === 'priority' ? Number($('action-priority').value)
      : action === 'hold' ? $('action-reason').value
        : action === 'assign' ? $('action-agent').value
          : action === 'reminder' ? $('action-reminder').value : null;
    saving = true;
    configure();
    $('action-result').textContent = 'Applying through WorkLane…';
    try {
      const response = await fetch('/api/work-order/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-BluePrint-Action': 'work-order'},
        body: JSON.stringify({project: order.project, id: order.ext_id, action, value, expected_updated_at: order.updated_at}),
        signal: AbortSignal.timeout(20000),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Change failed.');
      location.reload();
    } catch (error) {
      $('action-result').textContent = error.name === 'TimeoutError' || error.name === 'TypeError'
        ? 'Response interrupted. Reload before retrying; the change may already be saved.'
        : error.message;
    } finally {
      saving = false;
      configure();
    }
  });
})();
