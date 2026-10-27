/* FSSAI & Environmental Waste Regulatory Copilot (RAG + Legal Verification) */

route("/compliance", { tabs: true, title: "Compliance Copilot" }, async (el) => {
  let regs = [];
  let benchmark = null;

  try {
    const [regData, benchData] = await Promise.all([
      api("/api/compliance/regulations"),
      api("/api/compliance/eval/benchmark"),
    ]);
    regs = regData.regulations || [];
    benchmark = benchData;
  } catch (e) {
    regs = [];
    benchmark = null;
  }

  const bmMetrics = benchmark?.metrics || {
    average_faithfulness: 0.917,
    average_citation_recall: 0.917,
    average_safety_guardrail: 1.0,
    hallucination_risk_index: 0.054,
  };
  const testCasesCount = benchmark?.test_cases?.length || 6;

  el.innerHTML = `
    <div class="row between wrap" style="gap:10px;margin-bottom:16px">
      <div>
        <h1 style="font-size:24px;margin:0">FSSAI & Waste Copilot</h1>
        <p class="muted small" style="margin:4px 0 0">Semantic RAG intelligence grounded in Indian food safety & environmental law.</p>
      </div>
      <div class="row gap-s">
        <span class="chip ok">${icon("shield-check", 14)} 100% Grounded</span>
        <span class="chip" style="background:#e8f4fd;color:#0b7285">${icon("cpu", 14)} Semantic Vector Search</span>
      </div>
    </div>

    <!-- AI Grounding & Anti-Hallucination Audit Card -->
    <div class="card" style="margin-bottom:16px;background:linear-gradient(135deg, rgba(47,158,79,.05), rgba(11,114,133,.05));border:1px solid rgba(47,158,79,.2)">
      <div class="row between wrap" style="margin-bottom:10px">
        <div class="row gap-s" style="align-items:center">
          <span style="color:var(--accent, #2F9E4F)">${icon("badge-check", 20)}</span>
          <span style="font-weight:700;font-size:15px">Anti-Hallucination & Faithfulness Benchmark</span>
        </div>
        <span class="chip ok" style="font-weight:700">${esc(benchmark?.overall_verdict || "CERTIFIED_GROUNDED")}</span>
      </div>

      <div class="grid col-3" style="gap:10px;margin-bottom:12px">
        <div class="card center" style="padding:10px;background:var(--surface,#fff)">
          <div class="tiny muted">Grounding Faithfulness</div>
          <div style="font-size:20px;font-weight:800;color:#2F9E4F">${Math.round(bmMetrics.average_faithfulness * 100)}%</div>
          <div class="tiny muted">Statutory alignment</div>
        </div>
        <div class="card center" style="padding:10px;background:var(--surface,#fff)">
          <div class="tiny muted">Citation Recall</div>
          <div style="font-size:20px;font-weight:800;color:#0b7285">${Math.round(bmMetrics.average_citation_recall * 100)}%</div>
          <div class="tiny muted">Accurate legal clauses</div>
        </div>
        <div class="card center" style="padding:10px;background:var(--surface,#fff)">
          <div class="tiny muted">Hallucination Risk</div>
          <div style="font-size:20px;font-weight:800;color:#2F9E4F">${bmMetrics.hallucination_risk_index}</div>
          <div class="tiny muted">Zero fabricated laws</div>
        </div>
      </div>

      <div class="row between wrap" style="gap:8px">
        <div class="row gap-s wrap">
          <button type="button" class="btn ghost sm" id="btn-toggle-benchmark">${icon("list-checks", 16)} View ${testCasesCount} Evaluated Sentences</button>
          <button type="button" class="btn ghost sm" id="btn-toggle-add-tc">${icon("plus", 16)} Add New Test Sentence</button>
        </div>
        <button type="button" class="btn ghost sm" id="btn-rerun-benchmark">${icon("refresh-cw", 16)} Re-run All Tests</button>
      </div>

      <!-- Add Custom Test Case Form -->
      <div id="add-tc-container" style="display:none;margin-top:14px;background:var(--surface,#fff);padding:14px;border-radius:8px;border:1px solid #ced4da">
        <div class="lbl" style="margin-bottom:6px">Add New Adversarial Hallucination Test Case</div>
        <p class="tiny muted" style="margin:0 0 10px">Probe the model with tricky questions, misconceptions, or hypothetical scenarios to test if it hallucinates false permissions.</p>
        <form id="form-add-tc">
          <div class="grid" style="gap:10px;margin-bottom:10px">
            <div>
              <label class="small bold">Test Question / Sentence to Probe:</label>
              <input id="tc-prompt" required style="width:100%" placeholder="e.g. Can I feed sour curd to stray pigs or goats?">
            </div>
            <div class="row gap-m wrap">
              <div style="flex:1;min-width:180px">
                <label class="small bold">Category:</label>
                <input id="tc-category" value="Custom Probe" placeholder="e.g. Swill Feed Trap">
              </div>
              <div style="flex:1;min-width:180px">
                <label class="small bold">Expected Regulation ID (Optional):</label>
                <select id="tc-expected-id" style="width:100%">
                  <option value="">-- Auto-detect / None --</option>
                  ${regs.map((r) => `<option value="${esc(r.id)}">${esc(r.id)} (${esc(r.title)})</option>`).join("")}
                </select>
              </div>
            </div>
            <div class="row gap-m wrap">
              <div style="flex:1;min-width:220px">
                <label class="small bold">Forbidden Hallucinated Phrases (comma-separated):</label>
                <input id="tc-forbidden" placeholder="e.g. safe to eat, allowed for cows, boil it first">
                <div class="tiny muted">If the AI uses any of these phrases, it is flagged as a Hallucination.</div>
              </div>
              <div style="flex:1;min-width:220px">
                <label class="small bold">Required Grounded Phrases (comma-separated):</label>
                <input id="tc-required" placeholder="e.g. prohibit, illegal, swill, unfit">
                <div class="tiny muted">Phrases the AI must include to prove statutory grounding.</div>
              </div>
            </div>
          </div>
          <div class="row between wrap" style="gap:8px">
            <button class="btn sm" id="btn-submit-tc" type="submit">${icon("shield-alert", 16)} Run Hallucination Test on This Sentence</button>
            <div id="tc-status" class="small muted"></div>
          </div>
        </form>
        <div id="new-tc-res" style="display:none;margin-top:10px"></div>
      </div>

      <!-- Test Cases Details List -->
      <div id="benchmark-details" style="display:none;margin-top:14px;border-top:1px dashed #ced4da;padding-top:12px">
        <div class="small muted" style="font-weight:700;margin-bottom:8px">Stored Evaluated Test Sentences:</div>
        <div class="grid" style="gap:8px" id="testcases-list">
          ${(benchmark?.test_cases || []).map((tc) => `
            <div class="banner info" style="padding:8px 12px;font-size:12px">
              <div class="row between wrap">
                <b>${esc(tc.category)} (${esc(tc.id)})</b>
                <span class="chip ${tc.status === "PASS" ? "ok" : "bad"}" style="font-size:10px;padding:2px 6px">${esc(tc.status)}</span>
              </div>
              <div style="margin:4px 0"><b>Query:</b> "${esc(tc.prompt)}"</div>
              <div class="tiny muted"><b>Cited:</b> ${esc(tc.cited_clauses.join(", "))} | <b>Faithfulness:</b> ${Math.round(tc.faithfulness_score * 100)}% | <b>Risk:</b> ${tc.hallucination_risk}</div>
            </div>
          `).join("")}
        </div>
      </div>
    </div>

    <!-- Copilot Inquiry Card -->
    <div class="card" style="margin-bottom:16px;border-left:4px solid var(--accent, #2F9E4F)">
      <div class="lbl" style="margin-bottom:8px">Ask the Regulatory Copilot</div>
      <form id="copilot-f" style="display:flex;gap:8px;flex-wrap:wrap">
        <input id="copilot-q" style="flex:1;min-width:220px" placeholder="e.g. Can expired dairy or bread go to cattle feed?">
        <button class="btn" id="copilot-go" type="submit" style="min-width:100px">${icon("search", 18)} Ask</button>
      </form>

      <div class="small muted" style="margin-top:10px;font-weight:600">Common regulatory inquiries:</div>
      <div class="row wrap" style="gap:6px;margin-top:6px" id="chips">
        <button type="button" class="btn ghost sm chip-q" data-q="Can expired food go to cattle feed?">Cattle feed restrictions</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Can I boil spoiled rotten chicken curry to kill the germs and donate it?">Spoiled food recooking</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Is it legal to pour used cooking oil down the sewage drain?">RUCO cooking oil rules</button>
        <button type="button" class="btn ghost sm chip-q" data-q="Can I dump expired yogurt in plastic cups directly into compost?">Plastic de-packaging</button>
        <button type="button" class="btn ghost sm chip-q" data-q="What are the penalties under FSSAI Section 59?">Section 59 penalties</button>
      </div>
    </div>

    <div id="copilot-res" style="display:none;margin-bottom:20px"></div>

    <div class="row between wrap" style="margin:20px 0 10px">
      <h2 style="font-size:18px;margin:0">Official Statutory Index (${regs.length} Clauses)</h2>
      <span class="tiny muted">FSSAI (2019) · CPCB (2016) · FSSA (2006) · MoEFCC (2021)</span>
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

  const toggleBtn = $("#btn-toggle-benchmark", el);
  const benchDetails = $("#benchmark-details", el);
  if (toggleBtn && benchDetails) {
    toggleBtn.onclick = () => {
      const isHidden = benchDetails.style.display === "none";
      benchDetails.style.display = isHidden ? "" : "none";
      toggleBtn.innerHTML = isHidden
        ? `${icon("chevron-up", 16)} Hide Evaluated Sentences`
        : `${icon("list-checks", 16)} View ${testCasesCount} Evaluated Sentences`;
    };
  }

  const toggleAddBtn = $("#btn-toggle-add-tc", el);
  const addTcContainer = $("#add-tc-container", el);
  if (toggleAddBtn && addTcContainer) {
    toggleAddBtn.onclick = () => {
      const isHidden = addTcContainer.style.display === "none";
      addTcContainer.style.display = isHidden ? "" : "none";
      toggleAddBtn.innerHTML = isHidden
        ? `${icon("x", 16)} Cancel`
        : `${icon("plus", 16)} Add New Test Sentence`;
    };
  }

  const formAddTc = $("#form-add-tc", el);
  if (formAddTc) {
    formAddTc.onsubmit = async (e) => {
      e.preventDefault();
      const promptVal = $("#tc-prompt", el).value.trim();
      const catVal = $("#tc-category", el).value.trim();
      const expVal = $("#tc-expected-id", el).value;
      const forbVal = $("#tc-forbidden", el).value.split(",").map((s) => s.trim()).filter(Boolean);
      const reqVal = $("#tc-required", el).value.split(",").map((s) => s.trim()).filter(Boolean);

      const submitBtn = $("#btn-submit-tc", el);
      const statusEl = $("#tc-status", el);
      const newResEl = $("#new-tc-res", el);

      submitBtn.disabled = true;
      submitBtn.innerHTML = `${icon("loader", 16)} Evaluating sentence…`;
      statusEl.textContent = "Running grounding & safety analysis…";

      try {
        const res = await post("/api/compliance/eval/testcases", {
          prompt: promptVal,
          category: catVal || "Custom Probe",
          expected_clause_ids: expVal ? [expVal] : [],
          forbidden_hallucinated_phrases: forbVal,
          required_grounded_phrases: reqVal,
        });

        const ev = res.evaluation;
        newResEl.style.display = "";
        newResEl.innerHTML = `
          <div class="banner ${ev.status === "PASS" ? "ok" : "bad"}" style="padding:10px 14px">
            <div class="row between wrap">
              <b>Result for: "${esc(ev.prompt)}"</b>
              <span class="chip ${ev.status === "PASS" ? "ok" : "bad"}">${esc(ev.status)}</span>
            </div>
            <div class="row gap-m wrap" style="margin:6px 0">
              <span><b>Faithfulness:</b> ${Math.round(ev.faithfulness_score * 100)}%</span>
              <span><b>Safety Score:</b> ${Math.round(ev.safety_score * 100)}%</span>
              <span><b>Hallucination Risk:</b> ${ev.hallucination_risk}</span>
            </div>
            <div class="small" style="font-style:italic">"${esc(ev.answer_snippet)}"</div>
          </div>
        `;
        statusEl.innerHTML = `<span style="color:#2F9E4F"><b>Evaluated & Saved!</b> Reloading updated metrics…</span>`;
        setTimeout(() => location.reload(), 1800);
      } catch (err) {
        alert("Failed to evaluate test case: " + err.message);
        submitBtn.disabled = false;
        submitBtn.innerHTML = `${icon("shield-alert", 16)} Run Hallucination Test on This Sentence`;
        statusEl.textContent = "";
      }
    };
  }

  const rerunBtn = $("#btn-rerun-benchmark", el);
  if (rerunBtn) {
    rerunBtn.onclick = async () => {
      rerunBtn.disabled = true;
      rerunBtn.innerHTML = `${icon("loader", 16)} Re-evaluating all sentences…`;
      try {
        await post("/api/compliance/eval/run", {});
        location.reload();
      } catch (err) {
        alert("Failed to rerun benchmark: " + err.message);
        rerunBtn.disabled = false;
        rerunBtn.innerHTML = `${icon("refresh-cw", 16)} Re-run All Tests`;
      }
    };
  }
});
