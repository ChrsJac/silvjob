from __future__ import annotations

import json
from pathlib import Path

from .models import JobRecord


INDEX_HTML = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>SilvDocJobs</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <div>
      <h1>SilvDocJobs</h1>
      <p>Doctorate-relevant forestry, silviculture, quantitative silviculture, extension, research, and postdoc openings.</p>
    </div>
    <div class="controls">
      <input id="searchBox" type="search" placeholder="Search title, organization, topic, or source">
      <select id="typeFilter">
        <option value="">All job types</option>
        <option value="Faculty/Academic">Faculty/Academic</option>
        <option value="Postdoc">Postdoc</option>
        <option value="Research">Research</option>
        <option value="Extension">Extension</option>
        <option value="Director">Director</option>
      </select>
      <button id="refreshBtn" class="refresh-btn" title="Reload the latest job data">&#8635; Refresh</button>
    </div>
    <div id="lastUpdated" class="last-updated"></div>
  </header>

  <main class="layout">
    <section class="table-panel">
      <div class="table-wrap">
        <table id="jobsTable">
          <thead>
            <tr>
              <th>Organization</th>
              <th>Position</th>
              <th>Salary</th>
              <th>Date Posted</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <aside class="detail-panel" id="detailPanel">
      <div class="detail-empty">Select a position to view the cleaned description and source link.</div>
    </aside>
  </main>

  <script src="app.js"></script>
</body>
</html>
'''

APP_JS = '''const state = { jobs: [], filtered: [], selected: null };

function escapeHtml(value) {
  return (value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function renderTable() {
  const tbody = document.querySelector("#jobsTable tbody");
  tbody.innerHTML = "";

  state.filtered.forEach((job, index) => {
    const row = document.createElement("tr");
    row.className = state.selected === index ? "active" : "";
    row.innerHTML = `
      <td>${escapeHtml(job.organization || "--")}</td>
      <td><button class="title-button" data-index="${index}">${escapeHtml(job.title || "--")}</button></td>
      <td>${escapeHtml(job.salary || "$--.--")}</td>
      <td>${escapeHtml(job.date_posted || "--")}</td>
    `;
    tbody.appendChild(row);
  });

  document.querySelectorAll(".title-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.selected = Number(button.dataset.index);
      renderTable();
      renderDetail();
    });
  });
}

function renderDetail() {
  const panel = document.getElementById("detailPanel");
  if (state.selected === null || !state.filtered[state.selected]) {
    panel.innerHTML = `<div class="detail-empty">Select a position to view the cleaned description and source link.</div>`;
    return;
  }

  const job = state.filtered[state.selected];
  panel.innerHTML = `
    <article class="detail-card">
      <h2>${escapeHtml(job.title)}</h2>
      <div class="meta-grid">
        <div><span class="meta-label">Organization</span><span>${escapeHtml(job.organization || "--")}</span></div>
        <div><span class="meta-label">Job Type</span><span>${escapeHtml(job.job_type || "--")}</span></div>
        <div><span class="meta-label">Salary</span><span>${escapeHtml(job.salary || "$--.--")}</span></div>
        <div><span class="meta-label">Date Posted</span><span>${escapeHtml(job.date_posted || "--")}</span></div>
        <div><span class="meta-label">Location</span><span>${escapeHtml(job.location || "--")}</span></div>
        <div><span class="meta-label">Source</span><span>${escapeHtml(job.source || "--")}</span></div>
      </div>
      <section>
        <h3>Description</h3>
        <p class="description">${escapeHtml(job.description || "No description captured.")}</p>
      </section>
      <div class="links">
        <a href="${job.external_posting_url || job.listing_url}" target="_blank" rel="noopener noreferrer">Open original posting</a>
        <a href="${job.listing_url}" target="_blank" rel="noopener noreferrer">Open scraped source page</a>
      </div>
    </article>
  `;
}

function applyFilters() {
  const q = document.getElementById("searchBox").value.trim().toLowerCase();
  const typeFilter = document.getElementById("typeFilter").value;

  state.filtered = state.jobs.filter((job) => {
    const haystack = [
      job.title, job.organization, job.source, job.description, (job.matched_terms || []).join(" "), (job.matched_roles || []).join(" ")
    ].join(" ").toLowerCase();

    const matchesQuery = !q || haystack.includes(q);
    const matchesType = !typeFilter || job.job_type === typeFilter;
    return matchesQuery && matchesType;
  });

  state.selected = state.filtered.length ? 0 : null;
  renderTable();
  renderDetail();
}

async function loadJobs() {
  const response = await fetch("data/jobs.json?" + Date.now());
  const jobs = await response.json();
  jobs.sort((a, b) => {
    const da = a.date_posted || "9999-99-99";
    const db = b.date_posted || "9999-99-99";
    if (da !== db) return da < db ? -1 : 1;
    return (a.organization || "").localeCompare(b.organization || "");
  });
  return jobs;
}

