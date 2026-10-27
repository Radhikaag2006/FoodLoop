"use strict";
/* Plans, payment method, bills and payment (Razorpay test mode or the built-in simulator).
   Pay per ride: pick how you pay once, then pay the bill right after each pickup. */
const inr = (paise) => "₹" + (paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const inrR = (rupees) => inr(Math.round(rupees * 100));

const METHODS = [
  ["upi", "UPI", "smartphone", "Pay with any UPI app. Usually the quickest."],
  ["card", "Debit or credit card", "wallet", "Enter your card when you pay."],
  ["netbanking", "Net banking", "building-2", "Pay from your bank's website."],
];
const methodOf = (p) => METHODS.find((m) => m[0] === (p && p.method));
const methodText = (p) => !p ? "" : p.method === "upi" ? (p.vpa ? "UPI · " + p.vpa : "UPI") : p.method === "card" ? "Card" : "Net banking";
const dot = (on) => `<span style="width:22px;height:22px;border-radius:50%;border:2px solid ${on ? "var(--leaf)" : "var(--line-2)"};display:grid;place-items:center;flex:none">${on ? '<i style="width:10px;height:10px;border-radius:50%;background:var(--leaf)"></i>' : ""}</span>`;

function loadRzp() {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((ok, no) => {
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = ok; s.onerror = () => no(new Error("Couldn't load the payment window."));
    document.head.appendChild(s);
  });
}

/* The itemised bill. */
function billLines(i) {
  const rows = (i.lines && i.lines.length ? i.lines : [{ label: i.description, amount_paise: i.amount_paise }])
    .map((l) => `<div class="kv"><span>${esc(l.label)}</span><b>${inr(l.amount_paise)}</b></div>`).join("");
  return `<div>${rows}<div class="kv" style="border-top:1px solid var(--line);margin-top:6px;padding-top:8px;font-size:18px"><span><b>Total</b></span><b>${inr(i.amount_paise)}</b></div></div>`;
}

/* The QR itself: shown to the merchant, and to the collector in their bills view. */
function qrBlock(u, paise) {
  return `<div class="center"><div style="display:inline-block;background:#fff;padding:10px;border-radius:16px;border:1px solid var(--line)">
      <img alt="UPI QR code for ${inr(paise)}" src="${u.qr}" width="220" height="220"></div>
    <div style="font-size:30px;font-weight:800;margin:8px 0 0">${inr(paise)}</div>
    <div class="muted small">to ${esc(u.name)} · ${esc(u.vpa)}</div></div>
    ${u.demo ? '<div class="gap-s"></div>' + banner("warn", "Demo QR", "This points to a demo UPI ID, so scanning it moves no money. Set UPI_VPA in .env to use your own.", "triangle-alert") : ""}`;
}

/* Pay a ride bill by UPI QR. Resolves true once they say they've paid. */
async function payByUpi(inv) {
  let r;
  try { r = await api(`/api/billing/invoices/${inv.id}/upi`); }
  catch (e) { if (e.status === 503) return payByGateway(inv); throw e; }
  return new Promise((res) => {
    let outcome = false;
    sheet(`<h2>Pay ${inr(r.amount_paise)} by UPI</h2>
      <p class="muted small">Scan with any UPI app (PhonePe, Google Pay, Paytm, BHIM). The amount is already filled in.</p>
      ${qrBlock(r.upi, r.amount_paise)}
      <a class="btn secondary block" href="${esc(r.upi.uri)}" style="margin-top:12px">${icon("smartphone", 18)} Open my UPI app</a>
      <div class="field" style="margin-top:12px"><label for="utr">UPI reference (optional)</label><input id="utr" inputmode="numeric" autocomplete="off" placeholder="12-digit number from your app"><div class="hint">It helps us match your payment faster.</div></div>
      <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
      <button class="btn block" id="done" style="min-height:54px">I've paid ${inr(r.amount_paise)}</button>
      <button class="btn ghost block" id="other" style="margin-top:6px">Pay another way</button>
      <p class="tiny faint center" style="margin:6px 0 0">Only tap this after your UPI app shows success. We check every UPI payment against the bank.</p>`, (s, close) => {
      $("#other", s).onclick = () => { outcome = "other"; close(); };
      $("#done", s).onclick = (e) => busy(e.currentTarget, async () => {
        try { await post(`/api/billing/invoices/${inv.id}/upi-paid`, { ref: v("utr", s) }); outcome = true; close(); }
        catch (x) { $("#err", s).textContent = x.message; }
      });
    }, () => (outcome === "other" ? payByGateway(inv).then(res) : res(outcome)));
  });
}

/* Ride bills paid by UPI show a QR; everything else opens the payment window. */
function payInvoice(inv, pref) {
  return inv.kind === "ride" && pref && pref.method === "upi" ? payByUpi(inv) : payByGateway(inv);
}

/* Payment window (Razorpay, or the built-in test gateway). Resolves true when the server confirms payment. */
async function payByGateway(inv) {
  const o = await post(`/api/billing/invoices/${inv.id}/order`);
  if (o.mode === "razorpay") {
    await loadRzp();
    return new Promise((res) => {
      const rz = new Razorpay({
        key: o.key_id, amount: o.amount_paise, currency: o.currency, name: o.name,
        description: o.description, order_id: o.order_id, prefill: o.prefill, theme: { color: "#0F3D2E" },
        handler: async (r) => {
          try { await post(`/api/billing/invoices/${inv.id}/verify`, r); res(true); }
          catch (e) { toast(e.message, true); res(false); }
        },
        modal: { ondismiss: () => res(false) },
      });
      rz.on("payment.failed", (r) => toast((r.error && r.error.description) || "Payment failed.", true));
      rz.open();
    });
  }
  return new Promise((res) => {   // built-in simulator
    let paid = false;
    const m = methodOf({ method: o.method });
    sheet(`<h2>Test payment</h2><p class="muted small">Simulated gateway: no real money moves.</p>
      <div class="kv"><span>${esc(o.description)}</span><b>${inr(o.amount_paise)}</b></div>
      ${m ? `<div class="kv"><span>Paying with</span><b>${esc(methodText({ method: o.method, vpa: o.vpa }))}</b></div>` : ""}<div class="gap"></div>
      <button class="btn block" id="sp" style="min-height:54px">Pay ${inr(o.amount_paise)} (test)</button>
      <div class="gap-s"></div><button class="btn ghost block" id="sc">Cancel</button>`, (s, close) => {
      $("#sc", s).onclick = close;
      $("#sp", s).onclick = (e) => busy(e.currentTarget, async () => {
        await post(`/api/billing/invoices/${inv.id}/simulate-pay`); paid = true; close();
      });
    }, () => res(paid));
  });
}

/* "Pickup done, pay the fare", shown like the end of a ride. */
function payNowSheet(inv, pref, after) {
  sheet(`<div class="center"><div class="success-burst">${icon("truck", 40)}</div><h2>Pickup #${inv.pickup_id} is done</h2>
      <p class="muted">Your waste was collected and taken to the plant. Pay the fare to finish.</p></div>
    ${billLines(inv)}<div class="gap-s"></div>
    ${pref ? `<div class="row small muted" style="margin:6px 0 12px">${icon(methodOf(pref)[2], 18)} Paying with ${esc(methodText(pref))}</div>` : ""}
    <button class="btn block" id="pay" style="min-height:54px">Pay ${inr(inv.amount_paise)}</button>
    <button class="btn ghost block" id="later" style="margin-top:6px">Pay later</button>
    <p class="tiny faint center" style="margin:6px 0 0">You can't add new lots until this is paid.</p>`, (s, close) => {
    $("#later", s).onclick = close;
    $("#pay", s).onclick = (e) => busy(e.currentTarget, async () => {
      if (await payInvoice(inv, pref)) { close(); toast("Paid. Thank you!"); after && after(); }
    });
  });
}
/* Ask once per bill per visit, so it never nags. */
function duePrompt(b, after) {
  const inv = b.dues && b.dues[0]; if (!inv) return;
  try { if (sessionStorage.getItem("fl_due_" + inv.id)) return; sessionStorage.setItem("fl_due_" + inv.id, "1"); } catch (e) { /* storage blocked: ask anyway */ }
  payNowSheet(inv, b.pay_pref, after);
}

function billingBanner(b) {
  if (b.due_paise) return `<a class="banner bad" href="#/b/billing" style="text-decoration:none">${icon("triangle-alert", 20)}<div><b>${inr(b.due_paise)} to pay</b>Pay for your last pickup to keep adding lots.</div></a>`;
  if (b.plan) return "";
  if (b.trial.total === 0) return `<a class="banner warn" href="#/b/billing" style="text-decoration:none">${icon("wallet", 20)}<div><b>Choose how to pay</b>Pick a plan to start adding lots.</div></a>`;
  if (b.trial.left > 0) return `<a class="banner info" href="#/b/billing" style="text-decoration:none">${icon("ticket", 20)}<div><b>Free trial: ${b.trial.left} of ${b.trial.total} pickups left</b>See how you'll pay after that.</div></a>`;
  return `<a class="banner warn" href="#/b/billing" style="text-decoration:none">${icon("wallet", 20)}<div><b>Your free trial is over</b>Choose how to pay to keep adding lots.</div></a>`;
}

/* Choose UPI / card / net banking. Saved once; used to open the payment window. */
function methodSheet(cur, done) {
  let m = (cur && cur.method) || "upi";
  sheet(`<h2>How will you pay?</h2><p class="muted small">After each pickup you'll get the fare and pay right away. We never store your card details.</p>
    <div class="list" id="ml"></div><div class="gap-s"></div>
    <div class="field" id="vf"><label for="vpa">UPI ID (optional)</label><input id="vpa" placeholder="name@bank" autocapitalize="off" autocomplete="off" value="${esc((cur && cur.vpa) || "")}"><div class="hint">Saves typing it each time. You can change it when you pay.</div></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div>
    <button class="btn block" id="s" style="min-height:52px">Save and continue</button>`, (s, close) => {
    const drawList = () => {
      $("#ml", s).innerHTML = METHODS.map(([k, t, ic, d]) => `<button type="button" class="li" data-m="${k}"><span class="li-ic">${icon(ic, 20)}</span>
        <span class="li-main">${t}<span class="sub">${d}</span></span>${dot(k === m)}</button>`).join("");
      $("#vf", s).style.display = m === "upi" ? "" : "none";
      $$("[data-m]", s).forEach((b) => b.onclick = () => { m = b.dataset.m; drawList(); });
    };
    drawList();
    $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
      try { await put("/api/billing/method", { method: m, vpa: m === "upi" ? v("vpa", s) : "" }); close(); done && await done(); }
      catch (x) { $("#err", s).textContent = x.message; }
    });
  });
}

