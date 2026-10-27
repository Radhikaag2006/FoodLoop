"use strict";
const ADM = ["admin"];

route("/a/overview", { roles: ADM, tabs: true, title: "Overview" }, async (el) => {
  const o = await api("/api/admin/overview");
  const u = o.users;
  el.innerHTML = `${o.pending_orgs ? `<a class="banner warn" href="#/a/verify" style="text-decoration:none">${icon("badge-check", 20)}<div><b>${o.pending_orgs} organisation${o.pending_orgs > 1 ? "s" : ""} to verify</b>Review now</div></a>` : ""}
    <div class="grid2"><div class="kpi g"><div class="n">${num(o.kg)}<small>kg</small></div><div class="l">collected so far</div></div>
      <div class="kpi"><div class="n">${o.orgs}</div><div class="l">organisations</div></div>
      <div class="kpi"><div class="n">${o.pickups_open}</div><div class="l">runs in progress</div></div>
      <div class="kpi"><div class="n">${o.records}</div><div class="l">disposal records</div></div></div>
    ${o.mismatches ? `<div class="gap"></div>${banner("warn", `${o.mismatches} run${o.mismatches > 1 ? "s" : ""} with a weight mismatch`, "Worth a look before the next audit.", "scale")}` : ""}
    ${section("People")}<div class="list">${Object.entries({ business: "Businesses", hub: "Collectors", admin: "Admins" })
      .map(([k, t]) => `<div class="li"><span class="li-main">${t}</span><b>${u[k] || 0}</b></div>`).join("")}</div>
    ${section("Revenue")}<div class="list"><a class="li" href="#/a/billing"><span class="li-ic">${icon("wallet", 20)}</span><span class="li-main">Revenue and plans<span class="sub">Invoices, payments and price list</span></span>${icon("chevron-right", 20)}</a></div>
    ${section("Dispatch")}<div id="dp"></div>
    ${section("Collector invites")}<button class="btn block" id="inv">${icon("key-round", 20)} Create collector invite</button><div class="gap"></div><div id="il"></div>`;
  const il = async () => { const r = await api("/api/admin/invites");
    $("#il", el).innerHTML = r.length ? `<div class="list">${r.map((i) => `<div class="li"><span class="li-ic warn">${icon("key-round", 20)}</span><div class="li-main"><span class="num" style="letter-spacing:.1em">${esc(i.code)}</span><span class="sub">${esc(i.note || "Collector")} · expires ${fmtDay(i.expires)}</span></div>
      <button class="icon-btn" data-sh="${esc(i.code)}" aria-label="Share">${icon("share-2", 20)}</button></div>`).join("")}</div>` : "";
    $$("[data-sh]", el).forEach((b) => b.onclick = () => shareText(`Your FoodLoop collector invite code is ${b.dataset.sh}. Open ${location.origin} and choose "I have an invite code".`)); };
  il();
  const drawDispatch = async () => {
    const d = await api("/api/admin/dispatch"), c = d.compare;
    $("#dp", el).innerHTML = `<p class="small muted" style="margin:0 0 8px">Mode: <b>${esc(d.mode)}</b>${d.pending ? ` · ${d.pending} run${d.pending > 1 ? "s" : ""} waiting for the next batch` : ""}
      ${c.runs ? `<br>Shadow check over ${c.runs} run${c.runs > 1 ? "s" : ""}: rules ${c.rules_km} km, solver ${c.solver_km} km` : ""}</p>
      ${d.mode === "solver" ? `<button class="btn secondary block" id="dr">${icon("route", 18)} Give out waiting runs now</button><div class="gap-s"></div>` : ""}
      ${d.runs.length ? `<div class="list">${d.runs.slice(0, 8).map((r) => `<div class="li"><div class="li-main">Run #${r.run} · ${r.pending ? "waiting" : esc(r.driver || "open to all")}${r.km != null ? ` · ${r.km} km` : ""}<span class="sub">Why: ${esc(r.why || "n/a")}</span></div></div>`).join("")}</div>` : '<p class="small muted">No runs given out yet.</p>'}`;
    const b = $("#dr", el);
    if (b) b.onclick = () => busy(b, async () => { await post("/api/admin/dispatch/run"); toast("Runs given out"); drawDispatch(); });
  };
  drawDispatch().catch(() => {});
  $("#inv", el).onclick = () => sheet(`<h2>Collector invite</h2><div class="field"><label for="nt">Note</label><input id="nt" placeholder="e.g. Imran, Noida hub"></div><button class="btn block" id="mk">Create code</button>`, (s, close) => {
    $("#mk", s).onclick = (e) => busy(e.currentTarget, async () => { const r = await post("/api/admin/invites", { note: v("nt", s) }); close();
      sheet(`<h2>Invite code</h2><p class="muted small">Works for 7 days, once.</p><div class="codebox">${r.code}</div>`); il(); }); });
});

