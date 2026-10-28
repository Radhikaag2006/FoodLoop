"use strict";
/* Chat helper for business owners: a floating button that opens a chat.
   App how-to questions are answered here; food-safety and legal questions
   go to the compliance assistant (/api/compliance/ask). */

let _logoN = 0;
function chatLogo(size = 56) {
  const id = "cg" + (++_logoN);
  return `<svg class="chat-logo" width="${size}" height="${size}" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
    <defs><linearGradient id="${id}" x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#46C46B"/><stop offset="1" stop-color="#0F3D2E"/></linearGradient></defs>
    <circle cx="32" cy="32" r="32" fill="url(#${id})"/>
    <path d="M24 15h16a9 9 0 0 1 9 9v9a9 9 0 0 1-9 9H31.5l-8.6 7.2a.8.8 0 0 1-1.3-.7L22 42.8A9 9 0 0 1 15 34v-10a9 9 0 0 1 9-9z" fill="#fff"/>
    <path d="M32 36V28" stroke="#2F9E4F" stroke-width="2.2" stroke-linecap="round" fill="none"/>
    <path d="M32 29.5c-5.6.2-8-3.2-8.2-7 4.6-.3 8.2 1.7 8.2 7z" fill="#2F9E4F"/>
    <path d="M32 31.5c5.2.2 8.2-3 8.4-6.6-4.6-.3-8.4 1.6-8.4 6.6z" fill="#7AD08F"/>
    <path d="M51 7l1.4 3.6L56 12l-3.6 1.4L51 17l-1.4-3.6L46 12l3.6-1.4z" fill="#FFD166"/></svg>`;
}

/* ---------- what the helper can answer without a server ---------- */
const CHAT_FAQ = [
  { k: ["add", "adding", "create", "upload", "new lot", "लॉट जोड़", "जोड़ना"],
    a: "To add expired or surplus food, tap the green + Add lot button. Choose what it is, its condition, the weight and the expiry date. FoodLoop then picks the right route and the best nearby certified plant.",
    go: ["/b/add", "Add a lot"] },
  { k: ["pickup*", "collector*", "schedul*", "come", "पिकअप", "कब"],
    a: "A collector plans a run once enough lots are waiting for the same plant. You get a notification with the pickup time and the collector's name and number. You can also see it under Lots.",
    go: ["/b/lots", "See my lots"] },
  { k: ["track*", "qr", "journey", "my order", "where is my lot", "where is my waste", "ट्रैक"],
    a: "Every lot has a Tracking ID and QR code. Open the lot and tap Track this order to see where it is, from pickup to the plant.",
    go: ["/track", "Track an order"] },
  { k: ["pay*", "bill*", "invoice*", "upi", "fare", "price", "cost", "charge*", "plan*", "भुगतान", "बिल"],
    a: "Your first pickups are free. After that you can pay per pickup, right after it is done, or choose a monthly plan. You can pay by UPI, card or net banking.",
    go: ["/b/billing", "Plan and billing"] },
  { k: ["record*", "certificate*", "proof", "audit*", "pdf", "receipt*", "रिकॉर्ड"],
    a: "After a pickup is weighed and closed, you get a tamper-evident disposal record with a QR code and a PDF. Share it with auditors or customers. Find it under Records.",
    go: ["/b/records", "Open Records"] },
  { k: ["verif*", "approv*", "licence", "license", "pending"],
    a: "An admin checks your business before pickups start. Add your FSSAI licence number in Account to speed this up. You can add lots while you wait.",
    go: ["/me", "Open Account"] },
  { k: ["accept*", "allowed", "fresh", "which food", "what food", "kinds of", "route*"],
    a: "FoodLoop only takes food that is already waste: expired, spoiled or damaged food, plus empty packaging. Fresh food that is still in date is not accepted. Expired and spoiled food goes only to certified compost or biogas plants." },
  { k: ["weight*", "mismatch*", "differ*", "वज़न"],
    a: "Your load is weighed at the hub and again at the plant. If the two weights differ by more than 5%, the record shows a mismatch flag." },
  { k: ["remove", "delete", "cancel", "wrong", "mistake", "edit"],
    a: "Open Lots, tap the lot and choose Remove this lot. This works only while the lot is not in a pickup. To fix a weight or date, remove the lot and add it again.",
    go: ["/b/lots", "See my lots"] },
  { k: ["hindi", "english", "language*", "हिंदी"],
    a: "Tap the हिंदी / English button at the top of the screen to change the language at any time." },
];
const CHAT_LAW = ["cattle", "feed ban", "swill", "penalt", "section 59", "holding", "regulation", "law", "legal", "fssai rule", "fbo", "statut", "cooked food", "compost rule", "नियम", "क़ानून", "कानून"];
const CHAT_CHIPS = ["How do I add a lot?", "When will my pickup come?", "How do I pay?", "Can expired food go to cattle feed?"];
const CHAT_HELLO = "Hi! I'm the FoodLoop assistant. Ask me about adding lots, pickups, tracking, payments or food-safety rules.";
const CHAT_SORRY = "Sorry, I couldn't reach the assistant right now. Check your internet and try again.";

