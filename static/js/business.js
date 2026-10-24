"use strict";
const BIZ = ["business"];
const rate = (r) => r > 0 ? `pays about ₹${r}/kg` : r < 0 ? `gate fee about ₹${Math.abs(r)}/kg` : "no charge";

function pickupCard(p) {
  const done = p.status === "closed";
  return `<div class="card click" data-pk="${p.id}" tabindex="0" role="button"><div class="row"><span class="li-ic">${icon("truck", 20)}</span>
    <div class="grow"><b>${esc(p.facility)}</b><div class="muted small">Pickup #${p.id} · ${kg(p.expected_kg)} · ${fmtDay(done ? p.closed_at : p.created_at)}</div></div>
    ${statusChip(p.status)}${icon("chevron-right", 18)}</div>
    ${p.mismatch ? `<div class="gap-s"></div>${banner("warn", "Weight mismatch", "Hub and facility weights differ by more than 5%.", "scale")}` : ""}
    ${p.record ? `<div class="gap-s"></div><a class="btn secondary block" data-rec href="#/verify/${esc(p.record)}">${icon("shield-check", 18)} Record ${esc(p.record)}</a>` : ""}</div>`;
}

const CO2 = "placeholder factor, not an audited figure";
const when = (i) => i ? `${fmtDay(i)}, ${fmtTime(i)}` : "";
const kvs = (rows) => rows.filter(Boolean).map(([k, v]) => `<div class="kv"><span>${k}</span><b>${v}</b></div>`).join("");

function stepsHTML(p) {
  const rank = { planned: 0, collected: 1, closed: 2 }[p.status] ?? 0;
  const st = [["Pickup planned", when(p.created_at), "A collector has grouped your lots into a run."],
    ["Collected from you", rank >= 1 ? "Done" : "Waiting", "The collector picks the load up from your address."],
    ["Weighed and disposed", rank >= 2 ? when(p.closed_at) : "Waiting", "Weighed at the hub and the facility, then a record is issued."]];
  return `<div class="steps">${st.map(([t, d, h], i) => `<div class="step ${i < rank ? "done" : i === rank ? (rank === 2 ? "done" : "now") : ""}">
    <i></i><div><b>${t}</b><span>${esc(d)}</span><span class="tiny faint">${h}</span></div></div>`).join("")}</div>`;
}

function pickupBody(p) {
  const done = p.status === "closed";
  const lead = done ? `Disposed at ${esc(p.facility)}. ${p.certified ? "This is a certified facility." : ""}`
    : p.status === "collected" ? "Your load has been collected and is on its way to be weighed and disposed."
    : "A collector will pick this up from your address. We don't fix a time slot yet, so we'll send you a notification the moment it's collected.";
  return `<p class="muted" style="margin:0 0 10px">${lead}</p>${stepsHTML(p)}
    <div class="section" style="margin-top:14px"><h2 style="font-size:16px">Where it goes</h2></div>
    ${kvs([["Facility", esc(p.facility) + (p.certified ? ' <span class="chip ok">Certified</span>' : "")],
      p.facility_address && p.facility_address !== "Demo address" ? ["Address", esc(p.facility_address)] : null,
      p.facility_phone ? ["Phone", esc(p.facility_phone)] : null,
      p.cert_no ? ["Certificate", esc(p.cert_no)] : null])}
    <div class="section" style="margin-top:14px"><h2 style="font-size:16px">This pickup</h2></div>
    ${kvs([["Pickup number", "#" + p.id],
      p.pickup_from ? ["Collected from", esc(p.pickup_from.point || p.pickup_from.address)] : null,
      ["Your load", kg(p.your_kg)],
      ["Whole run (all stops)", `${kg(p.expected_kg)} · ${p.stops} stop${p.stops > 1 ? "s" : ""} · ${p.route_km} km`],
      done ? ["Hub scale", kg(p.hub_kg)] : null, done ? ["Facility scale", kg(p.facility_kg)] : null,
      done ? ["Weight check", p.mismatch ? '<span class="chip bad">Mismatch flagged</span>' : '<span class="chip ok">Within 5%</span>'] : null,
      done ? ["CO₂e avoided*", `about ${p.co2e_kg} kg`] : null])}
    ${p.lots.length ? `<div class="section" style="margin-top:14px"><h2 style="font-size:16px">Your lots in this run</h2></div>
      ${p.lots.map((x) => `<div class="kv"><span>${esc(x.item || "Lot")}</span><b>${tierChip(x.tier)} ${kg(x.kg)}</b></div>`).join("")}` : ""}
    ${p.record ? `<a class="btn block" data-rec style="margin-top:14px" href="#/verify/${esc(p.record)}">${icon("shield-check", 18)} View disposal record ${esc(p.record)}</a>` : ""}
    ${done ? `<p class="tiny faint" style="margin-top:10px">*CO₂e is a ${CO2}. Businesses don't earn points; the record and CO₂e avoided are your proof of disposal.</p>` : ""}`;
}

