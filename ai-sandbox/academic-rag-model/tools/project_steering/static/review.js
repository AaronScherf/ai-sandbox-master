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
  root.append(scoreBatches(data));
  root.append(routingBatches(data));
  const sections = [
    ['Next three', data.ranking.shortlist], ['Full scored order', data.ranking.ready],
    ...Object.entries(data.ranking.groups).map(([name, nodes]) => [name.replaceAll('_', ' '), nodes])
  ];
  for (const [name, nodes] of sections) {
    const section = document.createElement('section'); section.append(txt('h2', name));
    if (!nodes.length) section.append(txt('p', 'No items.'));
    if (name === 'Full scored order' && nodes.length) section.append(scoredTable(nodes));
    else for (const node of nodes) section.append(card(node));
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
      const inputs = [];
      const withScores = ids.filter(id => data.score_proposals[id]?.status === 'approved');
      if (kind.startsWith('Proposed') && ids.length) {
        const controls = document.createElement('div'); controls.className = 'batch-controls';
        const selectAll = document.createElement('label');
        const toggle = document.createElement('input'); toggle.type = 'checkbox';
        toggle.setAttribute('aria-label', `Select all ${agent} proposed routes`);
        toggle.addEventListener('change', () => {
          for (const input of inputs) { input.checked = toggle.checked;
            if (toggle.checked) selected.add(input.value); else selected.delete(input.value); }
          if (details._selectScores) details._selectScores.checked = false;
        });
        selectAll.append(toggle, txt('span', ` Select all ${agent} (${ids.length})`)); controls.append(selectAll);
        details._selectAll = toggle;
        const scoreLabel = document.createElement('label');
        const scoreToggle = document.createElement('input'); scoreToggle.type = 'checkbox';
        scoreToggle.setAttribute('aria-label', `Select only ${agent} proposed routes with approved score estimates`);
        scoreToggle.disabled = !withScores.length;
        scoreToggle.addEventListener('change', () => {
          for (const input of inputs) {
            input.checked = scoreToggle.checked && withScores.includes(input.value);
            if (input.checked) selected.add(input.value); else selected.delete(input.value);
          }
          toggle.checked = inputs.every(input => input.checked);
        });
        scoreLabel.append(scoreToggle, txt('span', ` Select with approved scores only (${withScores.length})`));
        controls.append(scoreLabel); details.append(controls); details._selectScores = scoreToggle;
      }
      for (const id of ids) {
        const line = document.createElement('p');
        if (kind.startsWith('Proposed')) {
          const input = document.createElement('input'); input.type = 'checkbox'; input.value = id;
          inputs.push(input);
          input.addEventListener('change', () => { if (input.checked) selected.add(id); else selected.delete(id);
            details._selectAll.checked = inputs.every(box => box.checked);
            details._selectScores.checked = inputs.every(box => box.checked === withScores.includes(box.value)); });
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
function scoredTable(nodes) {
  const container = document.createElement('div');
  const filterButton = document.createElement('button'); filterButton.type = 'button'; filterButton.textContent = 'Filter';
  filterButton.setAttribute('aria-expanded', 'false');
  const filters = document.createElement('div'); filters.className = 'table-filters'; filters.hidden = true;
  const search = document.createElement('input'); search.type = 'search'; search.placeholder = 'Task, ID, pipeline, or tag';
  search.setAttribute('aria-label', 'Filter scored tasks by text');
  const agentFilter = document.createElement('select'); agentFilter.setAttribute('aria-label', 'Filter scored tasks by agent');
  for (const value of ['', 'claude', 'gemini', 'codex', 'needs_human']) {
    const option = document.createElement('option'); option.value = value;
    option.textContent = value || 'All agents'; agentFilter.append(option);
  }
  const minimum = document.createElement('input'); minimum.type = 'number'; minimum.placeholder = 'Minimum score';
  minimum.setAttribute('aria-label', 'Minimum score');
  const clear = document.createElement('button'); clear.type = 'button'; clear.textContent = 'Clear filters';
  const count = txt('small', `${nodes.length} of ${nodes.length} tasks`);
  filters.append(search, agentFilter, minimum, clear);
  filterButton.addEventListener('click', () => {
    filters.hidden = !filters.hidden; filterButton.textContent = filters.hidden ? 'Filter' : 'Hide filters';
    filterButton.setAttribute('aria-expanded', String(!filters.hidden));
    if (!filters.hidden) search.focus();
  });
  container.append(filterButton, count, filters);
  const wrapper = document.createElement('div'); wrapper.className = 'table-scroll';
  const table = document.createElement('table'); table.className = 'scored-table';
  const thead = document.createElement('thead'), heading = document.createElement('tr');
  const columns = [['rank','# / ID'], ['task','Task (three words)'], ['section','Pipeline / section'],
    ['added','Added'], ['score','Score'], ['impact','Impact'], ['urgency','Urgency'],
    ['effort','Effort'], ['tags','Agent / tags'], [null,'Actions']];
  const headers = {}; let sortKey = 'rank', ascending = true;
  for (const [key,label] of columns) {
    const th = document.createElement('th'); th.scope = 'col';
    if (key) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'sort-header';
      button.textContent = label; button.setAttribute('aria-label', `Sort by ${label}`);
      button.addEventListener('click', () => { ascending = sortKey === key ? !ascending : true;
        sortKey = key; sortRows(); });
      th.append(button); headers[key] = th;
    } else th.textContent = label;
    heading.append(th);
  }
  headers.rank.setAttribute('aria-sort', 'ascending');
  thead.append(heading); table.append(thead);
  const tbody = document.createElement('tbody'), records = [];
  nodes.forEach((node, index) => {
    const task = node.task, decision = node.decision || {}, route = snapshot.routing.tasks[task.task_id];
    const tr = document.createElement('tr');
    tr.append(txt('td', `${index + 1} · ${task.task_id}`));
    const words = task.title.trim().split(/\s+/).slice(0, 3).join(' ');
    const taskCell = document.createElement('td'); taskCell.title = `${task.task_id}: ${task.title}`; tr.append(taskCell);
    const sectionCell = txt('td', task.section); sectionCell.title = task.section; tr.append(sectionCell);
    tr.append(txt('td', task.added), txt('td', String(node.score)));
    const selects = {};
    for (const [field, values] of [['impact',[0,1,2,3]], ['urgency',[0,1,2,3]],
      ['effort',['unknown','<2h','half_day','1_2_days','larger']]]) {
      const cell = document.createElement('td'), select = document.createElement('select');
      select.setAttribute('aria-label', `${field} for ${task.task_id}`);
      for (const value of values) {
        const option = document.createElement('option'); option.value = value; option.textContent = String(value);
        option.selected = String(decision[field]) === String(value); select.append(option);
      }
      selects[field] = select; cell.append(select); tr.append(cell);
    }
    const routeValues = route.fully_approved ? route.approved : route.proposed;
    const routeLabels = ['agent','complexity','difficulty','context'].map(field => routeValues[field]).filter(Boolean);
    const tags = routeLabels.length ? `${route.fully_approved ? '' : 'Proposed: '}${routeLabels.join(' · ')}` : 'Needs Human Review';
    const tagCell = txt('td', tags); tagCell.title = tags; tr.append(tagCell);
    const actions = document.createElement('td'); actions.className = 'table-actions';
    const save = document.createElement('button'); save.type = 'button'; save.textContent = 'Save scores';
    save.setAttribute('aria-label', `Save scores for ${task.task_id}`);
    save.addEventListener('click', async () => {
      const changes = {impact:Number(selects.impact.value), urgency:Number(selects.urgency.value), effort:selects.effort.value};
      try { await post('/api/decision', {task_id:task.task_id, fingerprint:task.fingerprint,
        source_sha256:snapshot.source_sha256, revision:snapshot.revision, changes}); await load();
      } catch (e) { error.textContent = String(e.message); }
    });
    const expand = document.createElement('button'); expand.type = 'button'; expand.textContent = words;
    expand.className = 'task-expand'; expand.title = task.title;
    expand.setAttribute('aria-expanded', 'false'); expand.setAttribute('aria-label', `Show details for ${task.task_id}: ${task.title}`);
    const detailRow = document.createElement('tr'); detailRow.hidden = true; detailRow.className = 'detail-row';
    const detailCell = document.createElement('td'); detailCell.colSpan = 10; detailRow.append(detailCell);
    const record = {node, index, row:tr, details:detailRow, expanded:false, selects, tags,
      agent:routeValues.agent || route.agent};
    expand.addEventListener('click', () => {
      record.expanded = !record.expanded; detailRow.hidden = !record.expanded;
      expand.setAttribute('aria-expanded', String(record.expanded));
      expand.setAttribute('aria-label', `${record.expanded ? 'Hide' : 'Show'} details for ${task.task_id}: ${task.title}`);
      if (record.expanded && !detailCell.hasChildNodes()) detailCell.append(card(node));
    });
    taskCell.append(expand); actions.append(save); tr.append(actions); tbody.append(tr, detailRow); records.push(record);
  });
  function sortValue(record, key) {
    const task = record.node.task;
    if (key === 'rank') return record.index;
    if (key === 'task') return task.title.toLowerCase();
    if (key === 'section') return task.section.toLowerCase();
    if (key === 'added') return task.added;
    if (key === 'score') return record.node.score;
    if (key === 'impact' || key === 'urgency') return Number(record.selects[key].value);
    if (key === 'effort') return ['<2h','half_day','1_2_days','larger','unknown'].indexOf(record.selects.effort.value);
    return record.tags.toLowerCase();
  }
  function sortRows() {
    for (const [key,th] of Object.entries(headers)) th.setAttribute('aria-sort',
      key === sortKey ? ascending ? 'ascending' : 'descending' : 'none');
    records.sort((a,b) => {
      const left = sortValue(a,sortKey), right = sortValue(b,sortKey);
      if (sortKey === 'added' && (left === 'unknown' || right === 'unknown')) {
        if (left !== right) return left === 'unknown' ? 1 : -1;
      }
      const compared = typeof left === 'number' ? left - right : left.localeCompare(right);
      return (ascending ? compared : -compared) || a.index - b.index;
    });
    tbody.replaceChildren(...records.flatMap(record => [record.row, record.details]));
  }
  function applyFilters() {
    const query = search.value.trim().toLowerCase(), min = minimum.value === '' ? null : Number(minimum.value);
    let shown = 0;
    for (const record of records) {
      const task = record.node.task;
      const text = `${task.task_id} ${task.title} ${task.section} ${record.tags}`.toLowerCase();
      const visible = (!query || text.includes(query)) && (!agentFilter.value || record.agent === agentFilter.value)
        && (min === null || record.node.score >= min);
      record.row.hidden = !visible; record.details.hidden = !visible || !record.expanded;
      if (visible) shown++;
    }
    count.textContent = `${shown} of ${nodes.length} tasks`;
  }
  for (const input of [search, agentFilter, minimum]) input.addEventListener('input', applyFilters);
  clear.addEventListener('click', () => { search.value = ''; agentFilter.value = ''; minimum.value = ''; applyFilters(); });
  table.append(tbody); wrapper.append(table); container.append(wrapper); return container;
}
function scoreBatches(data) {
  const section = document.createElement('section'); section.append(txt('h2', 'Potential priority estimates'));
  section.append(txt('p', 'These are provisional estimates grouped by proposed agent. Approve selected values to put them into the scored ranking, or adjust one task in its fields below. Unknown effort stays in Needs Estimate.'));
  const byId = Object.fromEntries(data.tasks.map(task => [task.task_id, task]));
  const ids = Object.entries(data.score_proposals).filter(([,row]) => row.status === 'unapproved')
    .map(([id]) => id);
  const agentFor = id => { const route = data.routing.tasks[id];
    return route.fully_approved ? route.agent : route.proposed.agent || 'needs_human'; };
  const selected = new Set();
  for (const [agent,label] of [['claude','Claude'], ['gemini','Gemini'], ['codex','Codex'], ['needs_human','Needs Human Review']]) {
    const agentIds = ids.filter(id => agentFor(id) === agent);
    const details = document.createElement('details');
    details.append(txt('summary', `${label}: ${agentIds.length} awaiting review`));
    if (!agentIds.length) { details.append(txt('p', 'No pending estimates.')); section.append(details); continue; }
    const controls = document.createElement('div'); controls.className = 'batch-controls';
    const inputs = [];
    const select = (input, checked) => { input.checked = checked;
      if (checked) selected.add(input.value); else selected.delete(input.value); };
    const allLabel = document.createElement('label'), all = document.createElement('input'); all.type = 'checkbox';
    all.setAttribute('aria-label', `Select all ${label} score estimates`);
    all.addEventListener('change', () => { for (const input of inputs) select(input, all.checked); });
    allLabel.append(all, txt('span', ` Select all ${agentIds.length}`)); controls.append(allLabel);
    for (const confidence of ['high', 'medium', 'low']) {
      const matching = agentIds.filter(id => data.score_proposals[id].confidence === confidence).length;
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = `Select ${confidence} only (${matching})`; button.disabled = !matching;
      button.addEventListener('click', () => {
        for (const input of inputs) select(input, data.score_proposals[input.value].confidence === confidence);
        all.checked = inputs.every(input => input.checked);
      });
      controls.append(button);
    }
    details.append(controls);
    for (const id of agentIds) {
      const row = data.score_proposals[id], line = document.createElement('p');
      const input = document.createElement('input'); input.type = 'checkbox'; input.value = id; inputs.push(input);
      input.setAttribute('aria-label', `Select score estimate for ${id}`);
      input.addEventListener('change', () => { select(input, input.checked);
        all.checked = inputs.every(box => box.checked); });
      line.append(input, txt('span', ` ${id} · ${byId[id]?.title || id} · impact ${row.impact}, urgency ${row.urgency}, effort ${row.effort} (${row.confidence} confidence)`));
      line.append(txt('small', ` ${row.rationale}`)); details.append(line);
    }
    section.append(details);
  }
  const button = document.createElement('button'); button.textContent = 'Approve selected score estimates';
  button.addEventListener('click', async () => {
    if (!selected.size) { error.textContent = 'Select score estimates first.'; return; }
    try { const result = await post('/api/scores/approve', {source_sha256:snapshot.source_sha256,
      revision:snapshot.revision,task_ids:[...selected]}); await load();
      if (result.stale.length) error.textContent = `Skipped stale scores: ${result.stale.join(', ')}`;
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
  const scoreProposal = snapshot.score_proposals[task.task_id];
  if (scoreProposal) article.append(txt('p', `Potential score (${scoreProposal.status}, ${scoreProposal.confidence} confidence): impact ${scoreProposal.impact}, urgency ${scoreProposal.urgency}, effort ${scoreProposal.effort}. ${scoreProposal.rationale}`));
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
  if (scoreProposal && scoreProposal.status === 'unapproved') {
    const use = document.createElement('button'); use.type = 'button'; use.textContent = 'Fill fields from potential score';
    use.addEventListener('click', () => { for (const field of ['impact','urgency','effort'])
      form.elements.namedItem(field).value = String(scoreProposal[field]); });
    form.append(use);
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
