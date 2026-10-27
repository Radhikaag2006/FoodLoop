"use strict";
/* Onboarding, welcome, sign in, sign up, reset, pending. */

const DEMO_ACCOUNTS = [
  ["Business", "Rohit Gupta", "9000000005"], ["Collector", "Imran Khan", "9000000007"], ["FoodLoop admin", "Admin", "admin@foodloop.local"],
];

function pwField(id, label = "Password", hint = "") {
  return `<div class="field"><label for="${id}">${label}</label><div class="pw">
    <input id="${id}" type="password" autocomplete="${id === "pw" ? "current-password" : "new-password"}" placeholder="${label}">
    <button type="button" class="icon-btn" data-eye="${id}" aria-label="Show password">${icon("eye", 20)}</button></div>
    ${hint ? `<div class="hint">${hint}</div>` : ""}</div>`;
}
function wireEyes(el) {
  $$("[data-eye]", el).forEach((b) => b.onclick = () => {
    const i = $("#" + b.dataset.eye, el);
    const show = i.type === "password"; i.type = show ? "text" : "password";
    b.innerHTML = icon(show ? "eye-off" : "eye", 20);
  });
}
const v = (id, el) => ($("#" + id, el)?.value || "").trim();

/* ---------- onboarding ---------- */
const ONB = [
  { t: "Expired stock has somewhere to go.", p: "Add expired or surplus food as a lot. FoodLoop picks the right route and the best nearby facility.",
    art: [["tomato", 118, 20, 56, -10], ["carrot", 120, 150, 24, 14], ["broccoli", 124, 40, 150, 6], ["greens", 110, 170, 150, -4], ["capsicum", 80, 120, 110, 0]] },
  { t: "We plan the pickup.", p: "A collector plans a run once enough lots are waiting, weighs the load, and hands it to a certified facility.",
    art: [["onion", 100, 24, 150, -8], ["eggplant", 116, 170, 128, 10], ["pumpkin", 110, 80, 60, 0], ["chilli", 70, 200, 40, 18]] },
  { t: "Expired food never reaches a plate.", p: "FoodLoop checks expiry dates and sends expired food only to certified compost or biogas, with a record anyone can verify.",
    art: [["corn", 110, 30, 70, -10], ["tomato", 100, 180, 100, 8], ["greens", 100, 100, 150, 0]] },
];
route("/onboarding", { bare: true, guestOnly: true }, (el) => {
  let i = 0;
  const draw = () => {
    const s = ONB[i];
    el.innerHTML = `<div class="onb"><div class="art"><div class="cluster">${s.art.map(([n, z, x, y, r]) =>
      veg(n, z, `style="left:${x}px;top:${y}px;transform:rotate(${r}deg)"`)).join("")}</div></div>
      <div class="txt"><div class="dots">${ONB.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</div>
      <h1>${s.t}</h1><p class="muted">${s.p}</p></div>
      <div class="foot"><button class="btn ghost" id="skip">Skip</button><span class="grow"></span>
      <button class="btn" id="next">${i === ONB.length - 1 ? "Get started" : "Next"}</button></div></div>`;
    const fin = () => { localStorage.setItem("fl_onb", "1"); go("/welcome"); };
    $("#skip", el).onclick = fin;
    $("#next", el).onclick = () => (i === ONB.length - 1 ? fin() : (i++, draw()));
  };
  draw();
});

/* ---------- welcome ---------- */
route("/welcome", { bare: true, guestOnly: true }, (el) => {
  el.innerHTML = `<div class="auth welcome"><div class="hero">
    ${logoSVG(56)}
    <h1>Dispose of surplus food safely.</h1><p>Add your expired stock. We plan the pickup and give you a record you can show auditors.</p>
    <div class="vegrow">${veg("carrot", 96)}${veg("tomato", 118)}${veg("broccoli", 124)}${veg("capsicum", 104)}${veg("greens", 100)}</div></div>
    <div class="body"><a class="btn block" href="#/signup" style="min-height:54px">Create account</a><div class="gap-s"></div>
    <a class="btn secondary block" href="#/login" style="min-height:54px">Sign in</a><div class="gap"></div>
    <p class="center small muted">Have a FoodLoop record code? <a href="#/verify">Check a disposal record</a></p></div></div>`;
});

