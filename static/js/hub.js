"use strict";
const HUBR = ["hub"];

route("/h/pool", { roles: HUBR, tabs: true, title: "Pool" }, async (el) => {
  const d = await api("/api/hub/pool");
  el.innerHTML = `${d.blocked_kg ? banner("warn", `${kg(d.blocked_kg)} is from organisations not verified yet`, "It stays in the pool and is skipped when planning runs.", "shield-check") : ""}
    <div class="kpi g"><div class="n">${num(d.total)}<small>kg waiting</small></div>
      <div class="row wrap" style="margin-top:10px">${Object.entries(d.by_tier).map(([t, x]) => `${tierChip(t)}<span style="color:#fff;font-weight:700">${x}</span>`).join(" &nbsp; ")}</div></div>
    <div class="gap"></div><div class="card"><div class="lbl">Smallest run worth sending</div>
      <div class="row"><input id="mk" type="number" inputmode="decimal" min="0" value="${d.min_kg}" style="max-width:120px"><span class="muted">kg per facility</span></div>
      <p class="small muted" style="margin:8px 0 12px">Small groups are clubbed into a nearby run. They only wait here when no run is close enough.</p>
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
      ${r.created.map((p) => `<div class="kv"><span>${esc(p.facility)}<br><span class="tiny faint">${p.assigned_to ? "To " + esc(p.assigned_to) : "No collector fits, open to all"}</span></span><b>${kg(p.expected_kg)} · ${p.route_km} km</b></div>`).join("")}
      ${r.waiting.length ? `<p class="small muted" style="margin-top:12px"><b>Still too small:</b> ${r.waiting.map((w) => `${esc(w.facility)} (${w.kg} of ${w.need} kg)`).join(", ")}</p>` : ""}
      <div class="gap"></div><button class="btn block" id="go">${r.created.length ? "See runs" : "OK"}</button>`, (s, close) => {
      $("#go", s).onclick = () => { close(); if (r.created.length) go("/h/runs"); else render(); }; });
  });
});

