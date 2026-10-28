"use strict";
/* Chat helper button for business owners, on the Home screen only.

   Self-contained: it adds its own styles, hooks the page by watching #app,
   and changes nothing else. App how-to questions are answered here; food
   safety and legal questions go to the compliance assistant
   (POST /api/compliance/ask), the same RAG the assistant screen uses.
   The whole file is wrapped, so a failure here can never break the app. */
(function () {
  try {
    const HOME_HASH = "#/b/home";
    let logoN = 0;

    /* ---------- styles (injected, so no stylesheet needs editing) ---------- */
    const CSS = `
#chat-fab { position: fixed; right: 16px; bottom: calc(var(--tab-h, 64px) + var(--safe-b, 0px) + 16px); z-index: 25; width: 58px; height: 58px;
  padding: 0; border: 0; border-radius: 50%; background: transparent; cursor: pointer; display: grid; place-items: center;
  filter: drop-shadow(0 6px 14px rgba(15,61,46,.38)); transition: transform .18s ease; -webkit-tap-highlight-color: transparent; }
#chat-fab:hover { transform: translateY(-2px) scale(1.04); } #chat-fab:active { transform: scale(.94); }
#chat-fab::after { content: ""; position: absolute; top: 3px; right: 3px; width: 13px; height: 13px; border-radius: 50%;
  background: #3DDC84; border: 2.5px solid #fff; }
#chat-fab .chat-tip { position: absolute; right: 68px; top: 50%; transform: translate(8px, -50%); white-space: nowrap; opacity: 0; pointer-events: none;
  background: #0F3D2E; color: #fff; font: 700 14px/1 var(--body, system-ui); padding: 10px 14px; border-radius: 14px; transition: opacity .2s, transform .2s; }
#chat-fab:hover .chat-tip, #chat-fab:focus-visible .chat-tip, #chat-fab.nudge .chat-tip { opacity: 1; transform: translate(0, -50%); }
#chat-fab.nudge { animation: chat-bob 1.6s ease-in-out 3; }
@keyframes chat-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@media (min-width: 900px) { #chat-fab { right: 28px; bottom: 28px; width: 62px; height: 62px; } }
.chat { display: flex; flex-direction: column; height: min(74dvh, 620px); margin: -4px -4px 0; }
.chat-head { display: flex; align-items: center; gap: 12px; padding: 2px 4px 12px; border-bottom: 1px solid var(--line, #E1EAE0); }
.chat-head .grow { flex: 1; }
.chat-head b { display: block; font: 800 18px/1.2 var(--display, system-ui); }
.chat-head .live { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #5B6B62; }
.chat-head .live i { width: 8px; height: 8px; border-radius: 50%; background: #3DDC84; }
.chat-log { flex: 1; overflow-y: auto; padding: 14px 2px; display: flex; flex-direction: column; gap: 12px; overscroll-behavior: contain; }
.chat .msg { display: flex; align-items: flex-end; gap: 8px; max-width: 92%; }
.chat .msg.me { align-self: flex-end; flex-direction: row-reverse; }
.chat .msg .chat-logo { flex: none; }
.chat .bub { background: #EEF4EC; border-radius: 18px 18px 18px 6px; padding: 11px 14px; font-size: 15px; line-height: 1.5; white-space: pre-line; }
.chat .msg.me .bub { background: #0F3D2E; color: #fff; border-radius: 18px 18px 6px 18px; }
.chat .bub .cites { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chat .bub .cites span { font-size: 11px; font-weight: 700; background: #fff; border: 1px solid var(--line-2, #D2DFD0); border-radius: 10px; padding: 3px 8px; }
.chat-go { display: inline-flex; align-items: center; gap: 4px; margin-top: 10px; border: 1.5px solid #2F9E4F; background: #fff; color: #0F3D2E;
  font: 700 14px/1 var(--body, system-ui); padding: 9px 12px; border-radius: 12px; cursor: pointer; }
.chat-go:hover { background: #E7F4EA; }
.chat .bub.dots { display: flex; gap: 5px; padding: 15px 16px; } .chat .bub.dots i { width: 8px; height: 8px; border-radius: 50%; background: #7A8B80; animation: chat-dot 1.1s infinite ease-in-out; }
.chat .bub.dots i:nth-child(2) { animation-delay: .15s; } .chat .bub.dots i:nth-child(3) { animation-delay: .3s; }
@keyframes chat-dot { 0%, 80%, 100% { opacity: .3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-4px); } }
.chat-chips { display: flex; flex-wrap: wrap; gap: 8px; padding: 6px 0 10px; }
.chat-chips .chip-q { border: 1.5px solid var(--line-2, #D2DFD0); background: #fff; color: var(--ink, #12231B); font: 600 13.5px/1.2 var(--body, system-ui); padding: 9px 12px; border-radius: 16px; cursor: pointer; text-align: left; }
.chat-chips .chip-q:hover { background: #E7F4EA; border-color: #2F9E4F; }
.chat-form { display: flex; gap: 8px; padding-top: 8px; border-top: 1px solid var(--line, #E1EAE0); }
.chat-form input { flex: 1; min-width: 0; font-size: 16px; }
.chat-form .send { width: 48px; flex: none; border: 0; border-radius: 14px; background: #0F3D2E; color: #fff; display: grid; place-items: center; cursor: pointer; }
.chat-form .send:hover { background: #17573F; }
@media (prefers-reduced-motion: reduce) { #chat-fab, #chat-fab * { animation: none !important; transition: none !important; } }`;

    /* ---------- the logo ---------- */
    function chatLogo(size) {
      const id = "cg" + (++logoN);
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

    /* ---------- what the helper can answer without the server ---------- */
    const FAQ = [
      { k: ["add", "adding", "create", "upload", "new lot"],
        a: "To add expired or surplus food, tap the green + Add lot button. Choose what it is, its condition, the weight and the expiry date. FoodLoop then picks the right route and the best nearby certified plant.",
        go: ["/b/add", "Add a lot"] },
      { k: ["pickup*", "collector*", "schedul*", "come"],
        a: "A collector plans a run once enough lots are waiting for the same plant. You get a notification with the pickup time and the collector's name and number. You can also see it under Lots.",
        go: ["/b/lots", "See my lots"] },
      { k: ["track*", "qr", "journey", "my order", "where is my lot", "where is my waste"],
        a: "Every lot has a Tracking ID and QR code. Open the lot and tap Track this order to see where it is, from pickup to the plant.",
        go: ["/track", "Track an order"] },
      { k: ["pay*", "bill*", "invoice*", "upi", "fare", "price", "cost", "charge*", "plan*"],
        a: "Your first pickups are free. After that you can pay per pickup, right after it is done, or choose a monthly plan. You can pay by UPI, card or net banking.",
        go: ["/b/billing", "Plan and billing"] },
      { k: ["record*", "certificate*", "proof", "audit*", "pdf", "receipt*"],
        a: "After a pickup is weighed and closed, you get a tamper-evident disposal record with a QR code and a PDF. Share it with auditors or customers. Find it under Records.",
        go: ["/b/records", "Open Records"] },
      { k: ["verif*", "approv*", "licence", "license", "pending"],
        a: "An admin checks your business before pickups start. Add your FSSAI licence number in Account to speed this up. You can add lots while you wait.",
        go: ["/me", "Open Account"] },
      { k: ["accept*", "allowed", "fresh", "which food", "what food", "kinds of", "route*"],
        a: "FoodLoop only takes food that is already waste: expired, spoiled or damaged food, plus empty packaging. Fresh food that is still in date is not accepted. Expired and spoiled food goes only to certified compost or biogas plants." },
      { k: ["weight*", "mismatch*", "differ*"],
        a: "Your load is weighed at the hub and again at the plant. If the two weights differ by more than 5%, the record shows a mismatch flag." },
      { k: ["remove", "delete", "cancel", "wrong", "mistake", "edit"],
        a: "Open Lots, tap the lot and choose Remove this lot. This works only while the lot is not in a pickup. To fix a weight or date, remove the lot and add it again.",
        go: ["/b/lots", "See my lots"] },
    ];
    const LAW = ["cattle", "feed ban", "swill", "penalt", "section 59", "holding", "regulation", "law", "legal", "fssai rule", "fbo", "statut", "cooked food", "compost rule"];
    const CHIPS = ["How do I add a lot?", "When will my pickup come?", "How do I pay?", "Can expired food go to cattle feed?"];
    const HELLO = "Hi! I'm the FoodLoop assistant. Ask me about adding lots, pickups, tracking, payments or food-safety rules.";
    const SORRY = "Sorry, I couldn't reach the assistant right now. Check your internet and try again.";

    function has(s, w) {                      // "word" = whole word, "word*" = starts with
      const stem = w.endsWith("*"), t = stem ? w.slice(0, -1) : w;
      return new RegExp("\\b" + t.replace(/ /g, "\\s+") + (stem ? "" : "\\b"), "i").test(s);
    }
    function pick(q) {
      const s = q.toLowerCase();
      if (LAW.some((w) => s.includes(w))) return null;          // legal question: ask the server
      let best = null, top = 0;
      for (const f of FAQ) {
        const n = f.k.reduce((c, w) => c + (has(s, w) ? 1 : 0), 0);
        if (n > top) { top = n; best = f; }
      }
      return best;
    }

    /* ---------- the chat panel ---------- */
    const log = [];                           // kept while the page stays open
    function bubble(m) {
      const mine = m.who === "me";
      return `<div class="msg ${mine ? "me" : "bot"}">${mine ? "" : chatLogo(28)}
    <div class="bub">${esc(m.text)}${m.cites && m.cites.length ? `<div class="cites">${m.cites.map((c) => `<span>${esc(c.authority)}: ${esc(c.clause)}</span>`).join("")}</div>` : ""}
    ${m.go ? `<button class="chat-go" type="button" data-go="${esc(m.go[0])}">${esc(m.go[1])} ${icon("chevron-right", 16)}</button>` : ""}</div></div>`;
    }

    function openChat() {
      try {
        if (!log.length) log.push({ who: "bot", text: HELLO });
        const fab = document.getElementById("chat-fab");
        if (fab) fab.classList.remove("nudge");
        sheet(`<div class="chat">
      <div class="chat-head">${chatLogo(42)}<div class="grow"><b>FoodLoop assistant</b><span class="live"><i></i> Here to help</span></div></div>
      <div class="chat-log" id="cl" aria-live="polite"></div>
      <div class="chat-chips" id="cc">${CHIPS.map((c) => `<button type="button" class="chip-q" data-q="${esc(c)}">${esc(c)}</button>`).join("")}</div>
      <form class="chat-form" id="cf" autocomplete="off"><input id="cq" placeholder="Type your question…" maxlength="300" aria-label="Your question" enterkeyhint="send">
        <button class="send" type="submit" aria-label="Send">${icon("send", 20)}</button></form></div>`, (s, close) => {
          const logEl = s.querySelector("#cl"), input = s.querySelector("#cq"), chips = s.querySelector("#cc");
          const draw = () => { logEl.innerHTML = log.map(bubble).join(""); logEl.scrollTop = logEl.scrollHeight; };
          const push = (m) => { log.push(m); draw(); };
          const ask = async (q) => {
            q = q.trim(); if (!q) return;
            input.value = ""; chips.style.display = "none";
            push({ who: "me", text: q });
            const f = pick(q);
            if (f) { setTimeout(() => push({ who: "bot", text: f.a, go: f.go }), 350); return; }
            logEl.insertAdjacentHTML("beforeend", `<div class="msg bot" id="typing">${chatLogo(28)}<div class="bub dots"><i></i><i></i><i></i></div></div>`);
            logEl.scrollTop = logEl.scrollHeight;
            try {
              const r = await post("/api/compliance/ask", { question: q });    // the same RAG as the assistant screen
              const t = s.querySelector("#typing"); if (t) t.remove();
              push({ who: "bot", text: r.answer, cites: (r.citations || []).slice(0, 2) });
            } catch (e) {
              const t = s.querySelector("#typing"); if (t) t.remove();
              push({ who: "bot", text: e && e.status === 0 ? SORRY : (e && e.message) || SORRY });
            }
          };
          s.querySelector("#cf").onsubmit = (e) => { e.preventDefault(); ask(input.value); };
          s.addEventListener("click", (e) => {
            const q = e.target.closest("[data-q]"); if (q) ask(q.dataset.q);
            const g = e.target.closest("[data-go]"); if (g) { close(); go(g.dataset.go); }
          });
          if (log.length > 1) chips.style.display = "none";
          draw();
          setTimeout(() => input.focus({ preventScroll: true }), 250);
        });
      } catch (e) { console.error("chat helper:", e); }
    }

    /* ---------- the button: business owners, Home screen only ---------- */
    let nudged = false;
    function wanted() {
      return !!(typeof S !== "undefined" && S && S.user && S.user.role === "business"
        && location.hash.split("?")[0] === HOME_HASH);
    }
    function update() {
      try {
        const app = document.getElementById("app");
        if (!app) return;
        const have = document.getElementById("chat-fab");
        if (!wanted()) { if (have) have.remove(); return; }
        if (have) return;
        const b = document.createElement("button");
        b.id = "chat-fab"; b.type = "button"; b.setAttribute("aria-label", "Ask FoodLoop assistant");
        b.innerHTML = `${chatLogo(58)}<span class="chat-tip">Ask FoodLoop</span>`;
        b.addEventListener("click", openChat);
        if (!nudged) { nudged = true; b.classList.add("nudge"); setTimeout(() => b.classList.remove("nudge"), 6000); }
        app.appendChild(b);
      } catch (e) { console.error("chat helper:", e); }
    }

    const st = document.createElement("style");
    st.id = "chat-css"; st.textContent = CSS;
    document.head.appendChild(st);

    const app = document.getElementById("app");
    if (app) new MutationObserver(update).observe(app, { childList: true });
    window.addEventListener("hashchange", () => setTimeout(update, 0));
    update();
  } catch (e) {
    console.error("chat helper disabled:", e);
  }
})();
