"use strict";
/* Shared screens: account, notifications, verify, legal. */

let _installEvt = null;
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); _installEvt = e; });
const ACCOUNT_EXTRA = {};   // role -> { html(u), bind(el, u) }

route("/me", { roles: ["business", "hub", "admin"], tabs: true, title: "Account" }, (el) => {
  const u = S.user;
  const x = ACCOUNT_EXTRA[u.role];
  el.innerHTML = `<div class="card"><div class="row"><div class="avatar">${initials(u.name)}</div>
    <div class="grow"><h3>${esc(u.name)}</h3><div class="muted small">${esc(u.phone ? "+91 " + u.phone : u.email)}</div></div></div>
    <div class="row wrap" style="margin-top:12px"><span class="chip ok">${ROLE_NAME[u.role]}</span>
      ${u.org ? `<span class="chip">${esc(u.org.name)}</span>` : ""}
      ${u.org && u.org.verify_status && u.role === "business" ? statusChip(u.org.verify_status === "rejected" ? "rejected_org" : u.org.verify_status) : ""}</div></div>
    ${x ? x.html(u) : ""}
    <div class="list">
      <button class="li" id="edit"><span class="li-ic">${icon("pencil", 20)}</span><span class="li-main">Edit profile</span>${icon("chevron-right", 20)}</button>
      <button class="li" id="pw"><span class="li-ic">${icon("key-round", 20)}</span><span class="li-main">Change password</span>${icon("chevron-right", 20)}</button>
      <button class="li" id="notes"><span class="li-ic info">${icon("bell", 20)}</span><span class="li-main">Notifications</span>${u.unread ? `<span class="chip bad">${u.unread} new</span>` : ""}${icon("chevron-right", 20)}</button>
      <a class="li" href="#/compliance"><span class="li-ic ok">${icon("shield-check", 20)}</span><span class="li-main"><b>Compliance Personal Assistant</b> <span class="chip ok sm" style="font-size:10px;padding:2px 6px">AI / RAG</span></span>${icon("chevron-right", 20)}</a>
      <button class="li" id="inst" style="display:none"><span class="li-ic">${icon("smartphone", 20)}</span><span class="li-main">Install FoodLoop on this device</span>${icon("chevron-right", 20)}</button>
      <a class="li" href="#/verify"><span class="li-ic mute">${icon("shield-check", 20)}</span><span class="li-main">Check a disposal record</span>${icon("chevron-right", 20)}</a>
      <a class="li" href="#/legal"><span class="li-ic mute">${icon("file-text", 20)}</span><span class="li-main">Terms and privacy</span>${icon("chevron-right", 20)}</a>
    </div>
    <div class="list"><button class="li" id="out"><span class="li-ic mute">${icon("log-out", 20)}</span><span class="li-main">Sign out</span></button>
      ${u.role !== "admin" ? `<button class="li" id="del"><span class="li-ic bad">${icon("trash-2", 20)}</span><span class="li-main" style="color:var(--bad)">Delete my account</span></button>` : ""}</div>
    <p class="center tiny faint">FoodLoop 1.0</p>`;
  if (x && x.bind) x.bind(el, u);
  if (_installEvt) { const b = $("#inst", el); b.style.display = ""; b.onclick = async () => { _installEvt.prompt(); _installEvt = null; b.remove(); }; }
  $("#notes", el).onclick = () => go("/notifications");
  $("#out", el).onclick = async () => { await post("/api/auth/logout"); S.user = null; go("/welcome"); };
  $("#edit", el).onclick = () => sheet(`<h2>Edit profile</h2><div class="gap-s"></div>
    <div class="field"><label for="n">Name</label><input id="n" value="${esc(u.name)}"></div>
    <div class="field"><label for="p">Mobile number</label><input id="p" type="tel" value="${esc(u.phone)}"></div>
    <div class="field"><label for="e">Email</label><input id="e" type="email" value="${esc(u.email)}"></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <button class="btn block" id="s">Save</button>`, (s, close) => {
    $("#s", s).onclick = (ev) => busy(ev.currentTarget, async () => {
      try { S.user = await put("/api/auth/profile", { name: v("n", s), phone: v("p", s), email: v("e", s) });
        close(); toast("Profile saved"); render(); } catch (x2) { $("#err", s).textContent = x2.message; }
    });
  });
  $("#pw", el).onclick = () => sheet(`<h2>Change password</h2><p class="muted small">You'll stay signed in here. Other devices are signed out.</p>
    <div class="gap-s"></div>${pwField("opw", "Current password")}${pwField("npw", "New password", "At least 8 characters with a letter and a number.")}
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <button class="btn block" id="s">Update password</button>`, (s, close) => {
    wireEyes(s);
    $("#s", s).onclick = (ev) => busy(ev.currentTarget, async () => {
      try { await post("/api/auth/password", { old_password: $("#opw", s).value, new_password: $("#npw", s).value });
        close(); toast("Password updated"); } catch (x2) { $("#err", s).textContent = x2.message; }
    });
  });
  const dl = $("#del", el);
  if (dl) dl.onclick = () => sheet(`<h2>Delete your account?</h2><p class="muted">This signs you out everywhere and removes your name, phone and email.
    Your lots and disposal records stay, without your personal details. This can't be undone.</p>${pwField("dpw", "Your password")}
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <div class="btn-row"><button class="btn secondary" id="c">Keep account</button><button class="btn tomato" id="s">Delete</button></div>`, (s, close) => {
    wireEyes(s); $("#c", s).onclick = close;
    $("#s", s).onclick = (ev) => busy(ev.currentTarget, async () => {
      try { await post("/api/auth/delete", { password: $("#dpw", s).value }); close(); S.user = null; toast("Account deleted"); go("/welcome"); }
      catch (x2) { $("#err", s).textContent = x2.message; }
    });
  });
});