route("/a/verify", { roles: ADM, tabs: true, title: "Verify" }, async (el) => {
  let st = "pending";
  const draw = async () => {
    const rows = await api("/api/admin/orgs?status=" + st);
    el.innerHTML = `<div class="seg" id="t">${[["pending", "To verify"], ["verified", "Verified"], ["rejected", "Declined"]].map(([k, t]) => `<button data-k="${k}" class="${k === st ? "on" : ""}">${t}</button>`).join("")}</div><div class="gap"></div>
      ${rows.length ? rows.map((o) => `<div class="card"><div class="row between"><h3>${esc(o.name)}</h3>${statusChip(o.status === "rejected" ? "rejected_org" : o.status)}</div>
        <div class="muted small" style="margin:4px 0 8px">${esc(o.business_type || "Business")} · ${esc(o.city)}</div>
        <div class="kv"><span>Owner</span><b>${esc(o.owner)}</b></div><div class="kv"><span>Mobile</span><b>${o.phone ? `<a href="tel:+91${esc(o.phone)}">+91 ${esc(o.phone)}</a>` : "-"}</b></div>
        <div class="kv"><span>Address</span><b style="text-align:right">${esc(o.address)}</b></div>
        ${o.kind === "business" ? `<div class="kv"><span>FSSAI licence</span><b>${o.fssai_no ? esc(o.fssai_no) : '<span class="chip warn">Not given</span>'}</b></div>` : ""}
        ${o.status !== "verified" ? `<div class="btn-row" style="margin-top:12px">${o.status === "pending" ? `<button class="btn danger" data-a="reject" data-o="${o.id}">Decline</button>` : ""}<button class="btn" data-a="verify" data-o="${o.id}">Verify</button></div>`
          : `<button class="btn danger block" style="margin-top:12px" data-a="reject" data-o="${o.id}">Withdraw verification</button>`}</div>`).join("")
        : empty("Nothing here", st === "pending" ? "New societies and businesses appear here when they sign up." : "No organisations in this list.", "greens")}
      <p class="tiny faint">Check licence numbers against the official FSSAI records before you verify a business.</p>`;
    wireSeg($("#t", el), (k) => { st = k; draw(); });
    $$("[data-a]", el).forEach((b) => b.onclick = async () => {
      if (b.dataset.a === "reject" && !await confirmSheet({ title: "Decline this organisation?", body: "They'll be told and won't get pickups.", ok: "Decline", danger: true })) return;
      busy(b, async () => { await post(`/api/admin/orgs/${b.dataset.o}/${b.dataset.a}`); toast(b.dataset.a === "verify" ? "Verified" : "Declined"); draw(); }); });
  };
  await draw();
});

