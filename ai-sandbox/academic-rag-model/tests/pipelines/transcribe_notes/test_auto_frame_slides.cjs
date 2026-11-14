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

test("matched scratch-layout handwriting expands an existing frame", () => {
  const s=png("s",-1481,-371,"a".repeat(40));
  const e=md("e",-2500,-371,"c".repeat(40));
  const upper=stroke("upper",-260,-455,45,78);
  const lower=stroke("lower",-20,205,29,30);
  const core=af.frameBounds([s,e],[]);
  const old={id:"f",type:"frame",x:core.x,y:core.y,
    width:core.w,height:core.h,name:"001 Slide 18",
    customData:{autoFrameSlidesKey:"e|s"}};
  const report=af.planFrames([s,e,upper,lower,old],registry,
    {slides:[entry(s,18)]});
  const plan=report.plans[0];
  assert.equal(plan.action,"update");
  assert.equal(plan.frameId,"f");
  assert.ok(plan.bounds.w>core.w);
  assert.ok(plan.bounds.h>core.h);
  assert.ok(af.contains(plan.bounds,af.box(upper)));
  assert.ok(af.contains(plan.bounds,af.box(lower)));
  assert.equal(plan.inkWarning,null);
});

test("image beside matched handwriting keeps the core frame and warns", () => {
  const s=png("s",-1481,-371,"a".repeat(40));
  const e=md("e",-2500,-371,"c".repeat(40));
  const ink=stroke("ink",-260,-400,40,70);
  const other={id:"other",type:"image",x:-250,y:-100,
    width:100,height:100,fileId:"missing"};
  const core=af.frameBounds([s,e],[]);
  const report=af.planFrames([s,e,ink,other],registry,
    {slides:[entry(s,18)]});
  const plan=report.plans[0];
  assert.equal(plan.action,"create");
  assert.equal(plan.bounds.w,core.w);
  assert.equal(plan.inkWarning,"partial_ink");
  assert.deepEqual([...plan.atRiskInkIds],["ink"]);
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

test("ink between row slides belongs to the slide on its left and is framed", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const ink=stroke("ink",1950,100,10,10);
  const report=af.planFrames([a,b,e,ink],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"create");
  assert.deepEqual([...first.inkIds],["ink"]);
  assert.ok(af.contains(first.bounds,af.box(ink)));
});

test("best-effort frame flags a stroke that crosses the next slide's band edge", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const edge=stroke("edge",2940,100,100,10);
  const report=af.planFrames([a,b,edge],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"create");
  assert.equal(first.inkWarning,"partial_ink");
  assert.deepEqual([...first.atRiskInkIds],["edge"]);
  assert.ok(first.bounds.x+first.bounds.w<=3000);
});

test("tall ink grows the frame instead of being left at the edge", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const tall=stroke("tall",1980,100,30,900);
  const report=af.planFrames([a,b,tall],registry,
    {slides:[entry(a,1),entry(b,2)]});
  const first=report.plans.find(p=>p.slideId==="a");
  assert.equal(first.action,"create");
  assert.equal(first.inkWarning,null);
  assert.ok(af.contains(first.bounds,af.box(tall)));
});

