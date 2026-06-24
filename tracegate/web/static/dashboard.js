const contextTable = document.querySelector("#context-table");
const evidenceTable = document.querySelector("#evidence-table");
const keyMetrics = document.querySelector("#key-metrics");
const riskMetrics = document.querySelector("#risk-metrics");
const contextSelect = document.querySelector("#context-group");
const demoForm = document.querySelector("#demo-form");
const demoResult = document.querySelector("#demo-result");

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderContextRows(rows) {
  contextTable.innerHTML = rows
    .map(
      (row) => `<tr>
        <td><strong>${row.name}</strong><br><span>${row.description}</span></td>
        <td>${row.safe_success}/${row.runs}</td>
        <td>pollution ${row.pollution}<br>destructive ${row.destructive_change}</td>
        <td>${row.avg_plan_quality.toFixed(2)}</td>
      </tr>`,
    )
    .join("");

  contextSelect.innerHTML = rows
    .map((row) => `<option value="${row.name}">${row.name}</option>`)
    .join("");
  contextSelect.value = "claim_with_evidence";
}

function renderEvidenceRows(rows) {
  evidenceTable.innerHTML = rows
    .map(
      (row) => `<tr>
        <td><strong>${row.evidence_status}</strong><br><span>${row.description}</span></td>
        <td>${row.expected_decision}</td>
        <td>${row.correct_decision}/${row.runs}</td>
        <td>${row.test_success}/${row.runs}</td>
      </tr>`,
    )
    .join("");
}

async function loadDashboard() {
  const overview = await fetch("/api/overview").then((response) => response.json());
  document.querySelector("#intro").textContent = overview.one_sentence_intro;
  document.querySelector("#source-badge").textContent = overview.data_source;
  document.querySelector("#total-runs").textContent = overview.total_runs;
  document.querySelector("#stage-line").textContent = `${overview.current_stage} · ${overview.model}`;

  keyMetrics.innerHTML = Object.entries(overview.key_metrics)
    .map(([label, value]) => metric(label, value))
    .join("");

  const totalPollution = overview.context_groups.reduce((sum, row) => sum + row.pollution, 0);
  const totalDestructive = overview.context_groups.reduce((sum, row) => sum + row.destructive_change, 0);
  riskMetrics.innerHTML =
    metric("Pollution", `${totalPollution}/${overview.total_runs}`) +
    metric("Destructive Change", `${totalDestructive}/${overview.total_runs}`) +
    metric("Hardest Evidence", "conflicting") +
    metric("Highest Safe Group", "tracegate_routed");

  renderContextRows(overview.context_groups);
  renderEvidenceRows(overview.evidence_statuses);
}

demoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  demoResult.textContent = "Analyzing...";
  const payload = {
    claim: document.querySelector("#claim").value,
    evidence: document.querySelector("#evidence").value,
    context_group: contextSelect.value,
  };
  const result = await fetch("/api/analyze-demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((response) => response.json());

  demoResult.innerHTML = `
    <strong>${result.suggested_decision}</strong>
    <p>${result.reason}</p>
    <p><strong>Verification plan</strong></p>
    <ul>${result.verification_plan.map((item) => `<li>${item}</li>`).join("")}</ul>
    <p><strong>Risk flags</strong>: ${result.risk_flags.length ? result.risk_flags.join(", ") : "none"}</p>
  `;
});

loadDashboard().catch((error) => {
  demoResult.textContent = `Failed to load dashboard data: ${error}`;
});