function chatHas(s, w) {
  if (/[^\x00-\x7f]/.test(w)) return s.includes(w);             // Hindi: plain contains
  const stem = w.endsWith("*"), t = stem ? w.slice(0, -1) : w;
  return new RegExp("\\b" + t.replace(/ /g, "\\s+") + (stem ? "" : "\\b"), "i").test(s);
}
function chatPick(q) {
  const s = q.toLowerCase();
  if (CHAT_LAW.some((w) => s.includes(w))) return null;       // legal question: ask the server
  let best = null, top = 0;
  for (const f of CHAT_FAQ) {
    const n = f.k.reduce((c, w) => c + (chatHas(s, w) ? 1 : 0), 0);
    if (n > top) { top = n; best = f; }
  }
  return best;
}

const _chat = { log: [] };            // kept while the page is open
function chatBubble(m) {
  const mine = m.who === "me";
  return `<div class="msg ${mine ? "me" : "bot"}">${mine ? "" : chatLogo(28)}
    <div class="bub" ${mine ? "data-notr" : ""}>${esc(m.text)}${m.cites && m.cites.length ? `<div class="cites">${m.cites.map((c) => `<span>${esc(c.authority)}: ${esc(c.clause)}</span>`).join("")}</div>` : ""}
    ${m.go ? `<button class="chat-go" type="button" data-go="${esc(m.go[0])}">${esc(m.go[1])} ${icon("chevron-right", 16)}</button>` : ""}</div></div>`;
}

function openChat() {
  if (!_chat.log.length) _chat.log.push({ who: "bot", text: CHAT_HELLO });
  const hush = $("#chat-fab"); if (hush) hush.classList.remove("nudge");
  sheet(`<div class="chat">
      <div class="chat-head">${chatLogo(42)}<div class="grow"><b>FoodLoop assistant</b><span class="live"><i></i> Here to help</span></div></div>
      <div class="chat-log" id="cl" aria-live="polite"></div>
      <div class="chat-chips" id="cc">${CHAT_CHIPS.map((c) => `<button type="button" class="chip-q" data-q="${esc(c)}">${esc(c)}</button>`).join("")}</div>
      <form class="chat-form" id="cf" autocomplete="off"><input id="cq" placeholder="Type your question…" maxlength="300" aria-label="Your question" enterkeyhint="send">
        <button class="send" type="submit" aria-label="Send">${icon("send", 20)}</button></form></div>`, (s, close) => {
    const logEl = $("#cl", s), input = $("#cq", s);
    const draw = () => { logEl.innerHTML = _chat.log.map(chatBubble).join(""); logEl.scrollTop = logEl.scrollHeight; };
    const push = (m) => { _chat.log.push(m); draw(); };
    const ask = async (q) => {
      q = q.trim(); if (!q) return;
      input.value = ""; $("#cc", s).style.display = "none";
      push({ who: "me", text: q });
      const f = chatPick(q);
      if (f) { setTimeout(() => push({ who: "bot", text: f.a, go: f.go }), 350); return; }
      logEl.insertAdjacentHTML("beforeend", `<div class="msg bot" id="typing">${chatLogo(28)}<div class="bub dots"><i></i><i></i><i></i></div></div>`);
      logEl.scrollTop = logEl.scrollHeight;
      try {
        const r = await post("/api/compliance/ask", { question: q });
        $("#typing", s)?.remove();
        push({ who: "bot", text: r.answer, cites: (r.citations || []).slice(0, 2) });
      } catch (e) {
        $("#typing", s)?.remove();
        push({ who: "bot", text: e.status === 0 ? CHAT_SORRY : e.message });
      }
    };
    $("#cf", s).onsubmit = (e) => { e.preventDefault(); ask(input.value); };
    s.addEventListener("click", (e) => {
      const q = e.target.closest("[data-q]"); if (q) ask(q.dataset.q);
      const g = e.target.closest("[data-go]"); if (g) { close(); go(g.dataset.go); }
    });
    if (_chat.log.length > 1) $("#cc", s).style.display = "none";
    draw();
    setTimeout(() => input.focus({ preventScroll: true }), 250);
  });
}

/* the floating button: only for business owners, on screens with tabs */
let _nudged = false;
function chatMount() {
  $("#chat-fab")?.remove();
  if (!S.user || S.user.role !== "business") return;
  const b = document.createElement("button");
  b.id = "chat-fab"; b.type = "button"; b.setAttribute("aria-label", "Ask FoodLoop assistant");
  b.innerHTML = `${chatLogo(58)}<span class="chat-tip">Ask FoodLoop</span>`;
  b.onclick = openChat;
  if (!_nudged) { _nudged = true; b.classList.add("nudge"); setTimeout(() => b.classList.remove("nudge"), 6000); }
  $("#app").appendChild(b);
}