async function pickupSheet(id) {
  let p;
  try { p = await api("/api/business/pickups/" + id); } catch (e) { return toast(e.message, true); }
  sheet(`<h2>Pickup #${p.id} ${statusChip(p.status)}</h2>${pickupBody(p)}`, (s, close) => {
    $$("[data-rec]", s).forEach((a) => a.addEventListener("click", close));
  });
}

async function lotSheet(id, onRemoved) {
  let l;
  try { l = await api("/api/business/lots/" + id); } catch (e) { return toast(e.message, true); }
  const left = l.days_left == null ? "" : l.days_left < 0 ? ` (expired ${-l.days_left} day${l.days_left < -1 ? "s" : ""} ago)`
    : l.days_left === 0 ? " (expires today)" : ` (${l.days_left} day${l.days_left > 1 ? "s" : ""} left)`;
  const waiting = l.status === "waiting";
  const unverified = l.verify_status !== "verified";
  const body = waiting ? `
    ${banner(unverified ? "warn" : "info", unverified ? "Waiting for your business to be verified" : "Waiting for a pickup",
      unverified ? "Pickups are only planned once an admin has verified your business." : "A collector plans a run once enough lots are waiting for the same facility. You'll get a notification when it's planned.", "clock")}
    <div class="lbl" style="margin-top:14px">Best facilities for this lot</div>${matchList(l.matches)}
    <button class="btn tomato block" id="rm" style="margin-top:14px">${icon("trash-2", 18)} Remove this lot</button>`
    : `<div class="section"><h2 style="font-size:16px">Pickup details</h2></div>${pickupBody(l.pickup)}`;
  sheet(`<div class="row"><span class="li-ic">${itemVis(l.key, 30)}</span><div class="grow"><h2 style="margin:0">${esc(l.item)}</h2>
      <div class="row wrap" style="margin-top:4px">${tierChip(l.tier)} ${statusChip(l.status)}</div></div></div>
    <div class="gap-s"></div>
    ${kvs([["Quantity", kg(l.qty_kg)], ["Condition", COND_LABEL[l.condition] || esc(l.condition)],
      l.expiry ? ["Expiry", fmtDay(l.expiry + "T00:00:00+05:30") + left] : null,
      ["Added", when(l.at)], ["Route", esc(l.route)]])}
    <p class="muted small" style="margin:8px 0 4px">${esc(l.reason)}</p><div class="row wrap">${lockChips(l.locked)}</div>
    <div class="gap"></div>${body}`, (s, close) => {
    $$("[data-rec]", s).forEach((a) => a.addEventListener("click", close));
    const rm = $("#rm", s);
    if (rm) rm.onclick = async () => {
      if (await confirmSheet({ title: "Remove this lot?", body: "It won't be included in any pickup.", ok: "Remove", danger: true }))
        busy(rm, async () => { await del("/api/business/lots/" + l.id); close(); toast("Lot removed"); onRemoved && onRemoved(l.id); });
    };
  });
}

function wirePickups(el) {
  $$("[data-pk]", el).forEach((c) => {
    const open = () => pickupSheet(+c.dataset.pk);
    c.onclick = (e) => { if (!e.target.closest("a")) open(); };
    c.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } };
  });
}

