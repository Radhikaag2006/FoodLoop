"use strict";
/* Core runtime: helpers, API client, router, shell, sheets, toasts. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const S = { user: null, cat: null, cleanup: null };
const TIERS = { A: "Rescue", B: "Process", C: "Feed", D: "Recover", E: "Packaging" };

class ApiError extends Error {
  constructor(m, status) { super(m); this.status = status; }
}

async function api(url, opts = {}) {
  let res;
  try { res = await fetch(url, { credentials: "same-origin", ...opts }); }
  catch (e) { throw new ApiError("No connection. Check your internet and try again.", 0); }
  let data = null;
  if ((res.headers.get("content-type") || "").includes("json")) {
    data = await res.json().catch(() => null);
  }
  if (!res.ok) {
    const msg = data && typeof data.detail === "string" ? data.detail
      : "Something went wrong. Please try again.";
    if (res.status === 401 && S.user) { S.user = null; go("/welcome"); }
    throw new ApiError(msg, res.status);
  }
  return data;
}
const send = (method, url, body) => api(url, {
  method, headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body || {}) });
const post = (u, b) => send("POST", u, b);
const put = (u, b) => send("PUT", u, b);
const del = (u) => api(u, { method: "DELETE" });

/* ---------- formatting (India time) ---------- */
const TZ = "Asia/Kolkata";
const _f = (o) => new Intl.DateTimeFormat("en-IN", { timeZone: TZ, ...o });
const F_TIME = _f({ hour: "numeric", minute: "2-digit", hour12: true });
const F_DAY = _f({ day: "numeric", month: "short" });
const F_DAYL = _f({ weekday: "long", day: "numeric", month: "short" });
const F_KEY = new Intl.DateTimeFormat("en-CA", { timeZone: TZ });
const fmtTime = (i) => i ? F_TIME.format(new Date(i)).toLowerCase() : "";
const fmtDay = (i) => i ? F_DAY.format(new Date(i)) : "";
const dayKey = (i) => F_KEY.format(new Date(i));
function ago(i) {
  if (!i) return "";
  const m = Math.round((Date.now() - new Date(i)) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24 && dayKey(i) === dayKey(new Date())) return `${h} h ago`;
  const y = new Date(Date.now() - 864e5);
  if (dayKey(i) === dayKey(y)) return `Yesterday, ${fmtTime(i)}`;
  return `${fmtDay(i)}, ${fmtTime(i)}`;
}
function dayLabel(i) {
  if (dayKey(i) === dayKey(new Date())) return "Today";
  if (dayKey(i) === dayKey(new Date(Date.now() - 864e5))) return "Yesterday";
  return F_DAYL.format(new Date(i));
}
const kg = (n) => `${(+n).toLocaleString("en-IN", { maximumFractionDigits: 1 })} kg`;
const num = (n) => (+n).toLocaleString("en-IN");
function greet() {
  const h = +_f({ hour: "numeric", hour12: false }).format(new Date());
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}
const initials = (n) => (n || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

/* ---------- small UI parts ---------- */
const tierChip = (t) => t ? `<span class="chip t${t}"><b>${t}</b> ${TIERS[t]}</span>` : "";
const lockChips = (l) => (l || []).map((t) =>
  `<span class="chip lock">${icon("lock", 12)} ${TIERS[t]}</span>`).join(" ");
const STATUS = {
  accepted: ["ok", "Accepted"], rejected: ["bad", "Rejected"], voided: ["", "Cancelled"],
  pending: ["warn", "Waiting"], waiting: ["warn", "Waiting"], planned: ["info", "Pickup planned"],
  collected: ["info", "Collected"], closed: ["ok", "Done"], active: ["ok", "Active"],
  requested: ["warn", "Requested"], fulfilled: ["ok", "Handed over"], cancelled: ["", "Cancelled"],
  verified: ["ok", "Verified"], rejected_org: ["bad", "Declined"], disabled: ["", "Turned off"],
};
const statusChip = (s) => { const [c, t] = STATUS[s] || ["", s]; return `<span class="chip ${c}">${t}</span>`; };

const ITEM_VIS = {
  tomato: { veg: "tomato" }, greens: { veg: "greens" }, kitchen_waste: { veg: "carrot" },
  banana: { ic: "apple" }, bread: { ic: "wheat" }, biscuits: { ic: "cookie" }, grains: { ic: "wheat" },
  dairy: { ic: "milk" }, ready_pack: { ic: "package" }, packaging: { ic: "recycle" },
};
const itemVis = (k, s = 40) => { const v = ITEM_VIS[k] || { ic: "leaf" };
  return v.veg ? veg(v.veg, s) : icon(v.ic, Math.round(s * 0.7)); };

function empty(title, text, vegName = "greens", action = "") {
  return `<div class="empty">${veg(vegName, 84, 'class="veg"')}<h3>${esc(title)}</h3>
    <p>${esc(text)}</p>${action}</div>`;
}
const skeleton = (n = 3) => Array.from({ length: n }, (_, i) =>
  `<div class="skeleton" style="height:${i ? 74 : 150}px;margin-bottom:12px"></div>`).join("");
function banner(kind, title, text, ic = "info") {
  return `<div class="banner ${kind}">${icon(ic, 20)}<div><b>${esc(title)}</b>${esc(text)}</div></div>`;
}
function section(title, right = "") {
  return `<div class="section"><h2>${esc(title)}</h2>${right}</div>`;
}

/* ---------- toast, sheet, confirm ---------- */
let _tt;
function toast(msg, bad) {
  const t = $("#toast");
  t.textContent = msg; t.className = "show" + (bad ? " err" : "");
  clearTimeout(_tt); _tt = setTimeout(() => (t.className = ""), 3800);
}
function sheet(html, onMount, onClose) {
  const bd = document.createElement("div");
  bd.className = "backdrop";
  bd.innerHTML = `<div class="sheet" role="dialog" aria-modal="true"><div class="grab"></div>${html}</div>`;
  document.body.appendChild(bd);
  const onKey = (e) => { if (e.key === "Escape") close(); };
  const close = () => {
    if (!bd.isConnected) return;
    bd.remove(); document.removeEventListener("keydown", onKey);
    if (onClose) onClose();
  };
  bd.addEventListener("click", (e) => { if (e.target === bd) close(); });
  document.addEventListener("keydown", onKey);
  const el = $(".sheet", bd);
  if (onMount) onMount(el, close);
  return close;
}
function confirmSheet({ title, body = "", ok = "Confirm", danger = false }) {
  return new Promise((res) => {
    let yes = false;
    sheet(`<h2>${esc(title)}</h2><p class="muted">${esc(body)}</p>
      <div class="btn-row" style="margin-top:14px"><button class="btn secondary" data-n>Cancel</button>
      <button class="btn ${danger ? "tomato" : ""}" data-y>${esc(ok)}</button></div>`, (el, c) => {
      $("[data-n]", el).onclick = c;
      $("[data-y]", el).onclick = () => { yes = true; c(); };
    }, () => res(yes));
  });
}
/* run an async action on a button: spinner, disable, toast on error */
async function busy(btn, fn) {
  if (btn.disabled) return;
  const old = btn.innerHTML; btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>';
  try { return await fn(); }
  catch (e) { toast(e.message || "Something went wrong.", true); }
  finally { btn.disabled = false; btn.innerHTML = old; }
}
const copyText = async (t) => { try { await navigator.clipboard.writeText(t); toast("Copied"); }
  catch { toast("Copy this: " + t); } };
const shareText = async (text) => {
  if (navigator.share) { try { await navigator.share({ text }); return; } catch { return; } }
  copyText(text);
};

/* ---------- charts and maps ---------- */
function barChart(canvas, labels, data, color = "#2F9E4F") {
  return new Chart(canvas, { type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: color, borderRadius: 5, maxBarThickness: 18 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, grid: { color: "#E7EFE5" }, ticks: { precision: 0 } },
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } } } } });
}
function makeMap(el, center, zoom = 11) {
  if (typeof L === "undefined") return null;
  L.Icon.Default.imagePath = "/static/vendor/leaflet/images/";
  const m = L.map(el, { scrollWheelZoom: false }).setView(center, zoom);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(m);
  return m;
}
const pin = (cls, label) => L.divIcon({ className: "", iconSize: [30, 30], iconAnchor: [15, 15],
  html: `<div style="width:30px;height:30px;border-radius:50%;background:${cls};color:#fff;display:grid;place-items:center;font:800 13px DM Sans;border:2.5px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)">${label}</div>` });

