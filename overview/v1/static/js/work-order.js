/* Work-order content is untrusted text, never executable markup. */
(async () => {
  const {safeReturnTo} = await import('/js/reader-navigation.mjs');
  const {backLabel, date, paintOutline, setTrustedHtml, bindHashReveal} = await import('/js/nav-shell.mjs');

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
    paintOutline(document.getElementById('description-outline'), order.description_outline); bindHashReveal(document);
    setTrustedHtml(document.getElementById('description'), order.description_html || order.description || 'No description provided.');
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
    const comments = document.getElementById('comments');
    if (!order.comments.length) comments.textContent = 'No comments yet.';
    for (const comment of order.comments) comments.append(window.paintComment(comment));
    message.hidden = true;
    document.getElementById('order').hidden = false;
  } catch (error) {
    message.textContent = error.message;
  }
})();