/* ---------- the collector's week: offers, schedule and pay ---------- */
function runLine(p) {
  const f = p.fare, n = (p.route || []).length;
  return `${kg(p.expected_kg)} · ${n} stop${n === 1 ? "" : "s"} · ${f.km} km round trip`;
}
function dropLine(p) {
  const nav = `https://www.google.com/maps/dir/?api=1&destination=${p.fac_lat},${p.fac_lng}`;
  return `<div class="stop" style="margin:8px 0"><div class="n" style="background:var(--tomato);color:#fff">${icon("factory", 14)}</div>
    <div class="grow"><div class="tiny faint">Drop-off</div><b>${esc(p.facility)}</b><div class="small muted">${esc(p.facility_address || "Address not listed")}</div></div>
    <a class="icon-btn" href="${nav}" target="_blank" rel="noopener" aria-label="Navigate to drop-off">${icon("navigation", 20)}</a>
    ${p.facility_phone ? `<a class="icon-btn" href="tel:+91${esc(p.facility_phone)}" aria-label="Call drop-off">${icon("phone", 20)}</a>` : ""}</div>`;
}
function offerCard(p) {
  const f = p.fare, perKm = f.km ? f.total / f.km : 0;
  return `<div class="card" style="margin-bottom:10px"><div class="row between"><div><div class="lbl" style="margin:0">Run #${p.id} · ${esc(p.facility)}</div>
      <div style="font-size:26px;font-weight:800">${rs(f.total)}</div></div>
      <div style="text-align:right"><b>${f.km} km</b><div class="tiny faint">${rs(perKm)} per km</div></div></div>
    <p class="small muted" style="margin:6px 0 0">${runLine(p)}</p>
    <p class="tiny faint" style="margin:4px 0 0">Pick up: ${(p.route || []).map((s) => esc(s.name)).join(" → ")}</p>${dropLine(p)}<div style="height:6px"></div>
    <div class="row" style="gap:8px">${p.mine ? `<button class="btn ghost" style="flex:1" data-pass="${p.id}">Pass</button>` : ""}
      <button class="btn" style="flex:2" data-accept="${p.id}">${icon("check", 18)} Accept · ${rs(f.total)}</button></div></div>`;
}
function weekRunCard(p) {
  const s = p.schedule && p.schedule.starts;
  return `<div class="card" style="margin-bottom:8px"><div class="row between"><b>${s ? fmtTime(s) : "Time not set"} · ${esc(p.facility)}</b><b>${rs(p.fare.total)}</b></div>
    <p class="small muted" style="margin:4px 0 0">${runLine(p)}</p>${dropLine(p)}
    <div class="row" style="gap:8px;margin-top:8px">${s ? "" : `<button class="btn secondary sm" data-set="${p.id}">${icon("clock", 16)} Set pickup time</button>`}
      <a class="btn secondary sm" href="#/h/runs">Open run</a></div></div>`;
}
route("/h/week", { roles: HUBR, tabs: true, title: "My week" }, async (el) => {
  const draw = async () => {
    const d = await api("/api/hub/week");
    const all = [...d.days.flatMap((x) => x.runs), ...d.unscheduled, ...d.later];
    el.innerHTML = `<div class="kpi g"><div class="n">${rs(d.week_total)}<small>booked this week</small></div>
        <div class="row wrap" style="margin-top:10px;gap:16px;color:#fff"><span>${d.week_runs} run${d.week_runs === 1 ? "" : "s"}</span><span>${d.week_km} km</span><span>${rs(d.earned_7d)} earned in last 7 days</span></div></div>
      ${d.offers.length ? `${section("New runs for you")}${d.offers.map(offerCard).join("")}` : ""}
      ${section("Your week")}
      ${d.days.map((x) => `<div class="row between" style="margin:14px 0 6px"><b>${fmtDay(x.date + "T00:00:00+05:30")}</b><span class="muted small">${x.runs.length ? rs(x.total) : "No runs"}</span></div>${x.runs.map(weekRunCard).join("")}`).join("")}
      ${d.later.length ? `<div class="lbl" style="margin-top:14px">Later</div>${d.later.map(weekRunCard).join("")}` : ""}
      ${d.unscheduled.length ? `<div class="lbl" style="margin-top:14px">Accepted, time not set</div>${d.unscheduled.map(weekRunCard).join("")}` : ""}
      ${!all.length && !d.offers.length ? empty("Nothing booked yet", "New runs show up here with the pay and distance, and you choose which to accept.", "greens") : ""}`;
    const find = (id) => [...d.offers, ...all].find((x) => x.id === +id);
    $$("[data-accept]", el).forEach((b) => b.onclick = () => busy(b, async () => {
      await post(`/api/hub/runs/${b.dataset.accept}/accept`); toast("Added to your week"); draw(); }));
    $$("[data-pass]", el).forEach((b) => b.onclick = async () => {
      if (await confirmSheet({ title: "Pass on this run?", body: "It goes to the next nearest collector.", ok: "Pass" }))
        busy(b, async () => { await post(`/api/hub/runs/${b.dataset.pass}/decline`); toast("Passed"); draw(); }); });
    $$("[data-set]", el).forEach((b) => b.onclick = () => scheduleSheet(find(b.dataset.set), draw));
  };
  await draw();
});

function stopsHTML(p) {
  const st = p.route || [];
  return `<div class="lbl" style="margin-top:12px">Route (${p.route_km} km)</div>${st.map((s, i) => `<div class="stop"><div class="n">${i + 1}</div>
    <div class="grow"><b>${esc(s.name)}</b><div class="small muted">${esc(s.point || s.address || "")}${s.kg ? " · " + kg(s.kg) : ""}</div></div>
    ${s.phone ? `<a class="icon-btn" href="tel:+91${esc(s.phone)}" aria-label="Call">${icon("phone", 20)}</a>` : ""}</div>`).join("")}
    <div class="stop"><div class="n" style="background:var(--tomato);color:#fff">${icon("factory", 14)}</div><div class="grow"><b>${esc(p.facility)}</b>
    <div class="small muted">${esc(p.facility_address || "Drop-off")}</div></div>${p.facility_phone ? `<a class="icon-btn" href="tel:+91${esc(p.facility_phone)}" aria-label="Call">${icon("phone", 20)}</a>` : ""}</div>`;
}