function receiptSheet(i, pref, after) {
  sheet(`<h2>${i.status === "paid" ? "Receipt" : "Bill"}</h2><p class="muted small">${esc(i.description)} · ${fmtDay(i.at)}</p>
    ${billLines(i)}<div class="gap-s"></div>
    ${i.status === "paid" ? `<div class="kv"><span>Status</span><b><span class="chip ok">Paid</span></b></div>${i.payment_id ? `<div class="kv"><span>Payment ID</span><b class="small">${esc(i.payment_id)}</b></div>` : ""}`
      : `<button class="btn block" id="pn" style="min-height:52px">Pay ${inr(i.amount_paise)}</button>`}`, (s, close) => {
    const pn = $("#pn", s);
    if (pn) pn.onclick = () => busy(pn, async () => { if (await payInvoice(i, pref)) { close(); toast("Paid. Thank you!"); after && after(); } });
  });
}

route("/b/billing", { roles: BIZ, tabs: false, back: "/me", title: "Plan and billing" }, async (el) => {
  const draw = async () => {
    const [b, inv] = await Promise.all([api("/api/billing/status"), api("/api/billing/invoices")]);
    const g = b.gateway, plan = b.plan, ride = plan && plan.kind === "ride", month = plan && plan.kind === "month";
    const rideP = b.plans.find((p) => p.kind === "ride"), months = b.plans.filter((p) => p.kind === "month");
    const pm = methodOf(b.pay_pref);
    const status = month ? `<div class="card"><div class="row between"><div><div class="tiny faint">Your plan</div><h3>${esc(plan.name)}</h3></div><span class="chip ok">Active</span></div>
        <p class="muted small" style="margin:6px 0 8px">Runs until ${fmtDay(plan.ends)}. ${plan.kg_used} of ${plan.quota_kg} kg used.</p>
        <div style="height:8px;border-radius:99px;background:var(--line)"><div style="height:8px;border-radius:99px;background:var(--leaf);width:${Math.min(100, Math.round(100 * plan.kg_used / plan.quota_kg))}%"></div></div></div>`
      : ride ? `<div class="card"><div class="row between"><div><div class="tiny faint">Your plan</div><h3>Pay per ride</h3></div><span class="chip ok">On</span></div>
        ${pm ? `<div class="row" style="margin-top:8px"><span class="li-ic">${icon(pm[2], 20)}</span><div class="grow"><div class="tiny faint">Paying with</div><b>${esc(methodText(b.pay_pref))}</b></div><button class="btn secondary sm" id="chg">Change</button></div>` : ""}</div>`
      : b.trial.total === 0 ? banner("info", "Choose how you'd like to pay", "Pick pay per ride or a monthly plan below to start adding lots.", "wallet")
      : b.trial.left > 0 ? `<div class="card"><div class="row between"><div><div class="tiny faint">Free trial</div><h3>${b.trial.left} of ${b.trial.total} pickups left</h3></div><span class="chip ok">Free</span></div>
        <p class="muted small" style="margin:6px 0 0">Your first ${b.trial.total} pickups cost nothing. Pick how you'll pay after that, below.</p></div>`
      : banner("warn", "Your free trial is over", "Choose how you'd like to pay to keep adding lots.", "wallet");
    const dues = b.dues.map((i) => `<div class="card" style="border-color:var(--bad)"><div class="row between"><h3>Pickup #${i.pickup_id} · to pay</h3><span class="chip bad">Due</span></div>
      <div class="gap-s"></div>${billLines(i)}<button class="btn block" style="margin-top:12px;min-height:52px" data-pay="${i.id}">Pay ${inr(i.amount_paise)}</button></div>`).join("");
    const rv = rideP ? Object.values(rideP.rates) : [0];
    const perKg = inrR(Math.max(...rv));
    const rateTxt = Math.min(...rv) === Math.max(...rv) ? `${perKg} per kg, any waste type` : `${inrR(Math.min(...rv))} to ${perKg} per kg by waste type`;
    const col = ({ name, price, per, sub, feats, current, badge, btn }) => `<div class="plan${current ? " on" : ""}">
      <div class="row between"><h3>${esc(name)}</h3>${current ? '<span class="chip ok">Current plan</span>' : badge ? `<span class="chip info">${badge}</span>` : ""}</div>
      <div class="plan-price"><b>${price}</b><span>${per}</span></div><div class="muted small">${sub}</div>
      <ul class="plan-feats">${feats.map((t) => `<li>${icon("check", 16)}<span>${t}</span></li>`).join("")}</ul>
      <div class="plan-cta">${btn}</div></div>`;
    const cols = [];
    if (rideP) cols.push(col({ name: "Pay per ride", price: inrR(rideP.base), per: "per pickup", sub: "+ " + rateTxt, current: ride,
      feats: ["Pay after each pickup", "Billed on the weight confirmed at the hub", "No monthly fee", "Pay by UPI, card or net banking"],
      btn: `<button class="btn ${ride ? "secondary " : ""}block" id="ride">${ride ? "Change payment" : "Use pay per ride"}</button>` }));
    months.forEach((p, i) => {
      const cur = plan && plan.code === p.code, nm = p.name.split(",")[0];
      cols.push(col({ name: nm, price: inrR(p.base), per: "/ month", sub: `${p.quota_kg} kg included`, current: cur, badge: i === months.length - 1 && months.length > 1 ? "Best value" : "",
        feats: [`${p.quota_kg} kg of waste every month`, "No pickup fee", `Extra kg at ${perKg} per kg`, `Valid for 30 days`],
        btn: cur ? '<button class="btn secondary block" disabled>Your current plan</button>'
          : `<button class="btn block" data-plan="${esc(p.code)}">${b.pending_plan && b.pending_plan.plan === p.code ? "Pay " + inr(b.pending_plan.amount_paise) : "Choose " + esc(nm)}</button>` }));
    });
    el.innerHTML = `
      ${g.mode === "off" ? banner("warn", "Payments aren't switched on", "Plans can't be bought right now.", "triangle-alert") : ""}
      ${g.mode !== "off" && g.test ? banner("info", "Test mode", g.mode === "mock" ? "Payments are simulated. No real money moves." : "No real money moves. Test card 4111 1111 1111 1111 (any future date and CVV) or UPI success@razorpay.", "shield-check") + '<div class="gap"></div>' : ""}
      ${status}${dues ? `<div class="gap"></div>${dues}` : ""}
      ${section("Plans")}<div class="plans">${cols.join("")}</div>
      ${section("Receipts")}
      ${inv.length ? `<div class="list">${inv.map((i) => `<button class="li" data-r="${i.id}"><span class="li-main">${esc(i.description)}<span class="sub">${fmtDay(i.at)}</span></span>
        <div class="li-end">${inr(i.amount_paise)}<span class="sub">${i.status === "paid" ? "Paid" : "Due"}</span></div>${icon("chevron-right", 18)}</button>`).join("")}</div>`
        : empty("No bills yet", "Your bills show up here after your free pickups are used.", "greens")}`;
    const after = () => draw();
    $$("[data-pay]", el).forEach((x) => x.onclick = () => busy(x, async () => {
      if (await payInvoice(b.dues.find((d) => d.id === +x.dataset.pay), b.pay_pref)) { toast("Paid. Thank you!"); await draw(); }
    }));
    $$("[data-r]", el).forEach((x) => x.onclick = () => receiptSheet(inv.find((i) => i.id === +x.dataset.r), b.pay_pref, after));
    const chg = $("#chg", el); if (chg) chg.onclick = () => methodSheet(b.pay_pref, after);
    const rb = $("#ride", el);
    if (rb) rb.onclick = () => methodSheet(b.pay_pref, async () => {
      if (!ride) { await post("/api/billing/plans/ride/select"); toast("Pay per ride is on. You'll pay after each pickup."); }
      await draw();
    });
    $$("[data-plan]", el).forEach((x) => x.onclick = () => busy(x, async () => {
      const r = await post(`/api/billing/plans/${x.dataset.plan}/select`);
      if (r.invoice && await payInvoice(r.invoice)) toast("Plan activated");
      await draw();
    }));
  };
  await draw();
});

