const token = new URLSearchParams(location.search).get('token');
let snapshot;
const root = document.getElementById('root');
const error = document.getElementById('error');
const txt = (tag, value) => { const el = document.createElement(tag); el.textContent = value; return el; };
async function post(path, payload) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json',
    'X-Project-Steering-Token':token},body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'Save failed');
  return result;
}
async function load() {
  const response = await fetch('/api/tasks?token=' + encodeURIComponent(token));
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Review unavailable');
  snapshot = data; root.replaceChildren(); error.textContent = '';
  root.append(routingBatches(data));
  const sections = [
    ['Next three', data.ranking.shortlist], ['Full scored order', data.ranking.ready],
    ...Object.entries(data.ranking.groups).map(([name, nodes]) => [name.replaceAll('_', ' '), nodes])
  ];
  for (const [name, nodes] of sections) {
    const section = document.createElement('section'); section.append(txt('h2', name));
    if (!nodes.length) section.append(txt('p', 'No items.'));
    for (const node of nodes) section.append(card(node));
    root.append(section);
  }
  if (data.warnings.length || data.notices.length) {
    const section = document.createElement('section'); section.append(txt('h2', 'Parser diagnostics'));
    for (const item of [...data.warnings, ...data.notices]) section.append(txt('p', `Line ${item.first_line}: ${item.kind} — ${item.excerpt}`));
    root.append(section);
  }
}
function routingBatches(data) {
  const section = document.createElement('section'); section.append(txt('h2', 'Agent routing'));
  section.append(txt('p', 'Proposed routes are unapproved. Only approved routes enter actual agent batches.'));
  const byId = Object.fromEntries(data.tasks.map(task => [task.task_id, task]));
  const selected = new Set();
  for (const [kind, batches] of [['Approved batches',data.routing.approved_batches],
                                  ['Proposed batches — unapproved',data.routing.proposed_batches]]) {
    section.append(txt('h3', kind));
    for (const [agent, ids] of Object.entries(batches)) {
      const details = document.createElement('details');
      details.append(txt('summary', `${agent}: ${ids.length} tasks`));
      for (const id of ids) {
        const line = document.createElement('p');
        if (kind.startsWith('Proposed')) {
          const input = document.createElement('input'); input.type = 'checkbox'; input.value = id;
          input.addEventListener('change', () => input.checked ? selected.add(id) : selected.delete(id));
          line.append(input);
        }
        line.append(txt('span', ` ${id} · ${byId[id]?.title || id}`)); details.append(line);
      }
      section.append(details);
    }
  }
  const button = document.createElement('button'); button.textContent = 'Approve selected proposed routes and tags';
  button.addEventListener('click', async () => {
    if (!selected.size) { error.textContent = 'Select proposed tasks first.'; return; }
    try {
      const result = await post('/api/routing/approve', {source_sha256:snapshot.source_sha256,
        revision:snapshot.revision,task_ids:[...selected]});
      await load();
      if (result.stale.length) error.textContent = `Skipped stale suggestions: ${result.stale.join(', ')}`;
    } catch (e) { error.textContent = String(e.message); }
  });
  section.append(button); return section;
}
function card(node) {
  const task = node.task, decision = node.decision || {};
  const route = snapshot.routing.tasks[task.task_id];
  const article = document.createElement('article');
  article.append(txt('h3', task.title));
  article.append(txt('small', `${task.task_id} · ${task.section} · added ${task.added} · line ${task.first_line}`));
  const source = document.createElement('a'); source.href = snapshot.tracker_uri + '#L' + task.first_line;
  source.textContent = 'Open source'; const sourceLine = document.createElement('p'); sourceLine.append(source); article.append(sourceLine);
  article.append(txt('p', node.score === null ? node.reasons.join('; ') || 'Needs owner estimates' :
    `Score ${node.score}: impact +${node.terms.impact}, urgency +${node.terms.urgency}, unlock +${node.terms.unlock}, effort −${node.terms.effort_penalty}`));
  if (node.selection_reason) article.append(txt('p', node.selection_reason));
  const proposed = Object.entries(route.proposed).filter(([,value]) => value !== null)
    .map(([field,value]) => `${field}: ${value}`).join('; ');
  const approved = Object.entries(route.approved).filter(([,value]) => value !== null)
    .map(([field,value]) => `${field}: ${value}`).join('; ');
  article.append(txt('p', `Route: ${route.agent} (${route.agent_source}). Approved tags: ${approved || 'none'}.`));
  if (proposed) article.append(txt('p', `Proposed — ${route.proposal_status}: ${proposed}`));
  const routeForm = document.createElement('form');
  const choices = {agent:['claude','gemini','codex','needs_human'],
    complexity:['trivial','moderate','complex'], difficulty:['low','medium','high'],
    context:['self_contained','needs_repo_context','needs_external_context']};
  for (const [field, values] of Object.entries(choices)) {
    const label = document.createElement('label'); label.append(txt('span', field + ' '));
    const select = document.createElement('select'); select.name = field;
    for (const value of ['',...values]) { const option = document.createElement('option'); option.value = value;
      option.textContent = value || '(unapproved)'; option.selected = (route.approved[field] || '') === value;
      select.append(option); }
    label.append(select); routeForm.append(label);
  }
  const dateLabel = document.createElement('label'); dateLabel.append(txt('span','Not before '));
  const notBefore = document.createElement('input'); notBefore.type = 'date'; notBefore.name = 'not_before';
  notBefore.value = route.not_before || ''; dateLabel.append(notBefore); routeForm.append(dateLabel);
  const routeButton = document.createElement('button'); routeButton.textContent = 'Save route and tags'; routeForm.append(routeButton);
  routeForm.addEventListener('submit', async event => {
    event.preventDefault(); const fields = new FormData(routeForm);
    const changes = Object.fromEntries(Object.keys(choices).map(field => [field, fields.get(field) || null]));
    changes.not_before = fields.get('not_before') || null;
    try { await post('/api/routing/decision', {task_id:task.task_id, fingerprint:task.fingerprint,
      source_sha256:snapshot.source_sha256, revision:snapshot.revision, changes}); await load();
    } catch (e) { error.textContent = String(e.message); }
  });
  article.append(routeForm);
  const form = document.createElement('form');
  for (const [field, choices] of [['impact', ['unknown',0,1,2,3]], ['urgency',['unknown',0,1,2,3]],
      ['effort',['unknown','<2h','half_day','1_2_days','larger']], ['status',['candidate','in_progress','done','deferred','declined']]]) {
    const label = document.createElement('label'); label.append(txt('span', field + ' '));
    const select = document.createElement('select'); select.name = field;
    for (const value of choices) { const option = document.createElement('option'); option.value = value;
      option.textContent = String(value); option.selected = String(decision[field] ?? 'unknown') === String(value); select.append(option); }
    label.append(select); form.append(label);
  }
  for (const [field, value] of [['depends_on', (decision.depends_on || []).join(', ')], ['defer_until', decision.defer_until || '']]) {
    const label = document.createElement('label'); label.append(txt('span', field + ' '));
    const input = document.createElement('input'); input.name = field; input.value = value;
    input.placeholder = field === 'depends_on' ? 'TODO-0001, TODO-0002' : 'YYYY-MM-DD'; label.append(input); form.append(label);
  }
  for (const suggestion of node.suggestions || []) {
    const label = document.createElement('label'); label.append(txt('span',
      `Suggested prerequisite ${suggestion.target} from “${suggestion.evidence}”: `));
    const select = document.createElement('select'); select.name = 'suggestion_' + suggestion.target;
    for (const value of ['leave', 'confirm', 'reject']) { const option = document.createElement('option');
      option.value = value; option.textContent = value; select.append(option); } label.append(select); form.append(label);
  }
  if (decision.recheck) { const label = document.createElement('label'); const input = document.createElement('input');
    input.type = 'checkbox'; input.name = 'ack'; label.append(input, txt('span', ' Acknowledge changed task')); form.append(label); }
  const button = document.createElement('button'); button.textContent = 'Save decision'; form.append(button);
  form.addEventListener('submit', async event => {
    event.preventDefault(); const fields = new FormData(form);
    const changes = {impact:Number(fields.get('impact')), urgency:Number(fields.get('urgency')),
      effort:fields.get('effort'), status:fields.get('status'),
      depends_on:String(fields.get('depends_on')).split(',').map(x=>x.trim()).filter(Boolean),
      defer_until:fields.get('defer_until') || null};
    const rejected = [...(decision.rejected_suggestions || [])];
    for (const suggestion of node.suggestions || []) {
      const choice = fields.get('suggestion_' + suggestion.target);
      if (choice === 'confirm') changes.depends_on.push(suggestion.target);
      if (choice === 'reject') rejected.push(suggestion.target);
    }
    changes.depends_on = [...new Set(changes.depends_on)]; changes.rejected_suggestions = [...new Set(rejected)];
    if (decision.recheck && fields.get('ack')) changes.recheck = false;
    if (fields.get('impact') === 'unknown' || fields.get('urgency') === 'unknown') {
      error.textContent = 'Choose impact and urgency before saving.'; return;
    }
    try { const response = await fetch('/api/decision', {method:'POST',headers:{'Content-Type':'application/json',
      'Origin':location.origin,'X-Project-Steering-Token':token},body:JSON.stringify({task_id:task.task_id,
      fingerprint:task.fingerprint,source_sha256:snapshot.source_sha256,revision:snapshot.revision,changes})});
      const result = await response.json(); if (!response.ok) throw Error(result.error); await load();
    } catch (e) { error.textContent = String(e.message); }
  });
  article.append(form); return article;
}
document.getElementById('close').addEventListener('click', async () => {
  await fetch('/api/close',{method:'POST',headers:{'Content-Type':'application/json','Origin':location.origin,
    'X-Project-Steering-Token':token},body:'{}'}); window.close();
});
load().catch(e => error.textContent = String(e.message));