const rs = (n) => "₹" + Math.round(n).toLocaleString("en-IN");
function fareHTML(p) {
  const f = p.fare, q = f.parts;
  return `<div class="card" style="margin:10px 0;background:var(--surface-2,#F3F8F1)"><div class="row between"><b>${p.status === "closed" ? "Driver fare" : "Driver fare for this trip"}</b><b style="font-size:20px">${rs(f.total)}</b></div>
    <div class="tiny faint" style="margin-top:4px">${f.km} km round trip (road estimate) · ${f.stops} stop${f.stops > 1 ? "s" : ""} · ${f.kg} kg<br>
    Base ${rs(q.base)} + distance ${rs(q.distance)} + extra stops ${rs(q.stops)} + weight ${rs(q.weight)}</div></div>`;
}
function ownerLine(p) {
  return p.mine ? `<span class="chip ok">Assigned to you</span>` : p.open ? `<span class="chip warn">Open: no collector fits yet</span>` : `<span class="chip">${esc(p.assigned_to)}</span>`;
}
function scheduleLine(p) {
  const s = p.schedule;
  return s && s.starts ? `<div class="kv" style="margin-top:8px"><span>Pickup time</span><b>${fmtDay(s.starts)}, ${fmtTime(s.starts)} to ${fmtTime(s.ends)}</b></div>`
    : `<p class="small muted" style="margin:8px 0 0">No pickup time set yet. Businesses are waiting to hear from you.</p>`;
}
function scheduleSheet(p, done) {
  const d = new Date(Date.now() + 3600e3), z = (n) => String(n).padStart(2, "0");
  const dv = `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}T${z(d.getHours())}:00`;
  sheet(`<h2>Pickup time for run #${p.id}</h2><p class="muted small">Businesses on this run get a notification with the time, your name and your number. Times are India time.</p>
    <div class="field"><label for="at">Arrive from</label><input id="at" type="datetime-local" value="${dv}"><div class="hint">They are told to expect you within 2 hours of this time.</div></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <button class="btn block" id="s">${icon("check", 20)} Confirm time</button>`, (s, close) => {
    $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
      const at = v("at", s); if (!at) { $("#err", s).textContent = "Pick a date and time."; return; }
      try { await post(`/api/hub/runs/${p.id}/schedule`, { at: at + "+05:30" }); close(); toast("Time sent to businesses"); done(); }
      catch (x) { $("#err", s).textContent = x.message; }
    });
  });
}