test("strict ink mode blocks a stroke crossing the next slide's band edge", () => {
  const a=png("a",0,0,"a".repeat(40));
  const b=png("b",3000,0,"b".repeat(40));
  const edge=stroke("edge",2940,100,100,10);
  const report=af.planFrames([a,b,edge],registry,
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

test("a nearby unmarked frame without exact members is not adopted", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const first=af.planFrames([s,e],registry,
    {slides:[entry(s,1)]}).plans[0];
  const f={id:"manual",type:"frame",x:first.bounds.x,y:first.bounds.y,
    width:first.bounds.w,height:first.bounds.h,name:"Manual page"};
  const record=af.planFrames([s,e,f],registry,
    {slides:[entry(s,1)]}).plans[0];
  assert.equal(record.action,"skip");
  assert.equal(record.reason,"unmanaged_existing_frame");
  assert.equal(record.frameId,null);
});

test("an unmarked frame with exact linked members can be adopted", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const first=af.planFrames([s,e],registry,
    {slides:[entry(s,1)]}).plans[0];
  const f={id:"linked",type:"frame",x:first.bounds.x,y:first.bounds.y,
    width:first.bounds.w,height:first.bounds.h,name:"Manual page"};
  s.frameId="linked";e.frameId="linked";
  const record=af.planFrames([s,e,f],registry,
    {slides:[entry(s,1)]}).plans[0];
  assert.equal(record.action,"update");
  assert.equal(record.frameId,"linked");
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
  const sidecar=source.replace(/\.excalidraw\.md$/,
    ".excalidraw.slide-order.json");
  const manifest=fs.existsSync(sidecar) ?
    JSON.parse(fs.readFileSync(sidecar,"utf8")) :
    {slides:kinds.slides.map((s,i)=>entry(s,i+1))};
  const diagnostic=af.planFrames(elements,registry,manifest);
  const actions=Object.fromEntries([...new Set(diagnostic.plans.map(p=>p.action))]
    .map(action=>[action,diagnostic.plans.filter(p=>p.action===action).length]));
  const reasons=Object.fromEntries([...new Set(diagnostic.plans.map(p=>p.reason).filter(Boolean))]
    .map(reason=>[reason,diagnostic.plans.filter(p=>p.reason===reason).length]));
  const byId=new Map(elements.map(e=>[e.id,e]));
  const conflicts=diagnostic.plans.filter(p=>p.action==="skip").map(p=>({
    slideId:p.slideId,reason:p.reason,
    slideAt:[byId.get(p.slideId)?.x,byId.get(p.slideId)?.y],
    conflicting:(p.conflictingIds||[]).map(id=>({id,
      type:byId.get(id)?.type,x:byId.get(id)?.x,y:byId.get(id)?.y,
      width:byId.get(id)?.width,height:byId.get(id)?.height})),
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
  },diagnostic:{actions,reasons,conflicts,ambiguousPairs,
    inkPlans:diagnostic.plans.filter(p=>p.inkIds.length).map(p=>({
      slideId:p.slideId,action:p.action,frameId:p.frameId,
      inkStrokes:p.inkIds.length,atRiskInkStrokes:(p.atRiskInkIds||[]).length,
      bounds:p.bounds}))},
    firstSlide:kinds.slides.slice(0,3).map(x=>x.id)}));
  assert.ok(kinds.slides.length>0);
});

const card = (id,x,y,slideId,w=950,h=500) => ({id,type:"image",x,y,width:w,height:h,
  fileId:"c".repeat(40),
  customData:{markdownImage:{schemaVersion:1},autoExplainKey:"ns|frame|"+slideId}});

test("card with autoExplainKey is its own bucket, not an explanation", () => {
  const s=png("s",0,0,"a".repeat(40));
  const result=af.classify([s,card("card",1000,0,"s")],registry);
  assert.equal(result.cards.length,1);
  assert.equal(result.explanations.length,0);
});

test("card does not trigger multiple_explanations or change the frame key", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const manifest={slides:[entry(s,1)]};
  const before=af.planFrames([s,e],registry,manifest).plans[0];
  const withCard=af.planFrames([s,e,card("card",1000,520,"s",950,100)],registry,manifest).plans[0];
  assert.notEqual(withCard.reason,"multiple_explanations");
  assert.equal(withCard.key,before.key);
});

test("card is a frame member, inside bounds, and not foreign content", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const c=card("card",0,520,"s",907,100);
  const plan=af.planFrames([s,e,c],registry,{slides:[entry(s,1)]}).plans[0];
  assert.notEqual(plan.action,"skip");
  assert.ok(plan.memberIds.includes("card"));
  assert.ok(af.contains(plan.bounds,af.box(c)));
});

test("frame containing a card is a no-op on rerun and adopts by exact members", () => {
  const s=png("s",0,0,"a".repeat(40));
  const e=md("e",1000,0,"c".repeat(40));
  const c=card("card",0,520,"s",907,100);
  const manifest={slides:[entry(s,1)]};
  const first=af.planFrames([s,e,c],registry,manifest).plans[0];
  const base={id:"frame",type:"frame",x:first.bounds.x,y:first.bounds.y,
    width:first.bounds.w,height:first.bounds.h,name:first.name};
  const marked=af.planFrames([s,e,c,{...base,customData:{autoFrameSlidesKey:first.key}}],
    registry,manifest).plans[0];
  assert.equal(marked.action,"noop");
  const linked=[{...s,frameId:"frame"},{...e,frameId:"frame"},{...c,frameId:"frame"},base];
  const adopted=af.planFrames(linked,registry,manifest).plans[0];
  assert.equal(adopted.frameId,"frame");
  assert.notEqual(adopted.reason,"unmanaged_existing_frame");
});