/* ---------- router ---------- */
const ROUTES = [];
function route(path, opts, fn) {
  const keys = [];
  const re = new RegExp("^" + path.replace(/:(\w+)/g, (_, k) => { keys.push(k); return "([^/]+)"; }) + "$");
  ROUTES.push({ path, re, keys, opts, fn });
}
const go = (p, replace) => {
  if (replace) location.replace("#" + p); else location.hash = p;
};
const HOME = {
  business: "/b/home", hub: "/h/pool", admin: "/a/overview" };
const TABS = {
  business: [["/b/home", "Home", "home"], ["/b/lots", "Lots", "boxes"],
    ["/b/add", "Add lot", "plus", "fab"], ["/b/records", "Records", "file-text"], ["/me", "Account", "user"]],
  hub: [["/h/pool", "Pool", "layers"], ["/h/runs", "Runs", "truck"], ["/h/sites", "Sites", "factory"],
    ["/me", "Account", "user"]],
  admin: [["/a/overview", "Overview", "bar-chart-3"], ["/a/verify", "Verify", "badge-check"],
    ["/a/sites", "Sites", "factory"], ["/a/people", "People", "users"], ["/me", "Account", "user"]],
};
const ROLE_NAME = {
  business: "Business", hub: "Collector", admin: "FoodLoop admin" };

