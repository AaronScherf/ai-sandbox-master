const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

const names = { a: "Alpha", b: "Beta", t: "Theorem T", c: "Gamma" };
const nameOf = (id) => names[id] || id;

test("edgeSentence reads naturally for each type and includes condition and via", () => {
  assert.equal(CG.edgeSentence({ type: "is_a", source: "a", target: "b", condition: "it is complete" }, nameOf),
    "Alpha is a Beta, that also: it is complete");
  assert.equal(CG.edgeSentence({ type: "is_a", source: "a", target: "b" }, nameOf), "Alpha is a Beta");
  assert.equal(CG.edgeSentence({ type: "has_property", source: "a", target: "b" }, nameOf), "Alpha has the property Beta");
  assert.equal(CG.edgeSentence({ type: "defined_on", source: "a", target: "b" }, nameOf), "Alpha is defined on Beta");
  assert.equal(CG.edgeSentence({ type: "component_of", source: "a", target: "b" }, nameOf),
    "Alpha is one of the conditions making up Beta");
  assert.equal(CG.edgeSentence({ type: "implies", source: "a", target: "b", condition: "x" }, nameOf), "Alpha implies Beta, when: x");
  assert.equal(CG.edgeSentence({ type: "iff", source: "a", target: "b", condition: "x", via: "t" }, nameOf),
    "Alpha holds exactly when Beta, given: x (via Theorem T)");
  assert.equal(CG.edgeSentence({ type: "hypothesis_of", source: "a", target: "t" }, nameOf), "Alpha is a hypothesis of Theorem T");
  assert.equal(CG.edgeSentence({ type: "yields", source: "t", target: "b" }, nameOf), "Theorem T yields Beta");
  assert.equal(CG.edgeSentence({ type: "counterexample_to", source: "a", target: "b" }, nameOf),
    "Alpha is a counterexample showing the converse of Beta fails");
});

const E = (source, type, target, extra = {}) => ({ source, type, target, ...extra });

test("prerequisites follows what each node needs, in the right direction for every type", () => {
  const edges = [
    E("total", "is_a", "partial"), // total needs partial
    E("partial", "has_property", "anti"), // partial needs anti
    E("partial", "hypothesis_of", "szp"), // szp needs partial
    E("szp", "yields", "total2"), // total2 needs szp
    E("al", "component_of", "bundle"), // bundle needs al
    E("bundle", "iff", "warp", { condition: "c" }), // each needs the other
  ];
  assert.deepEqual([...CG.prerequisites("total", edges)].sort(), ["anti", "partial"]);
  assert.deepEqual([...CG.prerequisites("total2", edges)].sort(), ["anti", "partial", "szp"]);
  assert.deepEqual([...CG.prerequisites("warp", edges)].sort(), ["al", "bundle"]);
});

test("prerequisites is safe on cycles and never includes the start node", () => {
  const edges = [E("a", "implies", "b", { condition: "x" }), E("b", "implies", "a", { condition: "y" })];
  assert.deepEqual([...CG.prerequisites("a", edges)], ["b"]);
});

test("prerequisites treats via as a prerequisite of the conclusion", () => {
  const edges = [E("a", "implies", "b", { condition: "x", via: "t" })];
  assert.deepEqual([...CG.prerequisites("b", edges)].sort(), ["a", "t"]);
});

const sections = [{ id: "s1", order: 1 }, { id: "s2", order: 2 }];
const N = (id, section, name = id, topic = "x") => ({ id, section, name, topic });

test("computeLayout puts later sections higher, keeps a band together, and never overlaps nodes", () => {
  const nodes = [N("a1", "s1"), N("a2", "s1"), N("b1", "s2")];
  const pos = CG.computeLayout(nodes, [E("a1", "is_a", "b1")], sections);
  assert.ok(pos.b1.y < pos.a1.y, "later section is higher on screen");
  assert.equal(pos.a1.y, pos.a2.y);
  const keys = new Set(Object.values(pos).map((p) => `${p.x},${p.y}`));
  assert.equal(keys.size, 3);
});

test("computeLayout wraps a crowded band into rows and is deterministic", () => {
  const nodes = Array.from({ length: 12 }, (_, i) => N(`n${i}`, "s1", `Name ${String(i).padStart(2, "0")}`));
  const a = CG.computeLayout(nodes, [], sections, { perRow: 8 });
  const b = CG.computeLayout(nodes, [], sections, { perRow: 8 });
  assert.deepEqual(a, b);
  const ys = new Set(Object.values(a).map((p) => p.y));
  assert.equal(ys.size, 2);
});

test("splitMath finds inline and display math and keeps text in order", () => {
  assert.deepEqual(CG.splitMath("a $x$ b $$y$$ c"), [
    { type: "text", value: "a " }, { type: "inline", value: "x" }, { type: "text", value: " b " },
    { type: "display", value: "y" }, { type: "text", value: " c" },
  ]);
});

test("splitMath treats a lone dollar as text", () => {
  assert.deepEqual(CG.splitMath("costs $5 today"), [{ type: "text", value: "costs $5 today" }]);
});