/* ---------- login ---------- */
route("/login", { bare: true, guestOnly: true }, (el) => {
  const demo = S.cat && S.cat.demo;
  el.innerHTML = `<div class="auth"><div class="small-top"><a class="icon-btn" href="#/welcome" aria-label="Back">${icon("chevron-left", 24)}</a></div>
    <div class="body"><h1 style="font-size:32px">Welcome back</h1><p class="muted">Sign in with your mobile number or email.</p><div class="gap"></div>
    <form id="f" novalidate><div class="field"><label for="id">Mobile number or email</label>
      <input id="id" inputmode="email" autocomplete="username" placeholder="98765 43210"></div>
    ${pwField("pw")}
    <div class="row between" style="margin:-4px 0 14px"><span></span><a class="small" href="#/forgot"><b>Forgot password?</b></a></div>
    <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:10px" role="alert"></div>
    <button class="btn block" id="go" type="submit">Sign in</button></form>
    ${demo ? `<div class="gap"></div><button class="btn secondary block" id="demo">${icon("users", 20)} Try a demo account</button>` : ""}
    <p class="center muted" style="margin-top:22px">New here? <a href="#/signup"><b>Create an account</b></a></p></div></div>`;
  wireEyes(el);
  $("#f", el).onsubmit = (e) => {
    e.preventDefault();
    $("#err", el).textContent = "";
    busy($("#go", el), async () => {
      try {
        S.user = await post("/api/auth/login", { identifier: v("id", el), password: $("#pw", el).value });
        go(S.user.status === "pending" ? "/pending" : HOME[S.user.role]);
      } catch (x) { $("#err", el).textContent = x.message; }
    });
  };
  const d = $("#demo", el);
  if (d) d.onclick = () => sheet(`<h2>Demo accounts</h2><p class="muted small">Fictional data for trying the app. Password for all: <b>Demo@1234</b></p>
    <div class="list">${DEMO_ACCOUNTS.filter(([r]) => r !== "FoodLoop admin" || S.cat.demo_admin).map(([r, n, id]) => `<button class="li" data-id="${id}"><div class="avatar">${initials(n)}</div>
      <div class="li-main">${r}<span class="sub">${n}</span></div>${icon("chevron-right", 20)}</button>`).join("")}</div>`, (s, close) => {
    $$("[data-id]", s).forEach((b) => b.onclick = () => {
      $("#id", el).value = b.dataset.id; $("#pw", el).value = "Demo@1234"; close(); $("#f", el).requestSubmit();
    });
  });
});

/* ---------- sign up ---------- */
const ROLES = [
  ["business", "I run a food business", "Distributor, manufacturer, retailer or caterer with expired or surplus stock", "store", "warn"],
  ["staff", "I have an invite code", "Pickup staff invited by FoodLoop", "key-round", "mute"],
];
route("/signup", { bare: true, guestOnly: true }, (el) => {
  el.innerHTML = `<div class="auth"><div class="small-top"><a class="icon-btn" href="#/welcome" aria-label="Back">${icon("chevron-left", 24)}</a></div>
    <div class="body"><h1 style="font-size:32px">Create your account</h1><p class="muted">How will you use FoodLoop?</p><div class="gap"></div>
    ${ROLES.map(([k, t, d, ic, c]) => `<a class="rolecard" href="#/signup/${k}"><span class="li-ic ${c}">${icon(ic, 24)}</span>
      <div class="grow"><b>${t}</b><span>${d}</span></div>${icon("chevron-right", 20)}</a>`).join("")}
    <p class="center muted" style="margin-top:18px">Already have an account? <a href="#/login"><b>Sign in</b></a></p></div></div>`;
});

const BTYPES = [["distributor", "Distributor or wholesaler"], ["manufacturer", "Manufacturer or packer"],
  ["retailer", "Retailer or supermarket"], ["caterer", "Restaurant or caterer"], ["other", "Other"]];