const sec = (sectionId,kind,anchorSlideId,order,strokeIds) =>
  ({sectionId,kind,anchorSlideId,order,strokeIds});
const secFile = (...sections) => ({schema:1,sections});

test("anchored section is named after its slide and ordered right after it", () => {
  const s=png("s",0,0,"a".repeat(40));
  const els=[s,stroke("k1",6000,100),stroke("k2",6030,110)];
  const report=af.planFrames(els,registry,{slides:[entry(s,18)]},
    secFile(sec("sec1","anchored","s",1,["k1","k2"])));
  assert.equal(report.plans.length,2);
  assert.equal(report.plans[0].slideId,"s");
  assert.equal(report.plans[1].name,report.plans[0].name+" · notes 1");
  assert.equal(report.plans[1].action,"create");
  assert.ok(af.contains(report.plans[1].bounds,af.box(els[1])));
  assert.equal(JSON.stringify(report.plans[1].memberIds),JSON.stringify(["k1","k2"]));
});

test("two sections for one slide are sequenced by order", () => {
  const s=png("s",0,0,"a".repeat(40));
  const els=[s,stroke("k1",6000,100),stroke("k2",8000,100)];
  const report=af.planFrames(els,registry,{slides:[entry(s,1)]},
    secFile(sec("b","anchored","s",2,["k2"]),sec("a","anchored","s",1,["k1"])));
  assert.equal(JSON.stringify(report.plans.slice(1).map(p=>p.name.slice(-7))),
    JSON.stringify(["notes 1","notes 2"]));
});

test("section overlapping a slide frame is skipped and writes nothing", () => {
  const s=png("s",0,0,"a".repeat(40));
  const els=[s,stroke("k1",300,100)];  // inside the slide
  const report=af.planFrames(els,registry,{slides:[entry(s,1)]},
    secFile(sec("sec1","anchored","s",1,["k1"])));
  assert.equal(report.plans[1].action,"skip");
  assert.equal(report.plans[1].reason,"section_overlaps_frame");
});

test("standalone section is named Notes 001 and follows all slide pages", () => {
  const s=png("s",0,0,"a".repeat(40));
  const els=[s,stroke("k1",6000,100)];
  const report=af.planFrames(els,registry,{slides:[entry(s,1)]},
    secFile(sec("n","standalone",null,1,["k1"])));
  assert.equal(report.plans[1].name,"Notes 001");
  assert.equal(report.plans[1].page,null);
});

test("section strokes are excluded from slide ink matching", () => {
  const s=png("s",0,0,"a".repeat(40));
  const els=[s,stroke("k1",1000,100)];   // near the slide
  const without=af.planFrames(els,registry,{slides:[entry(s,1)]});
  const withSec=af.planFrames(els,registry,{slides:[entry(s,1)]},
    secFile(sec("sec1","anchored","s",1,["k1"])));
  assert.equal(JSON.stringify(without.plans[0].inkIds),JSON.stringify(["k1"]));
  assert.equal(withSec.plans[0].inkIds.length,0);
});

test("missing sections file leaves slide planning unchanged", () => {
  const s=png("s",0,0,"a".repeat(40));
  const report=af.planFrames([s],registry,{slides:[entry(s,1)]});
  assert.equal(report.plans.length,1);
});

test("section with an unknown stroke id is skipped", () => {
  const s=png("s",0,0,"a".repeat(40));
  const report=af.planFrames([s],registry,{slides:[entry(s,1)]},
    secFile(sec("x","anchored","s",1,["ghost"])));
  assert.equal(report.plans[1].action,"skip");
  assert.equal(report.plans[1].reason,"missing_strokes");
});

test("ink-only scene yields Notes frames in reading order", () => {
  const els=[stroke("c",0,1500),stroke("b",3000,0),stroke("a",0,0)];
  const report=af.planFrames(els,registry,null);
  assert.equal(JSON.stringify(report.plans.map(p=>p.name)),
    JSON.stringify(["Notes 001","Notes 002","Notes 003"]));
  assert.equal(JSON.stringify(report.plans.map(p=>p.memberIds[0])),
    JSON.stringify(["a","b","c"]));
  assert.ok(report.plans.every(p=>p.action==="create" && p.slideId.startsWith("section:")));
  assert.ok(af.contains(report.plans[0].bounds,af.box(els[2])));
});

