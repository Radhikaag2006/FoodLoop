"use strict";
/* Language switch (English / Hindi).

   The screens are written in English. When Hindi is on, every piece of text
   that appears on the page is looked up in the Hindi dictionary (i18n-hi.js)
   and swapped, including text added later (toasts, sheets, lists). Anything
   not in the dictionary stays in English, so nothing breaks. Switching
   language swaps the text where it is: the screen is not redrawn, so
   nothing you typed or chose is lost. */
const I18N = { hi: {}, hiRe: [] };    // filled by i18n-hi.js
const LANGS = { en: "English", hi: "हिंदी" };

let LANG = (() => {
  try { const s = localStorage.getItem("fl-lang"); if (s in LANGS) return s; } catch { /* private mode */ }
  return /^hi\b/i.test(navigator.language || "") ? "hi" : "en";
})();
document.documentElement.lang = LANG;

const _squash = (s) => s.replace(/\s+/g, " ").trim();

/* English -> Hindi for one trimmed string, or null when there is no match */
function trCore(core) {
  const d = I18N.hi;
  if (Object.prototype.hasOwnProperty.call(d, core)) return d[core];
  for (const [re, rep] of I18N.hiRe) if (re.test(core)) return core.replace(re, rep);
  if (core.includes(" · ")) {                       // "Noida plant · 40 kg"
    let hit = false;
    const parts = core.split(" · ").map((p) => { const t = trCore(p); if (t !== null) hit = true; return t === null ? p : t; });
    if (hit) return parts.join(" · ");
  }
  return null;
}
/* keeps the spaces around the text as they were */
function trText(raw) {
  const core = _squash(raw);
  if (!core || !/[A-Za-z]/.test(core)) return null;
  const out = trCore(core);
  if (out === null) return null;
  return (/^\s/.test(raw) ? " " : "") + out + (/\s$/.test(raw) ? " " : "");
}
/* for text built in code (share messages, etc.) */
function tr(s) { if (LANG !== "hi") return s; const t = trText(String(s)); return t === null ? s : t; }

const _ATTRS = ["placeholder", "aria-label", "title", "alt"];
const _SKIP = "[data-notr],script,style,textarea,.leaflet-container";

/* What each node said in English, and what we turned it into. Switching
   language swaps text in place (no redraw), so a half-finished form or
   sign-up step is never lost. */
const _EN = new WeakMap(), _HI = new WeakMap();      // text nodes
const _EN_A = new WeakMap(), _HI_A = new WeakMap();  // attributes: el -> {attr: text}

function _trTextNode(n) {
  const v = n.nodeValue;
  if (_HI.get(n) === v) return;                      // already ours
  const t = trText(v);
  if (t !== null && t !== v) { _EN.set(n, v); _HI.set(n, t); n.nodeValue = t; }
  else { _EN.delete(n); _HI.delete(n); }
}
function _trAttrs(el) {
  for (const a of _ATTRS) {
    const v = el.getAttribute && el.getAttribute(a);
    if (!v) continue;
    const mine = _HI_A.get(el);
    if (mine && mine[a] === v) continue;
    const t = trText(v);
    if (t !== null && t !== v) {
      if (!_EN_A.has(el)) { _EN_A.set(el, {}); _HI_A.set(el, {}); }
      _EN_A.get(el)[a] = v; _HI_A.get(el)[a] = t; el.setAttribute(a, t);
    }
  }
}
function trTree(root) {
  if (LANG !== "hi" || !root) return;
  if (root.nodeType === 3) { if (!root.parentElement || !root.parentElement.closest(_SKIP)) _trTextNode(root); return; }
  if (root.nodeType !== 1 || root.closest(_SKIP)) return;
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (!n.parentElement.closest(_SKIP)) _trTextNode(n);
  }
  _trAttrs(root);
  root.querySelectorAll("[placeholder],[aria-label],[title],[alt]").forEach((e) => { if (!e.closest(_SKIP)) _trAttrs(e); });
}
/* back to English: put every text we changed back, but only where the app
   has not written something new since */
function untrTree(root) {
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (_HI.has(n) && n.nodeValue === _HI.get(n)) n.nodeValue = _EN.get(n);
    _HI.delete(n); _EN.delete(n);
  }
  root.querySelectorAll("[placeholder],[aria-label],[title],[alt]").forEach((e) => {
    const en = _EN_A.get(e), hi = _HI_A.get(e);
    if (en) for (const a in en) if (e.getAttribute(a) === hi[a]) e.setAttribute(a, en[a]);
    _EN_A.delete(e); _HI_A.delete(e);
  });
}

const _obs = new MutationObserver((ms) => {
  if (LANG !== "hi") return;
  for (const m of ms) {
    if (m.type === "childList") m.addedNodes.forEach(trTree);
    else if (m.type === "characterData") trTree(m.target);
    else if (m.type === "attributes" && !m.target.closest(_SKIP)) _trAttrs(m.target);
  }
});
_obs.observe(document.body, { childList: true, subtree: true, characterData: true,
  attributes: true, attributeFilter: _ATTRS });

/* ---------- the switch itself ---------- */
function langBtn(cls = "") {
  const other = LANG === "hi" ? "en" : "hi";
  return `<button class="lang-btn ${cls}" data-lang-toggle data-notr type="button" lang="${other}"
    aria-label="${other === "hi" ? "हिंदी में बदलें" : "Switch to English"}">${LANGS[other]}</button>`;
}
function setLang(l) {
  if (!(l in LANGS) || l === LANG) return;
  LANG = l;
  try { localStorage.setItem("fl-lang", l); } catch { /* private mode */ }
  document.documentElement.lang = l;
  if (l === "hi") trTree(document.body); else untrTree(document.body);
  document.querySelectorAll("[data-lang-toggle]").forEach((b) => {   // the button itself
    const other = l === "hi" ? "en" : "hi";
    b.textContent = LANGS[other]; b.lang = other;
    b.setAttribute("aria-label", other === "hi" ? "हिंदी में बदलें" : "Switch to English");
  });
}
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-lang-toggle]")) setLang(LANG === "hi" ? "en" : "hi");
});
