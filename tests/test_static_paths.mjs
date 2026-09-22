import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const code = fs.readFileSync(new URL("../docs/js/config.js", import.meta.url), "utf8");

function loadConfig({ hostname, pathname, editionIso = "2026-08-18" }) {
  const digestDate = { headerEdition: () => ({ iso: editionIso }) };
  const context = {
    window: { DigestDate: digestDate },
    DigestDate: digestDate,
    location: { hostname, pathname },
    MD_VERCEL_ORIGIN: "https://market-digest.example",
    console,
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  return context;
}

{
  const ctx = loadConfig({
    hostname: "wesleyhu1103.github.io",
    pathname: "/market-digest/archive/2026-08-18.html",
  });
  assert.equal(ctx.mdSitePath("fred-data.json"), "/market-digest/fred-data.json");
  assert.equal(
    ctx.mdSitePath("archive/manifest.json"),
    "/market-digest/archive/manifest.json"
  );
  assert.equal(ctx.mdMacroFredUrl(), "/market-digest/fred-data.json");
  assert.equal(ctx.mdScoreboardAnchorIso(), "2026-08-18");
}

{
  const ctx = loadConfig({
    hostname: "market-digest-liart.vercel.app",
    pathname: "/archive/2026-08-18.html",
  });
  assert.equal(ctx.mdSitePath("fred-data.json"), "/fred-data.json");
  assert.equal(ctx.mdSitePath("archive/2026-08-17.html"), "/archive/2026-08-17.html");
  assert.equal(ctx.mdMacroFredUrl(), "/api/fred-data");
  assert.equal(ctx.mdScoreboardAnchorIso(), "2026-08-18");
}

{
  const ctx = loadConfig({
    hostname: "localhost",
    pathname: "/archive/2026-08-18.html",
  });
  assert.equal(ctx.mdMacroFredUrl(), "/fred-data.json");
}

console.log("all static path tests passed");