/* ---------- notifications ---------- */
const NOTE_IC = { points: ["gift", ""], warn: ["triangle-alert", "warn"], approval: ["user-check", "info"], record: ["file-text", ""], info: ["bell", "info"] };
route("/notifications", { roles: ["business", "hub", "admin"], title: "Notifications", back: true }, async (el) => {
  const rows = await api("/api/auth/notifications");
  el.innerHTML = rows.length ? `<div class="list">${rows.map((n) => { const [ic, c] = NOTE_IC[n.kind] || NOTE_IC.info;
    return `<div class="li" style="${n.read ? "" : "background:#F3FAF1"}"><span class="li-ic ${c}">${icon(ic, 20)}</span>
      <div class="li-main">${esc(n.title)}<span class="sub">${esc(n.body)}</span></div><span class="tiny faint">${ago(n.at)}</span></div>`; }).join("")}</div>`
    : empty("You're all caught up", "Updates about your lots, pickups and records will show up here.", "greens");
  if (S.user.unread) { post("/api/auth/notifications/read").then(() => { S.user.unread = 0; }); }
});

/* ---------- verify (public) ---------- */
function verifyView(el, code) {
  el.innerHTML = `<div class="card"><p class="muted small">Enter the code printed on a FoodLoop disposal record, or scan its QR code.
    Every record is linked to the one before it, so changing any record breaks the check.</p>
    <div class="row"><input id="vc" placeholder="FL-2026-00001" value="${esc(code || "")}" autocapitalize="characters" style="flex:1">
    <button class="btn" id="vg">Check</button></div></div><div id="vout"></div>
    <p class="tiny muted">This confirms the record hasn't been changed after it was issued. It isn't an official FSSAI or pollution board certificate.</p>`;
  const run = async () => {
    const c = v("vc", el).toUpperCase(); if (!c) return;
    history.replaceState(null, "", "#/verify/" + encodeURIComponent(c));
    try {
      const r = await api("/api/records/" + encodeURIComponent(c));
      $("#vout", el).innerHTML = `<div class="card" style="border-color:${r.valid ? "#9bd3a8" : "#f0a99c"}">
        <div class="center"><div class="success-burst ${r.valid ? "" : "bad"}">${icon(r.valid ? "badge-check" : "triangle-alert", 40)}</div>
        <h2>${r.valid ? "Record is intact" : "Record doesn't match"}</h2><p class="muted small">${esc(r.code)}</p></div>
        <div class="kv"><span>Hash check</span><b>${r.hash_ok ? "Matches" : "Does not match"}</b></div>
        <div class="kv"><span>Link to previous record</span><b>${r.chain_ok ? "Intact" : "Broken"}</b></div>
        <div class="kv"><span>Facility</span><b>${esc(r.facility.name)}${r.facility.certified ? " " + '<span class="chip ok">Certified</span>' : ""}</b></div>
        <div class="kv"><span>Closed</span><b>${fmtDay(r.closed_at + "Z")}, ${fmtTime(r.closed_at + "Z")}</b></div>
        <div class="kv"><span>Weights (expected / hub / facility)</span><b>${r.expected_kg} / ${r.hub_kg} / ${r.facility_kg} kg</b></div>
        <div class="kv"><span>Weight check</span><b>${r.mismatch ? '<span class="chip bad">Mismatch flagged</span>' : '<span class="chip ok">Within 5%</span>'}</b></div>
        <div class="section" style="margin-top:14px"><h2 style="font-size:16px">Collected from</h2></div>
        ${r.lines.map((l) => `<div class="kv"><span>${esc(l.source)}</span><b>${tierChip(l.tier)} ${l.kg} kg</b></div>`).join("")}
        <a class="btn secondary block" style="margin-top:14px" href="/api/records/${encodeURIComponent(r.code)}/pdf" target="_blank" rel="noopener">${icon("download", 18)} Open PDF</a></div>`;
    } catch (e) {
      $("#vout", el).innerHTML = `<div class="card"><div class="empty" style="padding:10px">${veg("tomato", 72, 'class="veg"')}<h3>No record found</h3><p>${esc(e.message)} Check the code and try again.</p></div></div>`;
    }
  };
  $("#vg", el).onclick = run;
  $("#vc", el).onkeydown = (e) => { if (e.key === "Enter") run(); };
  if (code) run();
}
route("/verify", { title: "Check a record", back: "/", }, (el) => verifyView(el, ""));
route("/verify/:code", { title: "Check a record", back: "/" }, (el, p) => verifyView(el, p.code));