route("/signup/:role", { bare: true, guestOnly: true }, async (el, p) => {
  const role = p.role;
  let invite = null, geo = null;
  const cities = Object.keys((S.cat && S.cat.cities) || {});
  const cityField = () => `<div class="field"><label for="city">City</label><select id="city"><option value="">Choose your city</option>
    ${cities.map((c) => `<option>${c}</option>`).join("")}</select>
    <button type="button" class="btn ghost sm" id="loc" style="margin-top:6px;padding:0">${icon("crosshair", 16)} Use my exact location</button>
    <span class="tiny muted" id="locmsg"></span></div>`;
  const head = {
    business: ["Register your business", "We verify your details before pickups start."],
    staff: ["Join with an invite", "Enter the code your organisation sent you."],
  }[role];
  if (!head) return go("/signup", true);

  const fields = () => {
    if (role === "staff") return invite ? "" : "";
    if (role === "business") return `<div class="field"><label for="org">Business name</label><input id="org" placeholder="e.g. Fresh Foods Pvt Ltd"></div>
      <div class="field"><label for="btype">Business type</label><select id="btype">${BTYPES.map(([k, t]) => `<option value="${k}">${t}</option>`).join("")}</select></div>
      <div class="field"><label for="fssai">FSSAI licence number</label><input id="fssai" inputmode="numeric" placeholder="14 digits">
        <div class="hint">Needed to verify your business. You can add it later.</div></div>
      <div class="field"><label for="addr">Address</label><input id="addr" placeholder="Street, area"></div>${cityField()}`;
  };

  const draw = () => {
    el.innerHTML = `<div class="auth"><div class="small-top"><a class="icon-btn" href="#/signup" aria-label="Back">${icon("chevron-left", 24)}</a></div>
      <div class="body"><h1 style="font-size:30px">${head[0]}</h1><p class="muted">${head[1]}</p><div class="gap"></div>
      <form id="f" novalidate>
      ${role === "staff" && !invite ? `<div class="field"><label for="inv">Invite code</label>
        <input id="inv" placeholder="8-character code" autocapitalize="characters" style="text-transform:uppercase;letter-spacing:.12em"></div>
        <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:10px" role="alert"></div>
        <button class="btn block" id="go" type="submit">Continue</button>` : `
      ${invite ? `<div class="banner ok">${icon("badge-check", 20)}<div><b>Invite accepted</b>You're joining ${esc(invite.org)} as a collector.</div></div>` : ""}
      <div class="field"><label for="name">Your name</label><input id="name" autocomplete="name" placeholder="Full name"></div>
      <div class="field"><label for="phone">Mobile number</label><input id="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="98765 43210"></div>
      <div class="field"><label for="email">Email <span class="muted" style="font-weight:400">(optional)</span></label>
        <input id="email" type="email" autocomplete="email" placeholder="you@example.com">
        <div class="hint">Lets you reset your password by email.</div></div>
      ${fields()}
      ${pwField("npw", "Create a password", "At least 8 characters with a letter and a number.")}
      <label class="row" style="gap:10px;align-items:flex-start;margin:4px 0 14px;font-weight:500;font-size:14px"><input type="checkbox" id="agree" style="width:22px;height:22px;min-height:0;margin-top:2px">
        <span>I agree to the <a href="#/legal">Terms and Privacy notice</a>.</span></label>
      <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:10px" role="alert"></div>
      <button class="btn block" id="go" type="submit">Create account</button>`}
      </form><p class="center muted" style="margin-top:22px">Already have an account? <a href="#/login"><b>Sign in</b></a></p></div></div>`;
    wireEyes(el);
    const err = (m) => ($("#err", el).textContent = m);
    const loc = $("#loc", el);
    if (loc) loc.onclick = () => {
      if (!navigator.geolocation) return toast("Location isn't available on this device.", true);
      $("#locmsg", el).textContent = " Getting location…";
      navigator.geolocation.getCurrentPosition((pos) => {
        geo = [pos.coords.latitude, pos.coords.longitude];
        $("#locmsg", el).textContent = " Location saved.";
      }, () => { $("#locmsg", el).textContent = " Couldn't get location. Choose your city instead."; }, { timeout: 10000 });
    };
    $("#f", el).onsubmit = (e) => {
      e.preventDefault(); err("");
      busy($("#go", el), async () => {
        try {
          if (role === "staff" && !invite) {
            invite = await api("/api/auth/invite/" + encodeURIComponent(v("inv", el).toUpperCase()));
            invite.code = v("inv", el).toUpperCase();
            return draw();
          }
          if (!$("#agree", el).checked) return err("Please agree to the Terms and Privacy notice.");
          const b = { role: invite ? invite.role : role, name: v("name", el), phone: v("phone", el),
            email: v("email", el), password: $("#npw", el).value };
          if (invite) b.invite_code = invite.code;
          if (role === "business") {
            Object.assign(b, { org_name: v("org", el), address: v("addr", el), city: $("#city", el).value,
              business_type: $("#btype", el).value, fssai_no: v("fssai", el) });
            if (geo) { b.lat = geo[0]; b.lng = geo[1]; }
          }
          S.user = await post("/api/auth/signup", b);
          toast("Welcome to FoodLoop");
          go(S.user.status === "pending" ? "/pending" : HOME[S.user.role]);
        } catch (x) { err(x.message); }
      });
    };
  };
  draw();
});