function setLastUpdated() {
  const el = document.getElementById("lastUpdated");
  if (el) el.textContent = "Data loaded: " + new Date().toLocaleTimeString();
}

async function refreshData() {
  const btn = document.getElementById("refreshBtn");
  btn.disabled = true;
  btn.textContent = "Loading\u2026";
  try {
    state.jobs = await loadJobs();
    state.selected = null;
    setLastUpdated();
    applyFilters();
  } catch (error) {
    const el = document.getElementById("lastUpdated");
    if (el) el.textContent = "Refresh failed: " + String(error);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "&#8635; Refresh";
  }
}

async function init() {
  state.jobs = await loadJobs();
  setLastUpdated();

  document.getElementById("searchBox").addEventListener("input", applyFilters);
  document.getElementById("typeFilter").addEventListener("change", applyFilters);
  document.getElementById("refreshBtn").addEventListener("click", refreshData);
  applyFilters();
}

init().catch((error) => {
  const panel = document.getElementById("detailPanel");
  panel.innerHTML = `<div class="detail-empty">Failed to load jobs.json: ${escapeHtml(String(error))}</div>`;
});
'''

STYLES_CSS = '''* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f5f7f8;
  color: #172126;
}
.site-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
  padding: 1.25rem 1.5rem;
  background: white;
  border-bottom: 1px solid #d8e0e5;
  position: sticky;
  top: 0;
  z-index: 10;
}
.site-header h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.8rem;
}
.site-header p {
  margin: 0;
  max-width: 64ch;
  color: #4d5a62;
}
.controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.controls input, .controls select {
  min-width: 220px;
  padding: 0.7rem 0.8rem;
  border: 1px solid #cbd5db;
  border-radius: 10px;
  background: white;
}
.refresh-btn {
  padding: 0.7rem 1rem;
  border: 1px solid #cbd5db;
  border-radius: 10px;
  background: white;
  color: #134e7a;
  cursor: pointer;
  font: inherit;
  white-space: nowrap;
}
.refresh-btn:hover { background: #f0f4f6; }
.refresh-btn:disabled { opacity: 0.6; cursor: default; }
.last-updated {
  font-size: 0.78rem;
  color: #61717a;
  text-align: right;
  padding-top: 0.25rem;
}
.layout {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 1rem;
  padding: 1rem;
  min-height: calc(100vh - 90px);
}
.table-panel, .detail-panel {
  background: white;
  border: 1px solid #d8e0e5;
  border-radius: 18px;
  overflow: hidden;
}
.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 130px);
}
table {
  width: 100%;
  border-collapse: collapse;
}
thead th {
  position: sticky;
  top: 0;
  background: #f0f4f6;
  text-align: left;
  padding: 0.9rem;
  border-bottom: 1px solid #d8e0e5;
  font-size: 0.92rem;
}
tbody td {
  padding: 0.9rem;
  vertical-align: top;
  border-bottom: 1px solid #edf2f5;
}
tbody tr:hover, tbody tr.active {
  background: #f8fbfc;
}
.title-button {
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  color: #134e7a;
  cursor: pointer;
  font: inherit;
}
.title-button:hover { text-decoration: underline; }
.detail-panel {
  padding: 1rem 1.1rem;
  overflow: auto;
  max-height: calc(100vh - 130px);
}
.detail-card h2 {
  margin-top: 0;
  margin-bottom: 1rem;
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
  margin-bottom: 1rem;
}
.meta-grid div {
  padding: 0.8rem;
  border: 1px solid #e5ecef;
  border-radius: 14px;
  background: #fbfcfd;
}
.meta-label {
  display: block;
  font-size: 0.8rem;
  color: #61717a;
  margin-bottom: 0.25rem;
}
.description {
  white-space: pre-wrap;
  line-height: 1.55;
}
.links {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}
.links a {
  color: #134e7a;
  text-decoration: none;
}
.links a:hover { text-decoration: underline; }
.detail-empty {
  color: #61717a;
  padding: 1rem;
}
@media (max-width: 980px) {
  .site-header { flex-direction: column; align-items: stretch; }
  .controls { flex-direction: column; }
  .controls input, .controls select { min-width: 100%; }
  .layout { grid-template-columns: 1fr; }
  .table-wrap, .detail-panel { max-height: none; }
}
'''


def build_static_site(output_dir: Path, jobs: list[JobRecord]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(parents=True, exist_ok=True)

    (output_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (output_dir / "app.js").write_text(APP_JS, encoding="utf-8")
    (output_dir / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (output_dir / "data" / "jobs.json").write_text(
        json.dumps([job.to_dict() for job in jobs], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