function matchList(ms) {
  if (!ms || !ms.length) return `<p class="muted small">No eligible facility is listed for this route yet. We'll tell you when one is added.</p>`;
  return `<div class="list" style="margin:0">${ms.map((m, i) => `<div class="li"><span class="li-ic ${i ? "mute" : ""}">${icon("factory", 20)}</span>
    <div class="li-main">${esc(m.name)}${m.certified ? ' <span class="chip ok">Certified</span>' : ""}<span class="sub">${m.distance_km} km away · ${rate(m.rate_per_kg)}</span></div>
    ${i === 0 ? '<span class="chip info">Best match</span>' : ""}</div>`).join("")}</div><p class="tiny faint" style="margin:6px 2px 0">Rates are indicative and set by each facility.</p>`;
}

route("/b/home", { roles: BIZ, tabs: true, title: "Home" }, async (el) => {
  const h = await api("/api/business/home");
  setTitle(h.org);
  const vs = h.verify_status;
  el.innerHTML = `
    ${vs === "pending" ? banner("warn", "Verification in progress", h.fssai_no ? "We're checking your details. You can add lots now; pickups are planned once you're verified." : "Add your FSSAI licence number in Account so we can verify you. You can add lots meanwhile.", "clock") : ""}
    ${vs === "rejected" ? banner("bad", "Verification declined", "Please contact FoodLoop support to fix your details.", "triangle-alert") : ""}
    <div class="grid2"><div class="kpi g"><div class="n">${num(h.waiting_kg)}<small>kg</small></div><div class="l">waiting for pickup (${h.waiting_lots} lots)</div></div>
      <div class="kpi"><div class="n">${num(h.disposed_kg)}<small>kg</small></div><div class="l">safely disposed</div></div>
      <div class="kpi"><div class="n">${h.records}</div><div class="l">disposal records</div></div>
      <div class="kpi"><div class="n">${h.planned}</div><div class="l">pickups on the way</div></div></div>
    <div class="gap"></div><a class="btn lime block" href="#/b/add" style="min-height:54px">${icon("plus", 22)} Add a lot</a>
    ${Object.keys(h.by_tier).length ? `${section("Waiting by route")}<div class="card"><div class="row wrap">${Object.entries(h.by_tier).map(([t, x]) => `${tierChip(t)} <b>${x} kg</b>`).join(' &nbsp; ')}</div></div>` : ""}
    ${section("Recent pickups", `<a href="#/b/records">All records</a>`)}
    ${h.recent.length ? h.recent.map(pickupCard).join("") : empty("No pickups yet", "Add your expired or surplus stock. We'll match it to a certified facility and plan the pickup.", "capsicum")}
    <p class="tiny faint">CO₂e avoided so far: about ${h.co2e_kg} kg* (placeholder factor).</p>`;
  wirePickups(el);
});

