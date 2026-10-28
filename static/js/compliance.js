/* Regulatory Assistant: Verified guidance on food safety, surplus recovery, and disposal laws */

function formatLegalAnswer(text) {
  if (!text) return "";
  // Clean markdown headers and bullet points into clean HTML
  let clean = text
    .replace(/^###\s+(.*$)/gim, '<div style="font-weight:700;font-size:16px;margin-bottom:8px;color:#1B4332">$1</div>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\s*•\s+(.*$)/gim, '<div style="margin:4px 0 4px 16px;position:relative"><span style="position:absolute;left:-14px;color:#2F9E4F">•</span>$1</div>')
    .replace(/\n\n/g, '<div style="height:10px"></div>');
  return clean;
}

route("/compliance", { tabs: true, title: "Regulatory Assistant" }, async (el) => {
  let regs = [];
  try {
    const data = await api("/api/compliance/regulations");
    regs = data.regulations || [];
  } catch (e) {
    regs = [];
  }

  el.innerHTML = `
    <div style="margin-bottom:20px">
      <h1 style="font-size:22px;font-weight:700;margin:0 0 4px;letter-spacing:-0.01em">Regulatory Assistant</h1>
      <p class="muted small" style="margin:0">Official guidance on food surplus recovery, animal feed safety, and waste disposal rules in India.</p>
    </div>

    <!-- Query Box -->
    <div class="card" style="margin-bottom:20px;padding:16px">
      <form id="assistant-form" style="display:flex;gap:8px;flex-wrap:wrap">
        <input id="assistant-input" style="flex:1;min-width:240px;font-size:14px" placeholder="Ask a question (e.g. Can I donate leftover rotis to a gaushala?)">
        <button class="btn" id="assistant-submit" type="submit" style="min-width:110px">${icon("search", 16)} Search</button>
      </form>

      <div class="row wrap" style="gap:6px;margin-top:12px" id="chips">
        <button type="button" class="btn ghost sm chip-q" data-q="Can I donate left-over rotis to a gaushala?">Roti & Gaushala feed</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Can expired food go to cattle feed?">Cattle feed restrictions</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Can I boil spoiled rotten chicken curry to kill germs and donate it?">Spoiled food recooking</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Is it legal to pour used cooking oil down municipal sewage drains?">Used cooking oil disposal</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Can packaged yogurt cups be dumped directly into compost?">Packaging segregation</button>
        <button type="button" class="btn ghost sm chip-q" data-q="What are the penalties under FSSAI Section 59?">Section 59 penalties</button>
      </div>
    </div>

    <!-- Response Container -->
    <div id="assistant-res" style="display:none;margin-bottom:24px"></div>

    <!-- Regulations Directory -->
    <div style="margin:28px 0 14px">
      <h2 style="font-size:16px;font-weight:700;margin:0 0 2px">Statutory Reference Directory</h2>
      <p class="tiny muted" style="margin:0">Gazetted regulations from FSSAI, MoEFCC, and Central Pollution Control Board.</p>
    </div>

    <div class="grid" style="gap:10px">
      ${regs.map((r) => `
        <div class="card" style="padding:14px;border:1px solid #e9ecef">
          <div class="row between wrap" style="margin-bottom:4px">
            <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:#2F9E4F">${esc(r.authority)}</span>
            <span class="tiny muted">${esc(r.id)}</span>
          </div>
          <div style="font-weight:600;font-size:14px;margin-bottom:2px">${esc(r.title)}</div>
          <div class="tiny muted" style="margin-bottom:8px">${esc(r.regulation)}, ${esc(r.clause)}</div>
          <p class="small" style="line-height:1.5;margin:0 0 10px;color:#333">${esc(r.text)}</p>
          <div style="background:#f8f9fa;border-left:3px solid #2F9E4F;padding:6px 10px;font-size:12px;border-radius:2px">
            <strong>Mandate:</strong> ${esc(r.legal_mandate)}
          </div>
        </div>
      `).join("")}
    </div>
  `;

  const input = $("#assistant-input", el);
  const form = $("#assistant-form", el);
  const resEl = $("#assistant-res", el);

  const doAsk = async (query) => {
    if (!query) return;
    input.value = query;
    resEl.style.display = "";
    resEl.innerHTML = `
      <div class="card center" style="padding:20px">
        <p class="muted small" style="margin:0">Consulting regulatory reference directory…</p>
      </div>
    `;

    try {
      const res = await post("/api/compliance/ask", { question: query });
      const citations = res.citations || [];
      const formattedHTML = formatLegalAnswer(res.answer);

      resEl.innerHTML = `
        <div class="card" style="border-left:4px solid #2F9E4F;box-shadow:0 2px 8px rgba(0,0,0,.04);padding:18px">
          <div style="font-size:14px;line-height:1.65;margin-bottom:14px">
            ${formattedHTML}
          </div>
          ${citations.length ? `
            <div style="border-top:1px solid #eee;margin-top:14px;padding-top:12px">
              <div class="tiny muted" style="font-weight:700;text-transform:uppercase;letter-spacing:0.03em;margin-bottom:6px">Statutory References:</div>
              <div class="grid" style="gap:6px">
                ${citations.map((c) => `
                  <div style="font-size:12px;color:#495057">
                    <strong>${esc(c.authority)}:</strong> ${esc(c.regulation)}, ${esc(c.clause)}
                  </div>
                `).join("")}
              </div>
            </div>
          ` : ""}
        </div>
      `;
    } catch (err) {
      resEl.innerHTML = `<div class="banner bad" style="font-size:13px">${icon("triangle-alert", 16)}<div>${esc(err.message)}</div></div>`;
    }
  };

  form.onsubmit = (e) => {
    e.preventDefault();
    doAsk(input.value.trim());
  };

  el.querySelectorAll(".chip-q").forEach((btn) => {
    btn.onclick = () => doAsk(btn.dataset.q);
  });
});