test("ink-only mode needs no slide-order sidecar", () => {
  const report=af.planFrames([stroke("a",0,0)],registry,null);
  assert.equal(report.orderErrors.length,0);
});

test("empty scene yields no plans", () => {
  const report=af.planFrames([],registry,null);
  assert.equal(report.plans.length,0);
  assert.equal(report.orderErrors.length,0);
});

test("scene with slides and no sidecar falls back to reading order", () => {
  const s=png("s",0,0,"a".repeat(40));
  const report=af.planFrames([s,stroke("a",9000,0)],registry,null);
  assert.equal(report.orderErrors.length,0); assert.equal(report.plans[0].page,1);
});

test("explicit sections replace automatic clustering in ink-only mode", () => {
  const els=[stroke("a",0,0),stroke("b",3000,0)];
  const report=af.planFrames(els,registry,null,
    secFile(sec("only","standalone",null,1,["a","b"])));
  assert.equal(report.plans.length,1);
  assert.equal(report.plans[0].memberIds.length,2);
});

test("section card is a member of its section frame and inside its bounds", () => {
  const s=png("s",0,0,"a".repeat(40));
  const k=stroke("k1",6000,100);
  const c=card("sc",4800,100,"section:sec1",950,500);
  const report=af.planFrames([s,k,c],registry,{slides:[entry(s,1)]},
    secFile(sec("sec1","anchored","s",1,["k1"])));
  const p=report.plans[1];
  assert.notEqual(p.action,"skip");
  assert.ok(p.memberIds.includes("sc") && p.memberIds.includes("k1"));
  assert.ok(af.contains(p.bounds,af.box(c)) && af.contains(p.bounds,af.box(k)));
});

test("neighbouring section frames shrink their padding instead of overlapping", () => {
  const els=[stroke("k1",6000,100),stroke("k2",6000,180)];   // 60px gap between strokes
  const report=af.planFrames(els,registry,{slides:[]},
    secFile(sec("n1","standalone",null,1,["k1"]),sec("n2","standalone",null,2,["k2"])));
  assert.ok(report.plans.every(p=>p.action==="create"));
  const [a,b]=report.plans.map(p=>p.bounds);
  assert.ok(a.y+a.h<=b.y || b.y+b.h<=a.y);
  for (const [p,k] of [[a,els[0]],[b,els[1]]])
    assert.ok(p.x<=k.x && p.y<=k.y && p.x+p.w>=k.x+k.width && p.y+p.h>=k.y+k.height);
});

test("4:3 PNG slides are classified as slides", () => {
  const s={id:"p",type:"image",x:0,y:0,width:726,height:544,fileId:"a".repeat(40)};
  assert.equal(af.classify([s],registry).slides.length,1);
});

test("without a slide-order file slides are numbered like reading a page", () => {
  const a=png("a",0,0,"a".repeat(40)), b=png("b",1000,0,"b".repeat(40)),
    c=png("c",0,900,"a".repeat(40));
  const report=af.planFrames([c,b,a],registry,null);
  assert.deepEqual(JSON.parse(JSON.stringify(report.plans.map(p=>p.slideId))),["a","b","c"]);
  assert.deepEqual(JSON.parse(JSON.stringify(report.plans.map(p=>p.page))),[1,2,3]);
  assert.equal(report.orderErrors.length,0);
});

test("an unreadable slide-order file is still an error, not a silent fallback", () => {
  const a=png("a",0,0,"a".repeat(40));
  const report=af.planFrames([a],registry,{slides:[]});
  assert.ok(report.orderErrors.length>0);
});

test("ink-only sections absorb tiny fragments into the nearest large cluster", () => {
  const els=[];
  for (let i=0;i<25;i++) els.push(stroke("b"+String(i).padStart(2,"0"),i*40,0));
  els.push(stroke("f1",1100,0),stroke("f2",1130,0));
  const report=af.planFrames(els,registry,{slides:[]});
  assert.equal(report.plans.length,1);
});

// ---- band assignment (column/row bands, time tiebreak, classifier fallback) ----
const tstroke = (id,x,y,created,w=20,h=20) => ({id,type:"freedraw",x,y,width:w,height:h,points:[[0,0]],created});
const column = () => [
  png("s1",0,0,"a".repeat(40)),png("s2",30,1000,"b".repeat(40)),png("s3",-20,2000,"c".repeat(40))];
