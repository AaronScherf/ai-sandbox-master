// Drives hub_review_page.html's script against a fake DOM and an in-memory db. Usage: node page_harness.js PAGE.html
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const items = JSON.parse(html.match(/<script[^>]*id="review-items"[^>]*>([\s\S]*?)<\/script>/)[1]);
const scripts = [...html.matchAll(/<script(?![^>]*id="review-items")[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]);

class El {
  constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this._text = ""; this.className = ""; this.attrs = {}; }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  appendChild(c) { this.children.push(c); return c; }
  replaceChildren() { this.children = []; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  remove() {}
  click() { if (!this.disabled) (this.listeners.click || []).forEach((f) => f()); }
  find(pred, out = []) { if (pred(this)) out.push(this); this.children.forEach((c) => c.find && c.find(pred, out)); return out; }
}
const byId = {
  groups: new El("div"), summary: new El("div"), notices: new El("div"),
  "review-items": { textContent: JSON.stringify(items) },
};
global.document = {
  createElement: (t) => new El(t), createTextNode: (t) => { const e = new El("#text"); e._text = t; return e; },
  getElementById: (id) => byId[id] || (byId[id] = new El("div")),
};

// in-memory db: set/delete are async and notify snapshot listeners afterwards, like the real one
const store = new Map(); const subs = []; let failNext = null;
const notify = () => subs.forEach((f) => f({ metadata: { fromCache: false },
  docs: [...store].map(([id, v]) => ({ id, data: () => v })) }));
const tick = () => new Promise((r) => setTimeout(r, 5));
const db = { collection: () => ({
  doc: (id) => ({
    set: async (v) => { await tick(); if (failNext) { const e = new Error("boom"); e.code = failNext; failNext = null; throw e; } store.set(id, v); notify(); },
    delete: async () => { await tick(); store.delete(id); notify(); },
  }),
  onSnapshot: (f) => { subs.push(f); f({ metadata: { fromCache: false }, docs: [] }); },
}) };
global.window = { claude: { use: async () => db } };
global.setTimeout = ((orig) => (f, ms) => orig(f, ms > 1000 ? 1e9 : ms))(setTimeout);
global.clearTimeout = clearTimeout;

(0, eval)(scripts.join("\n"));

const fail = (m) => { console.error("FAIL:", m); process.exit(1); };
(async () => {
  await tick(); await tick();
  const target = items.items.find((i) => i.type === "relink" && i.candidates.length === 1);
  const twin = items.items.find((i) => i.candidates.filter((c) => ["byte_hash", "hub_id"].includes(c.basis)).length > 1);
  console.log("items:", items.items.length, "single-candidate relink:", !!target, "twin:", !!twin);
  // the card of one item, found by its subject path; buttons are then looked up inside it only
  const card = () => byId.groups.find((e) => e.className.startsWith("item") && e.textContent.includes(target.subject_paths[0]))[0];
  const btn = (label) => card().find((e) => e.tag === "button" && e.textContent.replace("✓ ", "") === label)[0];
  const text = () => card().textContent;
  // exactly the saved decision is highlighted; none while the card is open for changes
  const chosenLabels = () => card().find((e) => e.tag === "button" && e.className === "chosen")
    .map((e) => e.textContent.replace("✓ ", ""));
  const expectChosen = (want, when) => {
    const got = chosenLabels().join(",");
    if (got !== want) fail(`highlighted buttons ${when}: got [${got}], want [${want}]`);
  };
  expectChosen("", "before any decision");

  // 1. decline the item
  btn("Decline").click(); await tick(); await tick();
  if ((store.get(target.item_id) || {}).action !== "decline") fail("first decision not saved");
  if (!text().includes("Decided: decline")) fail("card not shown as decided");
  expectChosen("Decline", "after declining");

  // 2. change it, then defer instead: must overwrite the stored doc
  btn("Change decision").click(); await tick(); await tick();
  if (text().includes("Decided: decline")) fail("change decision did not reopen the card");
  if (btn("Defer").disabled) fail("buttons not enabled after Change decision");
  expectChosen("", "while changing");
  btn("Defer").click(); await tick(); await tick();
  const after = store.get(target.item_id);
  if (!after || after.action !== "defer") fail("changed decision not saved, store has " + JSON.stringify(after));
  if (!text().includes("Decided: defer")) fail("card not shown as decided: defer");
  expectChosen("Defer", "after changing to defer");

  // 3. change then keep the earlier decision
  btn("Change decision").click();
  btn("Keep earlier decision").click();
  if (!text().includes("Decided: defer")) fail("keep earlier decision did not restore the card");

  // 4. a failed write shows an error and leaves the earlier decision in place
  btn("Change decision").click();
  failNext = "permission_denied";
  btn("Decline").click();
  await tick(); await tick();
  if (!text().includes("Could not save: permission_denied")) fail("write error not shown");
  if (store.get(target.item_id).action !== "defer") fail("failed write altered the store");
  console.log("PASS: decide, change, overwrite, keep earlier, error path");
})().catch((e) => fail(e.stack));
