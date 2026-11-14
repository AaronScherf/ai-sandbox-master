const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const nodePath = require("node:path");

const path = process.env.SELECT_BELOW_SCRIPT ||
  nodePath.resolve(__dirname,
    "../../../../academic-hub/academic_notes/Excalidraw/Scripts/Select Below.md");
if (!fs.existsSync(path)) throw new Error("Set SELECT_BELOW_SCRIPT to the script path");
const context = {__SELECT_BELOW_TEST__: true};
vm.runInNewContext(fs.readFileSync(path, "utf8"), context, {filename: path});
const sb = context.__SELECT_BELOW_EXPORTS__;

const el = (id, y, h = 10, extra = {}) => ({id, type: "freedraw", x: 0, y, width: 10, height: h, ...extra});
const ids = (list) => JSON.stringify(list.map(e => e.id).sort());

test("selects elements whose centre is on or below the line", () => {
  const picked = sb.elementsBelow([el("a", 0), el("b", 100), el("c", 200)], 100);
  assert.equal(ids(picked), JSON.stringify(["b", "c"]));
});

test("a long stroke straddling the line goes with the side its centre is on", () => {
  const above = el("long-above", 50, 90);     // centre 95
  const below = el("long-below", 60, 100);    // centre 110
  assert.equal(ids(sb.elementsBelow([above, below], 100)), JSON.stringify(["long-below"]));
});

test("deleted and locked elements are skipped", () => {
  const picked = sb.elementsBelow([el("gone", 200, 10, {isDeleted: true}),
    el("fixed", 200, 10, {locked: true}), el("ok", 200)], 100);
  assert.equal(ids(picked), JSON.stringify(["ok"]));
});

test("contents of a selected frame are not added separately", () => {
  const frame = {id: "f", type: "frame", x: 0, y: 150, width: 500, height: 300};
  const inside = el("inside", 200, 10, {frameId: "f"});
  const free = el("free", 400);
  assert.equal(ids(sb.elementsBelow([frame, inside, free], 100)), JSON.stringify(["f", "free"]));
});

test("the line is the top of the highest selected element, else the pointer", () => {
  assert.equal(sb.chooseLine([el("a", 300), el("b", 120)], {y: 999}), 120);
  assert.equal(sb.chooseLine([], {y: 450}), 450);
  assert.equal(sb.chooseLine([], null), null);
  assert.equal(sb.chooseLine([], {y: NaN}), null);
});
