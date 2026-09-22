import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const configJs = fs.readFileSync(new URL("../docs/js/config.js", import.meta.url), "utf8");

function loadConfig(pathname, hostname = "wesleyhu1103.github.io") {
  const context = {
    location: { pathname, hostname },
    MD_VERCEL_ORIGIN: "https://market-digest-liart.vercel.app",
  };
  vm.createContext(context);
  vm.runInContext(configJs, context);
  return context;
}

let ctx = loadConfig("/market-digest/");
assert.equal(ctx.mdSitePath("archive/manifest.json"), "/market-digest/archive/manifest.json");
assert.equal(ctx.mdMacroFredUrl(), "/market-digest/fred-data.json");

ctx = loadConfig("/market-digest/archive/2026-08-25.html");
assert.equal(ctx.mdSitePath("archive/manifest.json"), "/market-digest/archive/manifest.json");
assert.equal(ctx.mdSitePath("fred-data.json"), "/market-digest/fred-data.json");
assert.equal(ctx.mdSitePath("archive/2026-08-24.html"), "/market-digest/archive/2026-08-24.html");
assert.equal(ctx.mdMacroFredUrl(), "/market-digest/fred-data.json");

ctx = loadConfig("/market-digest/archive");
assert.equal(ctx.mdSitePath("archive/manifest.json"), "/market-digest/archive/manifest.json");

ctx = loadConfig("/archive/2026-08-25.html", "market-digest-liart.vercel.app");
assert.equal(ctx.mdSitePath("archive/manifest.json"), "/archive/manifest.json");
assert.equal(ctx.mdSitePath("fred-data.json"), "/fred-data.json");
assert.equal(ctx.mdMacroFredUrl(), "/api/fred-data");

console.log("all archive runtime path tests passed");
