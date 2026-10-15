(function () {
  "use strict";
  var CG = self.CG;
  var G = JSON.parse(document.getElementById("graph-data").textContent);
  var $ = function (sel) { return document.querySelector(sel); };
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var nodesById = new Map(G.nodes.map(function (n) { return [n.id, n]; }));
  var edgesById = new Map(G.edges.map(function (e) { return [e.id, e]; }));
  var sectionsById = new Map(G.sections.map(function (s) { return [s.id, s]; }));
  function nameOf(id) { var n = nodesById.get(id); return n ? n.name : id; }

  var storage = CG.safeStorage(window);
  var STORE_KEY = "cg-review-" + G.graph_version;
  var decisions = [];
  try { decisions = JSON.parse(storage.get(STORE_KEY) || "[]"); } catch (e) { decisions = []; }
  var reviewer = storage.get("cg-reviewer") || "";
  var PROPOSAL_KEY = "cg-proposals-" + G.graph_version;
  var proposals = [];
  try { proposals = JSON.parse(storage.get(PROPOSAL_KEY) || "[]"); } catch (e) { proposals = []; }
  var KINDS = (G.vocab && G.vocab.kinds) || Array.from(new Set(G.nodes.map(function (n) { return n.kind; }))).sort();
  var pickOrder = []; // concept ids in the order they were selected, so the first one is the source
  var orderedPick = true;           // true after clicks and Ctrl-clicks (first = source); false after box, range or section
  var collapsed = new Set();
  try { JSON.parse(storage.get("cg-collapsed-" + G.graph_version) || "[]").forEach(function (id) { collapsed.add(id); }); } catch (e) { /* none */ }
  var activeSections = [];          // section ids whose button is highlighted (the filter)
  var lastListId = null;            // anchor for Shift-click ranges in the concept list
  var lastAdded = [];               // concepts added by the latest selection gesture
  function selectedIds() {
    return cy.nodes(":selected").filter(function (n) { return !n.hasClass("ghost"); }).map(function (n) { return n.id(); });
  }
  function visibleSet() {
    return new Set(CG.filterNodes(G.nodes, filters).map(function (n) { return n.id; }));
  }
  function setSelection(ids, ordered) {
    if (ordered !== undefined) orderedPick = ordered; // true: first concept is the source; false: an unordered group
    var before = new Set(selectedIds());
    lastAdded = ids.filter(function (id) { return !before.has(id); });
    cy.batch(function () {
      cy.elements().unselect();
      ids.forEach(function (id) { var el = cy.getElementById(id); if (el.nonempty() && !el.hasClass("hidden")) el.select(); });
    });
  }
  var selected = null; // {kind, id}
  var prereqMode = false;
  var editing = null; // field name being edited
  var flash = null; // {kind, id, text}: a "saved" confirmation shown under the review buttons
  var filters = { q: "", topics: [], sections: [], kinds: [], statuses: [] };
  var hiddenEdgeTypes = new Set();

  // ---- rendering helpers ----------------------------------------------------
  function rich(text, opts) {
    if (!text) return "";
    var splitter = opts && opts.formal ? CG.splitFormal : CG.splitMath;
    return "<p>" + splitter(text).map(function (p) {
      if (p.type === "text") return esc(p.value).replace(/\n\n+/g, "</p><p>").replace(/\n/g, "<br>");
      try {
        return window.katex.renderToString(p.value, { displayMode: p.type === "display", output: "mathml", throwOnError: false });
      } catch (e) { return "<code>" + esc(p.value) + "</code>"; }
    }).join("") + "</p>";
  }
  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.hidden = true; }, 6000);
  }
  function persist() {
    storage.set(STORE_KEY, JSON.stringify(decisions));
    storage.set(PROPOSAL_KEY, JSON.stringify(proposals));
    var n = decisions.length + proposals.length;
    $("#decision-count").textContent = n + (n === 1 ? " decision" : " decisions");
    renderProposals();
  }

  // ---- decisions ------------------------------------------------------------
  function item(kind, id) { return kind === "node" ? nodesById.get(id) : edgesById.get(id); }
  function decisionsFor(kind, id) {
    return decisions.filter(function (d) { return d.target.kind === kind && d.target.id === id; });
  }
  function effective(kind, id, field) {
    var d = decisionsFor(kind, id).filter(function (x) { return x.action === "edit" && x.field === field; })[0];
    return d ? d.new_value : item(kind, id)[field];
  }
  function decide(kind, id, action, extra) {
    var d = Object.assign({ target: { kind: kind, id: id }, action: action }, extra || {});
    decisions = CG.recordDecision(decisions, d);
    persist(); paintDecisions(); renderPanel();
  }
  function undecide(kind, id, action, field) {
    var key = CG.decisionKey({ target: { kind: kind, id: id }, action: action, field: field });
    decisions = decisions.filter(function (d) { return CG.decisionKey(d) !== key; });
    persist(); paintDecisions(); renderPanel();
  }

  // ---- graph ----------------------------------------------------------------
  var topicIndex = new Map(G.vocab.topics.map(function (t, i) { return [t, i]; }));
  function topicColor(t) { return "hsl(" + (((topicIndex.get(t) || 0) * 67 + 210) % 360) + ", 52%, 36%)"; }
  var EDGE_STYLE = {
    is_a: { color: "#64748b", arrow: "triangle-tee", label: "is a" },
    has_property: { color: "#0e7490", arrow: "vee", label: "has property" },
    defined_on: { color: "#4d7c0f", arrow: "vee", label: "defined on" },
    component_of: { color: "#a16207", arrow: "diamond", label: "part of" },
    implies: { color: "#1d4ed8", arrow: "triangle", label: "implies" },
    iff: { color: "#7e22ce", arrow: "triangle", label: "iff" },
    hypothesis_of: { color: "#be185d", arrow: "triangle", label: "hypothesis of" },
    yields: { color: "#be185d", arrow: "triangle", label: "yields" },
    counterexample_to: { color: "#b91c1c", arrow: "tee", label: "counterexample to" }
  };
  var pos = CG.spreadLayout(G.nodes, G.edges, G.sections);
  var elements = G.nodes.map(function (n) {
    var sec = sectionsById.get(n.section);
    return {
      group: "nodes",
      data: { id: n.id, label: n.name, color: topicColor(n.topic), status: n.status },
      classes: sec && sec.state === "planned" ? "planned" : "",
      position: pos[n.id]
    };
  }).concat(G.edges.map(function (e) {
    var st = EDGE_STYLE[e.type] || EDGE_STYLE.is_a;
    return {
      group: "edges",
      data: { id: e.id, source: e.source, target: e.target, type: e.type, status: e.status, color: st.color, arrow: st.arrow, label: st.label }
    };
  }));

  var cy = cytoscape({
    container: $("#cy"),
    elements: elements,
    layout: { name: "preset" },
    wheelSensitivity: 0.25, minZoom: 0.08, maxZoom: 3,
    style: [
      { selector: "node", style: { "background-color": "data(color)", label: "data(label)", color: "#fff", "text-wrap": "wrap", "text-max-width": 150, "font-size": 16, "text-valign": "center", "text-halign": "center", shape: "round-rectangle", width: "label", height: "label", padding: "10px", "border-width": 2, "border-color": "data(color)" } },
      { selector: "node[status = 'proposed']", style: { "border-style": "dashed", "border-color": "#e7e5e4" } },
      { selector: "node.ghost", style: { opacity: 0.75, "border-style": "dotted", "border-width": 3, "border-color": "#a8a29e" } },
      { selector: "edge.ghost", style: { opacity: 0.75, "line-style": "dotted" } },
      { selector: "node.planned", style: { opacity: 0.4 } },
      { selector: "node.accepted", style: { "border-color": "#16a34a", "border-width": 4, "border-style": "solid" } },
      { selector: "node.rejected, edge.rejected", style: { opacity: 0.25 } },
      { selector: "node.faded, edge.faded", style: { opacity: 0.1 } },
      { selector: "node.hidden, edge.hidden", style: { display: "none" } },
      { selector: "node:selected", style: { "border-width": 4, "border-color": "#f59e0b", "border-style": "solid" } },
      { selector: "edge", style: { width: 2, "curve-style": "bezier", "line-color": "data(color)", "target-arrow-color": "data(color)", "target-arrow-shape": "data(arrow)", "arrow-scale": 1.2 } },
      { selector: "edge[status = 'proposed']", style: { "line-style": "dashed" } },
      { selector: "edge[type = 'iff']", style: { "source-arrow-shape": "triangle", "source-arrow-color": "data(color)" } },
      { selector: "edge.accepted", style: { width: 4 } },
      { selector: "edge.labelled", style: { label: "data(label)", "font-size": 11, color: "#111", "text-background-color": "#fff", "text-background-opacity": 0.92, "text-background-padding": 2, "text-rotation": "autorotate" } },
      { selector: "edge:selected", style: { width: 4, "line-color": "#f59e0b", "target-arrow-color": "#f59e0b" } }
    ]
  });
  cy.fit(undefined, 30);

  function paintDecisions() {
    cy.elements().removeClass("accepted rejected");
    decisions.forEach(function (d) {
      var el = cy.getElementById(d.target.id);
      if (!el.nonempty()) return;
      if (d.action === "accept") el.addClass("accepted");
      if (d.action === "reject") el.addClass("rejected");
    });
  }

  function applyFilters() {
    var visible = new Set(CG.filterNodes(G.nodes, filters).map(function (n) { return n.id; }));
    cy.nodes().forEach(function (n) { n.toggleClass("hidden", !n.hasClass("ghost") && !visible.has(n.id())); });
    cy.edges().forEach(function (e) {
      var hide = hiddenEdgeTypes.has(e.data("type")) || !visible.has(e.data("source")) || !visible.has(e.data("target"));
      e.toggleClass("hidden", !e.hasClass("ghost") && hide);
    });
    var still = selectedIds().filter(function (id) { return visible.has(id); });
    if (still.length !== selectedIds().length) setSelection(still);
    renderNameList(visible);
  }

  function applyPrereqMode() {
    cy.elements().removeClass("faded");
    if (!prereqMode || !selected || selected.kind !== "node") return;
    var keep = CG.prerequisites(selected.id, G.edges);
    keep.add(selected.id);
    cy.nodes().forEach(function (n) { if (!keep.has(n.id())) n.addClass("faded"); });
    cy.edges().forEach(function (e) { if (!(keep.has(e.data("source")) && keep.has(e.data("target")))) e.addClass("faded"); });
  }

  function select(kind, id, focus) {
    selected = { kind: kind, id: id }; editing = null; flash = null;
    cy.elements().unselect();
    cy.edges().removeClass("labelled");
    var el = cy.getElementById(id);
    if (el.nonempty()) {
      el.select();
      if (kind === "node") el.connectedEdges().addClass("labelled");
      else el.addClass("labelled");
      if (focus) cy.animate({ center: { eles: el }, duration: 250 });
    }
    applyPrereqMode(); renderPanel(); renderNameList();
  }
    cy.on("tap", "node", function (ev) {
    if (ev.target.hasClass("ghost")) return;
    var oe = ev.originalEvent || {};
    if (oe.ctrlKey || oe.metaKey || oe.shiftKey) { lastAdded = [ev.target.id()]; return; } // Cytoscape toggles it
    lastListId = ev.target.id();
    select("node", ev.target.id(), false);
  });
  cy.on("tap", "edge", function (ev) { if (ev.target.hasClass("ghost")) return; select("edge", ev.target.id(), false); });
  cy.on("tap", function (ev) { if (ev.target === cy) { selected = null; cy.elements().unselect(); cy.edges().removeClass("labelled"); applyPrereqMode(); renderPanel(); renderNameList(); } });

  // ---- sidebar --------------------------------------------------------------
  function renderNameList(visibleArg) {
    var visible = visibleArg || visibleSet();
    var sel = new Set(selectedIds());
    var html = "";
    G.sections.slice().sort(function (a, b) { return a.order - b.order; }).forEach(function (s) {
      var list = G.nodes.filter(function (n) { return n.section === s.id && visible.has(n.id); })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      if (!list.length) return;
      var open = !collapsed.has(s.id) || (filters.q || "").trim() !== "";
      var count = list.filter(function (n) { return sel.has(n.id); }).length;
      html += '<h3><button type="button" class="chev" data-chev="' + esc(s.id) + '" aria-expanded="' + open + '">' + (open ? "\u25be" : "\u25b8") + "</button>" +
        '<button type="button" class="sec-title" data-section-head="' + esc(s.id) + '">' + esc(s.title) + (s.state === "planned" ? " (planned)" : "") + "</button>" +
        (count ? '<span class="sec-count">' + count + " of " + list.length + " selected</span>" : "") + "</h3>";
      html += '<div class="sec-group' + (open ? "" : " collapsed-group") + '">';
      list.forEach(function (n) {
        var cls = (s.state === "planned" ? "planned " : "") + (sel.has(n.id) ? "sel" : "");
        html += '<button type="button" class="' + cls + '" data-node="' + esc(n.id) + '">' + esc(n.name) + "</button>";
      });
      html += "</div>";
    });
    $("#name-list").innerHTML = html || '<p class="hint">No concepts match.</p>';
  }
  function saveCollapsed() { storage.set("cg-collapsed-" + G.graph_version, JSON.stringify(Array.from(collapsed))); }
  $("#name-list").addEventListener("click", function (ev) {
    var chev = ev.target.closest("button[data-chev]");
    if (chev) {
      var sid = chev.getAttribute("data-chev");
      if (collapsed.has(sid)) collapsed.delete(sid); else collapsed.add(sid);
      saveCollapsed(); renderNameList(); return;
    }
    var head = ev.target.closest("button[data-section-head]");
    if (head) { selectSection(head.getAttribute("data-section-head")); return; }
    var b = ev.target.closest("button[data-node]"); if (!b) return;
    var id = b.getAttribute("data-node");
    var mod = ev.ctrlKey || ev.metaKey, shift = ev.shiftKey;
    orderedPick = true;
    if (shift && lastListId) {
      var vis = visibleSet();
      setSelection(CG.rangeIds(CG.listOrder(G.sections, G.nodes), lastListId, id).filter(function (x) { return vis.has(x); }));
      orderedPick = false;
    } else if (mod) {
      setSelection(CG.toggleId(selectedIds(), id)); lastListId = id;
    } else {
      lastListId = id; select("node", id, true);
    }
  });
  $("#btn-collapse-all").addEventListener("click", function () {
    G.sections.forEach(function (s) { collapsed.add(s.id); }); saveCollapsed(); renderNameList();
  });
  $("#btn-expand-all").addEventListener("click", function () { collapsed.clear(); saveCollapsed(); renderNameList(); });
  function selectSection(sectionId) {
    var vis = visibleSet();
    setSelection(G.nodes.filter(function (n) { return n.section === sectionId && vis.has(n.id); }).map(function (n) { return n.id; }));
    orderedPick = false;
  }

  function buildFilters() {
    var topics = $("#f-topics");
    var ordered = G.sections.slice().sort(function (a, b) { return a.order - b.order; });
    topics.innerHTML = ordered.map(function (s) {
      return '<button type="button" data-section="' + esc(s.id) + '" title="' + esc(s.title) + '">' + esc(s.short || s.title) + "</button>";
    }).join("");
    topics.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-section]"); if (!b) return;
      var sid = b.getAttribute("data-section");
      var step = CG.sectionButtonClick(activeSections, sid);
      var removed = activeSections.filter(function (x) { return step.active.indexOf(x) === -1; });
      activeSections = step.active;
      filters.sections = activeSections.slice();
      Array.from(topics.querySelectorAll("button")).forEach(function (x) {
        x.classList.toggle("on", activeSections.indexOf(x.getAttribute("data-section")) !== -1);
      });
      applyFilters();
      if (step.select) selectSection(step.select);
      else if (removed.length) {
        var gone = new Set(G.nodes.filter(function (n) { return removed.indexOf(n.section) !== -1; }).map(function (n) { return n.id; }));
        setSelection(selectedIds().filter(function (id) { return !gone.has(id); }));
      }
    });
    var kinds = Array.from(new Set(G.nodes.map(function (n) { return n.kind; }))).sort();
    $("#f-kind").insertAdjacentHTML("beforeend", kinds.map(function (k) { return '<option value="' + esc(k) + '">' + esc(k) + "</option>"; }).join(""));
    $("#f-kind").addEventListener("change", function (ev) { filters.kinds = ev.target.value ? [ev.target.value] : []; applyFilters(); });
    $("#f-status").addEventListener("change", function (ev) { filters.statuses = ev.target.value ? [ev.target.value] : []; applyFilters(); });
    $("#search").addEventListener("input", function (ev) { filters.q = ev.target.value; applyFilters(); });
    var used = Array.from(new Set(G.edges.map(function (e) { return e.type; })));
    $("#f-edges").innerHTML = used.map(function (t) { return '<button type="button" class="on" data-etype="' + t + '">' + esc(EDGE_STYLE[t].label) + "</button>"; }).join("");
    $("#f-edges").addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-etype]"); if (!b) return;
      var t = b.getAttribute("data-etype");
      if (hiddenEdgeTypes.has(t)) hiddenEdgeTypes.delete(t); else hiddenEdgeTypes.add(t);
      b.classList.toggle("on", !hiddenEdgeTypes.has(t)); applyFilters();
    });
    $("#legend-body").innerHTML =
      "<p>Boxes are concepts, coloured by section; higher on the page means later in the course. A dashed outline means not yet reviewed. Faded boxes are in sections not taught yet.</p>" +
      "<p>Arrows read as sentences: select a concept to see every connection written out.</p><ul>" +
      Object.keys(EDGE_STYLE).map(function (t) { return '<li><span style="color:' + EDGE_STYLE[t].color + '">&#9632;</span> ' + esc(EDGE_STYLE[t].label) + "</li>"; }).join("") + "</ul>";
  }

  // ---- detail panel ---------------------------------------------------------
  function fieldBlock(kind, id, field, label, opts) {
    var it = item(kind, id);
    var value = effective(kind, id, field);
    if (!value && editing !== field) {
      return '<div class="field"><h4>' + label + '<button type="button" data-act="edit" data-field="' + field + '">Add</button></h4></div>';
    }
    if (editing === field) {
      return '<div class="field"><h4>' + label + '</h4><textarea id="edit-box">' + esc(value || "") + '</textarea>' +
        '<div class="actions"><button type="button" class="primary" data-act="save-edit" data-field="' + field + '">Save edit</button>' +
        '<button type="button" data-act="cancel-edit">Cancel</button></div></div>';
    }
    var edited = decisionsFor(kind, id).some(function (d) { return d.action === "edit" && d.field === field; });
    return '<div class="field"><h4>' + label + (edited ? ' <span class="badge proposed">edited</span>' : "") +
      '<button type="button" data-act="edit" data-field="' + field + '">Edit</button></h4>' + rich(value, opts) + "</div>";
  }
  function citations(it) {
    if (!it.citations || !it.citations.length) return "";
    return '<div class="field"><h4>Sources</h4><p class="cite">' + it.citations.map(function (c) { return esc(c.source + " " + c.ref); }).join(" &middot; ") + "</p></div>";
  }
  function criticBadge(it) {
    return it.critic && it.critic.verdict !== "supports"
      ? ' <span class="badge flag" title="' + esc(it.critic.note || "") + '">check: ' + esc(it.critic.verdict) + "</span>" : "";
  }
  function reviewControls(kind, id, it) {
    var mine = decisionsFor(kind, id);
    var acc = mine.some(function (d) { return d.action === "accept"; });
    var rej = mine.some(function (d) { return d.action === "reject"; });
    var cm = mine.filter(function (d) { return d.action === "comment"; })[0];
    return '<div class="field"><h4>Your review</h4><div class="actions">' +
      (it.status === "proposed" ? '<button type="button" class="' + (acc ? "on" : "") + '" data-act="accept">Accept</button>' +
        '<button type="button" class="' + (rej ? "on" : "") + '" data-act="reject">Reject</button>' : "") +
      "</div><textarea id=\"comment-box\" placeholder=\"Optional comment for the maintainer\" rows=\"2\" style=\"width:100%\">" + esc(cm ? cm.comment : "") + "</textarea>" +
      '<div class="actions"><button type="button" data-act="comment">Save comment</button></div>' +
      (flash && flash.kind === kind && flash.id === id ? '<p class="saved" role="status">' + esc(flash.text) + "</p>" : "") +
      "</div>";
  }
  function renderGroupPanel(p, ids) {
    var vis = visibleSet();
    var groups = CG.groupBySection(G.sections, G.nodes, ids, vis);
    var open = CG.expandedSection(groups, lastAdded.length ? lastAdded : ids, nodesById);
    p.innerHTML = "<h2>" + ids.length + " concepts selected</h2>" +
      '<div class="actions"><button type="button" data-act="clear-selection">Clear selection</button>' +
      '<button type="button" data-act="add-connection"' + (ids.length > 12 ? " disabled title=\"Select 12 or fewer concepts to propose connections\"" : "") + ">Add connection</button></div>" +
      groups.map(function (g) {
        var s = g.section;
        var head = esc(s.short || s.title) + ", " + g.ids.length + " of " + g.total + " selected" + (g.filtered ? " (filtered)" : "");
        var body = (g.full && s.summary ? '<p class="sec-summary">' + esc(s.summary) + "</p>" : "") +
          '<ul class="chosen">' + g.ids.map(function (id) {
            return '<li><button type="button" data-node="' + esc(id) + '">' + esc(nameOf(id)) + '</button>' +
              '<button type="button" data-remove="' + esc(id) + '" aria-label="Remove ' + esc(nameOf(id)) + ' from the selection">\u00d7</button></li>';
          }).join("") + "</ul>";
        return "<details" + (s.id === open ? " open" : "") + "><summary>" + head + "</summary>" + body + "</details>";
      }).join("");
  }
  function renderPanel() {
    var p = $("#panel");
    var ids = selectedIds();
    if (ids.length >= 2) return renderGroupPanel(p, ids);
    if (!selected) { p.innerHTML = '<p class="hint">Click a concept or a connection to read about it.</p>'; return; }
    if (selected.kind === "node") return renderNode(p);
    return renderEdge(p);
  }
  function renderNode(p) {
    var n = nodesById.get(selected.id), sec = sectionsById.get(n.section);
    var conns = G.edges.filter(function (e) { return e.source === n.id || e.target === n.id || e.via === n.id; });
    p.innerHTML =
      "<h2>" + esc(n.name) + "</h2>" +
      '<p class="meta">' + esc(n.kind) + " &middot; " + esc(n.topic) + " &middot; " + esc(sec ? sec.title : n.section) +
      ' <span class="badge ' + n.status + '">' + n.status + "</span>" + criticBadge(n) + "</p>" +
      fieldBlock("node", n.id, "gist", "Summary") +
      '<div class="actions"><button type="button" class="' + (prereqMode ? "on" : "") + '" data-act="prereq">Show what this needs</button>' +
      '<button type="button" data-act="propose-from">Propose a connection from this concept</button></div>' +
      fieldBlock("node", n.id, "explanation", "Explanation") +
      fieldBlock("node", n.id, "formal", "Formal statement", { formal: true }) +
      fieldBlock("node", n.id, "example", "Example") +
      citations(n) +
      '<div class="field"><h4>Connections</h4><ul class="conn">' +
      (conns.map(function (e) { return '<li><button type="button" data-edge="' + esc(e.id) + '">' + esc(CG.edgeSentence(e, nameOf)) + "</button></li>"; }).join("") || "<li class=\"hint\">None yet.</li>") +
      "</ul></div>" + reviewControls("node", n.id, n);
  }
  function renderEdge(p) {
    var e = edgesById.get(selected.id);
    p.innerHTML =
      "<h2>" + esc(CG.edgeSentence(e, nameOf)) + "</h2>" +
      '<p class="meta">' + esc(EDGE_STYLE[e.type].label) + ' <span class="badge ' + e.status + '">' + e.status + "</span>" + criticBadge(e) + "</p>" +
      fieldBlock("edge", e.id, "condition", "Condition") +
      fieldBlock("edge", e.id, "explanation", "Why") +
      citations(e) +
      '<div class="actions"><button type="button" data-node="' + esc(e.source) + '">Go to ' + esc(nameOf(e.source)) + '</button>' +
      '<button type="button" data-node="' + esc(e.target) + '">Go to ' + esc(nameOf(e.target)) + "</button></div>" +
      reviewControls("edge", e.id, e);
  }

  $("#panel").addEventListener("click", function (ev) {
    var b = ev.target.closest("button"); if (!b) return;
    if (b.hasAttribute("data-remove")) { setSelection(CG.toggleId(selectedIds(), b.getAttribute("data-remove"))); return; }
    if (b.getAttribute("data-act") === "clear-selection") { setSelection([]); return; }
    if (b.getAttribute("data-act") === "add-connection") { $("#btn-connect").click(); return; }
    if (b.hasAttribute("data-node") && (ev.ctrlKey || ev.metaKey)) { setSelection(CG.toggleId(selectedIds(), b.getAttribute("data-node"))); return; }
    if (b.hasAttribute("data-edge")) return select("edge", b.getAttribute("data-edge"), true);
    if (b.hasAttribute("data-node")) return select("node", b.getAttribute("data-node"), true);
    var act = b.getAttribute("data-act"); if (!act || !selected) return;
    if (act === "propose-from") return openProposal("edge", [selected.id], true);
    var kind = selected.kind, id = selected.id, field = b.getAttribute("data-field");
    if (act === "accept" || act === "reject") {
      var already = decisionsFor(kind, id).some(function (d) { return d.action === act; });
      return already ? undecide(kind, id, act) : decide(kind, id, act);
    }
    if (act === "prereq") { prereqMode = !prereqMode; applyPrereqMode(); return renderPanel(); }
    if (act === "edit") { editing = field; return renderPanel(); }
    if (act === "cancel-edit") { editing = null; return renderPanel(); }
    if (act === "save-edit") {
      var text = $("#edit-box").value;
      editing = null;
      decide(kind, id, "edit", { field: field, base_hash: item(kind, id).hashes[field], new_value: text });
      return toast("Edit saved. It will be included when you submit your review.");
    }
    if (act === "comment") {
      var c = $("#comment-box").value.trim();
      flash = { kind: kind, id: id, text: c ? "Comment saved." : "Comment removed." };
      return c ? decide(kind, id, "comment", { comment: c }) : undecide(kind, id, "comment");
    }
  });

  // ---- header: submit / download / clear -------------------------------------
  function needName() {
    if (reviewer.trim()) return true;
    $("#reviewer").focus(); toast("Please type your name first so your review can be credited.");
    return false;
  }
  function currentReview() { return CG.buildReview(G, decisions, reviewer.trim(), new Date().toISOString(), proposals); }
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () { return false; });
    }
    try {
      var ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
      var ok = document.execCommand("copy"); document.body.removeChild(ta); return Promise.resolve(ok);
    } catch (e) { return Promise.resolve(false); }
  }
  function download() {
    if (!needName() || !decisions.length) { if (!decisions.length) toast("Nothing to download yet: accept, reject, edit or comment first."); return; }
    var text = JSON.stringify(currentReview(), null, 2);
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    a.download = "review-" + reviewer.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a); a.click(); a.remove();
  }
  function submit() {
    if (!needName()) return;
    if (!decisions.length) return toast("Nothing to submit yet: accept, reject, edit or comment first.");
    var review = currentReview();
    var text = JSON.stringify(review, null, 2);
    var repo = G.site && G.site.repo;
    if (!repo) return toast("No GitHub repository is configured for this graph. Use Download review and send the file to the maintainer.");
    var res = CG.issueUrl(repo, review);
    copyText(text).then(function (copied) {
      window.open(res.url, "_blank", "noopener");
      toast(res.prefilled ? "A GitHub issue form opened with your review filled in. Press Submit new issue there."
        : copied ? "Your review is copied. Paste it into the box on the GitHub page that opened, then press Submit new issue."
          : "Could not copy automatically. Use Download review and attach the file to the GitHub issue.");
    });
  }
  $("#btn-submit").addEventListener("click", submit);
  $("#btn-download").addEventListener("click", download);
  $("#btn-clear").addEventListener("click", function () {
    var count = decisions.length + proposals.length;
    if (count && !window.confirm("Forget all " + count + " pending decisions and proposals?")) return;
    decisions = []; proposals = []; persist(); paintDecisions(); renderPanel();
  });
  $("#reviewer").value = reviewer;
  $("#reviewer").addEventListener("input", function (ev) { reviewer = ev.target.value; storage.set("cg-reviewer", reviewer); });

  function proposalLabel(p) {
    return p.action === "add_node" ? "Concept: " + p.proposal.name
      : "Connection: " + nameOf(p.proposal.source) + " → " + nameOf(p.proposal.target) + " (" + p.proposal.type + ")";
  }
  function renderProposals() {
    var box = $("#my-proposals");
    box.hidden = proposals.length === 0;
    $("#proposal-list").innerHTML = proposals.map(function (p, i) {
      return "<li><span>" + esc(proposalLabel(p)) + '</span><button type="button" data-withdraw="' + i + '">Withdraw</button></li>';
    }).join("");
    cy.elements(".ghost").remove();
    var placed = new Map();
    proposals.forEach(function (p, i) {
      if (p.action !== "add_node") return;
      var id = "ghost-n" + i;  // by position, so two proposals can never share an element id
      var near = (p.proposal.connections || []).map(function (c) { return cy.getElementById(c.other); }).filter(function (e) { return e.nonempty(); });
      var base = near.length ? near[0].position() : { x: 0, y: 0 };
      cy.add({ group: "nodes", classes: "ghost", data: { id: id, label: p.proposal.name, color: "#78716c", status: "proposed" },
               position: { x: base.x + 60 + 40 * i, y: base.y + 90 } });
      placed.set(CG.slugFromName(p.proposal.name), id);
      (p.proposal.connections || []).forEach(function (c, k) {
        if (!cy.getElementById(c.other).nonempty()) return;
        var s = c.direction === "in" ? c.other : id, t = c.direction === "in" ? id : c.other;
        cy.add({ group: "edges", classes: "ghost", data: { id: id + "-c" + k, source: s, target: t, color: "#78716c", arrow: "triangle", status: "proposed" } });
      });
    });
    proposals.forEach(function (p, i) {
      if (p.action !== "add_edge") return;
      var s = placed.get(p.proposal.source) || p.proposal.source, t = placed.get(p.proposal.target) || p.proposal.target;
      if (cy.getElementById(s).nonempty() && cy.getElementById(t).nonempty()) {
        cy.add({ group: "edges", classes: "ghost", data: { id: "ghost-edge-" + i, source: s, target: t, color: "#78716c", arrow: "triangle", status: "proposed" } });
      }
    });
  }
  $("#proposal-list").addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-withdraw]"); if (!b) return;
    proposals.splice(Number(b.getAttribute("data-withdraw")), 1);
    persist();
  });

  var dialog = $("#propose-dialog"), form = $("#propose-form");
  function nodeOptions(selectedId) {
    return G.nodes.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).map(function (n) {
      return '<option value="' + esc(n.id) + '"' + (n.id === selectedId ? " selected" : "") + ">" + esc(n.name) + "</option>";
    }).join("");
  }
  function typeOptions(current) {
    return Object.keys(EDGE_STYLE).map(function (t) {
      return '<option value="' + t + '"' + (t === current ? " selected" : "") + ">" + esc(EDGE_STYLE[t].label) + "</option>";
    }).join("");
  }
  function connectionRow(c) {
    c = c || {};
    return '<div class="row" data-conn><select data-f="other">' + nodeOptions(c.other) + '</select>' +
      '<select data-f="type">' + typeOptions(c.type || "is_a") + '</select>' +
      '<select data-f="direction"><option value="out"' + (c.direction === "in" ? "" : " selected") + '>this → that</option>' +
      '<option value="in"' + (c.direction === "in" ? " selected" : "") + '>that → this</option></select>' +
      '<button type="button" data-remove-row>×</button>' +
      '<input type="text" data-f="condition" placeholder="Condition (needed for implies / iff)" value="' + esc(c.condition || "") + '" style="grid-column: 1 / -1">' +
      '</div>';
  }
  function openNodeForm() {
    form.onclick = null; form.onchange = null; // the connection form assigns these
    form.innerHTML = '<h2 id="propose-title">Propose a concept</h2>' +
      '<label>Name<input type="text" id="p-name" maxlength="120"></label><div id="p-similar" class="similar" hidden></div>' +
      '<label>Kind<select id="p-kind">' + KINDS.map(function (k) { return "<option>" + esc(k) + "</option>"; }).join("") + "</select></label>" +
      '<label>Section<select id="p-section">' + G.sections.slice().sort(function (a, b) { return a.order - b.order; }).map(function (s) {
        return '<option value="' + esc(s.id) + '">' + esc(s.title || s.id) + "</option>"; }).join("") + "</select></label>" +
      '<label>One-line note (optional, 200 characters)<input type="text" id="p-note" maxlength="200"></label>' +
      '<label>Connections (optional)</label><div id="p-conns"></div>' +
      '<button type="button" id="p-add-conn">Add a connection</button>' +
      '<div class="errors" id="p-errors" hidden></div>' +
      '<div class="buttons"><button type="button" id="p-cancel">Cancel</button><button type="button" id="p-save">Add proposal</button></div>';
    $("#p-name").addEventListener("input", function () {
      var s = CG.similarNodes(G.nodes, $("#p-name").value, 3), box = $("#p-similar");
      box.hidden = !s.length;
      box.innerHTML = s.length ? "Similar existing: " + s.map(function (n) { return esc(n.name); }).join(", ") +
        ". Propose a connection instead if it is the same idea." : "";
    });
    $("#p-add-conn").addEventListener("click", function () { $("#p-conns").insertAdjacentHTML("beforeend", connectionRow()); });
    $("#p-save").addEventListener("click", function () {
      var conns = Array.from(form.querySelectorAll("[data-conn]")).map(function (row) {
        var g = function (f) { return row.querySelector('[data-f="' + f + '"]').value; };
        return { other: g("other"), type: g("type"), direction: g("direction"), condition: g("condition").trim() || null, note: "" };
      });
      var p = { name: $("#p-name").value.trim(), kind: $("#p-kind").value, section: $("#p-section").value,
                topic: (sectionsById.get($("#p-section").value) || {}).topic || G.vocab.topics[0], note: $("#p-note").value.trim(), connections: conns };
      saveProposal({ action: "add_node", proposal: p });
    });
    finishForm();
  }
  function openEdgeForm(ids, ordered) {
    ids = ids || [];
    var order = {};
    G.nodes.forEach(function (n) { var s = sectionsById.get(n.section); order[n.id] = [s ? s.order : 0, n.name]; });
    var chosen = ids.slice().sort(function (x, y) { return order[x][0] - order[y][0] || String(order[x][1]).localeCompare(String(order[y][1])); })[0] || "";
    if (ordered && ids.length) chosen = ids[0];
    var mode = "one_to_many";
    var rows = [];
    function rebuildRows() {
      rows = (ids.length >= 2 ? CG.connectionRows(mode, chosen, ids, order) : [{ source: chosen, target: "" }])
        .map(function (r) { return { a: r.source, b: r.target, type: "is_a", condition: "" }; });
    }
    function draw() {
      var chooser = (!ordered && ids.length >= 2)
        ? '<label>Mode<select id="e-mode">' +
          [["one_to_many", "One to many"], ["many_to_one", "Many to one"], ["chain", "Chain in course order"],
           ["all_pairs", "All pairs (up to 4 concepts)"]].map(function (m) {
            return '<option value="' + m[0] + '"' + (m[0] === mode ? " selected" : "") + ">" + m[1] + "</option>"; }).join("") + "</select></label>" +
          "<label>" + (mode === "many_to_one" ? "To (the chosen concept)" : "From (the chosen concept)") +
          '<select id="e-chosen">' + ids.map(function (id) {
            return '<option value="' + esc(id) + '"' + (id === chosen ? " selected" : "") + ">" + esc(nameOf(id)) + "</option>"; }).join("") + "</select></label>"
        : "";
      form.innerHTML = '<h2 id="propose-title">Propose a connection</h2>' + chooser +
        (mode === "all_pairs" && ids.length > 4 ? '<div class="errors">All pairs needs four or fewer concepts.</div>' : "") +
        '<div id="e-rows">' + rows.map(function (r, i) {
          return '<div class="row sentence" data-i="' + i + '">' +
            '<span class="from">' + (r.a ? esc(nameOf(r.a)) : '<select data-f="a">' + nodeOptions("") + "</select>") + "</span>" +
            '<select data-f="type">' + typeOptions(r.type) + "</select>" +
            '<select data-f="b">' + nodeOptions(r.b) + "</select>" +
            '<button type="button" data-reverse="' + i + '" title="Reverse this row">\u21c4</button>' +
            '<button type="button" data-del="' + i + '">\u00d7</button>' +
            '<input type="text" data-f="condition" placeholder="Condition (needed for implies / iff)" value="' + esc(r.condition) + '" style="grid-column: 1 / -1">' +
            "</div>";
        }).join("") + "</div>" +
        '<button type="button" id="e-reverse-all">Reverse all rows</button> <button type="button" id="e-add">Add a row</button>' +
        '<div class="errors" id="p-errors" hidden></div>' +
        '<div class="buttons"><button type="button" id="p-cancel">Cancel</button><button type="button" id="p-save">Add proposal</button></div>';
    }
    function readRows() {
      Array.from(form.querySelectorAll("[data-i]")).forEach(function (el) {
        var r = rows[Number(el.getAttribute("data-i"))]; if (!r) return;
        var a = el.querySelector('[data-f="a"]');
        r.type = el.querySelector('[data-f="type"]').value;
        r.b = el.querySelector('[data-f="b"]').value;
        r.condition = el.querySelector('[data-f="condition"]').value;
        if (a) r.a = a.value;
      });
    }
    form.onchange = function (ev) {
      if (ev.target.id === "e-mode") { mode = ev.target.value; rebuildRows(); draw(); }
      else if (ev.target.id === "e-chosen") { chosen = ev.target.value; rebuildRows(); draw(); }
    };
    form.onclick = function (ev) {
      var t = ev.target;
      if (t.id === "p-cancel") return dialog.close();
      if (t.hasAttribute("data-reverse")) {
        readRows(); var r = rows[Number(t.getAttribute("data-reverse"))];
        var tmp = r.a; r.a = r.b; r.b = tmp; draw();
      } else if (t.id === "e-reverse-all") {
        readRows(); rows.forEach(function (r) { var x = r.a; r.a = r.b; r.b = x; }); draw();
      } else if (t.hasAttribute("data-del")) {
        readRows(); rows.splice(Number(t.getAttribute("data-del")), 1); draw();
      } else if (t.id === "e-add") {
        readRows(); rows.push({ a: chosen, b: "", type: "is_a", condition: "" }); draw();
      } else if (t.id === "p-save") {
        readRows();
        var made = rows.map(function (r) {
          return { action: "add_edge", proposal: { source: r.a, type: r.type, target: r.b, condition: (r.condition || "").trim() || null, note: "" } };
        });
        var all = [];
        for (var i = 0; i < made.length; i++) {
          var res = CG.checkProposal(G, made[i].proposal, proposals.concat(all));
          if (res.errors.length) return showErrors(res.errors);
          all.push(made[i]);
        }
        if (!all.length) return showErrors(["Add at least one connection."]);
        proposals = proposals.concat(all);
        dialog.close(); persist(); toast(all.length + " connection" + (all.length === 1 ? "" : "s") + " added to your proposals.");
      }
    };
    rebuildRows(); draw();
    if (!dialog.open) dialog.showModal();
  }
  function showErrors(list) {
    var box = $("#p-errors"); box.hidden = false;
    box.innerHTML = list.map(function (m) { return "<div>" + esc(m) + "</div>"; }).join("");
  }
  function saveProposal(p) {
    var res = CG.checkProposal(G, p.proposal, proposals);
    if (res.errors.length) return showErrors(res.errors);
    proposals.push(p); dialog.close(); persist(); toast("Added to your proposals. Submit your review to send it.");
  }
  form.addEventListener("click", function (ev) {
    if (ev.target.hasAttribute("data-remove-row")) ev.target.closest(".row").remove();
    if (ev.target.id === "p-cancel") dialog.close();
  });
  function finishForm() { if (!dialog.open) dialog.showModal(); }
  function openProposal(kind, ids, ordered) {
    if (!needName()) return;
    if (kind === "node") openNodeForm(); else openEdgeForm(ids || [], ordered);
  }

  $("#btn-propose").addEventListener("click", function () { var m = $("#propose-menu"); m.hidden = !m.hidden; });
  $("#propose-menu").addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-propose]"); if (!b) return;
    $("#propose-menu").hidden = true; openProposal(b.getAttribute("data-propose"));
  });

  var changeQueued = false;
  function onSelectionChanged() {
    changeQueued = false;
    var ids = selectedIds();
    pickOrder = pickOrder.filter(function (id) { return ids.indexOf(id) !== -1; });
    ids.forEach(function (id) { if (pickOrder.indexOf(id) === -1) pickOrder.push(id); });
    if (ids.length === 1) selected = { kind: "node", id: ids[0] };
    else if (ids.length === 0 && selected && selected.kind === "node") selected = null;
    $("#btn-connect").hidden = ids.length < 2 || ids.length > 12;
    renderPanel(); renderNameList();
  }
  cy.on("select unselect", "node", function () {
    if (changeQueued) return;
    changeQueued = true;
    Promise.resolve().then(onSelectionChanged);
  });
  cy.on("boxselect", function () { orderedPick = false; });
  $("#btn-connect").addEventListener("click", function () {
    openProposal("edge", pickOrder.slice(), orderedPick);
  });

  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") setSelection([]); });

  if (/[?&]debug\b/.test(location.search)) {
    window.__cg = { cy: cy, selectedIds: selectedIds, setSelection: setSelection,
                    groups: function () { return CG.groupBySection(G.sections, G.nodes, selectedIds(), visibleSet()); } };
  }

  var LAYOUTS = [
    { id: "spread", name: "Spread", compute: function () { return CG.spreadLayout(G.nodes, G.edges, G.sections); } },
    { id: "rows", name: "Section rows", compute: function () { return CG.computeLayout(G.nodes, G.edges, G.sections); } },
    { id: "cluster", name: "By section", compute: function () { return CG.clusterLayout(G.nodes, G.sections); } },
    { id: "timeline", name: "Course timeline", compute: function () { return CG.timelineLayout(G.nodes, G.sections); } }
  ].concat((G.layouts || []).map(function (l) {
    return { id: "file:" + l.id, name: l.name, compute: function () {
      var base = CG.spreadLayout(G.nodes, G.edges, G.sections), out = {};
      G.nodes.forEach(function (n) { out[n.id] = l.positions[n.id] || base[n.id]; });
      return out;
    } };
  }));
  var DEBUG = /[?&]debug\b/.test(location.search); // headless tests: animation frames do not advance there
  var currentLayout = storage.get("cg-layout-" + G.graph_version) || "spread";
  function movedKey(id) { return "cg-moved-" + G.graph_version + "-" + id; }
  function layoutPositions(id) {
    var def = LAYOUTS.filter(function (l) { return l.id === id; })[0] || LAYOUTS[0];
    var pos = def.compute();
    try { var moved = JSON.parse(storage.get(movedKey(def.id)) || "{}"); Object.keys(moved).forEach(function (k) { if (pos[k]) pos[k] = moved[k]; }); } catch (e) { /* none */ }
    return pos;
  }
  function applyLayout(id, animate) {
    currentLayout = id; storage.set("cg-layout-" + G.graph_version, id);
    var pos = layoutPositions(id);
    cy.layout({ name: "preset", positions: function (n) { return pos[n.id()]; }, animate: !!animate && !DEBUG,
      animationDuration: 350, fit: false }).run();
    setTimeout(function () { touched = false; refit(); }, animate ? 400 : 0);
  }
  $("#layout-select").innerHTML = LAYOUTS.map(function (l) {
    return '<option value="' + esc(l.id) + '"' + (l.id === currentLayout ? " selected" : "") + ">" + esc(l.name) + "</option>";
  }).join("");
  $("#layout-select").addEventListener("change", function (ev) { applyLayout(ev.target.value, true); });
  cy.on("dragfree", "node", function () {
    var moved = {};
    cy.nodes().forEach(function (n) { if (!n.hasClass("ghost")) moved[n.id()] = { x: Math.round(n.position("x")), y: Math.round(n.position("y")) }; });
    storage.set(movedKey(currentLayout), JSON.stringify(moved));
  });
  $("#btn-layout-reset").addEventListener("click", function () {
    storage.set(movedKey(currentLayout), "{}"); applyLayout(currentLayout, true);
  });
  $("#btn-layout-download").addEventListener("click", function () {
    var positions = {};
    cy.nodes().forEach(function (n) { if (!n.hasClass("ghost")) positions[n.id()] = { x: Math.round(n.position("x")), y: Math.round(n.position("y")) }; });
    var blob = new Blob([JSON.stringify({ name: "My layout", positions: positions }, null, 2)], { type: "application/json" });
    var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "layout-my-layout.json"; a.click();
  });

  // ---- start ----------------------------------------------------------------
  $("#title").textContent = (G.site && G.site.title) || "Concept graph";
  buildFilters(); persist(); paintDecisions(); applyFilters();
  if (currentLayout !== "spread") applyLayout(currentLayout, false);
  // Keep the whole graph in view until the reader moves it themselves: the window may still be settling
  // to its final size when the page first draws, and a phone can rotate.
  var touched = false;
  ["wheel", "mousedown", "touchstart"].forEach(function (name) {
    $("#cy").addEventListener(name, function () { touched = true; }, { passive: true });
  });
  function refit() { cy.resize(); if (!touched) cy.fit(undefined, 30); }
  window.addEventListener("resize", refit);
  window.addEventListener("load", refit);
  $("#btn-fit").addEventListener("click", function () { touched = false; refit(); });
})();
