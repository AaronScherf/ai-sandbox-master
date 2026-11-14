// Test helper: prints clusterInk(strokes) from the framer script as [[ids]...].
const fs = require("node:fs");
const vm = require("node:vm");
const {webcrypto} = require("node:crypto");
const context = {__AUTO_FRAME_TEST__: true, crypto: webcrypto, TextEncoder};
vm.runInNewContext(fs.readFileSync(process.argv[2], "utf8"), context);
const strokes = JSON.parse(fs.readFileSync(0, "utf8"));
const ex = context.__AUTO_FRAME_EXPORTS__;
let regions = ex.clusterInk(strokes);
if (process.argv[3] === "merge") regions = ex.mergeFragments(regions);
process.stdout.write(JSON.stringify(regions.map(r => r.strokes.map(s => s.id))));