const idsOf = (res,slideId) => [...(res.assigned.get(slideId)||[]).flatMap(r=>r.strokes.map(s=>s.id))].sort();

test("jittered column: far-right ink goes to the slide whose band it sits in", () => {
  const ink=[stroke("a",2500,100),stroke("b",2500,1100),stroke("c",2500,2100)];
  const res=af.matchInk(column(),ink);
  assert.deepEqual(idsOf(res,"s1"),["a"]);
  assert.deepEqual(idsOf(res,"s2"),["b"]);
  assert.deepEqual(idsOf(res,"s3"),["c"]);
  assert.equal(res.warnings.length,0);
});

function boundaryScene(extra) {
  const ink=[];
  for (let i=0;i<20;i++) ink.push(tstroke("u"+i,2500,100+i*25,1000+i*5000));    // band 1 core, t 1000..96000
  for (let i=0;i<20;i++) ink.push(tstroke("l"+i,2500,1400+i*25,300000+i*5000)); // band 2 core, t 300000+
  return [...ink,...extra];
}

test("stroke just below a boundary follows time when it was drawn with the slide above", () => {
  const res=af.matchInk(column(),boundaryScene([tstroke("x",2500,1010,98000)]));
  assert.ok(idsOf(res,"s1").includes("x"));
});

test("stroke just below a boundary follows time when drawn with the slide below", () => {
  const res=af.matchInk(column(),boundaryScene([tstroke("x",2500,1010,299000)]));
  assert.ok(idsOf(res,"s2").includes("x"));
});

test("a stroke drawn long after both bands ignores time and uses geometry", () => {
  const res=af.matchInk(column(),boundaryScene([tstroke("x",2500,1010,9000000)]));
  assert.ok(idsOf(res,"s2").includes("x"));
});

test("strokes sharing an identical created value are treated as edited in post", () => {
  const res=af.matchInk(column(),boundaryScene([
    tstroke("x",2500,1010,98000),tstroke("y",2900,1010,98000)]));
  assert.ok(idsOf(res,"s2").includes("x"));      // time ignored -> geometry
});

test("without timestamps, ink connected to the slide above defers to it", () => {
  const ink=[];
  for (let i=0;i<14;i++) ink.push(stroke("c"+i,2500,300+i*50,20,40));   // chain 300..1000, crosses band edge
  ink.push(stroke("t",2500,1020,20,40));                                // just below the edge, same cluster
  for (let i=0;i<5;i++) ink.push(stroke("n"+i,2500,1500+i*50,20,40));   // s2 core
  const res=af.matchInk(column(),ink);
  assert.ok(idsOf(res,"s1").includes("t"));
  assert.deepEqual(idsOf(res,"s2"),["n0","n1","n2","n3","n4"]);
});

test("slides side by side use row bands", () => {
  const row=[png("a",0,0,"a".repeat(40)),png("b",1500,10,"b".repeat(40))];
  const res=af.matchInk(row,[stroke("p",100,900),stroke("q",1600,900)]);
  assert.deepEqual(idsOf(res,"a"),["p"]);
  assert.deepEqual(idsOf(res,"b"),["q"]);
});

const grid = () => [png("a",0,0,"a".repeat(40)),png("b",1000,0,"b".repeat(40)),
  png("c",0,700,"c".repeat(40)),png("d",1000,700,"d".repeat(40))];

test("grid layout falls back to the classifier: clearly nearest slide wins", () => {
  const res=af.matchInk(grid(),[stroke("near",-60,300)]);
  assert.deepEqual(idsOf(res,"a"),["near"]);
});

test("grid layout: equidistant ink is reported as ambiguous, not forced", () => {
  const res=af.matchInk(grid(),[stroke("mid",950,100,10,10)]);
  assert.equal(res.warnings[0].reason,"ambiguous_ink");
  assert.equal(["a","b","c","d"].flatMap(id=>idsOf(res,id)).length,0);
});

test("a lone slide still rejects ink miles away", () => {
  const res=af.matchInk([png("a",0,0,"a".repeat(40))],[stroke("far",9000,9000)]);
  assert.equal(idsOf(res,"a").length,0);
});

test("frame is left-anchored to the slide and grows right and down over its ink", () => {
  const s=png("s",0,0,"a".repeat(40));
  const ink={bounds:{x:2500,y:0,w:100,h:1500},strokes:[]};
  const b=af.frameBounds([s],[ink]);
  assert.ok(b.x<=-500 && b.x>=-560);
  assert.ok(b.x+b.w>=2640);
  assert.ok(b.h>=1500+60);
});