/* ---------- forgot / reset ---------- */
route("/forgot", { bare: true, guestOnly: true }, (el) => {
  let ident = "", dev = "";
  const step1 = () => {
    el.innerHTML = `<div class="auth"><div class="small-top"><a class="icon-btn" href="#/login" aria-label="Back">${icon("chevron-left", 24)}</a></div>
      <div class="body"><h1 style="font-size:30px">Reset your password</h1>
      <p class="muted">Enter your mobile number or email. If you added an email, we'll send a 6-digit code. Otherwise ask the FoodLoop team for a code.</p><div class="gap"></div>
      <form id="f"><div class="field"><label for="id">Mobile number or email</label><input id="id" inputmode="email" value="${esc(ident)}"></div>
      <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:10px"></div>
      <button class="btn block" id="go" type="submit">Send code</button></form>
      <button class="btn ghost block" id="have" style="margin-top:8px">I already have a code</button></div></div>`;
    $("#have", el).onclick = () => { ident = v("id", el); step2(); };
    $("#f", el).onsubmit = (e) => { e.preventDefault(); busy($("#go", el), async () => {
      try { ident = v("id", el); const r = await post("/api/auth/forgot", { identifier: ident });
        dev = r.dev_code || ""; toast(r.message); step2(); } catch (x) { $("#err", el).textContent = x.message; } }); };
  };
  const step2 = () => {
    el.innerHTML = `<div class="auth"><div class="small-top"><button class="icon-btn" id="b" aria-label="Back">${icon("chevron-left", 24)}</button></div>
      <div class="body"><h1 style="font-size:30px">Enter your code</h1><p class="muted">Use the 6-digit code for <b>${esc(ident)}</b>, then choose a new password.</p>
      ${dev ? `<div class="banner warn"><div><b>Development mode</b>Your code is ${dev}. This is never shown in production.</div></div>` : ""}
      <form id="f"><div class="field"><label for="code">6-digit code</label><input id="code" inputmode="numeric" maxlength="6" autocomplete="one-time-code"></div>
      ${pwField("npw", "New password", "At least 8 characters with a letter and a number.")}
      <div class="err" id="err" style="color:var(--bad);font-weight:600;margin-bottom:10px"></div>
      <button class="btn block" id="go" type="submit">Set new password</button></form></div></div>`;
    wireEyes(el);
    $("#b", el).onclick = step1;
    $("#f", el).onsubmit = (e) => { e.preventDefault(); busy($("#go", el), async () => {
      try { await post("/api/auth/reset", { identifier: ident, code: v("code", el), new_password: $("#npw", el).value });
        toast("Password updated. Sign in with it."); go("/login"); } catch (x) { $("#err", el).textContent = x.message; } }); };
  };
  step1();
});

/* ---------- pending approval ---------- */
route("/pending", { bare: true }, (el) => {
  const u = S.user;
  if (!u) return go("/welcome", true);
  go(HOME[u.role] || "/welcome", true);
});