/* ---------- admin: revenue and price list ---------- */
route("/a/billing", { roles: ADM, tabs: false, back: "/a/overview", title: "Revenue and plans" }, async (el) => {
  const draw = async () => {
    const s = await api("/api/billing/admin/summary");
    el.innerHTML = `<div class="grid2"><div class="kpi g"><div class="n">${inrR(s.paid)}</div><div class="l">received (${s.paid_count} payments)</div></div>
      <div class="kpi"><div class="n">${inrR(s.due)}</div><div class="l">unpaid (${s.due_count})</div></div>
      <div class="kpi"><div class="n">${s.active_monthly}</div><div class="l">active monthly plans</div></div>
      <div class="kpi"><div class="n">${inrR(s.driver_cost)}</div><div class="l">driver fares (${s.driver_runs} closed runs)</div></div></div>
      ${s.upi_pending.length ? `${section("UPI payments to check")}<p class="small muted" style="margin:-4px 0 8px">Merchants say they paid these by QR. Match each to your bank statement.</p>
        ${s.upi_pending.map((x) => `<div class="card"><div class="row between"><b>${esc(x.org)}</b><b>${inr(x.amount_paise)}</b></div>
          <div class="muted small">${esc(x.description)}${x.ref ? " · UTR " + esc(x.ref) : " · no UTR given"}</div>
          <div class="btn-row" style="margin-top:10px"><button class="btn danger sm" data-no="${x.invoice_id}">Not received</button><button class="btn sm" data-ok="${x.invoice_id}">Received</button></div></div>`).join("")}` : ""}
      ${section("Price list")}<div class="list">${s.plans.map((p) => `<button class="li" data-p="${esc(p.code)}"><span class="li-main">${esc(p.name)}${p.active ? "" : ' <span class="chip">Off</span>'}
        <span class="sub">${inrR(p.base)}${p.kind === "month" ? ` / month · ${p.quota_kg} kg` : " per pickup + per kg"}</span></span>${icon("chevron-right", 20)}</button>`).join("")}</div>
      ${section("Recent invoices")}${s.recent.length ? `<div class="list">${s.recent.map((i) => `<div class="li"><span class="li-main">${esc(i.org)}<span class="sub">${esc(i.description)}</span></span>
        <div class="li-end"><b>${inr(i.amount_paise)}</b> <span class="chip ${i.status === "paid" ? "ok" : ""}">${esc(i.status)}</span></div></div>`).join("")}</div>`
        : empty("No invoices yet", "They start once businesses finish their free trial.", "greens")}`;
    $$("[data-ok],[data-no]", el).forEach((b) => b.onclick = () => busy(b, async () => {
      const id = b.dataset.ok || b.dataset.no;
      await post(`/api/billing/admin/upi/${id}/${b.dataset.ok ? "verify" : "reject"}`);
      toast(b.dataset.ok ? "Marked received" : "Sent back to the merchant as unpaid"); draw();
    }));
    $$("[data-p]", el).forEach((b) => b.onclick = () => planForm(s.plans.find((p) => p.code === b.dataset.p), draw));
  };
  await draw();
});

