// app.js - vanilla JavaScript for the dashboard (no frameworks).
//
// Two jobs:
//   1. Every 1.5 seconds ask the server for /api/status and redraw the page.
//   2. When a button is clicked, send a POST request and show the server's message.

const $ = (id) => document.getElementById(id);

// Escape text before putting it in HTML, so a weird file name can never inject code.
function esc(value) {
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function badge(level) {
  return `<span class="badge ${esc(level)}">${esc(level)}</span>`;
}

// ---------- drawing ----------
function render(d) {
  // KPI cards
  $("k-total").textContent = d.total_files;
  $("k-modified").textContent = d.modified_recent;
  $("k-warn").textContent = d.warnings;
  $("k-crit").textContent = d.criticals;

  const statusLabel = { NORMAL: "SECURE", WARNING: "WARNING", CRITICAL: "CRITICAL" }[d.status];
  $("k-status").textContent = statusLabel;
  $("k-status").className = "badge " + d.status;
  $("k-status-note").textContent = d.incident_active ? "open incident" : "no open incident";

  $("k-risk").textContent = d.risk_level;
  $("k-risk").className = "badge " + d.risk_level;
  $("k-score").textContent = `score ${d.risk_score} / 100`;
  const meter = $("k-meter");
  meter.style.width = d.risk_score + "%";
  meter.style.background =
    d.risk_level === "HIGH" ? "var(--red)" : d.risk_level === "MEDIUM" ? "var(--amber)" : "var(--green)";

  // Incident banner
  const banner = $("banner");
  if (d.incident_active) {
    banner.className = "banner " + d.status.toLowerCase();
    banner.textContent = d.status === "CRITICAL"
      ? "CRITICAL: abnormal file activity detected. Click 'Protect Data' to snapshot, then 'Recover'."
      : "WARNING: unusual file activity detected. Review the reasons below.";
  } else {
    banner.className = "banner hidden";
  }

  // Explainability
  $("reasons").innerHTML = d.reasons.map((r) => `<li>${esc(r)}</li>`).join("");
  const l = d.live, r = d.rules;
  $("w-sec").textContent = r.window;
  $("w-total").textContent = l.total_changes;
  $("w-ren").textContent = l.renames;
  $("w-ext").textContent = l.ext_changes;
  $("r-wc").textContent = r.warning_changes + "+";
  $("r-cc").textContent = r.critical_changes + "+";
  $("r-wr").textContent = r.warning_renames + "+";
  $("r-cr").textContent = r.critical_renames + "+";
  $("r-we").textContent = r.warning_ext + "+";
  const b = l.breakdown;
  $("breakdown").textContent =
    `Risk score = volume ${b.volume} + renames ${b.renames} + extensions ${b.extensions}` +
    (b.floor_applied ? " (raised to match the alert level)" : "") + ` = ${l.risk_score}`;

  // Chart (bar colour follows the same thresholds as the rules)
  const max = Math.max(...d.chart, 1);
  $("chart").innerHTML = d.chart.map((n) => {
    const cls = n >= r.critical_changes ? "crit" : n >= r.warning_changes ? "warn" : "";
    return `<div class="bar ${cls}" style="height:${Math.max(2, (n / max) * 100)}%" title="${n} events"></div>`;
  }).join("");

  // Alerts
  $("alerts").innerHTML = d.alerts.length
    ? d.alerts.map((a) => `
        <div class="alert ${esc(a.level)}">
          ${badge(a.level)} <span class="when">${esc(a.time_text)} &middot; risk ${a.risk_score}</span>
          <span class="tag">${a.resolved ? "(resolved)" : "(open)"}</span>
          <ul>${a.reasons.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
        </div>`).join("")
    : '<p class="small">No alerts yet. Everything looks normal.</p>';

  // Protection status
  $("p-snap").textContent = d.snapshot ? `${d.snapshot.name} (${d.snapshot.file_count} files)` : "none yet";
  $("p-count").textContent = d.snapshot_count;
  $("p-sandbox").innerHTML =
    `<span class="badge ${d.sandbox.state === "CLEAN" ? "NORMAL" : "CRITICAL"}">${esc(d.sandbox.state)}</span>`;
  $("p-files").textContent = `${d.sandbox.files} (${d.sandbox.locked} with fake .locked_sim)`;

  // Activity log table
  $("log").innerHTML = d.events.map((e) => `
    <tr>
      <td>${esc(e.time_text)}</td>
      <td>${esc(e.event)}</td>
      <td>${esc(e.file)}</td>
      <td>${badge(e.severity)}</td>
      <td>${esc(e.reason)}</td>
    </tr>`).join("");
}

async function refresh() {
  try {
    const res = await fetch("/api/status");
    render(await res.json());
  } catch (err) {
    console.error("Could not reach the server:", err);
  }
}

// ---------- buttons ----------
const buttons = ["btn-sim", "btn-protect", "btn-recover", "btn-reset"];

function showMessage(data) {
  const box = $("msg");
  box.className = "msg " + (data.ok ? "ok" : "bad");
  let html = `<b>${esc(data.message)}</b>`;
  if (data.steps) html += `<ul>${data.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>`;
  if (data.reasons) html += `<ul>${data.reasons.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>`;
  box.innerHTML = html;
}

async function act(url, busyText) {
  buttons.forEach((id) => ($(id).disabled = true));
  const box = $("msg");
  box.className = "msg";
  box.textContent = busyText;
  try {
    const res = await fetch(url, { method: "POST" });
    showMessage(await res.json());
  } catch (err) {
    showMessage({ ok: false, message: "Request failed: " + err });
  }
  buttons.forEach((id) => ($(id).disabled = false));
  refresh();
}

$("btn-sim").onclick = () => act("/api/simulate", "Running safe simulation inside sandbox_data ...");
$("btn-protect").onclick = () => act("/api/protect", "Creating snapshot ...");
$("btn-recover").onclick = () => act("/api/recover", "Recovering from the latest snapshot ...");
$("btn-reset").onclick = () => act("/api/reset", "Resetting demo ...");

refresh();
setInterval(refresh, 1500);