test("band-assigned ink gives a frame that holds it and stops above the next slide", () => {
  const els=[...column(),stroke("a",2500,100),stroke("edge",2500,940,20,100),stroke("c",2500,2100)];
  const report=af.planFrames(els,new Map([["a".repeat(40),"s1.png"],["b".repeat(40),"s2.png"],["c".repeat(40),"s3.png"]]),null);
  const p1=report.plans.find(p=>p.slideId==="s1");
  assert.equal(p1.action,"create");
  assert.ok(p1.bounds.x+p1.bounds.w>=2540);
  assert.ok(p1.bounds.y+p1.bounds.h<=1000);
  assert.ok(p1.atRiskInkIds.includes("edge"));
});

test("tightly stacked slides still get frames that do not cover their neighbours", () => {
  const a=png("a",0,0,"a".repeat(40)), b=png("b",0,534,"b".repeat(40)), c=png("c",0,1068,"c".repeat(40));
  const report=af.planFrames([a,b,c],new Map([["a".repeat(40),"s1.png"],["b".repeat(40),"s2.png"],["c".repeat(40),"s3.png"]]),null);
  assert.ok(report.plans.every(p=>p.action==="create"));
  const mid=report.plans.find(p=>p.slideId==="b");
  assert.ok(mid.bounds.y>=a.y+a.height && mid.bounds.y+mid.bounds.h<=c.y);
  assert.ok(af.contains(mid.bounds,af.box(b)));
});

test("clamped frame suggests how far to move the next slide", () => {
  const a=png("a",0,0,"a".repeat(40)), b=png("b",3000,0,"b".repeat(40));
  const edge=stroke("edge",2940,100,100,10);          // right edge 3040, band limit 2988
  const first=af.planFrames([a,b,edge],registry,{slides:[entry(a,1),entry(b,2)]})
    .plans.find(p=>p.slideId==="a");
  assert.equal(first.suggestion.axis,"x");
  assert.equal(first.suggestion.nextSlideId,"b");
  assert.ok(first.suggestion.px>=52 && first.suggestion.px<=100);
});

test("no suggestion when all ink fits", () => {
  const a=png("a",0,0,"a".repeat(40)), b=png("b",3000,0,"b".repeat(40));
  const first=af.planFrames([a,b,stroke("ok",1500,100)],registry,{slides:[entry(a,1),entry(b,2)]})
    .plans.find(p=>p.slideId==="a");
  assert.equal(first.suggestion||null,null);
});

test("preview text tells the user to move the next slide and rerun", () => {
  const a=png("a",0,0,"a".repeat(40)), b=png("b",3000,0,"b".repeat(40));
  const plan=af.planFrames([a,b,stroke("edge",2940,100,100,10)],registry,{slides:[entry(a,1),entry(b,2)]}).plans[0];
  const line=af.previewLine({...plan,inkStrokes:plan.inkIds.length,
    atRiskInkStrokes:plan.atRiskInkIds.length});
  assert.match(line,/move/i);
  assert.match(line,/rerun/i);
});

test("ink above the next slide's top stays with its slide even when drawn after the transition", () => {
  const res=af.matchInk(column(),boundaryScene([tstroke("x",2500,950,299000)])); // centre 960 < 1000
  assert.ok(idsOf(res,"s1").includes("x"));
});

test("a burst of writing that starts above the edge stays together across it", () => {
  const scene=boundaryScene([tstroke("x1",2500,950,299000),tstroke("x2",2500,1010,300500)]);
  const res=af.matchInk(column(),scene);
  assert.ok(idsOf(res,"s1").includes("x1"));
  assert.ok(idsOf(res,"s1").includes("x2"));
});

test("neighbouring frames never overlap each other", () => {
  const els=[...column(),stroke("a",2500,100),stroke("edge",2500,940,20,50),stroke("b",2500,1100)];
  const report=af.planFrames(els,new Map([["a".repeat(40),"s1.png"],["b".repeat(40),"s2.png"],["c".repeat(40),"s3.png"]]),null);
  const [p1,p2]=report.plans;
  assert.ok(p2.bounds.y>=p1.bounds.y+p1.bounds.h);
  assert.ok(af.contains(p2.bounds,af.box(els[1])));
});