test("filterNodes combines search with facet filters", () => {
  const nodes = [
    { id: "a", name: "Alpha", gist: "first", topic: "t1", section: "s1", kind: "axiom", status: "proposed" },
    { id: "b", name: "Beta", gist: "second", topic: "t2", section: "s2", kind: "object", status: "verified" },
  ];
  assert.equal(CG.filterNodes(nodes, { q: "", topics: [], sections: [], kinds: [], statuses: [] }).length, 2);
  assert.deepEqual(CG.filterNodes(nodes, { q: "SEC", topics: [], sections: [], kinds: [], statuses: [] }).map((n) => n.id), ["b"]);
  assert.deepEqual(CG.filterNodes(nodes, { q: "", topics: ["t1"], sections: [], kinds: [], statuses: ["proposed"] }).map((n) => n.id), ["a"]);
  assert.equal(CG.filterNodes(nodes, { q: "", topics: ["t1"], sections: [], kinds: [], statuses: ["verified"] }).length, 0);
});

test("recordDecision replaces the same decision and keeps accept and reject exclusive", () => {
  const t = { kind: "node", id: "n" };
  let d = CG.recordDecision([], { target: t, action: "accept" });
  d = CG.recordDecision(d, { target: t, action: "reject" });
  assert.deepEqual(d.map((x) => x.action), ["reject"]);
  d = CG.recordDecision(d, { target: t, action: "edit", field: "gist", base_hash: "h", new_value: "one" });
  d = CG.recordDecision(d, { target: t, action: "edit", field: "gist", base_hash: "h", new_value: "two" });
  assert.deepEqual(d.map((x) => x.action + ":" + (x.new_value || "")), ["reject:", "edit:two"]);
  d = CG.recordDecision(d, { target: t, action: "edit", field: "explanation", base_hash: "h2", new_value: "z" });
  assert.equal(d.length, 3);
});

test("buildReview has the shape apply-review expects", () => {
  const r = CG.buildReview({ graph_version: "abc123" }, [{ target: { kind: "node", id: "n" }, action: "accept" }], "Ada", "2026-10-20T00:00:00Z");
  assert.deepEqual(r, {
    schema_version: 2, graph_version: "abc123", reviewer: { name: "Ada" }, created: "2026-10-20T00:00:00Z",
    decisions: [{ target: { kind: "node", id: "n" }, action: "accept" }],
  });
});

test("issueUrl prefills a short review", () => {
  const review = CG.buildReview({ graph_version: "v" }, [], "Ada", "t");
  const { url, prefilled } = CG.issueUrl("me/graph", review);
  assert.equal(prefilled, true);
  assert.ok(url.startsWith("https://github.com/me/graph/issues/new?template=review.yml&title="));
  assert.ok(url.includes("&review="));
});

test("issueUrl falls back when the review is too long", () => {
  const decisions = Array.from({ length: 400 }, (_, i) => ({ target: { kind: "node", id: "n" + i }, action: "accept" }));
  const review = CG.buildReview({ graph_version: "v" }, decisions, "Ada", "t");
  const { url, prefilled } = CG.issueUrl("me/graph", review);
  assert.equal(prefilled, false);
  assert.ok(!url.includes("&review="));
  assert.ok(url.length < 500);
});

test("safeStorage survives a throwing localStorage", () => {
  const hostile = { get localStorage() { throw new Error("blocked"); } };
  const s = CG.safeStorage(hostile);
  assert.equal(s.get("k"), null);
  assert.equal(s.set("k", "v"), false);
});

test("safeStorage reads and writes through a working localStorage", () => {
  const mem = {};
  const win = { localStorage: { getItem: (k) => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = v; } } };
  const s = CG.safeStorage(win);
  assert.equal(s.set("k", "v"), true);
  assert.equal(s.get("k"), "v");
});

test("splitMath keeps two prices in one passage as plain text", () => {
  assert.deepEqual(CG.splitMath("costs $5 today, $10 tomorrow"), [{ type: "text", value: "costs $5 today, $10 tomorrow" }]);
  assert.deepEqual(CG.splitMath("$5 and $6"), [{ type: "text", value: "$5 and $6" }]);
});

test("splitMath still finds several real math spans in one passage", () => {
  assert.deepEqual(CG.splitMath("$x$ and $y$ with $R \subseteq X$."), [
    { type: "inline", value: "x" }, { type: "text", value: " and " }, { type: "inline", value: "y" },
    { type: "text", value: " with " }, { type: "inline", value: "R \subseteq X" }, { type: "text", value: "." },
  ]);
});

test("splitFormal returns empty array for empty or whitespace-only text", () => {
  assert.deepEqual(CG.splitFormal(""), []);
  assert.deepEqual(CG.splitFormal("   "), []);
  assert.deepEqual(CG.splitFormal(null), []);
  assert.deepEqual(CG.splitFormal(undefined), []);
});

test("splitFormal treats bare LaTeX without dollar signs as one display part", () => {
  const latex = "\\forall x, y, z \\in X, \\quad x R x \\quad \\text{and} ...";
  assert.deepEqual(CG.splitFormal(latex), [{ type: "display", value: latex }]);
  assert.deepEqual(CG.splitFormal("  " + latex + "\n"), [{ type: "display", value: latex }]);
});

test("splitFormal delegates to splitMath when text contains dollar signs", () => {
  const withMath = "Let $x \\in X$, then $$f(x) = y$$.";
  assert.deepEqual(CG.splitFormal(withMath), CG.splitMath(withMath));
  const inlineOnly = "Let $x \\in X$.";
  assert.deepEqual(CG.splitFormal(inlineOnly), CG.splitMath(inlineOnly));
});

