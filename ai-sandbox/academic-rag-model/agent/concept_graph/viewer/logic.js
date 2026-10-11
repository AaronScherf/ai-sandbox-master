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
    computeLayout: computeLayout, spreadLayout: spreadLayout, splitMath: splitMath, splitFormal: splitFormal, filterNodes: filterNodes,
    decisionKey: decisionKey, recordDecision: recordDecision, buildReview: buildReview,
    issueUrl: issueUrl, safeStorage: safeStorage
  };
});