function shellHTML(def) {
  const tabs = def.tabs ? (TABS[S.user.role] || []) : [];
  const cur = location.hash.slice(1).split("?")[0];
  const unread = S.user ? S.user.unread : 0;
  const back = def.back ? `<button class="icon-btn" id="tb-back" aria-label="Back">${icon("chevron-left", 24)}</button>` : "";
  const right = def.tabs ? `<button class="icon-btn" id="tb-bell" aria-label="Notifications">${icon("bell", 22)}
      ${unread ? `<span class="dot">${unread > 9 ? "9+" : unread}</span>` : ""}</button>` : "";
  return `<div class="shell ${def.tabs ? "" : "plain"}">
    <header class="topbar">${back}<div class="tb-title" id="tb-title">${esc(def.title || "")}</div>${right}</header>
    <main class="content" id="view"></main>
    ${tabs.length ? `<nav class="tabbar" aria-label="Main">${tabs.map(([p, l, ic, fab]) => {
      const on = cur === p || (p !== "/me" && cur.startsWith(p + "/"));
      return `<a class="tab ${on ? "active" : ""} ${fab ? "fab" : ""}" href="#${p}" ${on ? 'aria-current="page"' : ""}>
        ${fab ? `<span class="fab-btn">${icon(ic, 26)}</span>` : icon(ic, 24)}<span>${l}</span></a>`;
    }).join("")}</nav>` : ""}</div>`;
}
const setTitle = (t) => { const e = $("#tb-title"); if (e) e.textContent = t; };

async function render() {
  if (S.cleanup) { try { S.cleanup(); } catch (e) { /* ignore */ } S.cleanup = null; }
  const hash = location.hash.slice(1) || "/";
  const [path, qs] = hash.split("?");
  let r, params = {};
  for (const x of ROUTES) {
    const m = x.re.exec(path);
    if (m) { r = x; x.keys.forEach((k, i) => (params[k] = decodeURIComponent(m[i + 1]))); break; }
  }
  const u = S.user;
  if (!r) return go(u ? (u.status === "pending" ? "/pending" : HOME[u.role]) : "/welcome", true);
  const o = r.opts;
  if (o.roles) {
    if (!u) return go("/welcome", true);
    if (u.status === "pending") return go("/pending", true);
    if (!o.roles.includes(u.role)) return go(HOME[u.role], true);
  }
  if (o.guestOnly && u) return go(u.status === "pending" ? "/pending" : HOME[u.role], true);
  window.scrollTo(0, 0);
  params.q = new URLSearchParams(qs || "");
  const app = $("#app");
  if (o.bare) { app.innerHTML = `<div id="view"></div>`; }
  else { app.innerHTML = shellHTML(o); }
  const view = $("#view");
  const bk = $("#tb-back");
  if (bk) bk.onclick = () => (typeof o.back === "string" ? go(o.back) : history.length > 1 ? history.back() : go(HOME[u?.role] || "/"));
  const bell = $("#tb-bell");
  if (bell) bell.onclick = () => go("/notifications");
  if (!o.bare) view.innerHTML = skeleton();
  try {
    const cleanup = await r.fn(view, params);
    if (typeof cleanup === "function") S.cleanup = cleanup;
  } catch (e) {
    if (e.status === 401) return;
    view.innerHTML = `<div class="empty">${veg("tomato", 84, 'class="veg"')}<h3>Couldn't load this</h3>
      <p>${esc(e.message)}</p><button class="btn secondary" id="retry">Try again</button></div>`;
    const rt = $("#retry"); if (rt) rt.onclick = render;
  }
  if (u && !o.bare) refreshMe();
}
let _me = 0;
async function refreshMe() {
  const t = ++_me;
  try {
    const d = await api("/api/auth/me");
    if (t !== _me || !d.user) return;
    const had = S.user ? S.user.unread : 0;
    S.user = d.user;
    const bell = $("#tb-bell");
    if (bell && d.user.unread !== had) {
      $(".dot", bell)?.remove();
      if (d.user.unread) bell.insertAdjacentHTML("beforeend",
        `<span class="dot">${d.user.unread > 9 ? "9+" : d.user.unread}</span>`);
    }
  } catch { /* offline */ }
}
window.addEventListener("hashchange", render);
/* refresh read-only dashboards when the app comes back to the foreground */
const LIVE = /^#\/(b\/home|b\/lots|h\/pool|h\/runs|notifications)$/;
let _hid = 0;
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { _hid = Date.now(); return; }
  if (_hid && Date.now() - _hid > 20000 && S.user && LIVE.test(location.hash) && !document.querySelector(".sheet")) render();
});

/* debounce */
const debounce = (fn, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
