const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

const sections = [{ id: "s1", order: 1 }, { id: "s2", order: 2 }, { id: "s3", order: 3 }];
const nodes = [];
sections.forEach((s) => { for (let i = 0; i < 7; i++) nodes.push({ id: s.id + "n" + i, name: "N" + i, section: s.id }); });

function overlaps(pos) {
  const ids = Object.keys(pos);
  for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
    const dx = Math.abs(pos[ids[i]].x - pos[ids[j]].x), dy = Math.abs(pos[ids[i]].y - pos[ids[j]].y);
    if (dx < 170 && dy < 56) return true;
  }
  return false;
}

test("clusterLayout places every concept without overlap and keeps a section together", () => {
  const pos = CG.clusterLayout(nodes, sections);
  assert.equal(Object.keys(pos).length, nodes.length);
  assert.ok(!overlaps(pos));
  const xs = ["s1n0", "s1n6"].map((id) => pos[id].x);
  const farX = pos.s3n0.x;
  assert.ok(Math.abs(xs[0] - xs[1]) < Math.abs(xs[0] - farX) + 1);
});

test("timelineLayout orders sections left to right", () => {
  const pos = CG.timelineLayout(nodes, sections);
  assert.ok(!overlaps(pos));
  assert.ok(pos.s1n0.x < pos.s2n0.x && pos.s2n0.x < pos.s3n0.x);
});
