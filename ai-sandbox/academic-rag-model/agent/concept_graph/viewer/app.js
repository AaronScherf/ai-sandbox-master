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
    $("#decision-count").textContent = decisions.length + (decisions.length === 1 ? " decision" : " decisions");
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
    cy.nodes().forEach(function (n) { n.toggleClass("hidden", !visible.has(n.id())); });
    cy.edges().forEach(function (e) {
      var hide = hiddenEdgeTypes.has(e.data("type")) || !visible.has(e.data("source")) || !visible.has(e.data("target"));
      e.toggleClass("hidden", hide);
    });
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
  cy.on("tap", "node", function (ev) { select("node", ev.target.id(), false); });
  cy.on("tap", "edge", function (ev) { select("edge", ev.target.id(), false); });
  cy.on("tap", function (ev) { if (ev.target === cy) { selected = null; cy.elements().unselect(); cy.edges().removeClass("labelled"); applyPrereqMode(); renderPanel(); renderNameList(); } });

  // ---- sidebar --------------------------------------------------------------
  function renderNameList(visibleSet) {
    var visible = visibleSet || new Set(CG.filterNodes(G.nodes, filters).map(function (n) { return n.id; }));
    var html = "";
    G.sections.slice().sort(function (a, b) { return a.order - b.order; }).forEach(function (s) {
      var list = G.nodes.filter(function (n) { return n.section === s.id && visible.has(n.id); })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      if (!list.length) return;
      html += "<h3>" + esc(s.title) + (s.state === "planned" ? " (planned)" : "") + "</h3>";
      list.forEach(function (n) {
        var cls = (s.state === "planned" ? "planned " : "") + (selected && selected.id === n.id ? "sel" : "");
        html += '<button type="button" class="' + cls + '" data-node="' + esc(n.id) + '">' + esc(n.name) + "</button>";
      });
    });
    $("#name-list").innerHTML = html || '<p class="hint">No concepts match.</p>';
  }
  $("#name-list").addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-node]");
    if (b) select("node", b.getAttribute("data-node"), true);
  });

  function buildFilters() {
    var topics = $("#f-topics");
    topics.innerHTML = G.vocab.topics.map(function (t) { return '<button type="button" data-topic="' + esc(t) + '">' + esc(t) + "</button>"; }).join("");
    topics.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-topic]"); if (!b) return;
      var t = b.getAttribute("data-topic"), i = filters.topics.indexOf(t);
      if (i === -1) filters.topics.push(t); else filters.topics.splice(i, 1);
      b.classList.toggle("on", i === -1); applyFilters();
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
      "<p>Boxes are concepts, coloured by topic; higher on the page means later in the course. A dashed outline means not yet reviewed. Faded boxes are in sections not taught yet.</p>" +
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
  function renderPanel() {
    var p = $("#panel");
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
      '<div class="actions"><button type="button" class="' + (prereqMode ? "on" : "") + '" data-act="prereq">Show what this needs</button></div>' +
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
    if (b.hasAttribute("data-edge")) return select("edge", b.getAttribute("data-edge"), true);
    if (b.hasAttribute("data-node")) return select("node", b.getAttribute("data-node"), true);
    var act = b.getAttribute("data-act"); if (!act || !selected) return;
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
  function currentReview() { return CG.buildReview(G, decisions, reviewer.trim(), new Date().toISOString()); }
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
    if (decisions.length && !window.confirm("Forget all " + decisions.length + " pending decisions?")) return;
    decisions = []; persist(); paintDecisions(); renderPanel();
  });
  $("#reviewer").value = reviewer;
  $("#reviewer").addEventListener("input", function (ev) { reviewer = ev.target.value; storage.set("cg-reviewer", reviewer); });

  // ---- start ----------------------------------------------------------------
  $("#title").textContent = (G.site && G.site.title) || "Concept graph";
  buildFilters(); persist(); paintDecisions(); applyFilters();
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