route("/a/sites", { roles: ADM, tabs: true, title: "Facilities" }, async (el) => {
  const draw = async () => {
    const rows = await api("/api/admin/facilities");
    el.innerHTML = `<button class="btn block" id="add">${icon("plus", 20)} Add facility</button><div class="gap"></div>
      ${rows.length ? `<div class="list">${rows.map((f) => `<button class="li" data-f="${f.id}"><span class="li-ic ${f.certified ? "" : "mute"}">${icon("factory", 20)}</span>
        <span class="li-main">${esc(f.name)}${f.active ? "" : ' <span class="chip">Hidden</span>'}<span class="sub">${[...f.tiers].map(tierChip).join(" ")} ${f.certified ? `<span class="chip ok">${esc(f.cert_no || "Certified")}</span>` : ""}</span></span>${icon("chevron-right", 20)}</button>`).join("")}</div>`
        : empty("No facilities yet", "Add the compost units, biogas plants, processors and feed makers you partner with. Matching only works with these.", "greens")}`;
    $("#add", el).onclick = () => facForm(null, draw);
    $$("[data-f]", el).forEach((b) => b.onclick = () => facForm(rows.find((x) => x.id === +b.dataset.f), draw));
  };
  await draw();
});
function facForm(f, done) {
  const cities = (S.cat && S.cat.cities) || {};
  sheet(`<h2>${f ? "Edit facility" : "Add facility"}</h2><div class="gap-s"></div>
    <div class="field"><label for="n">Name</label><input id="n" value="${esc(f?.name || "")}"></div>
    <div class="grid2"><div class="field"><label for="k">Type</label><select id="k">${["processor", "feed", "compost", "biogas", "recycler"].map((k) => `<option ${f?.kind === k ? "selected" : ""}>${k}</option>`).join("")}</select></div>
    <div class="field"><label for="cap">Capacity (kg)</label><input id="cap" type="number" value="${f?.capacity_kg ?? ""}"></div></div>
    <div class="field"><label>Takes these routes</label><div class="row wrap" id="tr">${Object.entries(TIERS).map(([k, t]) => `<label class="chip t${k}" style="cursor:pointer;padding:8px 12px"><input type="checkbox" value="${k}" ${f?.tiers.includes(k) ? "checked" : ""} style="width:16px;height:16px;min-height:0;margin-right:4px"> ${TIER_LETTER[k]} ${t}</label>`).join("")}</div></div>
    <div class="toggle ${f?.certified ? "on" : ""}" id="cert" role="switch"><div><b>Has a valid certificate</b><div class="small muted">Required for Recover (C) and Packaging (D)</div></div><span class="sw"></span></div><div class="gap"></div>
    <div class="field"><label for="cn">Certificate number</label><input id="cn" value="${esc(f?.cert_no || "")}"></div>
    <div class="grid2"><div class="field"><label for="la">Latitude</label><input id="la" type="number" step="any" value="${f?.lat ?? ""}"></div><div class="field"><label for="lo">Longitude</label><input id="lo" type="number" step="any" value="${f?.lng ?? ""}"></div></div>
    <div class="field"><label for="ad">Address</label><input id="ad" value="${esc(f?.address || "")}"></div>
    <div class="grid2"><div class="field"><label for="ph">Phone</label><input id="ph" type="tel" value="${esc(f?.phone || "")}"></div>
    <div class="field"><label for="rt">₹ per kg</label><input id="rt" type="number" step="0.1" value="${f?.rate_per_kg ?? 0}"><div class="hint">+ they pay you, − gate fee</div></div></div>
    ${f ? `<div class="field"><label>Certificate document</label><div class="small muted" id="docst">${f.has_document ? 'A document is on file. <a href="/api/facilities/' + f.id + '/document" target="_blank" rel="noopener">View</a>' : "No document uploaded yet."}</div>
      <input id="docf" type="file" accept="application/pdf,image/png,image/jpeg" style="margin-top:8px">
      <div class="btn-row" style="margin-top:8px"><button type="button" class="btn secondary" id="docup">Upload</button>${f.has_document ? '<button type="button" class="btn ghost" id="docrm">Remove</button>' : ""}</div>
      <div class="hint">PDF, PNG or JPEG, up to 5 MB. Businesses can open it from their pickup.</div></div>`
      : `<p class="small muted">Save the facility first, then you can upload its certificate.</p>`}
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <button class="btn block" id="s">Save</button>${f ? `<div class="gap-s"></div><button class="btn ghost block" id="tg">${f.active ? "Hide from matching" : "Show in matching"}</button>` : ""}`, (s, close) => {
    wireToggle($("#cert", s));
    $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
      const b = { name: v("n", s), kind: $("#k", s).value, capacity_kg: +v("cap", s), tiers: $$("#tr input:checked", s).map((i) => i.value).join(""),
        certified: $("#cert", s).classList.contains("on"), cert_no: v("cn", s), lat: +v("la", s), lng: +v("lo", s), address: v("ad", s), phone: v("ph", s), rate_per_kg: +v("rt", s) };
      try { f ? await put("/api/admin/facilities/" + f.id, b) : await post("/api/admin/facilities", b); close(); toast("Saved"); done(); } catch (x) { $("#err", s).textContent = x.message; } });
    const up = $("#docup", s); if (up) up.onclick = () => busy(up, async () => {
      const file = $("#docf", s).files[0]; if (!file) { $("#err", s).textContent = "Choose a file first."; return; }
      const fd = new FormData(); fd.append("file", file);
      try { await api(`/api/facilities/${f.id}/document`, { method: "POST", body: fd }); close(); toast("Certificate uploaded"); done(); }
      catch (x) { $("#err", s).textContent = x.message; } });
    const rm = $("#docrm", s); if (rm) rm.onclick = () => busy(rm, async () => { await del(`/api/facilities/${f.id}/document`); close(); toast("Removed"); done(); });
    const tg = $("#tg", s); if (tg) tg.onclick = () => busy(tg, async () => { await post(`/api/admin/facilities/${f.id}/toggle`); close(); done(); });
  });
}

