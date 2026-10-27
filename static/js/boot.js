"use strict";
function buildSplash() {
  const W = "min(100vw, 520px)";
  const vegs = SPLASH_VEG.map(([n, size, x, y, rot], i) => {
    const w = `calc(${W} * ${size} / 360)`;
    const left = `calc(50% - ${W} / 2 + ${W} * ${x} / 360)`;
    const lift = (y > 30 ? 0.18 : 0.3) * size;
    return `<div style="position:absolute;left:${left};bottom:calc(100% - ${lift.toFixed(0)}px - ${y > 30 ? 6 : 0}px);width:${w};height:${w};z-index:${y > 30 ? 0 : 1}">${
      veg(n, "100%", `style="width:100%;height:100%;--r0:${rot * 3}deg;--r1:${rot}deg;animation-delay:${(0.75 + i * 0.13).toFixed(2)}s"`)}</div>`;
  }).join("");
  $("#splash").innerHTML = `
    <div class="brand"><span class="logo-tile">${logoSVG(112)}</span>
      <h1>FoodLoop</h1><p>Waste less. Earn more.</p></div>
    <div class="stall" style="left:50%;width:${W};transform:translateX(-50%);height:calc(${W} * 140 / 360)">
      <div class="produce" style="inset:auto 0 0 0;height:100%;overflow:visible">${vegs}</div>
      <svg class="crate" viewBox="0 60 360 140" preserveAspectRatio="none" style="z-index:2">${
        splashCrate().replace(/^<svg[^>]*>|<\/svg>$/g, "")}</svg>
    </div>`;
}

(async function boot() {
  const first = !sessionStorage.getItem("fl_seen");
  buildSplash();
  const t0 = Date.now();
  const [me, cat] = await Promise.all([
    api("/api/auth/me").catch(() => ({ user: null })),
    api("/api/catalog").catch(() => null)]);
  S.user = me.user; S.cat = cat;
  const wait = Math.max(0, (first ? 2600 : 700) - (Date.now() - t0));
  await new Promise((r) => setTimeout(r, wait));
  sessionStorage.setItem("fl_seen", "1");

  // deep link from the PDF QR: /verify/CODE
  const m = /^\/verify\/([^/]+)/.exec(location.pathname);
  if (m) history.replaceState(null, "", "/#/verify/" + m[1]);
  const tk = /^\/track\/([^/]+)/.exec(location.pathname);       // from a tracking QR
  if (tk) history.replaceState(null, "", "/#/track/" + tk[1]);
  if (!location.hash || location.hash === "#/" || location.hash === "#") {
    const u = S.user;
    const dest = u ? (u.status === "pending" ? "/pending" : HOME[u.role])
      : (localStorage.getItem("fl_onb") ? "/welcome" : "/onboarding");
    history.replaceState(null, "", "/#" + dest);
  }
  await render();
  const sp = $("#splash");
  sp.classList.add("out");
  setTimeout(() => sp.remove(), 600);
  sp.addEventListener("click", () => sp.remove());

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
})();
