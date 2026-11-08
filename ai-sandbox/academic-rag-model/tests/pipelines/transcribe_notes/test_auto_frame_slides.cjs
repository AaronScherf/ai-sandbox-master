const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const nodePath = require("node:path");
const {execFileSync} = require("node:child_process");
const {createHash,webcrypto} = require("node:crypto");

const path = process.env.AUTO_FRAME_SCRIPT ||
  nodePath.resolve(__dirname,
    "../../../../academic-hub/academic_notes/Excalidraw/Scripts/Auto-Frame Slides.md");
if (!fs.existsSync(path))
  throw new Error("Set AUTO_FRAME_SCRIPT to the child-worktree script path");
const context = {__AUTO_FRAME_TEST__: true,crypto:webcrypto,TextEncoder};
vm.runInNewContext(fs.readFileSync(path, "utf8"), context, {filename:path});
const af = context.__AUTO_FRAME_EXPORTS__;

const png = (id,x,y,fileId) => ({id,type:"image",x,y,width:907,height:510,fileId});
const md = (id,x,y,fileId) => ({id,type:"image",x,y,width:950,height:500,fileId});
const stroke = (id,x,y,w=20,h=20) => ({id,type:"freedraw",x,y,width:w,height:h,points:[[0,0]]});
const registry = new Map([
  ["a".repeat(40),"slide-1.png"],["b".repeat(40),"slide-2.png"],
  ["c".repeat(40),"markdown-image"],["d".repeat(40),"markdown-image"]
]);
const entry = (slide,page) => ({
  slideElementId:slide.id,fileId:slide.fileId,assetSha1:"e".repeat(40),
  deck:"LIML",page,total:56
});

test("embedded file parser retains entries after blank lines", () => {
  const raw = "# Markdown Images\n\n## Embedded Files\n"+
    "a".repeat(40)+": [[slide-1.png]]\n\n"+
    "c".repeat(40)+": markdown-image\n\n%%\n## Drawing\n";
  const found=af.embeddedFiles(raw);
  assert.equal(found.size,2);
  assert.equal(found.get("c".repeat(40)),"markdown-image");
});

test("classification distinguishes slides, markdown images, and ink", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const other=png("o",3000,0,"missing");
  const result=af.classify([s,e,stroke("i",300,20),other],registry);
  assert.equal(result.slides.length,1);
  assert.equal(result.explanations.length,1);
  assert.equal(result.ink.length,1);
  assert.equal(result.unrelated.length,1);
});

test("slide numbers determine frame order after spatial shuffle", () => {
  const s2=png("s2",0,1000,"a".repeat(40));
  const s1=png("s1",3000,0,"b".repeat(40));
  const e2=md("e2",1000,1000,"c".repeat(40));
  const e1=md("e1",4000,0,"d".repeat(40));
  const report=af.planFrames([s2,s1,e2,e1],registry,
    {slides:[entry(s2,2),entry(s1,1)]});
  assert.equal(report.orderErrors.length,0);
  assert.equal(report.plans[0].slideId,"s1");
  assert.equal(report.plans[0].name,"001 Slide 1");
  assert.equal(report.plans[1].slideId,"s2");
  assert.equal(report.plans[1].name,"002 Slide 2");
  assert.ok(report.plans.every(p=>p.action==="create"));
});

test("handwriting is included spatially without modifying strokes", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const i=stroke("ink",1950,100,15,20);
  const before=JSON.stringify(i);
  const report=af.planFrames([s,e,i],registry,{slides:[entry(s,18)]});
  const frame=report.plans[0];
  assert.equal(frame.action,"create");
  assert.equal(frame.inkIds.length,1);
  assert.equal(frame.inkIds[0],"ink");
  assert.ok(af.contains(frame.bounds,af.box(i)));
  assert.equal(JSON.stringify(i),before);
});

test("ambiguous ink is reported instead of assigned", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const region=af.clusterInk([stroke("shared",1950,100,10,10)]);
  const result=af.matchInk([a,b],region);
  assert.equal(result.warnings.length,1);
  assert.equal(result.warnings[0].reason,"ambiguous_ink");
});

test("same-row explanation outranks the next slide below it", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",0,550,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const matched=af.matchExplanations([a,b],[e]);
  assert.equal(matched.warnings.length,0);
  assert.equal(matched.assigned.get("a")[0].id,"e");
});

