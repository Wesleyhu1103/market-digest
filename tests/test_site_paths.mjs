import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const configJs = fs.readFileSync(new URL("../docs/js/config.js", import.meta.url), "utf8");

function loadConfig(pathname, hostname = "market-digest-liart.vercel.app") {
  const context = {
    location: { pathname, hostname },
    MD_VERCEL_ORIGIN: "https://market-digest-liart.vercel.app",
  };
  vm.createContext(context);
  vm.runInContext(configJs, context, { filename: "docs/js/config.js" });
  return context;
}

{
  const ctx = loadConfig("/archive/2026-08-17.html");
  assert.equal(ctx.mdSiteBasePath(), "/");
  assert.equal(ctx.mdSitePath("archive/manifest.json"), "/archive/manifest.json");
}

{
  const ctx = loadConfig("/market-digest/archive/2026-08-17.html", "wesleyhu1103.github.io");
  assert.equal(ctx.mdSiteBasePath(), "/market-digest/");
  assert.equal(ctx.mdSitePath("archive/2026-08-14.html"), "/market-digest/archive/2026-08-14.html");
  assert.equal(ctx.mdMacroFredUrl(), "/market-digest/fred-data.json");
}

{
  const ctx = loadConfig("/market-digest/");
  assert.equal(ctx.mdSiteBasePath(), "/market-digest/");
  assert.equal(ctx.mdSitePath("/fred-data.json"), "/market-digest/fred-data.json");
}

console.log("site path tests passed");
