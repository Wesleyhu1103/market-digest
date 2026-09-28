import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const configJs = fs.readFileSync(new URL("../docs/js/config.js", import.meta.url), "utf8");

function loadConfig({ hostname, pathname }) {
  const context = {
    location: { hostname, pathname },
    MD_VERCEL_ORIGIN: "https://market-digest-liart.vercel.app",
  };
  vm.runInNewContext(configJs, context);
  return context;
}

{
  const ctx = loadConfig({
    hostname: "wesleyhu1103.github.io",
    pathname: "/market-digest/archive/2026-09-10.html",
  });
  assert.equal(ctx.mdSitePath("fred-data.json"), "/market-digest/fred-data.json");
  assert.equal(ctx.mdSitePath("archive/manifest.json"), "/market-digest/archive/manifest.json");
  assert.equal(ctx.mdMacroFredUrl(), "/market-digest/fred-data.json");
}

{
  const ctx = loadConfig({
    hostname: "market-digest-liart.vercel.app",
    pathname: "/archive/2026-09-10.html",
  });
  assert.equal(ctx.mdSitePath("fred-data.json"), "/fred-data.json");
  assert.equal(ctx.mdSitePath("archive/2026-09-09.html"), "/archive/2026-09-09.html");
  assert.equal(ctx.mdMacroFredUrl(), "/api/fred-data");
}

{
  const ctx = loadConfig({
    hostname: "wesleyhu1103.github.io",
    pathname: "/market-digest/",
  });
  assert.equal(ctx.mdSitePath("archive/manifest.json"), "/market-digest/archive/manifest.json");
}

console.log("site path tests passed");
