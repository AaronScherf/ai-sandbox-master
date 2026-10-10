(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CG = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var SENTENCE = {
    is_a: function (s, t, c) { return s + " is a " + t + (c ? ", that also: " + c : ""); },
    has_property: function (s, t) { return s + " has the property " + t; },
    defined_on: function (s, t) { return s + " is defined on " + t; },
    component_of: function (s, t) { return s + " is one of the conditions making up " + t; },
    implies: function (s, t, c) { return s + " implies " + t + (c ? ", when: " + c : ""); },
    iff: function (s, t, c) { return s + " holds exactly when " + t + (c ? ", given: " + c : ""); },
    hypothesis_of: function (s, t) { return s + " is a hypothesis of " + t; },
    yields: function (s, t) { return s + " yields " + t; },
    counterexample_to: function (s, t) { return s + " is a counterexample showing the converse of " + t + " fails"; }
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
        pairs.push([e.source, e.target]); break;
      case "component_of": case "hypothesis_of": case "yields":
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

  function buildReview(graph, decisions, reviewerName, nowIso) {
    return {
      schema_version: 1,
      graph_version: graph.graph_version,
      reviewer: { name: reviewerName },
      created: nowIso,
      decisions: decisions
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

  return {
    edgeSentence: edgeSentence, needsPairs: needsPairs, prerequisites: prerequisites,
    computeLayout: computeLayout, splitMath: splitMath, filterNodes: filterNodes,
    decisionKey: decisionKey, recordDecision: recordDecision, buildReview: buildReview,
    issueUrl: issueUrl, safeStorage: safeStorage
  };
});
