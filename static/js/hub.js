"use strict";
const HUBR = ["hub"];

route("/h/pool", { roles: HUBR, tabs: true, title: "Pool" }, async (el) => {
  const d = await api("/api/hub/pool");
  el.innerHTML = `${d.blocked_kg ? banner("warn", `${kg(d.blocked_kg)} is from organisations not verified yet`, "It stays in the pool and is skipped when planning runs.", "shield-check") : ""}
    <div class="kpi g"><div class="n">${num(d.total)}<small>kg waiting</small></div>
      <div class="row wrap" style="margin-top:10px">${Object.entries(d.by_tier).map(([t, x]) => `${tierChip(t)}<span style="color:#fff;font-weight:700">${x}</span>`).join(" &nbsp; ")}</div></div>
    <div class="gap"></div><div class="card"><div class="lbl">Smallest run worth sending</div>
      <div class="row"><input id="mk" type="number" inputmode="decimal" min="0" value="${d.min_kg}" style="max-width:120px"><span class="muted">kg per facility</span></div>
      <p class="small muted" style="margin:8px 0 12px">Groups smaller than this stay in the pool, so trucks only go out when it's worth it.</p>
      <button class="btn block" id="plan">${icon("route", 20)} Plan pickup runs</button></div>
    ${section("Where it's from")}
    ${d.orgs.length ? `<div class="list">${d.orgs.map((o) => `<div class="li"><span class="li-ic ${o.kind === "business" ? "warn" : ""}">${icon(o.kind === "business" ? "store" : "building-2", 20)}</span>
      <div class="li-main">${esc(o.name)}<span class="sub">Business</span></div>
      <div class="li-end">${kg(o.kg)}<span class="sub">${o.verified ? "Verified" : "Not verified"}</span></div></div>`).join("")}</div>`
      : empty("The pool is empty", "Business lots show up here as they come in.", "greens")}`;
  $("#plan", el).onclick = (e) => busy(e.currentTarget, async () => {
    const r = await post("/api/hub/plan", { min_kg: +v("mk", el) });
    sheet(`<div class="center"><div class="success-burst ${r.created.length ? "" : "bad"}">${icon(r.created.length ? "truck" : "clock", 40)}</div>
      <h2>${r.created.length ? `${r.created.length} run${r.created.length > 1 ? "s" : ""} planned` : "No runs yet"}</h2></div>
      ${r.created.map((p) => `<div class="kv"><span>${esc(p.facility)}</span><b>${kg(p.expected_kg)} · ${p.route_km} km</b></div>`).join("")}
      ${r.waiting.length ? `<p class="small muted" style="margin-top:12px"><b>Still too small:</b> ${r.waiting.map((w) => `${esc(w.facility)} (${w.kg} of ${w.need} kg)`).join(", ")}</p>` : ""}
      <div class="gap"></div><button class="btn block" id="go">${r.created.length ? "See runs" : "OK"}</button>`, (s, close) => {
      $("#go", s).onclick = () => { close(); if (r.created.length) go("/h/runs"); else render(); }; });
  });
});

function stopsHTML(p) {
  const st = p.route || [];
  return `<div class="lbl" style="margin-top:12px">Route (${p.route_km} km)</div>${st.map((s, i) => `<div class="stop"><div class="n">${i + 1}</div>
    <div class="grow"><b>${esc(s.name)}</b><div class="small muted">${esc(s.point || s.address || "")}${s.kg ? " · " + kg(s.kg) : ""}</div></div>
    ${s.phone ? `<a class="icon-btn" href="tel:+91${esc(s.phone)}" aria-label="Call">${icon("phone", 20)}</a>` : ""}</div>`).join("")}
    <div class="stop"><div class="n" style="background:var(--tomato);color:#fff">${icon("factory", 14)}</div><div class="grow"><b>${esc(p.facility)}</b>
    <div class="small muted">${esc(p.facility_address || "Drop-off")}</div></div>${p.facility_phone ? `<a class="icon-btn" href="tel:+91${esc(p.facility_phone)}" aria-label="Call">${icon("phone", 20)}</a>` : ""}</div>`;
}