route("/h/runs", { roles: HUBR, tabs: true, title: "Runs" }, async (el) => {
  let tab = "open", maps = [];
  const draw = async () => {
    maps.forEach((m) => m.remove()); maps = [];
    const rows = await api("/api/hub/runs?status=" + tab);
    el.innerHTML = `<div class="seg" id="t"><button data-k="open" class="${tab === "open" ? "on" : ""}">To do</button><button data-k="closed" class="${tab === "closed" ? "on" : ""}">Finished</button></div><div class="gap"></div>
      ${rows.length ? rows.map((p) => `<div class="card"><div class="row between"><b>Run #${p.id}</b>${statusChip(p.status)}</div>
        <p style="margin:6px 0 0"><b>${esc(p.facility)}</b> ${p.certified ? '<span class="chip ok">Certified</span>' : ""} ${ownerLine(p)}</p>
        <p class="muted small" style="margin:2px 0 0">Expected ${kg(p.expected_kg)}</p>
        ${p.status === "closed" ? `<div class="kv" style="margin-top:8px"><span>Hub / facility</span><b>${p.hub_kg} / ${p.facility_kg} kg ${p.mismatch ? '<span class="chip bad">Mismatch</span>' : ""}</b></div>
          <a class="btn secondary sm" style="margin-top:10px" href="#/verify/${p.record}">${icon("shield-check", 16)} ${p.record}</a> <a class="btn secondary sm" style="margin-top:10px" href="/api/records/${p.record}/pdf" target="_blank" rel="noopener">PDF</a>
          <button class="btn secondary sm" style="margin-top:10px" data-b="${p.id}">${icon("wallet", 16)} Merchant bills</button>`
        : `${fareHTML(p)}${scheduleLine(p)}${stopsHTML(p)}<div class="map" id="m${p.id}" style="height:200px;margin-top:10px"></div>
          ${p.status === "planned" ? `<button class="btn secondary block" style="margin-bottom:8px" data-s="${p.id}">${icon("clock", 20)} ${p.schedule && p.schedule.starts ? "Change pickup time" : p.open ? "Take this run and set time" : "Set pickup time"}</button>${p.mine ? `<button class="btn ghost block" style="margin-bottom:8px" data-d="${p.id}">Can't do this run</button>` : ""}<button class="btn block" data-c="${p.id}">${icon("truck", 20)} Mark as collected</button>`
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
    $$("[data-b]", el).forEach((b) => b.onclick = () => billsSheet(+b.dataset.b));
    $$("[data-d]", el).forEach((b) => b.onclick = async () => {
      if (await confirmSheet({ title: "Hand this run back?", body: "It goes to the next nearest collector. Any time you set is cancelled.", ok: "Hand back" }))
        busy(b, async () => { await post(`/api/hub/runs/${b.dataset.d}/decline`); toast("Handed back"); draw(); });
    });
    $$("[data-s]", el).forEach((b) => b.onclick = () => scheduleSheet(rows.find((x) => x.id === +b.dataset.s), draw));
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
  if (m && rows.length) { const pts = rows.map((f) => [f.lat, f.lng]); rows.forEach((f) => L.marker([f.lat, f.lng], { icon: pin(f.certified ? "#2F9E4F" : "#5B6B62", TIER_LETTER[f.tiers[0]] || f.tiers[0]) }).addTo(m).bindPopup(esc(f.name))); m.fitBounds(pts, { padding: [24, 24] }); }
  return () => m && m.remove();
});
function facilityList(rows) {
  return rows.length ? `<div class="list">${rows.map((f) => `<div class="li"><span class="li-ic ${f.certified ? "" : "mute"}">${icon("factory", 20)}</span>
    <div class="li-main">${esc(f.name)}<span class="sub">${esc(f.address || f.kind)} · ${num(f.capacity_kg)} kg</span><span class="sub">${[...f.tiers].map(tierChip).join(" ")}${f.certified ? ' <span class="chip ok">Certified</span>' : ""}</span></div>
    ${f.phone ? `<a class="icon-btn" href="tel:+91${esc(f.phone)}" aria-label="Call">${icon("phone", 20)}</a>` : ""}</div>`).join("")}</div>`
    : empty("No facilities yet", "A FoodLoop admin adds partner facilities. Until then, nothing can be matched.", "greens");
}

/* ---------- collector's vehicle and home base ---------- */
function vehicleSheet(done) {
  api("/api/hub/profile").then(({ profile: p }) => {
    const cities = (S.cat && S.cat.cities) || {};
    let geo = p ? [p.base_lat, p.base_lng] : null, label = p ? p.base_label : "";
    sheet(`<h2>Vehicle and start point</h2><p class="muted small">We offer you the runs closest to where your vehicle starts, and only ones it can carry.</p>
      <div class="field"><label for="vh">Vehicle</label><input id="vh" placeholder="e.g. Tata Ace" value="${esc(p ? p.vehicle : "")}"></div>
      <div class="field"><label for="cp">Can carry (kg)</label><input id="cp" type="number" inputmode="decimal" min="1" value="${p ? p.capacity_kg : ""}" placeholder="e.g. 500"></div>
      <div class="field"><label for="ct">Starts from</label><select id="ct"><option value="">Choose a city</option>${Object.keys(cities).map((c) => `<option ${c === label ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
        <div class="hint" id="bs">${geo ? "Saved: " + esc(label || "my location") : "Or use your current location."}</div></div>
      <button class="btn secondary block" id="loc" type="button">${icon("crosshair", 18)} Use my current location</button><div class="gap-s"></div>
      <div class="toggle ${!p || p.available ? "on" : ""}" id="av" role="switch"><div><b>Available for runs</b><div class="small muted">Turn off when you are not working</div></div><span class="sw"></span></div><div class="gap"></div>
      <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div><button class="btn block" id="s">Save</button>`, (s, close) => {
      wireToggle($("#av", s));
      $("#ct", s).onchange = (e) => { const c = cities[e.target.value]; if (c) { geo = c; label = e.target.value; $("#bs", s).textContent = "Saved: " + label; } };
      $("#loc", s).onclick = () => {
        if (!navigator.geolocation) return toast("Location isn't available here. Choose a city.", true);
        navigator.geolocation.getCurrentPosition((pos) => { geo = [pos.coords.latitude, pos.coords.longitude]; label = "My location"; $("#ct", s).value = ""; $("#bs", s).textContent = "Saved: my location"; },
          () => toast("Couldn't get location. Choose a city instead.", true), { timeout: 10000 });
      };
      $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
        if (!geo) { $("#err", s).textContent = "Choose where your vehicle starts from."; return; }
        try { await put("/api/hub/profile", { vehicle: v("vh", s), capacity_kg: +v("cp", s), base_lat: geo[0], base_lng: geo[1], base_label: label, available: $("#av", s).classList.contains("on") }); close(); toast("Saved"); done && done(); }
        catch (x) { $("#err", s).textContent = x.message; }
      });
    });
  }).catch((e) => toast(e.message, true));
}
ACCOUNT_EXTRA.hub = {
  html: () => `<div class="list"><button class="li" id="vp"><span class="li-ic">${icon("truck", 20)}</span><span class="li-main">Vehicle and start point<span class="sub">Decides which runs you are offered</span></span>${icon("chevron-right", 20)}</button></div>`,
  bind: (el) => { $("#vp", el).onclick = () => vehicleSheet(); },
};

