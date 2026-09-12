/* Work-order content is untrusted text, never executable markup. */
(async () => {
  const message = document.getElementById('message');
  const params = new URLSearchParams(location.search);
  try {
    const query = new URLSearchParams({id: params.get('id') || '', project: params.get('project') || ''});
    const response = await fetch('/api/work-order?' + query);
    const order = await response.json();
    if (!response.ok) throw new Error(order.error || 'Unable to load work order.');
    for (const [id, text] of Object.entries({identity: `${order.project} · ${order.ext_id}`, title: order.title,
      state: `${order.status} · Priority ${order.priority} · Updated ${order.updated_at}`,
      description: order.description || 'No description provided.'})) {
      document.getElementById(id).textContent = text;
    }
    window.bpOrder = order;
    window.dispatchEvent(new Event('bp-order-ready'));
    const comments = document.getElementById('comments');
    if (!order.comments.length) comments.textContent = 'No comments yet.';
    for (const comment of order.comments) {
      const item = document.createElement('section');
      const heading = document.createElement('h3');
      heading.textContent = `${comment.author || 'Unknown author'} · ${comment.created_at}`;
      const body = document.createElement('p');
      body.style.whiteSpace = 'pre-wrap';
      body.style.overflowWrap = 'anywhere';
      body.textContent = comment.body;
      item.append(heading, body);
      comments.append(item);
    }
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
  let saving = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (saving || !body.value.trim()) return;
    saving = true; button.disabled = true; body.disabled = true;
    status.textContent = 'Saving through WorkLane…'; status.dataset.error = 'false';
    const params = new URLSearchParams(location.search);
    try {
      const identity = document.getElementById('identity').textContent.split(' · ');
      const response = await fetch('/api/work-order/note', {
        method: 'POST', headers: {'Content-Type':'application/json','X-BluePrint-Action':'note'},
        body: JSON.stringify({project: params.get('project') || identity[0], id: params.get('id'), body: body.value}),
        signal: AbortSignal.timeout(20000)
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'The note could not be saved.');
      const comment = result.comment;
      if(window.bpOrder)window.bpOrder.updated_at=result.task?.updated_at || comment.created_at;
      const section = document.createElement('section');
      const heading = document.createElement('h3'); heading.textContent = `${comment.author} · ${comment.created_at}`;
      const text = document.createElement('p'); text.style.whiteSpace = 'pre-wrap'; text.textContent = comment.body;
      section.append(heading, text);
      const comments = document.getElementById('comments');
      if (comments.textContent === 'No comments yet.') comments.replaceChildren();
      comments.append(section); document.getElementById('state').textContent = document.getElementById('state').textContent.replace(/Updated .*/, 'Updated ' + comment.created_at); body.value = ''; status.textContent = 'Note saved to WorkLane.';
    } catch (error) {
      status.dataset.error = 'true';
      status.textContent = error.name === 'TimeoutError' || error.name === 'TypeError' ? 'The response was interrupted. Refresh the record before retrying; the note may already be saved.' : error.message;
    } finally { saving = false; button.disabled = false; body.disabled = false; }
  });
})();

(() => {
  const $ = id => document.getElementById(id);
  let saving = false;
  function configure() {
    const action = $('work-action').value, order = window.bpOrder;
    if (!order) return;
    $('work-controls').hidden = ['done','canceled','cancelled'].includes(order.status);
    for (const [name, visible] of [['priority',action==='priority'],['reason',action==='hold'],['agent',action==='assign']]) {
      $('action-'+name).hidden = !visible; $(name+'-label').hidden = !visible;
    }
    $('action-reason').required = action==='hold';
    const options = order.assignment_options || [];
    $('action-submit').disabled = saving || (action==='assign' && !options.length) || (action==='resume' && !order.gate_type);
    $('action-explanation').textContent = action==='assign' && !options.length ? 'No local agent is registered for this project. Remote repository activity does not create an assignable agent.' : action==='resume' ? (order.gate_type ? 'Clear the current hold. The assigned agent can resume when WorkLane considers this work ready.' : 'This work order has no hold to release.') : '';
  }
  window.addEventListener('bp-order-ready', () => {
    const order=window.bpOrder; $('action-priority').value=String(order.priority);
    $('action-agent').replaceChildren(...(order.assignment_options || []).map(agent=>new Option(agent.name,agent.id)));
    configure();
  });
  $('work-action').addEventListener('change',configure);
  $('action-form').addEventListener('submit', async event => {
    event.preventDefault(); if(saving || !window.bpOrder)return;
    const order=window.bpOrder, action=$('work-action').value;
    const value=action==='priority'?Number($('action-priority').value):action==='hold'?$('action-reason').value:action==='assign'?$('action-agent').value:null;
    saving=true;configure();$('action-result').textContent='Applying through WorkLane…';
    try {
      const response=await fetch('/api/work-order/action',{method:'POST',headers:{'Content-Type':'application/json','X-BluePrint-Action':'work-order'},body:JSON.stringify({project:order.project,id:order.ext_id,action,value,expected_updated_at:order.updated_at}),signal:AbortSignal.timeout(20000)});
      const result=await response.json();if(!response.ok || !result.ok)throw new Error(result.error || 'Change failed.');
      location.reload();
    } catch(error) { $('action-result').textContent=error.name==='TimeoutError' || error.name==='TypeError' ? 'Response interrupted. Reload before retrying; the change may already be saved.' : error.message; }
    finally {saving=false;configure();}
  });
})();
