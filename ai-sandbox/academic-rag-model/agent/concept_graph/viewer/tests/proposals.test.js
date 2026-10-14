const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const CG = require("../logic.js");

const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "similarity_cases.json"), "utf8"));

test("similarNames agrees with the shared fixture", () => {
  cases.similar.forEach(([a, b]) => assert.ok(CG.similarNames(a, b) && CG.similarNames(b, a), `${a} ~ ${b}`));
  cases.different.forEach(([a, b]) => assert.ok(!CG.similarNames(a, b), `${a} !~ ${b}`));
});

test("slugFromName drops apostrophes and punctuation", () => {
  assert.equal(CG.slugFromName("Sen's Alpha (axiom)"), "sens-alpha-axiom");
  assert.equal(CG.slugFromName("  !!  "), "");
});

const graph = {
  graph_version: "v1",
  nodes: [{ id: "budget-set", name: "Budget set", kind: "object", section: "s1", topic: "demand" },
          { id: "walrasian-demand", name: "Walrasian demand", kind: "object", section: "s1", topic: "demand" }],
  edges: [{ id: "budget-set--is_a--walrasian-demand", source: "budget-set", type: "is_a", target: "walrasian-demand" }],
  sections: [{ id: "s1", order: 1 }],
  vocab: { kinds: ["object", "property"], topics: ["demand"] }
};

test("similarNodes lists the closest existing concepts first", () => {
  const got = CG.similarNodes(graph.nodes, "Walrasian demand correspondence", 3);
  assert.deepEqual(got.map((n) => n.id), ["walrasian-demand"]);
});

test("checkProposal flags the same problems the server does", () => {
  const ok = { action: "add_node", proposal: { name: "Quasi concavity", kind: "property", section: "s1", topic: "demand", note: "", connections: [] } };
  assert.deepEqual(CG.checkProposal(graph, ok.proposal, []).errors, []);
  const bad = { name: "Budget set", kind: "widget", section: "zz", topic: "nope", note: "", connections: [] };
  const errs = CG.checkProposal(graph, bad, []).errors.join(" | ");
  assert.match(errs, /already/); assert.match(errs, /kind/); assert.match(errs, /section/); assert.match(errs, /topic/);
});

test("checkProposal for a connection needs a condition for implies and refuses duplicates", () => {
  const e = { source: "budget-set", type: "implies", target: "walrasian-demand", condition: "", note: "" };
  assert.match(CG.checkProposal(graph, e, []).errors.join(" "), /condition/);
  const dup = { source: "budget-set", type: "is_a", target: "walrasian-demand", condition: null, note: "" };
  assert.match(CG.checkProposal(graph, dup, []).errors.join(" "), /already exists/);
});

test("buildReview emits version 2 and appends proposals after decisions", () => {
  const p = { action: "add_edge", proposal: { source: "a", type: "is_a", target: "b" } };
  const r = CG.buildReview(graph, [{ target: { kind: "node", id: "x" }, action: "accept" }], "Ada", "2026-10-20T00:00:00Z", [p]);
  assert.equal(r.schema_version, 2);
  assert.equal(r.decisions.length, 2);
  assert.equal(r.decisions[1].action, "add_edge");
});

test("checkProposal refuses a concept that is already among the pending proposals", () => {
  const pending = [{ action: "add_node", proposal: { name: "foo bar", kind: "object", section: "s1", topic: "demand", note: "", connections: [] } }];
  const again = { name: "Foo  Bar", kind: "object", section: "s1", topic: "demand", note: "", connections: [] };
  assert.match(CG.checkProposal(graph, again, pending).errors.join(" "), /already in your proposals/);
});