route("/b/add", { roles: BIZ, tabs: true, title: "Add a lot" }, (el) => {
  const cat = S.cat; const items = cat.items.filter((i) => !i.fixed);
  let item = items[0].key, cond = "fresh", map, layer;
  const today = new Date().toISOString().slice(0, 10);
  el.innerHTML = `<div class="lbl">What is it?</div>${tilesHTML(items, item)}<div class="gap"></div>
    <div id="condw"><div class="lbl">Condition</div>${segHTML("cond", cat.conditions.map((c) => [c, COND_LABEL[c]]), cond)}<div class="gap"></div></div>
    <div class="grid2"><div class="field"><label for="qty">Quantity (kg)</label><input id="qty" type="number" inputmode="decimal" min="1" step="0.5" placeholder="e.g. 40"></div>
    <div class="field" id="expf"><label for="exp">Expiry date</label><input id="exp" type="date"><div class="hint" id="exph"></div></div></div>
    <div id="prev"></div><div id="mapw" style="display:none"><div class="map" id="map"></div></div>
    <button class="btn block" id="add" disabled style="min-height:54px">${icon("check", 22)} Add lot</button>`;
  const sync = () => { const it = items.find((i) => i.key === item); $("#expf", el).style.display = it.dated ? "" : "none"; };
  const preview = debounce(async () => {
    const it = items.find((i) => i.key === item), qty = +v("qty", el), exp = v("exp", el);
    const ready = qty > 0 && (!it.dated || exp);
    $("#add", el).disabled = !ready;
    if (!ready) { $("#prev", el).innerHTML = ""; $("#mapw", el).style.display = "none"; return; }
    try {
      const r = await post("/api/business/preview", { item, condition: cond, qty_kg: qty, expiry: it.dated ? exp : null });
      $("#prev", el).innerHTML = `<div class="card"><div class="row wrap">${tierChip(r.tier)} ${lockChips(r.locked)}</div>
        <p style="margin:10px 0 4px"><b>${esc(r.route)}</b></p><p class="muted small">${esc(r.reason)}</p>
        <div class="lbl" style="margin-top:14px">Best facilities for this</div>${matchList(r.matches)}</div>`;
      drawMap(r.matches);
    } catch (e) { $("#prev", el).innerHTML = `<div class="banner bad">${icon("triangle-alert", 20)}<div>${esc(e.message)}</div></div>`; }
  }, 350);
  const drawMap = (ms) => {
    const org = S.user.org; const w = $("#mapw", el);
    if (!ms.length) { w.style.display = "none"; return; }
    w.style.display = "";
    if (!map) { const home = [ms[0].lat, ms[0].lng]; map = makeMap($("#map", el), home, 10); layer = map && L.layerGroup().addTo(map); }
    if (!map) return;
    layer.clearLayers(); const pts = [];
    ms.forEach((m, i) => { L.marker([m.lat, m.lng], { icon: pin(i ? "#5B6B62" : "#2F9E4F", i + 1) }).addTo(layer).bindPopup(esc(m.name)); pts.push([m.lat, m.lng]); });
    map.invalidateSize(); map.fitBounds(pts, { padding: [30, 30], maxZoom: 13 });
  };
  wireTiles(el, (k) => { item = k; sync(); preview(); });
  wireSeg($("#cond", el), (k) => { cond = k; preview(); });
  $("#qty", el).oninput = preview; $("#exp", el).oninput = preview;
  $("#add", el).onclick = (e) => busy(e.currentTarget, async () => {
    const it = items.find((i) => i.key === item);
    const r = await post("/api/business/lots", { item, condition: cond, qty_kg: +v("qty", el), expiry: it.dated ? v("exp", el) : null });
    sheet(`<div class="center"><div class="success-burst">${icon("check", 44)}</div><h2>Lot added</h2>
      <p class="muted">${kg(r.lot.qty_kg)} of ${esc(r.lot.item)} will go to ${esc(r.route.toLowerCase())}. We'll include it in the next pickup run.</p></div>
      <div class="btn-row" style="margin-top:12px"><button class="btn secondary" id="an">Add another</button><button class="btn" id="vl">View lots</button></div>`, (s, close) => {
      $("#an", s).onclick = () => { close(); render(); }; $("#vl", s).onclick = () => { close(); go("/b/lots"); }; }, () => go("/b/lots"));
  });
  sync();
  return () => map && map.remove();
});

