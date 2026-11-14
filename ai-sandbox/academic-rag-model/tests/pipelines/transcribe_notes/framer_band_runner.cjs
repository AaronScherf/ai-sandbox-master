// Test helper: prints matchInk(slides, strokes) from the framer as {bySlide, loose}.
const fs = require("node:fs");
const vm = require("node:vm");
const {webcrypto} = require("node:crypto");
const context = {__AUTO_FRAME_TEST__: true, crypto: webcrypto, TextEncoder};
vm.runInNewContext(fs.readFileSync(process.argv[2], "utf8"), context);
const {slides, strokes} = JSON.parse(fs.readFileSync(0, "utf8"));
const res = context.__AUTO_FRAME_EXPORTS__.matchInk(slides, strokes);
const bySlide = {};
for (const [id, regions] of res.assigned)
  bySlide[id] = regions.flatMap(r => r.strokes.map(s => s.id)).sort();
const loose = res.warnings.flatMap(w => w.ids).sort();
process.stdout.write(JSON.stringify({bySlide, loose}));