/* ---------- legal (draft) ---------- */
route("/legal", { title: "Terms and privacy", back: true }, (el) => {
  el.innerHTML = `<div class="banner warn">${icon("triangle-alert", 20)}<div><b>Draft text</b>Have a lawyer review and replace this before you open the app to the public.</div></div>
    <div class="card"><h3>What we collect</h3><p class="muted">Your name, mobile number, optional email, your business details (name, address, location, FSSAI number), and the lots you enter (item, weight, expiry).</p>
    <h3>Why</h3><p class="muted">To plan pickups, match your lots to facilities and issue disposal records. We don't sell your data.</p>
    <h3>Who can see it</h3><p class="muted">Collectors see pickup totals and stops. FoodLoop admins can see accounts to verify businesses and keep the service safe. Disposal records show organisation names.</p>
    <h3>Your choices</h3><p class="muted">You can edit your details or delete your account from Account. Deleting removes your name, phone and email. Past disposal records stay, without your personal details.</p></div>`;
});

/* ---------- shared pickers ---------- */
const COND_LABEL = { fresh: "Fresh", overripe: "Overripe", bruised: "Bruised", spoiled: "Spoiled" };
function tilesHTML(items, sel) {
  return `<div class="tiles" role="radiogroup">${items.map((i) => `<button type="button" class="tile ${i.key === sel ? "on" : ""}"
    data-k="${i.key}" role="radio" aria-checked="${i.key === sel}"><span class="ti">${itemVis(i.key, 64)}</span>${esc(i.label)}</button>`).join("")}</div>`;
}
function segHTML(id, opts, sel) {
  return `<div class="seg" id="${id}">${opts.map(([k, t]) => `<button type="button" data-k="${k}" class="${k === sel ? "on" : ""}">${t}</button>`).join("")}</div>`;
}
function wireSeg(root, cb) {
  $$("button", root).forEach((b) => b.onclick = () => {
    $$("button", root).forEach((x) => x.classList.toggle("on", x === b)); cb && cb(b.dataset.k);
  });
}
function wireTiles(root, cb) {
  $$(".tile", root).forEach((b) => b.onclick = () => {
    $$(".tile", root).forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-checked", x === b); }); cb(b.dataset.k);
  });
}
function toggleHTML(id, label, sub = "") {
  return `<div class="toggle" id="${id}" role="switch" aria-checked="false" tabindex="0"><div><b>${label}</b>${sub ? `<div class="small muted">${sub}</div>` : ""}</div><span class="sw"></span></div>`;
}
function wireToggle(t, cb) {
  const flip = () => { const on = t.classList.toggle("on"); t.setAttribute("aria-checked", on); cb && cb(on); };
  t.onclick = flip; t.onkeydown = (e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); } };
}
function classifyCard(r) {
  return `<div class="card"><div class="row wrap">${tierChip(r.tier)} ${lockChips(r.locked)}</div>
    <p style="margin:10px 0 4px"><b>${esc(r.route)}</b></p><p class="muted small" style="margin:0">${esc(r.reason)}</p></div>`;
}
