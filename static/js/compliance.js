/* FSSAI & Environmental Waste Regulatory Copilot (RAG + Legal Verification) */

route("/compliance", { tabs: true, title: "Compliance Copilot" }, async (el) => {
  let regs = [];
  try {
    const data = await api("/api/compliance/regulations");
    regs = data.regulations || [];
  } catch (e) {
    regs = [];
  }

  el.innerHTML = `
    <div class="row between wrap" style="gap:10px;margin-bottom:16px">
      <div>
        <h1 style="font-size:24px;margin:0">FSSAI & Waste Copilot</h1>
        <p class="muted small" style="margin:4px 0 0">Statutory RAG intelligence grounded in Indian food safety & environmental law.</p>
      </div>
      <span class="chip ok">${icon("shield-check", 14)} Statutory Grounded</span>
    </div>

    <div class="card" style="margin-bottom:16px;border-left:4px solid var(--accent, #2F9E4F)">
      <div class="lbl" style="margin-bottom:8px">Ask the Regulatory Copilot</div>
      <form id="copilot-f" style="display:flex;gap:8px;flex-wrap:wrap">
        <input id="copilot-q" style="flex:1;min-width:220px" placeholder="e.g. Can expired dairy or bread go to cattle feed?">
        <button class="btn" id="copilot-go" type="submit" style="min-width:100px">${icon("search", 18)} Ask</button>
      </form>

      <div class="small muted" style="margin-top:10px;font-weight:600">Common regulatory inquiries:</div>
      <div class="row wrap" style="gap:6px;margin-top:6px" id="chips">
        <button type="button" class="btn ghost sm chip-q" data-q="Can expired food go to cattle feed?">Cattle feed restrictions</button>
        <button type="button" class="btn ghost sm chip-q" data-q="What is the maximum holding time for cooked meals?">Cooked food holding limits</button>
        <button type="button" class="btn ghost sm chip-q" data-q="What are the penalties under FSSAI Section 59?">Section 59 penalties</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Why is Tier D mandatory for spoiled produce?">Spoiled produce routing</button>
        <button type="button" class="btn ghost sm chip-q" data-q="What records must an FBO maintain under Regulation 3?">FBO record keeping</button>
      </div>
    </div>

    <div id="copilot-res" style="display:none;margin-bottom:20px"></div>

    <div class="row between wrap" style="margin:20px 0 10px">
      <h2 style="font-size:18px;margin:0">Official Statutory Index (${regs.length} Clauses)</h2>
      <span class="tiny muted">FSSAI (2019) · CPCB (2016) · FSSA (2006)</span>
    </div>

    <div class="grid" style="gap:12px">
      ${regs.map((r) => `
        <div class="card" style="padding:14px">
          <div class="row between wrap" style="margin-bottom:6px">
            <span class="chip" style="font-weight:700">${esc(r.authority)}</span>
            <span class="tiny muted">${esc(r.id)}</span>
          </div>
          <div style="font-weight:700;font-size:15px;margin-bottom:4px">${esc(r.title)}</div>
          <div class="small muted" style="font-style:italic;margin-bottom:8px">${esc(r.regulation)} — ${esc(r.clause)}</div>
          <p class="small" style="line-height:1.45;margin:0 0 10px">${esc(r.text)}</p>
          <div class="banner ok" style="padding:8px 10px;margin-top:6px;font-size:12px">
            <b>Mandate:</b> ${esc(r.legal_mandate)}
          </div>
        </div>
      `).join("")}
    </div>
  `;

  const input = $("#copilot-q", el);
  const form = $("#copilot-f", el);
  const resEl = $("#copilot-res", el);

  const doAsk = async (query) => {
    if (!query) return;
    input.value = query;
    resEl.style.display = "";
    resEl.innerHTML = `<div class="card center"><p class="muted">${icon("search", 20)} Consulting statutory RAG knowledge base…</p></div>`;

    try {
      const res = await post("/api/compliance/ask", { question: query });
      const citations = res.citations || [];
      resEl.innerHTML = `
        <div class="card" style="border:1.5px solid var(--accent, #2F9E4F);box-shadow:0 4px 14px rgba(47,158,79,.12)">
          <div class="row between wrap" style="margin-bottom:10px">
            <span class="chip ok">${icon("badge-check", 14)} Grounded Legal Opinion</span>
            <div class="row gap-s wrap">
              <span class="chip" style="font-size:11px;background:#e8f4fd;color:#0b7285">${icon("cpu", 12)} ${res.retrieval_mode === "dense_gemini_embedding" ? "Gemini Vector Embedding" : "Semantic Vector Search"}</span>
              <span class="tiny muted" style="align-self:center">Engine: ${esc(res.source)}</span>
            </div>
          </div>
          <div style="font-size:15px;line-height:1.55;white-space:pre-line;margin-bottom:14px">${esc(res.answer)}</div>
          ${citations.length ? `
            <div class="lbl" style="margin-top:12px">Statutory Citations:</div>
            <div class="grid" style="gap:8px;margin-top:6px">
              ${citations.map((c) => `
                <div class="banner info" style="padding:8px 12px">
                  <div style="font-weight:700;font-size:13px">${esc(c.authority)}: ${esc(c.clause)}</div>
                  <div class="tiny muted">${esc(c.title)} — ${esc(c.legal_mandate)}</div>
                </div>
              `).join("")}
            </div>
          ` : ""}
        </div>
      `;
    } catch (err) {
      resEl.innerHTML = `<div class="banner bad">${icon("triangle-alert", 20)}<div>${esc(err.message)}</div></div>`;
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
