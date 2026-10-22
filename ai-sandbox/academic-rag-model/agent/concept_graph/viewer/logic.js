(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CG = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function when(text, condition) { return text + (condition ? "; context: " + condition : ""); }

  var SENTENCE = {
    is_a: function (s, t, c) { return s + " is a " + t + (c ? ", that also: " + c : ""); },
    has_property: function (s, t, c) { return when(s + " has the property " + t, c); },
    defined_on: function (s, t, c) { return when(s + " is defined on " + t, c); },
    component_of: function (s, t, c) { return when(s + " is one of the conditions making up " + t, c); },
    implies: function (s, t, c) { return s + " implies " + t + (c ? ", when: " + c : ""); },
    iff: function (s, t, c) { return s + " holds exactly when " + t + (c ? ", given: " + c : ""); },
    hypothesis_of: function (s, t, c) { return when(s + " is a hypothesis of " + t, c); },
    yields: function (s, t, c) { return when(s + " yields " + t, c); },
    counterexample_to: function (s, t, c) { return when(s + " is a counterexample showing the converse of " + t + " fails", c); },
    uses: function (s, t, c) { return when(s + " uses " + t, c); },
    applies_to: function (s, t, c) { return when(s + " applies to " + t, c); },
    estimates: function (s, t, c) { return when(s + " estimates " + t, c); },
    computed_from: function (s, t, c) { return when(s + " is computed from " + t, c); },
    variant_of: function (s, t, c) { return when(s + " is a variant of " + t, c); },
    defined_via: function (s, t, c) { return when(s + " is defined via " + t, c); },
    assumption_of: function (s, t, c) { return when(s + " is an assumption of " + t, c); }
  };

  function edgeSentence(edge, nameOf) {
    var make = SENTENCE[edge.type];
    var text = make ? make(nameOf(edge.source), nameOf(edge.target), edge.condition) : nameOf(edge.source) + " - " + edge.type + " - " + nameOf(edge.target);
    if (edge.via) text += " (via " + nameOf(edge.via) + ")";
    return text;
  }

  // Each pair is [dependent, prerequisite]: "dependent" needs "prerequisite" to be understood.
  function needsPairs(e) {
    var pairs = [];
    switch (e.type) {
      case "is_a": case "has_property": case "defined_on":
      case "uses": case "estimates": case "computed_from": case "variant_of": case "defined_via":
        pairs.push([e.source, e.target]); break;
      case "component_of": case "hypothesis_of": case "yields": case "assumption_of":
        pairs.push([e.target, e.source]); break;
      case "implies":
        pairs.push([e.target, e.source]);
        if (e.via) pairs.push([e.target, e.via]);
        break;
      case "iff":
        pairs.push([e.target, e.source], [e.source, e.target]);
        if (e.via) pairs.push([e.target, e.via], [e.source, e.via]);
        break;
      default: break;
    }
    return pairs;
  }

  function prerequisites(startId, edges) {
    var prereq = new Map();
    edges.forEach(function (e) {
      needsPairs(e).forEach(function (p) {
        if (!prereq.has(p[0])) prereq.set(p[0], new Set());
        prereq.get(p[0]).add(p[1]);
      });
    });
    var seen = new Set();
    var stack = [startId];
    while (stack.length) {
      var id = stack.pop();
      (prereq.get(id) || []).forEach(function (p) {
        if (!seen.has(p)) { seen.add(p); stack.push(p); }
      });
    }
    seen.delete(startId);
    return seen;
  }

  function computeLayout(nodes, edges, sections, opts) {
    opts = opts || {};
    var dx = opts.dx || 210, dy = opts.dy || 230, rowGap = opts.rowGap || 90;
    var perRow = opts.perRow || 5, sweeps = opts.sweeps == null ? 4 : opts.sweeps;
    var orderOf = new Map(sections.map(function (s) { return [s.id, s.order]; }));
    var bands = Array.from(new Set(nodes.map(function (n) { return n.section; })))
      .sort(function (a, b) { return orderOf.get(a) - orderOf.get(b); });
    var bandIndex = new Map(bands.map(function (b, i) { return [b, i]; }));
    var byBand = bands.map(function () { return []; });
    nodes.slice()
      .sort(function (a, b) { return (a.topic + "|" + a.name).localeCompare(b.topic + "|" + b.name); })
      .forEach(function (n) { byBand[bandIndex.get(n.section)].push(n); });

    var x = new Map();
    function renorm() {
      byBand.forEach(function (list) {
        list.forEach(function (n, i) { x.set(n.id, (i + 0.5) / list.length); });
      });
    }
    renorm();
    var nbrs = new Map(nodes.map(function (n) { return [n.id, []]; }));
    edges.forEach(function (e) {
      if (nbrs.has(e.source) && nbrs.has(e.target)) {
        nbrs.get(e.source).push(e.target);
        nbrs.get(e.target).push(e.source);
      }
    });
    for (var k = 0; k < sweeps; k++) {
      byBand.forEach(function (list) {
        var key = new Map();
        list.forEach(function (n) {
          var ns = nbrs.get(n.id);
          var m = ns.length ? ns.reduce(function (acc, id) { return acc + x.get(id); }, 0) / ns.length : x.get(n.id);
          key.set(n.id, m);
        });
        list.sort(function (a, b) { return key.get(a.id) - key.get(b.id) || a.name.localeCompare(b.name); });
      });
      renorm();
    }

    var pos = {};
    var top = 0;
    byBand.forEach(function (list) {
      var rows = Math.max(1, Math.ceil(list.length / perRow));
      list.forEach(function (n, i) {
        var row = Math.floor(i / perRow);
        var inRow = Math.min(perRow, list.length - row * perRow);
        var col = i % perRow;
        pos[n.id] = { x: (col - (inRow - 1) / 2) * dx, y: -(top + row * rowGap) };
      });
      top += (rows - 1) * rowGap + dy;
    });
    return pos;
  }

  // Starting from the section rows, let connected concepts attract and every pair repel (Fruchterman-Reingold),
  // with a soft pull toward the section's height so the course still reads bottom to top, and a weak pull toward
  // the topic's centre of mass. A fixed iteration count and no randomness keep the picture identical on every load;
  // a last pass pushes apart any boxes that still overlap.
  function spreadLayout(nodes, edges, sections, opts) {
    opts = opts || {};
    var boxW = opts.boxW || 170, boxH = opts.boxH || 56;
    var iterations = opts.iterations || 400;
    var k = opts.idealLength || 200, bandGap = opts.bandGap || 220;
    var bandPull = opts.bandPull == null ? 0.35 : opts.bandPull, topicPull = opts.topicPull == null ? 0.04 : opts.topicPull;
    var gravity = opts.gravity == null ? 0.15 : opts.gravity, reach = (opts.reach || 3) * k;
    var seed = computeLayout(nodes, edges, sections, opts);
    var n = nodes.length;
    if (n <= 1) return seed;

    var orderOf = new Map(sections.map(function (s) { return [s.id, s.order]; }));
    var bands = Array.from(new Set(nodes.map(function (m) { return m.section; })))
      .sort(function (a, b) { return orderOf.get(a) - orderOf.get(b); });
    var targetY = new Map(bands.map(function (b, i) { return [b, -i * bandGap]; }));
    var index = new Map(nodes.map(function (m, i) { return [m.id, i]; }));
    var px = [], py = [];
    nodes.forEach(function (m, i) {  // a small repeatable offset so identical seeds can separate
      px.push(seed[m.id].x + ((i * 37) % 11 - 5) * 4);
      py.push(seed[m.id].y + ((i * 53) % 13 - 6) * 4);
    });
    var links = [];
    edges.forEach(function (e) {
      if (index.has(e.source) && index.has(e.target) && e.source !== e.target) links.push([index.get(e.source), index.get(e.target)]);
    });
    var topics = Array.from(new Set(nodes.map(function (m) { return m.topic; })));
    var topicOf = nodes.map(function (m) { return topics.indexOf(m.topic); });

    for (var it = 0; it < iterations; it++) {
      var fx = new Array(n).fill(0), fy = new Array(n).fill(0);
      var i, j, dx, dy, d, f;
      for (i = 0; i < n; i++) {
        for (j = i + 1; j < n; j++) {
          dx = px[i] - px[j]; dy = py[i] - py[j];
          d = Math.sqrt(dx * dx + dy * dy);
          if (d < 1) { dx = 1; dy = 0; d = 1; }
          if (d > reach) continue;  // far-apart concepts ignore each other, so loose ones are not flung away
          f = (k * k) / d / d;  // repulsion k^2/d, split into its x/y parts
          fx[i] += dx * f; fy[i] += dy * f; fx[j] -= dx * f; fy[j] -= dy * f;
        }
      }
      links.forEach(function (l) {
        dx = px[l[0]] - px[l[1]]; dy = py[l[0]] - py[l[1]];
        d = Math.sqrt(dx * dx + dy * dy) || 1;
        f = d / k;  // attraction d^2/k, split into its x/y parts
        fx[l[0]] -= dx * f; fy[l[0]] -= dy * f; fx[l[1]] += dx * f; fy[l[1]] += dy * f;
      });
      var cx = topics.map(function () { return 0; }), cy = topics.map(function () { return 0; }), cn = topics.map(function () { return 0; });
      for (i = 0; i < n; i++) { cx[topicOf[i]] += px[i]; cy[topicOf[i]] += py[i]; cn[topicOf[i]]++; }
      var maxStep = 60 * (1 - it / iterations) + 1;
      for (i = 0; i < n; i++) {
        fy[i] += (targetY.get(nodes[i].section) - py[i]) * bandPull;
        fx[i] += (cx[topicOf[i]] / cn[topicOf[i]] - px[i]) * topicPull;
        fy[i] += (cy[topicOf[i]] / cn[topicOf[i]] - py[i]) * topicPull;
        fx[i] -= px[i] * gravity;
        var mag = Math.sqrt(fx[i] * fx[i] + fy[i] * fy[i]);
        if (mag > 0) { var s = Math.min(mag, maxStep) / mag; px[i] += fx[i] * s; py[i] += fy[i] * s; }
      }
    }

    for (var pass = 0, moved = true; pass < 500 && moved; pass++) {
      moved = false;
      for (var a = 0; a < n; a++) {
        for (var b = a + 1; b < n; b++) {
          var ddx = px[a] - px[b], ddy = py[a] - py[b];
          var ox = boxW + 1 - Math.abs(ddx), oy = boxH + 1 - Math.abs(ddy);
          if (ox <= 0 || oy <= 0) continue;
          moved = true;
          if (ox < oy) { var sx = (ddx === 0 ? (a < b ? 1 : -1) : Math.sign(ddx)) * ox / 2; px[a] += sx; px[b] -= sx; }
          else { var sy = (ddy === 0 ? (a < b ? 1 : -1) : Math.sign(ddy)) * oy / 2; py[a] += sy; py[b] -= sy; }
        }
      }
    }
    var out = {};
    nodes.forEach(function (m, i) { out[m.id] = { x: Math.round(px[i] * 10) / 10, y: Math.round(py[i] * 10) / 10 }; });
    return out;
  }

  function splitMath(text) {
    var out = [];
    // Inline math must hug its dollar signs ("$x$"), and the closing one must not be followed by a digit, so
    // two prices in one passage ("$5 today, $10 tomorrow") stay plain text.
    var re = /\$\$([\s\S]+?)\$\$|\$(?!\s)([^$\n]*?[^\s$])\$(?!\d)/g;
    var last = 0, m;
    text = text || "";
    while ((m = re.exec(text))) {
      if (m.index > last) out.push({ type: "text", value: text.slice(last, m.index) });
      if (m[1] !== undefined) out.push({ type: "display", value: m[1].trim() });
      else out.push({ type: "inline", value: m[2] });
      last = re.lastIndex;
    }
    if (last < text.length) out.push({ type: "text", value: text.slice(last) });
    return out;
  }

  function splitFormal(text) {
    text = text || "";
    if (text.indexOf("$") !== -1) return splitMath(text);
    var trimmed = text.trim();
    if (!trimmed) return [];
    return [{ type: "display", value: trimmed }];
  }

  function filterNodes(nodes, f) {
    var q = (f.q || "").trim().toLowerCase();
    function ok(list, value) { return !list || list.length === 0 || list.indexOf(value) !== -1; }
    return nodes.filter(function (n) {
      if (q && (n.name + " " + (n.gist || "") + " " + n.id).toLowerCase().indexOf(q) === -1) return false;
      return ok(f.topics, n.topic) && ok(f.sections, n.section) && ok(f.kinds, n.kind) && ok(f.statuses, n.status);
    });
  }

  function decisionKey(d) {
    return [d.target.kind, d.target.id, d.action, d.field || ""].join("|");
  }

  function recordDecision(decisions, d) {
    var key = decisionKey(d);
    var exclusive = d.action === "accept" ? "reject" : d.action === "reject" ? "accept" : null;
    var kept = decisions.filter(function (x) {
      if (decisionKey(x) === key) return false;
      if (exclusive && x.target.kind === d.target.kind && x.target.id === d.target.id && x.action === exclusive) return false;
      return true;
    });
    kept.push(d);
    return kept;
  }

  function buildReview(graph, decisions, reviewerName, nowIso, proposals) {
    return {
      schema_version: 2,
      graph_version: graph.graph_version,
      reviewer: { name: reviewerName },
      created: nowIso,
      decisions: decisions.concat(proposals || [])
    };
  }

  function issueUrl(repo, review, maxLen) {
    maxLen = maxLen || 6000;
    var base = "https://github.com/" + repo + "/issues/new?template=review.yml&title=" +
      encodeURIComponent("Review: " + review.reviewer.name);
    var full = base + "&review=" + encodeURIComponent(JSON.stringify(review));
    return full.length <= maxLen ? { url: full, prefilled: true } : { url: base, prefilled: false };
  }

  function safeStorage(win) {
    function store() { try { return win.localStorage || null; } catch (e) { return null; } }
    return {
      get: function (key) { try { var s = store(); return s ? s.getItem(key) : null; } catch (e) { return null; } },
      set: function (key, value) { try { var s = store(); if (!s) return false; s.setItem(key, value); return true; } catch (e) { return false; } }
    };
  }

  var GENERIC = ["function", "correspondence", "relation", "problem", "theorem", "axiom", "condition", "property",
    "set", "model", "equation", "lemma", "principle", "assumption"];
  var FILLER = ["of", "the", "a", "an", "and", "for", "in", "to"];
  var NAME_MAX = 120, NOTE_MAX = 200;
  var CONDITION_REQUIRED = ["implies", "iff"];

  function normalizeName(name) {
    return String(name || "").toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/).filter(Boolean).join(" ");
  }
  function slugFromName(name) { return normalizeName(name).split(" ").filter(Boolean).join("-"); }
  function tokens(name) {
    var all = normalizeName(name).split(" ").filter(function (t) { return t && FILLER.indexOf(t) === -1; });
    return all.filter(function (t, i) { return all.indexOf(t) === i; }); // a set, as on the server
  }
  var QUALIFIERS = ["strictly", "strict", "locally", "globally", "weak", "weakly", "strong", "strongly", "non", "not",
    "anti", "quasi", "marginal", "relative", "absolute", "average",
    "autoregressive", "cumulative", "partial", "conditional", "generalized"];
  var NEGATING_PREFIXES = ["un", "non", "in", "im", "ir", "dis"];
  function opposed(ta, tb) {
    var onlyA = ta.filter(function (t) { return tb.indexOf(t) === -1; });
    var onlyB = tb.filter(function (t) { return ta.indexOf(t) === -1; });
    if (onlyA.concat(onlyB).some(function (t) { return QUALIFIERS.indexOf(t) !== -1; })) return true;
    return onlyA.some(function (x) {
      return onlyB.some(function (y) {
        return NEGATING_PREFIXES.some(function (pre) { return y === pre + x || x === pre + y; });
      });
    });
  }
  function distance(a, b) {
    var prev = []; for (var j = 0; j <= b.length; j++) prev.push(j);
    for (var i = 1; i <= a.length; i++) {
      var cur = [i];
      for (var k = 1; k <= b.length; k++) {
        cur.push(Math.min(prev[k] + 1, cur[k - 1] + 1, prev[k - 1] + (a[i - 1] === b[k - 1] ? 0 : 1)));
      }
      prev = cur;
    }
    return prev[b.length];
  }
  function similarNames(a, b) {
    var na = normalizeName(a), nb = normalizeName(b);
    if (!na || !nb) return false;
    if (na === nb) return true;
    var ta = tokens(a), tb = tokens(b);
    if (ta.length && tb.length) {
      var small = ta.length <= tb.length ? ta : tb, big = ta.length <= tb.length ? tb : ta;
      var inBig = function (t) { return big.indexOf(t) !== -1; };
      var extra = big.filter(function (t) { return small.indexOf(t) === -1; });
      if (small.length >= 2 && small.every(inBig) && extra.every(function (t) { return GENERIC.indexOf(t) !== -1; })) return true;
      if (opposed(ta, tb)) return false;
      var shared = ta.filter(function (t) { return tb.indexOf(t) !== -1; }).length;
      var union = new Set(ta.concat(tb)).size;
      if (shared / union >= 0.75) return true;
    }
    return distance(na, nb) <= 0.10 * Math.max(na.length, nb.length);
  }
  function similarNodes(nodes, name, limit) {
    return nodes.filter(function (n) { return similarNames(n.name, name); }).slice(0, limit || 3);
  }

  // Mirrors proposals.py check_node / check_edge so the form can say what is wrong before anything is sent.
  function checkProposal(graph, p, pending) {
    var errors = [], similar = [];
    var ids = new Set(graph.nodes.map(function (n) { return n.id; }));
    (pending || []).forEach(function (x) { if (x.action === "add_node") ids.add(slugFromName(x.proposal.name)); });
    if (p.name !== undefined) {
      var slug = slugFromName(p.name);
      if (!String(p.name).trim()) errors.push("name is empty");
      else if (p.name.length > NAME_MAX) errors.push("name is longer than " + NAME_MAX + " characters");
      else if (!slug) errors.push("name does not give a usable id");
      if (slug && graph.nodes.some(function (n) { return n.id === slug; })) errors.push("'" + slug + "' is already a concept in the graph");
      if (graph.vocab.kinds.indexOf(p.kind) === -1) errors.push("kind '" + p.kind + "' is not one of " + graph.vocab.kinds.join(", "));
      var propSection = graph.sections.filter(function (x) { return x.id === p.section; })[0];
      if (!(propSection && propSection.topic) && graph.vocab.topics.indexOf(p.topic) === -1) errors.push("topic '" + p.topic + "' is not one of " + graph.vocab.topics.join(", "));
      if (!graph.sections.some(function (s) { return s.id === p.section; })) errors.push("section '" + p.section + "' does not exist");
      if ((p.note || "").length > NOTE_MAX) errors.push("note is longer than " + NOTE_MAX + " characters");
      similar = similarNodes(graph.nodes, p.name, 3);
      if ((pending || []).some(function (x) { return x.action === "add_node" && similarNames(x.proposal.name, p.name); })) {
        errors.push("a concept like this is already in your proposals");
      }
      (p.connections || []).forEach(function (c) {
        if (!ids.has(c.other)) errors.push("connection to '" + c.other + "': not a concept in the graph");
        if (CONDITION_REQUIRED.indexOf(c.type) !== -1 && !(c.condition || "").trim()) errors.push("a " + c.type + " connection needs a condition");
      });
    } else {
      if (!ids.has(p.source)) errors.push("source '" + p.source + "' is not a concept in the graph");
      if (!ids.has(p.target)) errors.push("target '" + p.target + "' is not a concept in the graph");
      if (p.source === p.target) errors.push("a concept cannot connect to itself");
      if (CONDITION_REQUIRED.indexOf(p.type) !== -1 && !(p.condition || "").trim()) errors.push("a " + p.type + " connection needs a condition (when does it hold?)");
      var id = p.source + "--" + p.type + "--" + p.target;
      var taken = graph.edges.some(function (e) { return e.id === id; }) ||
        (pending || []).some(function (x) { return x.action === "add_edge" && x.proposal.source + "--" + x.proposal.type + "--" + x.proposal.target === id; });
      if (taken) errors.push(id + " already exists");
    }
    return { errors: errors, similar: similar };
  }

  function sortedSections(sections) { return sections.slice().sort(function (a, b) { return a.order - b.order; }); }
  function listOrder(sections, nodes) {
    var out = [];
    sortedSections(sections).forEach(function (s) {
      nodes.filter(function (n) { return n.section === s.id; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); })
        .forEach(function (n) { out.push(n.id); });
    });
    return out;
  }
  function rangeIds(order, a, b) {
    var i = order.indexOf(a), j = order.indexOf(b);
    if (j === -1) return [];
    if (i === -1) return [b];
    return order.slice(Math.min(i, j), Math.max(i, j) + 1);
  }
  function toggleId(ids, id) {
    return ids.indexOf(id) === -1 ? ids.concat([id]) : ids.filter(function (x) { return x !== id; });
  }
  function groupBySection(sections, nodes, selectedIds, visibleIds) {
    var chosen = new Set(selectedIds);
    var out = [];
    sortedSections(sections).forEach(function (s) {
      var members = nodes.filter(function (n) { return n.section === s.id; });
      var shown = members.filter(function (n) { return visibleIds.has(n.id); });
      var ids = shown.filter(function (n) { return chosen.has(n.id); }).map(function (n) { return n.id; });
      if (!ids.length) return;
      out.push({ section: s, ids: ids, total: shown.length, full: ids.length === shown.length,
                 filtered: shown.length < members.length });
    });
    return out;
  }
  function expandedSection(groups, newIds, nodesById) {
    var fresh = new Set(newIds), best = null, bestCount = -1;
    groups.forEach(function (g) {
      var c = g.ids.filter(function (id) { return fresh.has(id); }).length;
      if (c > bestCount) { best = g.section.id; bestCount = c; }
    });
    return best || (groups.length ? groups[groups.length - 1].section.id : null);
  }
  function sectionButtonClick(active, sectionId) {
    var i = active.indexOf(sectionId);
    if (i === -1) return { active: active.concat([sectionId]), select: sectionId };
    var next = active.filter(function (x) { return x !== sectionId; });
    return { active: next, select: null };
  }
  function connectionRows(mode, chosen, ids, ord) {
    function key(id) { var o = ord[id] || [0, id]; return o; }
    function cmp(a, b) { var x = key(a), y = key(b); return x[0] - y[0] || String(x[1]).localeCompare(String(y[1])); }
    var others = ids.filter(function (id) { return id !== chosen; });
    if (mode === "one_to_many") return others.map(function (id) { return { source: chosen, target: id }; });
    if (mode === "many_to_one") return others.map(function (id) { return { source: id, target: chosen }; });
    var sorted = ids.slice().sort(cmp);
    if (mode === "chain") {
      return sorted.slice(1).map(function (id, i) { return { source: sorted[i], target: id }; });
    }
    if (mode === "all_pairs") {
      if (sorted.length > 4) return [];
      var rows = [];
      for (var i = 0; i < sorted.length; i++) for (var j = i + 1; j < sorted.length; j++) rows.push({ source: sorted[i], target: sorted[j] });
      return rows;
    }
    return [];
  }
  var CELL_W = 200, CELL_H = 74;
  function gridInside(members, cx, cy, out) {
    var cols = Math.max(1, Math.ceil(Math.sqrt(members.length)));
    members.forEach(function (n, k) {
      out[n.id] = { x: cx + (k % cols) * CELL_W, y: cy + Math.floor(k / cols) * CELL_H };
    });
    return { w: cols * CELL_W, h: Math.ceil(members.length / cols) * CELL_H };
  }
  function clusterLayout(nodes, sections) {
    var out = {}, perRow = 3, gapX = 260, gapY = 200;
    var rowH = 0, x = 0, y = 0, colIndex = 0;
    sortedSections(sections).forEach(function (s) {
      var members = nodes.filter(function (n) { return n.section === s.id; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      if (!members.length) return;
      var size = gridInside(members, x, y, out);
      rowH = Math.max(rowH, size.h);
      colIndex += 1;
      if (colIndex % perRow === 0) { x = 0; y += rowH + gapY; rowH = 0; } else { x += size.w + gapX; }
    });
    return out;
  }
  function timelineLayout(nodes, sections) {
    var out = {}, x = 0;
    sortedSections(sections).forEach(function (s) {
      var members = nodes.filter(function (n) { return n.section === s.id; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      members.forEach(function (n, k) { out[n.id] = { x: x, y: k * CELL_H }; });
      x += CELL_W + 80;
    });
    return out;
  }

  return {
    edgeSentence: edgeSentence, needsPairs: needsPairs, prerequisites: prerequisites,
    computeLayout: computeLayout, spreadLayout: spreadLayout, splitMath: splitMath, splitFormal: splitFormal, filterNodes: filterNodes,
    decisionKey: decisionKey, recordDecision: recordDecision, buildReview: buildReview,
    normalizeName: normalizeName, slugFromName: slugFromName, similarNames: similarNames,
    similarNodes: similarNodes, checkProposal: checkProposal,
    listOrder: listOrder, rangeIds: rangeIds, toggleId: toggleId, groupBySection: groupBySection,
    expandedSection: expandedSection, sectionButtonClick: sectionButtonClick, connectionRows: connectionRows,
    clusterLayout: clusterLayout, timelineLayout: timelineLayout,
    issueUrl: issueUrl, safeStorage: safeStorage
  };
});