function planForm(p, done) {
  const ride = p.kind === "ride";
  sheet(`<h2>${esc(p.name)}</h2><div class="gap-s"></div>
    <div class="field"><label for="n">Name</label><input id="n" value="${esc(p.name)}"></div>
    <div class="field"><label for="b">${ride ? "Base fee per pickup" : "Price per month"} (₹)</label><input id="b" type="number" step="0.01" value="${p.base}"></div>
    ${ride ? `<div class="lbl">₹ per kg by route</div><div class="grid2">${Object.entries(p.rates).map(([t, r]) => `<div class="field"><label for="r${t}">${TIER_LETTER[t] || t} ${esc(TIERS[t] || "")}</label><input id="r${t}" type="number" step="0.01" value="${r}"></div>`).join("")}</div>`
      : `<div class="field"><label for="q">Included kg per month</label><input id="q" type="number" value="${p.quota_kg}"></div>`}
    <div class="toggle ${p.active ? "on" : ""}" id="on" role="switch"><div><b>Available to businesses</b></div><span class="sw"></span></div><div class="gap"></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:8px"></div><button class="btn block" id="s">Save</button>`, (s, close) => {
    wireToggle($("#on", s));
    $("#s", s).onclick = (e) => busy(e.currentTarget, async () => {
      const rates = {}; if (ride) Object.keys(p.rates).forEach((t) => { rates[t] = Math.round(+v("r" + t, s) * 100); });
      try {
        await put("/api/billing/admin/plans/" + p.code, { name: v("n", s), base_paise: Math.round(+v("b", s) * 100),
          quota_kg: ride ? 0 : +v("q", s), rates, active: $("#on", s).classList.contains("on") });
        close(); toast("Saved"); done();
      } catch (x) { $("#err", s).textContent = x.message; }
    });
  });
}