test("fully enclosed uncertain ink is reported but does not block framing", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const uncertain=stroke("uncertain",1950,100,10,10);
  const report=af.planFrames([a,b,e,uncertain],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"create");
  assert.deepEqual([...first.unverifiedInkIds],["uncertain"]);
  assert.ok(af.contains(first.bounds,af.box(uncertain)));
});

test("best-effort frame flags a touching stroke that crosses its edge", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const edge=stroke("edge",1980,100,30,10);
  const report=af.planFrames([a,b,e,edge],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"create");
  assert.equal(first.inkWarning,"partial_ink");
  assert.deepEqual([...first.atRiskInkIds],["edge"]);
});

test("oversize touching ink is disclosed without blocking slide framing", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const edge=stroke("edge",1980,100,30,900);
  const report=af.planFrames([a,b,e,edge],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"create");
  assert.equal(first.inkWarning,"partial_ink");
  assert.ok(first.atRiskInkIds.includes("edge"));
});

test("strict ink mode blocks a stroke crossing the frame edge", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const edge=stroke("edge",1980,100,30,10);
  const report=af.planFrames([a,b,e,edge],registry,
    {slides:[entry(a,1),entry(b,2)],inkPolicy:"strict"});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"skip");
  assert.equal(first.reason,"ink_at_frame_edge");
});

test("another image inside the print area still blocks framing", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const other={id:"other",type:"image",x:1700,y:20,width:200,
    height:200,fileId:"missing"};
  const report=af.planFrames([a,b,e,other],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"skip");
  assert.equal(first.reason,"foreign_content");
});

test("missing or duplicated numbers block order-dependent apply", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  assert.equal(af.validateOrder([a,b],{slides:[entry(a,1)]}).errors.length,1);
  assert.ok(af.validateOrder([a,b],{slides:[entry(a,1),entry(b,1)]}).errors.length>0);
  const report=af.planFrames([a,b],registry,{slides:[entry(a,1)]});
  assert.ok(report.plans.every(p=>p.action==="skip"));
});

test("oversize content is never clipped into a frame", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));e.height=1100;
  const report=af.planFrames([s,e],registry,{slides:[entry(s,1)]});
  assert.equal(report.plans[0].action,"skip");
  assert.equal(report.plans[0].reason,"overflow");
});

test("managed frame with unchanged geometry is a no-op", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const manifest={slides:[entry(s,1)]};
  const first=af.planFrames([s,e],registry,manifest).plans[0];
  const f={id:"frame",type:"frame",x:first.bounds.x,y:first.bounds.y,
    width:first.bounds.w,height:first.bounds.h,name:first.name,
    customData:{autoFrameSlidesKey:first.key}};
  const second=af.planFrames([s,e,f],registry,manifest).plans[0];
  assert.equal(second.action,"noop");
  assert.equal(second.frameId,"frame");
});

test("an overlapping unmanaged frame is not duplicated", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const f={id:"manual",type:"frame",x:-300,y:-100,width:2600,height:800,
    name:"Manual page"};
  const record=af.planFrames([s,e,f],registry,{slides:[entry(s,1)]}).plans[0];
  assert.equal(record.action,"skip");
  assert.equal(record.reason,"unmanaged_existing_frame");
});

test("sidecar template hashes the linked PNG and rejects a stale hash", async () => {
  const image=png("s",0,0,"a".repeat(40));
  const file={path:"lecture/note.excalidraw.md"};
  const asset={path:"lecture/assets/slide-1.png"};
  const bytes=Buffer.from("test png bytes");
  const actual=createHash("sha1").update(bytes).digest("hex");
  const scene="## Embedded Files\n"+"a".repeat(40)+": [[slide-1.png]]\n\n%%\n";
  const sidecar={slides:[{...entry(image,1),assetSha1:"0".repeat(40)}]};
  context.app={
    vault:{
      read:async f=>f===file ? scene : JSON.stringify(sidecar),
      getAbstractFileByPath:()=>({path:"sidecar"}),
      readBinary:async()=>bytes
    },
    metadataCache:{getFirstLinkpathDest:()=>asset}
  };
  const result=await af.readInputs(file,[image]);
  assert.equal(result.template.slides[0].assetSha1,actual);
  assert.equal(result.errors.length,1);
  assert.match(result.errors[0],/Stale asset hash/);
});

