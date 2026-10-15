const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

const sections = [{ id: "s2", order: 2, short: "Two" }, { id: "s1", order: 1, short: "One" }];
const nodes = [
  { id: "b", name: "Beta", section: "s1" }, { id: "a", name: "Alpha", section: "s1" },
  { id: "d", name: "Delta", section: "s2" }, { id: "c", name: "Gamma", section: "s2" }
];
const byId = new Map(nodes.map((n) => [n.id, n]));

test("listOrder is sections by order then names", () => {
  assert.deepEqual(CG.listOrder(sections, nodes), ["a", "b", "d", "c"]);
});

test("rangeIds is inclusive, crosses sections and works in either direction", () => {
  const order = CG.listOrder(sections, nodes);
  assert.deepEqual(CG.rangeIds(order, "b", "c"), ["b", "d", "c"]);
  assert.deepEqual(CG.rangeIds(order, "c", "b"), ["b", "d", "c"]);
  assert.deepEqual(CG.rangeIds(order, "zzz", "d"), ["d"]);
});

test("toggleId adds then removes only that id", () => {
  assert.deepEqual(CG.toggleId(["a", "b"], "c"), ["a", "b", "c"]);
  assert.deepEqual(CG.toggleId(["a", "b", "c"], "b"), ["a", "c"]);
});

test("groupBySection marks full sections and reports filtered ones", () => {
  const all = new Set(["a", "b", "c", "d"]);
  let g = CG.groupBySection(sections, nodes, ["a", "b", "d"], all);
  assert.deepEqual(g.map((x) => [x.section.id, x.ids.length, x.total, x.full]), [["s1", 2, 2, true], ["s2", 1, 2, false]]);
  g = CG.groupBySection(sections, nodes, ["d"], new Set(["a", "b", "d"]));   // "c" is hidden by a filter
  assert.equal(g[0].full, true);
  assert.equal(g[0].filtered, true);
});

test("expandedSection picks the section with most newly added concepts, ties by course order", () => {
  const g = CG.groupBySection(sections, nodes, ["a", "b", "d"], new Set(["a", "b", "c", "d"]));
  assert.equal(CG.expandedSection(g, ["a", "b", "d"], byId), "s1");
  assert.equal(CG.expandedSection(g, ["d"], byId), "s2");
  assert.equal(CG.expandedSection(g, ["a", "d"], byId), "s1");   // tie: earlier in the course
});

test("sectionButtonClick follows the three table rows", () => {
  assert.deepEqual(CG.sectionButtonClick([], "s1"), { active: ["s1"], select: "s1" });
  assert.deepEqual(CG.sectionButtonClick(["s1"], "s2"), { active: ["s1", "s2"], select: "s2" });
  assert.deepEqual(CG.sectionButtonClick(["s1", "s2"], "s1"), { active: ["s2"], select: null });
  assert.deepEqual(CG.sectionButtonClick(["s1"], "s1"), { active: [], select: null });
});

test("connectionRows modes", () => {
  const ord = { a: [1, "Alpha"], b: [1, "Beta"], d: [2, "Delta"], c: [2, "Gamma"] };
  const ids = ["a", "b", "d"];
  assert.deepEqual(CG.connectionRows("one_to_many", "b", ids, ord), [{ source: "b", target: "a" }, { source: "b", target: "d" }]);
  assert.deepEqual(CG.connectionRows("many_to_one", "b", ids, ord), [{ source: "a", target: "b" }, { source: "d", target: "b" }]);
  assert.deepEqual(CG.connectionRows("chain", "a", ["d", "a", "b"], ord), [{ source: "a", target: "b" }, { source: "b", target: "d" }]);
  assert.equal(CG.connectionRows("all_pairs", "a", ids, ord).length, 3);
  assert.deepEqual(CG.connectionRows("all_pairs", "a", ["a", "b", "d"], ord)[0], { source: "a", target: "b" });
});

test("all_pairs refuses more than four concepts", () => {
  const ord = {}; ["a", "b", "c", "d", "e"].forEach((i, k) => { ord[i] = [1, i + k]; });
  assert.deepEqual(CG.connectionRows("all_pairs", "a", ["a", "b", "c", "d", "e"], ord), []);
});
