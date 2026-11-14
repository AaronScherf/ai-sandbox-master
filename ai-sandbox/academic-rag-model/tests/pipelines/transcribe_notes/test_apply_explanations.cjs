const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const nodePath = require("node:path");
const {createHash,webcrypto} = require("node:crypto");

const path = process.env.APPLY_EXPLANATIONS_SCRIPT;
if (!path || !fs.existsSync(path))
  throw new Error("Set APPLY_EXPLANATIONS_SCRIPT to the nested-vault Apply Explanations.md");
const context = {__APPLY_EXPLANATIONS_TEST__: true,crypto:webcrypto,TextEncoder};
vm.runInNewContext(fs.readFileSync(path, "utf8"), context, {filename:path});
const ax = context.__APPLY_EXPLANATIONS_EXPORTS__;

const fixDir = nodePath.join(__dirname,"fixtures","framed_explainer");
const load = (name) => JSON.parse(fs.readFileSync(nodePath.join(fixDir,name),"utf8"));
const elements = () => load("scene_elements_ok.json");
const J = (x) => JSON.stringify(x);
const sectionFrame = {x:5960,y:60,width:100,height:100};
const framesOf = (els,extra=[sectionFrame]) =>
  els.filter(e=>e.type==="frame").concat(extra);

test("ok fixture validates", () => {
  const r=ax.validateResult(load("result_ok.json"),elements());
  assert.equal(J(r.errors),"[]");
  assert.equal(r.ok,true);
});

test("duplicate stroke fails and names the id", () => {
  const r=ax.validateResult(load("result_dup_stroke.json"),elements());
  assert.equal(r.ok,false);
  assert.ok(r.errors.some(e=>e.includes("duplicate stroke k1")));
});

test("unknown slide, three paragraphs and reserved text fail", () => {
  const bad=load("result_ok.json");
  bad.slides[0].slide_id="nope";
  assert.ok(ax.validateResult(bad,elements()).errors.some(e=>e.includes("unknown slide nope")));
  const three=load("result_ok.json");
  three.slides[0].card.paragraphs.push("third");
  assert.ok(ax.validateResult(three,elements()).errors.some(e=>e.includes("exactly two")));
  const marker=load("result_ok.json");
  marker.sections[0].transcription="x # Markdown Images y";
  assert.ok(ax.validateResult(marker,elements()).errors.some(e=>e.includes("reserved")));
});

test("resolved fixture passes coverage with its section frame; counts match", () => {
  const els=elements();
  const a=ax.auditCoverage(load("result_resolved_ok.json"),els,framesOf(els));
  assert.equal(a.ok,true);
  assert.equal(J(a.counts),J({assigned:2,fallback_nearest:1,section:1}));
});

test("stroke outside every frame fails outsideFrame", () => {
  const els=elements();
  const a=ax.auditCoverage(load("result_resolved_ok.json"),els,framesOf(els,[]));
  assert.equal(a.ok,false);
  assert.equal(J(a.outsideFrame),J(["k4"]));
});

test("stroke missing from every disposition fails coverage", () => {
  const els=elements(), res=load("result_resolved_ok.json");
  res.slides[0].ink[0].stroke_ids=["k1"];   // k2 dropped
  const a=ax.auditCoverage(res,els,framesOf(els));
  assert.equal(a.ok,false);
  assert.equal(J(a.missing),J(["k2"]));
});

test("duplicated stroke fails coverage", () => {
  const els=elements(), res=load("result_resolved_ok.json");
  res.sections[0].stroke_ids=["k4","k1"];
  const a=ax.auditCoverage(res,els,framesOf(els));
  assert.equal(a.ok,false);
  assert.equal(J(a.duplicated),J(["k1"]));
});

test("deleted strokes are ignored by the audit", () => {
  const els=elements();
  els.push({id:"kd",type:"freedraw",x:99999,y:99999,width:5,height:5,isDeleted:true});
  const a=ax.auditCoverage(load("result_resolved_ok.json"),els,framesOf(els));
  assert.equal(a.ok,true);
});