test("mock EA saves a new frame once and preserves source coordinates", async () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const scene=[s,e];
  const workbench=new Map();
  let saves=0;
  const view={file:null};
  context.ea={
    targetView:view,
    clear(){workbench.clear();},
    getViewElements(){return scene;},
    getElements(){return [...workbench.values()];},
    copyViewElementsToEAforEditing(items) {
      for (const item of items) workbench.set(item.id,{...item});
    },
    addFrame(x,y,width,height,name) {
      workbench.set("f",{id:"f",type:"frame",x,y,width,height,name});
      return "f";
    },
    getElement(id){return workbench.get(id);},
    addElementsToFrame(id,ids) {
      for (const member of ids) workbench.get(member).frameId=id;
    },
    async addElementsToView() {
      saves++;
      for (const item of workbench.values()) {
        const at=scene.findIndex(x=>x.id===item.id);
        if (at<0) scene.push(item); else scene[at]=item;
      }
      return true;
    }
  };
  const manifest={slides:[entry(s,1)]};
  const plan=af.planFrames(scene,registry,manifest);
  const result=await af.applyPlan(view,null,af.fingerprint(scene),plan,registry);
  assert.equal(result[0].action,"create");
  assert.equal(saves,1);
  assert.equal(scene.filter(x=>x.type==="frame").length,1);
  assert.equal(scene[0].x,0);
  assert.equal(scene[1].x,1000);
  const repeat=af.planFrames(scene,registry,manifest);
  assert.equal(repeat.plans[0].action,"noop");
  scene[1].x+=50;
  const changed=af.planFrames(scene,registry,manifest);
  assert.equal(changed.plans[0].action,"update");
  await af.applyPlan(view,null,af.fingerprint(scene),changed,registry);
  assert.equal(saves,2);
  assert.equal(scene.filter(x=>x.type==="frame").length,1);
});

test("optional read-only live scene inventory", {skip:!process.env.AUTO_FRAME_LIVE_SCENE}, () => {
  const source=process.env.AUTO_FRAME_LIVE_SCENE;
  const python = [
    "import json,re,sys,pathlib",
    "from lzstring import LZString",
    "s=pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')",
    "m=re.search(r'```compressed-json\\s*\\n(.*?)\\n```',s,re.S)",
    "d=json.loads(LZString().decompressFromBase64(re.sub(r'\\s+','',m.group(1))))",
    "print(json.dumps([{k:x.get(k) for k in ('id','type','x','y','width','height','fileId','customData','isDeleted','frameId','name','version')} for x in d['elements']]))"
  ].join("\n");
  const raw=fs.readFileSync(source,"utf8");
  const elements=JSON.parse(execFileSync("python",["-c",python,source],
    {encoding:"utf8",maxBuffer:20_000_000,timeout:120_000}));
  const registry=af.embeddedFiles(raw);
  const kinds=af.classify(elements,registry);
  const regions=af.clusterInk(kinds.ink);
  const matched=af.matchInk(kinds.slides,regions);
  const diagnostic=af.planFrames(elements,registry,
    {slides:kinds.slides.map((s,i)=>entry(s,i+1))});
  const actions=Object.fromEntries([...new Set(diagnostic.plans.map(p=>p.action))]
    .map(action=>[action,diagnostic.plans.filter(p=>p.action===action).length]));
  const reasons=Object.fromEntries([...new Set(diagnostic.plans.map(p=>p.reason).filter(Boolean))]
    .map(reason=>[reason,diagnostic.plans.filter(p=>p.reason===reason).length]));
  const byId=new Map(elements.map(e=>[e.id,e]));
  const conflicts=diagnostic.plans.filter(p=>p.action==="skip").map(p=>({
    slideId:p.slideId,reason:p.reason,
    conflictingTypes:Object.fromEntries([...new Set((p.conflictingIds||[])
      .map(id=>byId.get(id)?.type))].map(type=>[type,
      (p.conflictingIds||[]).filter(id=>byId.get(id)?.type===type).length]))
  }));
  const ambiguousPairs=diagnostic.warnings.filter(w=>w.reason==="ambiguous_pair")
    .map(w=>({explanation:w.ids[0],
      explanationAt:[byId.get(w.ids[0])?.x,byId.get(w.ids[0])?.y],
      candidateSlides:w.slideIds.map(id=>({id,
        at:[byId.get(id)?.x,byId.get(id)?.y]}))}));
  console.log(JSON.stringify({scene:source,counts:{
    elements:elements.length,slides:kinds.slides.length,
    explanations:kinds.explanations.length,strokes:kinds.ink.length,
    regions:regions.length,frames:kinds.frames.length,
    inkAmbiguous:matched.warnings.length
  },diagnostic:{actions,reasons,conflicts,ambiguousPairs},
    firstSlide:kinds.slides.slice(0,3).map(x=>x.id)}));
  assert.ok(kinds.slides.length>0);
});
