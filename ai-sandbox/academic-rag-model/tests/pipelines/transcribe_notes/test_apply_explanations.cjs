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

const slide907 = {x:0,y:0,width:907,height:510};
const frameAt = (x,w=3300,h=600) => ({x,y:-10,width:w,height:h});
const natural = {w:1000,h:547};
const near = (a,b,eps=0.01) => Math.abs(a-b) < eps;

test("slot is left of the slide, top-aligned, 4 percent gap, 1.08x width (LIML2 convention)", () => {
  const r=ax.planCardSlot(frameAt(-1100),slide907,natural,[]);
  assert.equal(r.ok,true);
  assert.ok(near(r.w,1.08*907));
  assert.ok(near(r.x+r.w,-0.04*907));
  assert.equal(r.y,0);
  assert.ok(near(r.h,547*r.w/1000));
});

test("width is clamped to the free frame width when expansion is not offered", () => {
  const r=ax.planCardSlot(frameAt(-600),slide907,natural,[]);
  assert.equal(r.ok,true);
  assert.ok(near(r.x,-600));
  assert.ok(r.w < 1.08*907 && r.w >= 0.5*907);
});

test("ink in the slot yields placement_conflict", () => {
  const r=ax.planCardSlot(frameAt(-1100),slide907,natural,[{x:-500,y:100,width:50,height:50}]);
  assert.equal(r.ok,false);
  assert.equal(r.reason,"placement_conflict");
});

test("expansion happens only when allowed by the caller", () => {
  const narrow=frameAt(-200);
  const denied=ax.planCardSlot(narrow,slide907,natural,[],{canExpand:()=>false});
  assert.equal(denied.ok,false);
  const allowed=ax.planCardSlot(narrow,slide907,natural,[],{canExpand:()=>true});
  assert.equal(allowed.ok,true);
  assert.ok(near(allowed.w,1.08*907));
  assert.ok(allowed.expandFrame.x <= allowed.x);
  assert.ok(allowed.expandFrame.x+allowed.expandFrame.width >= narrow.x+narrow.width);
});

test("expansion is preferred over clamping when allowed", () => {
  const r=ax.planCardSlot(frameAt(-600),slide907,natural,[],{canExpand:()=>true});
  assert.ok(near(r.w,1.08*907));
  assert.ok(r.expandFrame);
});

test("slot scales with slide size (607 and 1473 wide)", () => {
  const small={x:0,y:0,width:607,height:457}, big={x:0,y:0,width:1473,height:828};
  const a=ax.planCardSlot(frameAt(-800,2600,560),small,natural,[]);
  const b=ax.planCardSlot(frameAt(-2000,6000,900),big,natural,[]);
  assert.ok(near(a.w,1.08*607) && near(a.x+a.w,-0.04*607));
  assert.ok(near(b.w,1.08*1473) && near(b.x+b.w,-0.04*1473));
});

test("card taller than the frame is a conflict unless expansion is allowed", () => {
  const short=frameAt(-1100,3300,400);
  assert.equal(ax.planCardSlot(short,slide907,natural,[]).ok,false);
  assert.equal(ax.planCardSlot(short,slide907,natural,[],{canExpand:()=>true}).ok,true);
});

test("card action: create, noop, update_stale, skipped_existing", () => {
  const cards=new Map([["k1",{fingerprint:"fpA"}]]);
  assert.equal(ax.decideCardAction(cards,"k2","fpA",false),"create");
  assert.equal(ax.decideCardAction(cards,"k1","fpA",false),"noop");
  assert.equal(ax.decideCardAction(cards,"k1","fpB",false),"update_stale");
  assert.equal(ax.decideCardAction(cards,"k2","fpA",true),"skipped_existing");
  assert.equal(ax.decideCardAction(cards,"k1","fpB",true),"update_stale");
});

test("refWidth sizes the card from a reference width instead of the box width", () => {
  const inkBox={x:0,y:0,width:300,height:200};
  const r=ax.planCardSlot(frameAt(-1500),inkBox,natural,[],{refWidth:907});
  assert.ok(near(r.w,1.08*907));
  assert.ok(near(r.x+r.w,-0.04*907));
});

// ---- applyResolved orchestration (adapter stubbed; real card creation is a live probe) ----
function makeAdapter(els, o={}) {
  const calls=[]; let n=0;
  return {calls,
    measureCard: async () => ({w:1000,h:547}),
    createCard: async (spec) => {
      calls.push(["create",spec.key]);
      const id="card"+(++n);
      if (!o.dropCard) els.push({id,type:"image",x:spec.x,y:spec.y,width:spec.w,height:spec.h,
        fileId:"f"+id,frameId:spec.frameId,
        customData:{markdownImage:{schemaVersion:1},autoExplainKey:spec.key,
          autoExplainFingerprint:spec.fingerprint}});
      return {id};
    },
    deleteElement: async (id) => { calls.push(["delete",id]);
      els.find(e=>e.id===id).isDeleted=true; },
    expandFrame: async (id,b) => { calls.push(["expand",id]);
      Object.assign(els.find(e=>e.id===id),b); },
    writeSections: async (json) => { calls.push(["sections",json.sections.length]); this_last=json; },
    getElements: () => els};
}
let this_last=null;
const ctxFor = (els, adapter, resolved=load("result_resolved_ok.json"), sha="1".repeat(40)) =>
  ({resolved, elements:els, sceneSha1:sha, adapter});

