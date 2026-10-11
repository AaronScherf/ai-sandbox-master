const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

// A seeded pseudo-random graph, so the tests are repeatable: 3 sections of 10 nodes and 40 edges, mostly inside a
// section and between neighbouring sections, like the real course graph.
function sampleGraph() {
  let seed = 12345;
  const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
  const sections = [{ id: "s1", order: 1 }, { id: "s2", order: 2 }, { id: "s3", order: 3 }];
  const topics = ["order", "choice", "demand"];
  const nodes = [];
  sections.forEach((s, si) => {
    for (let i = 0; i < 10; i++) {
      nodes.push({ id: `${s.id}n${i}`, section: s.id, name: `Concept ${si}-${i}`, topic: topics[(i + si) % 3] });
    }
  });
  const edges = [];
  while (edges.length < 40) {
    const a = nodes[Math.floor(rnd() * nodes.length)];
    const near = nodes.filter((n) => Math.abs(n.section.charCodeAt(1) - a.section.charCodeAt(1)) <= 1 && n.id !== a.id);
    const b = near[Math.floor(rnd() * near.length)];
    if (!edges.some((e) => (e.source === a.id && e.target === b.id) || (e.source === b.id && e.target === a.id))) {
      edges.push({ id: `${a.id}->${b.id}`, source: a.id, target: b.id, type: "implies" });
    }
  }
  return { nodes, edges, sections };
}

function crossings(pos, edges) {
  const seg = (e) => [pos[e.source], pos[e.target]];
  const orient = (a, b, c) => Math.sign((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x));
  let n = 0;
  for (let i = 0; i < edges.length; i++) {
    for (let j = i + 1; j < edges.length; j++) {
      const shared = [edges[i].source, edges[i].target].some((id) => id === edges[j].source || id === edges[j].target);
      if (shared) continue;
      const [a, b] = seg(edges[i]), [c, d] = seg(edges[j]);
      if (orient(a, b, c) !== orient(a, b, d) && orient(c, d, a) !== orient(c, d, b)) n++;
    }
  }
  return n;
}

const mean = (xs) => xs.reduce((s, x) => s + x, 0) / xs.length;

test("spreadLayout is deterministic and places every node at a finite position", () => {
  const { nodes, edges, sections } = sampleGraph();
  const a = CG.spreadLayout(nodes, edges, sections);
  const b = CG.spreadLayout(nodes, edges, sections);
  assert.deepEqual(a, b);
  assert.equal(Object.keys(a).length, nodes.length);
  Object.values(a).forEach((p) => assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y)));
});

test("spreadLayout never lets two node boxes overlap", () => {
  const { nodes, edges, sections } = sampleGraph();
  const pos = CG.spreadLayout(nodes, edges, sections, { boxW: 170, boxH: 56 });
  const ids = Object.keys(pos);
  for (let i = 0; i < ids.length; i++) {
    for (let j = i + 1; j < ids.length; j++) {
      const dx = Math.abs(pos[ids[i]].x - pos[ids[j]].x), dy = Math.abs(pos[ids[i]].y - pos[ids[j]].y);
      assert.ok(dx >= 170 - 1e-6 || dy >= 56 - 1e-6, `${ids[i]} overlaps ${ids[j]}`);
    }
  }
});

test("spreadLayout still reads bottom to top: later sections sit higher on average", () => {
  const { nodes, edges, sections } = sampleGraph();
  const pos = CG.spreadLayout(nodes, edges, sections);
  const avg = (sid) => mean(nodes.filter((n) => n.section === sid).map((n) => pos[n.id].y));
  assert.ok(avg("s3") < avg("s2") && avg("s2") < avg("s1"), "y is negative upward");
});

test("spreadLayout pulls connected concepts closer than the section rows do", () => {
  const { nodes, edges, sections } = sampleGraph();
  const rows = CG.computeLayout(nodes, edges, sections);
  const spread = CG.spreadLayout(nodes, edges, sections);
  const len = (pos) => mean(edges.map((e) => Math.hypot(pos[e.source].x - pos[e.target].x, pos[e.source].y - pos[e.target].y)));
  assert.ok(len(spread) < len(rows), `spread ${len(spread)} should be shorter than rows ${len(rows)}`);
});

test("spreadLayout has fewer edge crossings than the section rows", () => {
  const { nodes, edges, sections } = sampleGraph();
  const rows = crossings(CG.computeLayout(nodes, edges, sections), edges);
  const spread = crossings(CG.spreadLayout(nodes, edges, sections), edges);
  assert.ok(spread < rows, `spread ${spread} should cross less than rows ${rows}`);
});

test("spreadLayout copes with no edges and with a single node", () => {
  const { nodes, sections } = sampleGraph();
  assert.equal(Object.keys(CG.spreadLayout(nodes, [], sections)).length, nodes.length);
  assert.deepEqual(Object.keys(CG.spreadLayout([nodes[0]], [], sections)), [nodes[0].id]);
});

test("spreadLayout keeps loose concepts from drifting far from the rest", () => {
  const { nodes, sections } = sampleGraph();
  const pos = CG.spreadLayout(nodes, [], sections);  // no edges at all: nothing holds the nodes together
  const xs = Object.values(pos).map((p) => p.x);
  assert.ok(Math.max(...xs) - Math.min(...xs) < 3500, "width stays bounded");
});
