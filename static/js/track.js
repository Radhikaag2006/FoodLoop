"use strict";
/* Order tracking: look an order up by its ID or by scanning its QR.
   Public (no sign-in): the page shows the waste's journey, never people. */

const TRACK_ICON = { placed: "clipboard-list", planned: "route", scheduled: "calendar", in_transit: "truck", delivered: "badge-check" };

/* The box at the top of the dashboard (and the Track page). */
function trackCard(title = "Track your waste", sub = "Enter a tracking ID or scan the QR to see where it went.") {
  return `<div class="card" id="trk"><div class="row"><span class="li-ic">${icon("route", 20)}</span>
    <div class="grow"><b>${title}</b><div class="muted small">${sub}</div></div></div>
    <div class="row" style="margin-top:12px"><input id="tid" placeholder="FL-XXXXXXXX" autocapitalize="characters" autocomplete="off" spellcheck="false" aria-label="Tracking ID" style="flex:1;min-width:0;text-transform:uppercase">
      <button class="btn" id="tgo">Track</button><button class="btn secondary" id="tscan" aria-label="Scan QR code" title="Scan QR code">${icon("scan-qr-code", 20)}</button></div></div>`;
}
function wireTrack(el) {
  const box = $("#trk", el); if (!box) return;
  const run = () => {
    const c = ($("#tid", box).value || "").trim();
    if (!c) return toast("Enter the tracking ID from your order.", true);
    go("/track/" + encodeURIComponent(c));
  };
  $("#tgo", box).onclick = run;
  $("#tid", box).onkeydown = (e) => { if (e.key === "Enter") run(); };
  $("#tscan", box).onclick = scanSheet;
}

/* A scanned QR holds a link like https://.../track/FL-XXXXXXXX. */
const codeFromScan = (text) => { const m = /\/track\/([A-Za-z0-9-]+)/.exec(text || ""); return (m ? m[1] : (text || "")).trim(); };
function loadScanner() {
  if (window.Html5Qrcode) return Promise.resolve();
  return new Promise((ok, no) => {
    const s = document.createElement("script");
    s.src = "/static/vendor/html5-qrcode.min.js";
    s.onload = ok; s.onerror = () => no(new Error("scanner"));
    document.head.appendChild(s);
  });
}
function scanSheet() {
  let sc;
  sheet(`<h2>Scan the QR</h2><p class="muted small">Point your camera at the QR code on your order. If the camera doesn't work, type the ID instead.</p>
    <div id="rd" style="width:100%;min-height:260px;border-radius:16px;overflow:hidden;background:#101c16"></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin:8px 0"></div>
    <button class="btn ghost block" id="cx">Type the ID instead</button>`, async (s, close) => {
    $("#cx", s).onclick = close;
    try {
      await loadScanner();
      sc = new Html5Qrcode("rd");
      await sc.start({ facingMode: "environment" }, { fps: 10, qrbox: 220 }, (text) => {
        const code = codeFromScan(text); if (!code) return;
        close(); go("/track/" + encodeURIComponent(code));
      }, () => {});
    } catch (e) {
      const plain = location.protocol === "http:" && !["localhost", "127.0.0.1"].includes(location.hostname);
      $("#err", s).textContent = plain ? "The camera needs a secure (https) connection. Type the ID instead." : "Couldn't open the camera. Type the ID instead.";
    }
  }, () => { if (sc) sc.stop().then(() => sc.clear()).catch(() => {}); });
}

/* ---------- the Track page ---------- */
route("/track", { title: "Track an order", back: "/" }, async (el) => {
  let lots = [];
  if (S.user && S.user.role === "business") { try { lots = (await api("/api/business/lots")).slice(0, 12); } catch (e) { /* the box still works */ } }
  el.innerHTML = `${trackCard("Where is my waste?", "Type the tracking ID from your order, or scan its QR code.")}
    ${lots.length ? `${section("Your orders")}<div class="list">${lots.map((l) => `<button class="li" data-c="${esc(l.track_code)}"><span class="li-ic">${itemVis(l.key, 30)}</span>
      <span class="li-main">${esc(l.item)} · ${kg(l.qty_kg)}<span class="sub num" style="letter-spacing:.04em">${esc(l.track_code)}</span></span>
      <div class="li-end">${statusChip(l.status)}</div>${icon("chevron-right", 18)}</button>`).join("")}</div>` : ""}`;
  wireTrack(el);
  $$("[data-c]", el).forEach((b) => b.onclick = () => go("/track/" + encodeURIComponent(b.dataset.c)));
});

/* ---------- one order's journey ---------- */
route("/track/:code", { title: "Order tracking", back: "/track" }, async (el, p) => {
  let t;
  try { t = await api("/api/track/" + encodeURIComponent(p.code)); }
  catch (e) {
    el.innerHTML = `${trackCard("Track another order", "Check the ID and try again.")}<div class="gap"></div>${empty("No order found", e.message, "tomato")}`;
    wireTrack(el); return;
  }
  const done = t.state === "delivered";
  el.innerHTML = `
    <div class="card"><div class="row between"><div><div class="tiny faint">Tracking ID</div><h3 class="num" style="letter-spacing:.06em">${esc(t.code)}</h3></div>
        <button class="icon-btn" id="cp" aria-label="Copy tracking link">${icon("copy", 20)}</button></div>
      <div class="row" style="margin-top:12px"><span class="li-ic ${done ? "" : "info"}">${icon(TRACK_ICON[t.state] || "route", 22)}</span>
        <div class="grow"><b style="font-size:19px">${esc(t.state_label)}</b><div class="muted small">${esc(t.item.label)} · ${kg(t.item.kg)}</div></div></div></div>
    ${section("Journey")}
    <div class="card"><div class="steps">${t.steps.map((s) => `<div class="step ${s.done ? "done" : s.current ? "now" : ""}"><i></i>
      <div><b>${esc(s.title)}</b><span>${esc(s.detail)}</span>${s.at ? `<span class="tiny faint">${fmtDay(s.at)}, ${fmtTime(s.at)}</span>` : ""}</div></div>`).join("")}</div></div>
    ${t.plant ? `${section("Where it went")}${plantCard(t.plant)}` : ""}
    ${t.how_used ? `${section("How it was used")}<div class="card"><div class="row"><span class="li-ic">${icon("sprout", 20)}</span><div class="grow"><b>${esc(t.how_used)}</b></div></div>
      <div class="gap-s"></div>${kvs([["Confirmed weight", kg(t.confirmed_kg)], ["Weight check", t.weights_match ? '<span class="chip ok">Matched</span>' : '<span class="chip bad">Flagged</span>'],
        t.co2e_kg ? ["CO₂e avoided*", `about ${t.co2e_kg} kg`] : null])}
      <p class="tiny faint" style="margin:6px 0 0">*Placeholder factor, not an audited figure.</p></div>` : ""}
    ${t.record ? `<a class="btn block" style="margin-top:14px" href="#/verify/${esc(t.record)}">${icon("shield-check", 18)} View disposal record ${esc(t.record)}</a>` : ""}
    <div class="gap"></div>${trackCard("Track another order", "Type an ID or scan a QR.")}`;
  wirePlants(el); wireTrack(el);
  $("#cp", el).onclick = () => copyText(location.origin + "/track/" + t.code);
});