test("apply aborts with no write when the scene hash differs from collect", async () => {
  const els=elements(), ad=makeAdapter(els);
  els.find(e=>e.id==="k1").x+=500;   // handwriting really moved
  await assert.rejects(ax.applyResolved(ctxFor(els,ad,undefined,"2".repeat(40))),
    /changed since collect/);
  assert.equal(ad.calls.length,0);
});

test("apply refuses when the coverage audit fails", async () => {
  const els=elements(), ad=makeAdapter(els), res=load("result_resolved_ok.json");
  res.slides[0].ink[0].stroke_ids=["k1"];   // k2 has no disposition
  await assert.rejects(ax.applyResolved(ctxFor(els,ad,res)),/coverage/);
  assert.equal(ad.calls.length,0);
});

test("a follow-up apply survives the framer rewriting the file when the strokes are unchanged", async () => {
  const els=elements(), ad=makeAdapter(els);
  const out=await ax.applyResolved(ctxFor(els,ad,undefined,"2".repeat(40)));
  assert.equal(out.find(r=>r.key==="t--x|f1|s1").action,"create");
});

test("a failed card creation leaves the old card in place", async () => {
  const els=elements(), ad=makeAdapter(els);
  await ax.applyResolved(ctxFor(els,ad));
  const res=load("result_resolved_ok.json"); res.fingerprints.s1="fpNEW";
  ad.createCard=async()=>{ throw new Error("adapter down"); };
  await assert.rejects(ax.applyResolved(ctxFor(els,ad,res)),/adapter down/);
  assert.equal(els.filter(e=>!e.isDeleted && e.customData?.autoExplainKey==="t--x|f1|s1").length,1);
});

test("sections.json is written last, after the cards exist", async () => {
  const els=elements(), ad=makeAdapter(els);
  await ax.applyResolved(ctxFor(els,ad));
  assert.equal(ad.calls[ad.calls.length-1][0],"sections");
});

test("apply refuses a result with no namespace instead of crashing", async () => {
  const els=elements(), ad=makeAdapter(els), res=load("result_resolved_ok.json");
  delete res.namespace;
  await assert.rejects(ax.applyResolved(ctxFor(els,ad,res)),/namespace/);
});

test("apply writes cards, creates one card for s1, reports the rest", async () => {
  const els=elements(), ad=makeAdapter(els);
  const results=await ax.applyResolved(ctxFor(els,ad));
  assert.ok(ad.calls.some(c=>c[0]==="expand" && c[1]==="f1"));
  const byKey=Object.fromEntries(results.map(r=>[r.key,r.action]));
  assert.equal(byKey["t--x|f1|s1"],"create");
  assert.equal(byKey["t--x|f2|s2"],"needs_review");
  assert.equal(Object.values(byKey).filter(a=>a==="awaiting_frame").length,1);
  assert.equal(this_last.sections[0].kind,"standalone");
  const card=els.find(e=>e.customData?.autoExplainKey==="t--x|f1|s1");
  const f1=els.find(e=>e.id==="f1");
  assert.ok(card.x+card.width <= -0.04*907+0.01 && card.x >= f1.x);
});

test("rerun on unchanged input is a no-op", async () => {
  const els=elements(), ad=makeAdapter(els);
  await ax.applyResolved(ctxFor(els,ad));
  const before=ad.calls.filter(c=>c[0]==="create").length;
  const again=await ax.applyResolved(ctxFor(els,ad));
  assert.equal(ad.calls.filter(c=>c[0]==="create").length,before);
  assert.equal(again.find(r=>r.key==="t--x|f1|s1").action,"noop");
});

test("changed fingerprint replaces the card once, never duplicates it", async () => {
  const els=elements(), ad=makeAdapter(els);
  await ax.applyResolved(ctxFor(els,ad));
  const res=load("result_resolved_ok.json"); res.fingerprints.s1="fpNEW";
  const out=await ax.applyResolved(ctxFor(els,ad,res));
  assert.equal(out.find(r=>r.key==="t--x|f1|s1").action,"update_stale");
  const live=els.filter(e=>!e.isDeleted && e.customData?.autoExplainKey==="t--x|f1|s1");
  assert.equal(live.length,1);
  assert.equal(live[0].customData.autoExplainFingerprint,"fpNEW");
});

test("a manual explanation in the frame is protected", async () => {
  const els=elements(), ad=makeAdapter(els);
  els.push({id:"manual",type:"image",x:-1000,y:0,width:950,height:500,fileId:"m",
    frameId:"f1",customData:{markdownImage:{schemaVersion:1}}});
  const out=await ax.applyResolved(ctxFor(els,ad));
  assert.equal(out.find(r=>r.key==="t--x|f1|s1").action,"skipped_existing");
  assert.equal(ad.calls.filter(c=>c[0]==="create").length,0);
});

test("a blocked slot is a placement_conflict and leaves the frame untouched", async () => {
  const els=elements(), ad=makeAdapter(els);
  els.push({id:"blocker",type:"image",x:-500,y:100,width:200,height:200,fileId:"b"});
  const out=await ax.applyResolved(ctxFor(els,ad));
  assert.equal(out.find(r=>r.key==="t--x|f1|s1").action,"placement_conflict");
  assert.equal(ad.calls.filter(c=>c[0]==="create"||c[0]==="expand").length,0);
});

test("post-save audit failure aborts loudly", async () => {
  const els=elements(), ad=makeAdapter(els,{dropCard:true});
  await assert.rejects(ax.applyResolved(ctxFor(els,ad)),/Post-save audit/);
});