route("/a/people", { roles: ADM, tabs: true, title: "People" }, async (el) => {
  el.innerHTML = `<div class="input-icon">${icon("search", 20)}<input id="q" placeholder="Search name, mobile or email"></div><div class="gap"></div><div id="rows"></div>`;
  const load = debounce(async () => {
    const rows = await api("/api/admin/users?q=" + encodeURIComponent(v("q", el)));
    $("#rows", el).innerHTML = rows.length ? `<div class="list">${rows.map((r) => `<button class="li" data-u="${r.id}"><div class="avatar">${initials(r.name)}</div>
      <span class="li-main">${esc(r.name)}<span class="sub">${ROLE_NAME[r.role]}${r.org ? " · " + esc(r.org) : ""}</span></span>${statusChip(r.status)}</button>`).join("")}</div>` : empty("No one found", "Try a different name or number.", "tomato");
    $$("[data-u]", el).forEach((b) => b.onclick = () => { const r = rows.find((x) => x.id === +b.dataset.u);
      sheet(`<h2>${esc(r.name)}</h2><p class="muted small">${ROLE_NAME[r.role]}${r.org ? " · " + esc(r.org) : ""}<br>${r.phone ? "+91 " + esc(r.phone) : ""} ${esc(r.email || "")}</p>
        ${r.role === "admin" ? "" : `<div class="list"><button class="li" id="rc"><span class="li-ic info">${icon("key-round", 20)}</span><span class="li-main">Give a password reset code</span></button>
        <button class="li" id="tg"><span class="li-ic bad">${icon("ban", 20)}</span><span class="li-main">${r.status === "disabled" ? "Turn account on" : "Turn account off"}</span></button></div>`}`, (s, close) => {
        const rc = $("#rc", s); if (rc) rc.onclick = async () => { const c = await post(`/api/admin/users/${r.id}/reset-code`); close(); sheet(`<h2>Reset code</h2><p class="muted small">Give this to ${esc(r.name)}. It works for ${c.minutes} minutes.</p><div class="codebox">${c.code}</div>`); };
        const tg = $("#tg", s); if (tg) tg.onclick = async () => { await post(`/api/admin/users/${r.id}/${r.status === "disabled" ? "enable" : "disable"}`); close(); load(); }; }); });
  });
  $("#q", el).oninput = load; load();
});