/* ---------- what each merchant owes for a finished run ---------- */
async function billsSheet(pid) {
  let rows;
  try { rows = await api(`/api/hub/runs/${pid}/bills`); } catch (e) { return toast(e.message, true); }
  sheet(`<h2>Merchant bills · run #${pid}</h2><p class="muted small">What each business pays for this run. Unpaid bills have a UPI QR the merchant can scan.</p>
    ${rows.length ? rows.map((i) => `<div class="card"><div class="row between"><b>${esc(i.org)}</b><span class="chip ${i.status === "paid" ? "ok" : "warn"}">${i.status === "paid" ? "Paid" : "To pay"}</span></div>
      <div class="gap-s"></div>${billLines(i)}
      ${i.upi ? `<button class="btn secondary block" style="margin-top:10px" data-qr="${i.id}">${icon("qr-code", 18)} Show UPI QR</button><div id="q${i.id}" style="display:none;margin-top:10px">${qrBlock(i.upi, i.amount_paise)}</div>` : ""}
      ${i.phone ? `<a class="btn ghost block" style="margin-top:6px" href="tel:+91${esc(i.phone)}">${icon("phone", 18)} Call ${esc(i.org)}</a>` : ""}</div>`).join("")
      : empty("No bills for this run", "A run's bills appear once it's closed and the business has used its free pickups.", "greens")}`, (s) => {
    $$("[data-qr]", s).forEach((b) => b.onclick = () => { const q = $("#q" + b.dataset.qr, s); q.style.display = q.style.display === "none" ? "" : "none"; });
  });
}