route("/h/runs", { roles: HUBR, tabs: true, title: "Runs" }, async (el) => {
  let tab = "open", maps = [];
  const draw = async () => {
    maps.forEach((m) => m.remove()); maps = [];
    const rows = await api("/api/hub/runs?status=" + tab);
    el.innerHTML = `<div class="seg" id="t"><button data-k="open" class="${tab === "open" ? "on" : ""}">To do</button><button data-k="closed" class="${tab === "closed" ? "on" : ""}">Finished</button></div><div class="gap"></div>
      ${rows.length ? rows.map((p) => `<div class="card"><div class="row between"><b>Run #${p.id}</b>${statusChip(p.status)}</div>
        <p style="margin:6px 0 0"><b>${esc(p.facility)}</b> ${p.certified ? '<span class="chip ok">Certified</span>' : ""}</p>
        <p class="muted small" style="margin:2px 0 0">Expected ${kg(p.expected_kg)}</p>
        ${p.status === "closed" ? `<div class="kv" style="margin-top:8px"><span>Hub / facility</span><b>${p.hub_kg} / ${p.facility_kg} kg ${p.mismatch ? '<span class="chip bad">Mismatch</span>' : ""}</b></div>
          <a class="btn secondary sm" style="margin-top:10px" href="#/verify/${p.record}">${icon("shield-check", 16)} ${p.record}</a> <a class="btn secondary sm" style="margin-top:10px" href="/api/records/${p.record}/pdf" target="_blank" rel="noopener">PDF</a>`
        : `${stopsHTML(p)}<div class="map" id="m${p.id}" style="height:200px;margin-top:10px"></div>
          ${p.status === "planned" ? `<button class="btn block" data-c="${p.id}">${icon("truck", 20)} Mark as collected</button>`
            : `<button class="btn block" data-x="${p.id}" data-e="${p.expected_kg}">${icon("scale", 20)} Weigh and close</button>`}`}</div>`).join("")
        : empty(tab === "open" ? "No runs to do" : "Nothing finished yet", tab === "open" ? "Plan runs from the Pool tab when enough waste has built up." : "Closed runs and their records show up here.", "greens")}`;
    wireSeg($("#t", el), (k) => { tab = k; draw(); });
    rows.filter((p) => p.status !== "closed").forEach((p) => {
      const m = makeMap($("#m" + p.id, el), [p.fac_lat, p.fac_lng], 11); if (!m) return; maps.push(m);
      const pts = [[p.fac_lat, p.fac_lng], ...p.route.map((s) => [s.lat, s.lng]), [p.fac_lat, p.fac_lng]];
      L.polyline(pts, { color: "#2F9E4F", weight: 3, dashArray: "6 6" }).addTo(m);
      p.route.forEach((s, i) => L.marker([s.lat, s.lng], { icon: pin("#0F3D2E", i + 1) }).addTo(m).bindPopup(esc(s.name)));
      L.marker([p.fac_lat, p.fac_lng], { icon: pin("#E8472F", "F") }).addTo(m).bindPopup(esc(p.facility));
      m.fitBounds(pts, { padding: [24, 24], maxZoom: 13 });
    });
    $$("[data-c]", el).forEach((b) => b.onclick = () => busy(b, async () => { await post(`/api/hub/runs/${b.dataset.c}/collect`); toast("Marked as collected"); draw(); }));
    $$("[data-x]", el).forEach((b) => b.onclick = () => closeSheet(+b.dataset.x, +b.dataset.e, draw));
  };
  await draw();
  return () => maps.forEach((m) => m.remove());
});

function closeSheet(id, exp, done) {
  sheet(`<h2>Weigh and close run #${id}</h2><p class="muted small">Expected ${kg(exp)}. Enter what the hub scale and the facility scale showed. A difference over 5% is flagged on the record.</p>
    <div class="grid2"><div class="field"><label for="h">Hub weight (kg)</label><input id="h" type="number" inputmode="decimal" step="0.1"></div>
    <div class="field"><label for="f">Facility weight (kg)</label><input id="f" type="number" inputmode="decimal" step="0.1"></div></div>
    <div id="warn"></div><div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <button class="btn block" id="s">${icon("badge-check", 20)} Close and issue record</button>`, (s, close) => {
    const chk = () => { const h = +v("h", s), f = +v("f", s); if (!h || !f) return;
      const bad = Math.abs(h - exp) / exp > 0.05 || Math.abs(f - h) / h > 0.05;
      $("#warn", s).innerHTML = bad ? banner("warn", "Weights differ by more than 5%", "You can still close it. The record will show a mismatch flag.", "triangle-alert") : ""; };
    $("#h", s).oninput = chk; $("#f", s).oninput = chk;
    $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
      try { const r = await post(`/api/hub/runs/${id}/close`, { hub_kg: +v("h", s), facility_kg: +v("f", s) }); close(); toast(`Record ${r.record} issued`); done(); }
      catch (x) { $("#err", s).textContent = x.message; } }); });
}

route("/h/sites", { roles: HUBR, tabs: true, title: "Facilities" }, async (el) => {
  const rows = await api("/api/hub/facilities"); let m;
  el.innerHTML = `<div class="map" id="m"></div>${facilityList(rows)}`;
  m = makeMap($("#m", el), [28.55, 77.45], 9);
  if (m && rows.length) { const pts = rows.map((f) => [f.lat, f.lng]); rows.forEach((f) => L.marker([f.lat, f.lng], { icon: pin(f.certified ? "#2F9E4F" : "#5B6B62", f.tiers[0]) }).addTo(m).bindPopup(esc(f.name))); m.fitBounds(pts, { padding: [24, 24] }); }
  return () => m && m.remove();
});
function facilityList(rows) {
  return rows.length ? `<div class="list">${rows.map((f) => `<div class="li"><span class="li-ic ${f.certified ? "" : "mute"}">${icon("factory", 20)}</span>
    <div class="li-main">${esc(f.name)}<span class="sub">${esc(f.address || f.kind)} · ${num(f.capacity_kg)} kg</span><span class="sub">${[...f.tiers].map(tierChip).join(" ")}${f.certified ? ' <span class="chip ok">Certified</span>' : ""}</span></div>
    ${f.phone ? `<a class="icon-btn" href="tel:+91${esc(f.phone)}" aria-label="Call">${icon("phone", 20)}</a>` : ""}</div>`).join("")}</div>`
    : empty("No facilities yet", "A FoodLoop admin adds partner facilities. Until then, nothing can be matched.", "greens");
}