route("/b/lots", { roles: BIZ, tabs: true, title: "Your lots" }, async (el) => {
  let f = "all";
  const all = await api("/api/business/lots");
  const draw = () => {
    const rows = all.filter((l) => f === "all" || l.status === f);
    el.innerHTML = `<div class="seg" id="f">${[["all", "All"], ["waiting", "Waiting"], ["planned", "Planned"]].map(([k, t]) => `<button data-k="${k}" class="${k === f ? "on" : ""}">${t}</button>`).join("")}</div><div class="gap"></div>
      ${rows.length ? `<div class="list">${rows.map((l) => `<div class="li click" data-lot="${l.id}" tabindex="0" role="button"><span class="li-ic">${itemVis(l.key, 30)}</span>
        <div class="li-main">${esc(l.item)}<span class="sub">${kg(l.qty_kg)}${l.expiry ? " · expiry " + fmtDay(l.expiry + "T00:00:00+05:30") : ""}</span><span class="sub">${tierChip(l.tier)}</span></div>
        <div class="li-end">${statusChip(l.status)}${l.status === "waiting" ? `<button class="icon-btn" data-d="${l.id}" aria-label="Remove lot">${icon("trash-2", 18)}</button>` : ""}</div></div>`).join("")}</div>`
        : empty("No lots here", "Add expired or surplus stock and we'll plan the pickup.", "capsicum", `<a class="btn" href="#/b/add" style="margin-top:12px">${icon("plus", 20)} Add a lot</a>`)}`;
    wireSeg($("#f", el), (k) => { f = k; draw(); });
    $$("[data-lot]", el).forEach((r) => {
      const open = () => lotSheet(+r.dataset.lot, (gone) => { all.splice(all.findIndex((x) => x.id === gone), 1); draw(); });
      r.onclick = (e) => { if (!e.target.closest("[data-d]")) open(); };
      r.onkeydown = (e) => { if (e.target === r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); open(); } };
    });
    $$("[data-d]", el).forEach((b) => b.onclick = async (e) => {
      e.stopPropagation();
      if (await confirmSheet({ title: "Remove this lot?", body: "It won't be included in any pickup.", ok: "Remove", danger: true }))
        busy(b, async () => { await del("/api/business/lots/" + b.dataset.d); all.splice(all.findIndex((x) => x.id === +b.dataset.d), 1); draw(); });
    });
  };
  draw();
});

route("/b/records", { roles: BIZ, tabs: true, title: "Records" }, async (el) => {
  const rows = await api("/api/business/pickups");
  el.innerHTML = `<p class="muted small" style="margin-top:-2px">Each finished pickup gets a tamper-evident record with a QR code. Share it with auditors or your own customers.</p>
    <a class="btn secondary block" href="/api/business/report.csv" download>${icon("download", 18)} Export CSV report</a><div class="gap"></div>
    ${rows.length ? rows.map(pickupCard).join("") : empty("No records yet", "Records appear here after a pickup is collected, weighed and closed.", "greens")}`;
  wirePickups(el);
});

function editBiz(o, done) {
  sheet(`<h2>Business details</h2><div class="gap-s"></div>
    <div class="field"><label for="n">Business name</label><input id="n" value="${esc(o.name)}"></div>
    <div class="field"><label for="t">Type</label><select id="t">${BTYPES.map(([k, t]) => `<option value="${k}" ${k === o.business_type ? "selected" : ""}>${t}</option>`).join("")}</select></div>
    <div class="field"><label for="f">FSSAI licence number</label><input id="f" inputmode="numeric" value="${esc(o.fssai_no)}"><div class="hint">Changing this sends your business for re-verification.</div></div>
    <div class="field"><label for="a">Address</label><input id="a" value="${esc(o.address)}"></div>
    <div class="field"><label for="p">Contact mobile</label><input id="p" type="tel" value="${esc(S.user.phone)}"></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div><button class="btn block" id="s">Save</button>`, (s, close) => {
    $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
      try { await put("/api/business/profile", { name: v("n", s), business_type: $("#t", s).value, fssai_no: v("f", s), address: v("a", s), contact_phone: v("p", s) });
        close(); toast("Saved"); const d = await api("/api/auth/me"); S.user = d.user; done(); } catch (x) { $("#err", s).textContent = x.message; } }); });
}
ACCOUNT_EXTRA.business = {
  html: (u) => `<div class="list"><button class="li" id="bp"><span class="li-ic">${icon("store", 20)}</span><span class="li-main">Business details<span class="sub">${u.org.fssai_no ? "FSSAI " + esc(u.org.fssai_no) : "Add your FSSAI licence number"}</span></span>${icon("chevron-right", 20)}</button></div>`,
  bind: (el, u) => { $("#bp", el).onclick = () => editBiz(u.org, () => render()); },
};
