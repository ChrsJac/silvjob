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
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
  <header class="site-header">
    <div class="header-main">
      <div>
        <h1>SilvDocJobs</h1>
        <p>Doctorate-relevant forestry, silviculture, quantitative silviculture, extension, research, and postdoc openings.</p>
      </div>
      <div class="controls" id="jobsControls">
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
    </div>
    <div id="lastUpdated" class="last-updated"></div>
    <nav class="tab-nav" role="tablist">
      <button class="tab-btn active" data-tab="jobs" role="tab" aria-selected="true">SilvDocJobs</button>
      <button class="tab-btn" data-tab="sitpred" role="tab" aria-selected="false">&#128202; SitPred</button>
    </nav>
  </header>

  <!-- Jobs tab -->
  <div id="jobsTab" role="tabpanel">
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
  </div>

  <!-- SitPred tab -->
  <div id="sitpredTab" role="tabpanel" hidden>
    <div class="sp-page">

      <!-- Filter / view toolbar -->
      <div class="sp-toolbar">
        <div class="sp-filters">
          <label>From <select id="spYearFrom" class="sp-select"></select></label>
          <label>To <select id="spYearTo" class="sp-select"></select></label>
          <label class="sp-check"><input type="checkbox" id="spIncludeRetired"> Retired/emeritus</label>
          <label class="sp-check"><input type="checkbox" id="spShowUnmatched"> Unmatched</label>
          <label>Min tours
            <select id="spMinApps" class="sp-select">
              <option value="1">1+</option>
              <option value="2">2+</option>
              <option value="3">3+</option>
              <option value="5">5+</option>
            </select>
          </label>
        </div>
        <div class="sp-view-btns" role="group" aria-label="Chart view">
          <button class="sp-view-btn active" data-view="presence">Presence Over Time</button>
          <button class="sp-view-btn" data-view="institutions">By Institution</button>
          <button class="sp-view-btn" data-view="retired">Retired/Emeritus</button>
        </div>
      </div>

      <!-- Stats summary -->
      <p id="spStats" class="sp-stats"></p>

      <!-- Chart canvas -->
      <div id="spChartBox" class="sp-chart-box">
        <canvas id="spChart"></canvas>
      </div>

      <!-- Institution drill-down detail -->
      <div id="spDetailPanel"></div>

      <!-- Methodology disclaimer -->
      <p class="sp-disclaimer">
        &#9888; <strong>Methodology note:</strong> Institutions are matched from the public
        <a href="https://www.silvicultureinstructors.com" target="_blank" rel="noopener">2021 Directory</a>
        and may not reflect the attendee&rsquo;s exact affiliation in every tour year.
        Historical SIT attendance data may be incomplete per the site&rsquo;s own leaderboard note.
        This panel shows <em>SIT Activity Trends</em> &mdash; a proxy for institutional presence
        and network engagement, not a direct measure of hiring.
      </p>
    </div>
  </div>

  <script src="app.js"></script>
  <script src="sitpred.js"></script>
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

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach(b => {
    const active = b.dataset.tab === tab;
    b.classList.toggle("active", active);
    b.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.getElementById("jobsTab").hidden = (tab !== "jobs");
  document.getElementById("sitpredTab").hidden = (tab !== "sitpred");
  document.getElementById("jobsControls").hidden = (tab !== "jobs");
  if (tab === "sitpred") spInitIfNeeded();
}

async function init() {
  state.jobs = await loadJobs();
  setLastUpdated();

  document.getElementById("searchBox").addEventListener("input", applyFilters);
  document.getElementById("typeFilter").addEventListener("change", applyFilters);
  document.getElementById("refreshBtn").addEventListener("click", refreshData);
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  applyFilters();
}

init().catch((error) => {
  const panel = document.getElementById("detailPanel");
  panel.innerHTML = `<div class="detail-empty">Failed to load jobs.json: ${escapeHtml(String(error))}</div>`;
});
'''

# ── SitPred JavaScript (sitpred.js) ──────────────────────────────────────────
SITPRED_JS = '''/* sitpred.js – SIT Activity Trends tab
 *
 * Loads docs/data/sitpred.json and renders four views:
 *   1. Presence Over Time  – line chart, institution × year
 *   2. By Institution      – horizontal bar, unique attendees in range
 *   3. Retired/Emeritus    – bar chart by year
 *   4. People              – searchable activity table
 *
 * Methodology note displayed on the page:
 *   Institutions are matched from the 2021 Directory and may not reflect
 *   the person\'s exact affiliation in every tour year. Historical data
 *   may be incomplete per the site\'s own leaderboard note.
 */

const SP = {
  data: null,
  loaded: false,
  chart: null,
  yearFrom: null,
  yearTo: null,
  includeRetired: false,
  showUnmatched: false,
  minAppearances: 1,
  view: "presence",
};

// Palette for multi-series line charts (institution presence)
const SP_COLORS = [
  "#134e7a","#e07b39","#2e7d32","#6a1a7a","#b71c1c",
  "#00695c","#f57f17","#37474f","#880e4f","#4527a0",
  "#006064","#558b2f","#4e342e","#1565c0","#ff6f00",
];

// ── Bootstrap ────────────────────────────────────────────────────────────────

function spInitIfNeeded() {
  if (SP.loaded) return;
  SP.loaded = true; // prevent double-fetch
  spInit();
}

async function spInit() {
  try {
    const resp = await fetch("data/sitpred.json?" + Date.now());
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    SP.data = await resp.json();
    spBuildYearSelects();
    spBindEvents();
    spRender();
  } catch (err) {
    document.getElementById("sitpredTab").querySelector(".sp-page").innerHTML =
      `<div class="detail-empty" style="padding:2rem 1.5rem">
        <strong>SitPred data not yet available.</strong><br>
        Run the scraper (<code>python main.py</code>) to generate
        <code>docs/data/sitpred.json</code> from silvicultureinstructors.com.
      </div>`;
  }
}

function spBuildYearSelects() {
  const years = [...new Set(SP.data.records.map(r => r.year))].sort((a, b) => a - b);
  if (!years.length) return;
  SP.yearFrom = years[0];
  SP.yearTo = years[years.length - 1];

  const fromEl = document.getElementById("spYearFrom");
  const toEl   = document.getElementById("spYearTo");
  for (const y of years) {
    fromEl.add(new Option(y, y));
    toEl.add(new Option(y, y));
  }
  fromEl.value = SP.yearFrom;
  toEl.value   = SP.yearTo;
}

function spBindEvents() {
  document.getElementById("spYearFrom").addEventListener("change", e => {
    SP.yearFrom = +e.target.value; spRender();
  });
  document.getElementById("spYearTo").addEventListener("change", e => {
    SP.yearTo = +e.target.value; spRender();
  });
  document.getElementById("spIncludeRetired").addEventListener("change", e => {
    SP.includeRetired = e.target.checked; spRender();
  });
  document.getElementById("spShowUnmatched").addEventListener("change", e => {
    SP.showUnmatched = e.target.checked; spRender();
  });
  document.getElementById("spMinApps").addEventListener("change", e => {
    SP.minAppearances = +e.target.value; spRender();
  });
  document.querySelectorAll(".sp-view-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".sp-view-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      SP.view = btn.dataset.view;
      spRender();
    });
  });
}

// ── Filter helpers ────────────────────────────────────────────────────────────

function spActiveRecords() {
  return SP.data.records.filter(r => {
    if (r.year < SP.yearFrom || r.year > SP.yearTo) return false;
    if (!SP.includeRetired && r.status_bucket === "retired_or_emeritus") return false;
    if (!SP.showUnmatched  && r.status_bucket === "unmatched") return false;
    return true;
  });
}

function spYearsInRange() {
  const years = [];
  for (let y = SP.yearFrom; y <= SP.yearTo; y++) years.push(y);
  return years;
}

// ── Render dispatcher ─────────────────────────────────────────────────────────

function spRender() {
  const chartBox   = document.getElementById("spChartBox");
  chartBox.hidden   = false;
  if      (SP.view === "presence")     spRenderPresenceChart();
  else if (SP.view === "institutions") spRenderInstitutionsChart();
  else if (SP.view === "retired")      spRenderRetiredChart();
  spUpdateStats();
}

function spUpdateStats() {
  const recs = spActiveRecords();
  const insts = new Set(recs.filter(r => r.institution).map(r => r.institution)).size;
  const tourYears = new Set(recs.map(r => r.year)).size;
  const el = document.getElementById("spStats");
  if (el) el.textContent =
    `${recs.length}\u00a0appearances \u00b7 ${insts}\u00a0institutions \u00b7 ${tourYears}\u00a0tour years`;
}

// ── View 1: Institution presence over time (line chart) ───────────────────────

function spRenderPresenceChart() {
  const recs = spActiveRecords().filter(r => r.institution);

  // Build { institution → { year → Set<personNorm> } }
  const presMap = {};
  for (const r of recs) {
    if (!presMap[r.institution]) presMap[r.institution] = {};
    if (!presMap[r.institution][r.year]) presMap[r.institution][r.year] = new Set();
    presMap[r.institution][r.year].add(r.person_name_normalized);
  }

  // Rank institutions by total unique attendees in the range
  const ranked = Object.entries(presMap).map(([inst, yearMap]) => ({
    inst,
    total: new Set(Object.values(yearMap).flatMap(s => [...s])).size,
  })).filter(x => x.total >= SP.minAppearances)
     .sort((a, b) => b.total - a.total)
     .slice(0, 15);

  const yearLabels = spYearsInRange();
  const datasets = ranked.map((x, i) => ({
    label: x.inst,
    data: yearLabels.map(y => presMap[x.inst][y] ? presMap[x.inst][y].size : 0),
    borderColor: SP_COLORS[i % SP_COLORS.length],
    backgroundColor: SP_COLORS[i % SP_COLORS.length] + "22",
    tension: 0.2,
    pointRadius: 3,
    pointHoverRadius: 6,
    fill: false,
  }));

  spDrawChart("line", { labels: yearLabels, datasets }, {
    plugins: {
      legend: { display: true, position: "right",
        labels: { boxWidth: 12, font: { size: 11 }, filter: i => i.text.length <= 40 } },
      title: { display: true,
        text: "Institution Presence on SIT by Year (active attendees; top 15 institutions)" },
      tooltip: {
        callbacks: {
          title: items => `Year: ${items[0].label}`,
          label: item => item.raw > 0
            ? `${item.dataset.label}: ${item.raw} attendee${item.raw !== 1 ? "s" : ""}`
            : null,
          filter: item => item.raw > 0,
        },
      },
    },
    scales: {
      x: { title: { display: true, text: "Tour Year" } },
      y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 },
           title: { display: true, text: "Unique Attendees" } },
    },
    onClick: (e, elements) => {
      if (elements.length > 0) {
        const inst = ranked[elements[0].datasetIndex]?.inst;
        if (inst) spShowInstitutionDetail(inst, recs);
      }
    },
  });
}

// ── View 2: By institution – horizontal bar ───────────────────────────────────

function spRenderInstitutionsChart() {
  const recs = spActiveRecords().filter(r => r.institution);

  const instPeople = {};
  for (const r of recs) {
    if (!instPeople[r.institution]) instPeople[r.institution] = new Set();
    instPeople[r.institution].add(r.person_name_normalized);
  }

  const sorted = Object.entries(instPeople)
    .map(([inst, people]) => ({ inst, count: people.size }))
    .filter(x => x.count >= SP.minAppearances)
    .sort((a, b) => b.count - a.count)
    .slice(0, 25);

  spDrawChart("bar",
    {
      labels: sorted.map(x => x.inst.length > 45 ? x.inst.slice(0, 43) + "\u2026" : x.inst),
      datasets: [{
        label: "Unique Attendees",
        data: sorted.map(x => x.count),
        backgroundColor: "#134e7a",
        borderRadius: 4,
        hoverBackgroundColor: "#1a6090",
      }],
    },
    {
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        title: { display: true,
          text: "Active Silviculturists by Institution – Unique Attendees in Selected Range (top 25)" },
        tooltip: {
          callbacks: {
            title: items => sorted[items[0].dataIndex].inst,
            label: item => `${item.raw} unique attendee${item.raw !== 1 ? "s" : ""}`,
          },
        },
      },
      scales: {
        x: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 },
             title: { display: true, text: "Unique Attendees" } },
      },
      onClick: (e, elements) => {
        if (elements.length > 0) {
          const inst = sorted[elements[0].index]?.inst;
          if (inst) spShowInstitutionDetail(inst, recs);
        }
      },
    }
  );
}

// ── View 3: Retired/Emeritus participation by year (bar) ─────────────────────

function spRenderRetiredChart() {
  // Always include retired records for this view regardless of the toggle
  const recs = SP.data.records.filter(r =>
    r.year >= SP.yearFrom &&
    r.year <= SP.yearTo &&
    r.status_bucket === "retired_or_emeritus"
  );

  const byYear = {};
  for (const r of recs) {
    if (!byYear[r.year]) byYear[r.year] = new Set();
    byYear[r.year].add(r.person_name_normalized);
  }

  const yearLabels = spYearsInRange();
  spDrawChart("bar",
    {
      labels: yearLabels,
      datasets: [{
        label: "Retired/Emeritus Attendees",
        data: yearLabels.map(y => byYear[y] ? byYear[y].size : 0),
        backgroundColor: "#7a8a90",
        borderRadius: 4,
      }],
    },
    {
      plugins: {
        legend: { display: false },
        title: { display: true, text: "Retired/Emeritus SIT Participation by Year" },
      },
      scales: {
        x: { title: { display: true, text: "Tour Year" } },
        y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 },
             title: { display: true, text: "Attendees" } },
      },
    }
  );
}

// ── Institution drill-down ─────────────────────────────────────────────────────

function spShowInstitutionDetail(institution, activeRecs) {
  const instRecs = activeRecs.filter(r => r.institution === institution);
  const uniquePeople = new Set(instRecs.map(r => r.person_name_normalized)).size;
  const years  = [...new Set(instRecs.map(r => r.year))].sort((a, b) => a - b);

  // Group by year → tour → count
  const grouped = {};
  for (const r of instRecs) {
    if (!grouped[r.year]) grouped[r.year] = {};
    if (!grouped[r.year][r.tour]) grouped[r.year][r.tour] = 0;
    grouped[r.year][r.tour] += 1;
  }

  const tourRows = Object.entries(grouped)
    .sort(([a], [b]) => b - a)
    .flatMap(([year, tours]) =>
      Object.entries(tours).map(([tour, count]) =>
        `<tr><td>${year}</td><td>${escapeHtml(tour)}</td>` +
        `<td>${count}</td></tr>`
      )
    ).join("");

  document.getElementById("spDetailPanel").innerHTML = `
    <div class="sp-detail-card">
      <div class="sp-detail-header">
        <h3>${escapeHtml(institution)}</h3>
        <button class="sp-close-btn" onclick="document.getElementById('spDetailPanel').innerHTML=''"
          aria-label="Close">&times;</button>
      </div>
      <div class="meta-grid" style="grid-template-columns:repeat(3,1fr);margin-top:0.75rem">
        <div><span class="meta-label">Unique Attendees</span><span>${uniquePeople}</span></div>
        <div><span class="meta-label">Tour Years Active</span><span>${years.length}</span></div>
        <div><span class="meta-label">Total Appearances</span><span>${instRecs.length}</span></div>
      </div>
      ${tourRows
        ? `<h4 style="margin:0.9rem 0 0.4rem">Tour Appearances</h4>
           <div class="sp-table-wrap">
           <table class="sp-detail-table">
             <thead><tr><th>Year</th><th>Tour</th><th>Attendees</th></tr></thead>
             <tbody>${tourRows}</tbody>
           </table></div>`
        : ""}
    </div>`;
}

// ── Chart helper ──────────────────────────────────────────────────────────────

function spDrawChart(type, data, extraOptions) {
  const ctx = document.getElementById("spChart");
  if (SP.chart) { SP.chart.destroy(); SP.chart = null; }
  SP.chart = new Chart(ctx, {
    type,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      ...extraOptions,
    },
  });
}
'''

STYLES_CSS = '''* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f5f7f8;
  color: #172126;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.site-header {
  display: flex;
  flex-direction: column;
  background: white;
  border-bottom: 1px solid #d8e0e5;
  position: sticky;
  top: 0;
  z-index: 10;
}
.header-main {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
  padding: 1.25rem 1.5rem 0.75rem 1.5rem;
}
.site-header h1 { margin: 0 0 0.25rem 0; font-size: 1.8rem; }
.site-header p  { margin: 0; max-width: 64ch; color: #4d5a62; }

.controls { display: flex; gap: 0.75rem; align-items: center; }
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
.refresh-btn:hover   { background: #f0f4f6; }
.refresh-btn:disabled { opacity: 0.6; cursor: default; }

.last-updated {
  font-size: 0.78rem;
  color: #61717a;
  text-align: right;
  padding: 0 1.5rem 0.25rem 1.5rem;
}

/* ── Tab navigation ──────────────────────────────────────────────────────── */
.tab-nav {
  display: flex;
  padding: 0 1.5rem;
  border-top: 1px solid #e8eff2;
  gap: 0;
}
.tab-btn {
  padding: 0.6rem 1.4rem;
  border: none;
  border-bottom: 3px solid transparent;
  background: none;
  cursor: pointer;
  font: inherit;
  font-size: 0.95rem;
  color: #61717a;
  margin-bottom: -1px;
}
.tab-btn.active {
  color: #134e7a;
  border-bottom-color: #134e7a;
  font-weight: 600;
}
.tab-btn:hover { color: #134e7a; }

/* ── Jobs layout ─────────────────────────────────────────────────────────── */
.layout {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 1rem;
  padding: 1rem;
  min-height: calc(100vh - 120px);
}
.table-panel, .detail-panel {
  background: white;
  border: 1px solid #d8e0e5;
  border-radius: 18px;
  overflow: hidden;
}
.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 160px);
}
table { width: 100%; border-collapse: collapse; }
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
tbody tr:hover, tbody tr.active { background: #f8fbfc; }
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
  max-height: calc(100vh - 160px);
}
.detail-card h2  { margin-top: 0; margin-bottom: 1rem; }
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
.description { white-space: pre-wrap; line-height: 1.55; }
.links { display: flex; gap: 1rem; margin-top: 1rem; }
.links a { color: #134e7a; text-decoration: none; }
.links a:hover { text-decoration: underline; }
.detail-empty { color: #61717a; padding: 1rem; }

/* ── SitPred tab ─────────────────────────────────────────────────────────── */
.sp-page {
  padding: 1rem 1.25rem;
  max-width: 1600px;
}

/* Toolbar */
.sp-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.6rem;
}
.sp-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}
.sp-filters label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: #4d5a62;
}
.sp-check { cursor: pointer; }
.sp-select {
  padding: 0.4rem 0.6rem;
  border: 1px solid #cbd5db;
  border-radius: 8px;
  background: white;
  font: inherit;
  font-size: 0.9rem;
}
.sp-view-btns {
  display: flex;
  gap: 0;
  border: 1px solid #cbd5db;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
}
.sp-view-btn {
  padding: 0.55rem 1rem;
  border: none;
  border-right: 1px solid #cbd5db;
  background: white;
  cursor: pointer;
  font: inherit;
  font-size: 0.88rem;
  color: #4d5a62;
}
.sp-view-btn:last-child { border-right: none; }
.sp-view-btn.active {
  background: #134e7a;
  color: white;
  font-weight: 600;
}
.sp-view-btn:hover:not(.active) { background: #f0f4f6; }

/* Stats bar */
.sp-stats {
  font-size: 0.82rem;
  color: #61717a;
  margin: 0 0 0.5rem 0;
}

/* Chart box */
.sp-chart-box {
  background: white;
  border: 1px solid #d8e0e5;
  border-radius: 18px;
  padding: 1rem;
  height: 500px;
  position: relative;
}

/* People panel */
.sp-table-wrap {
  overflow: auto;
  max-height: 480px;
  background: white;
  border: 1px solid #d8e0e5;
  border-radius: 18px;
}
.sp-detail-table {
  width: 100%;
  border-collapse: collapse;
}
.sp-detail-table thead th {
  position: sticky;
  top: 0;
  background: #f0f4f6;
  text-align: left;
  padding: 0.8rem 0.9rem;
  border-bottom: 1px solid #d8e0e5;
  font-size: 0.9rem;
}
.sp-detail-table tbody td {
  padding: 0.75rem 0.9rem;
  border-bottom: 1px solid #edf2f5;
  font-size: 0.9rem;
  vertical-align: top;
}
.sp-detail-table tbody tr:hover {
  background: #f8fbfc;
}

/* Institution detail card */
#spDetailPanel { margin-top: 1rem; }
.sp-detail-card {
  background: white;
  border: 1px solid #d8e0e5;
  border-radius: 18px;
  padding: 1.25rem;
}
.sp-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.sp-detail-header h3 { margin: 0; }
.sp-close-btn {
  border: none;
  background: none;
  font-size: 1.4rem;
  color: #61717a;
  cursor: pointer;
  line-height: 1;
  padding: 0 0.25rem;
}
.sp-close-btn:hover { color: #172126; }

/* Disclaimer */
.sp-disclaimer {
  margin-top: 1.25rem;
  font-size: 0.82rem;
  color: #61717a;
  border-top: 1px solid #e8eff2;
  padding-top: 0.75rem;
  line-height: 1.55;
}
.sp-disclaimer a { color: #134e7a; }

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 980px) {
  .header-main { flex-direction: column; align-items: stretch; }
  .controls { flex-direction: column; }
  .controls input, .controls select { min-width: 100%; }
  .layout { grid-template-columns: 1fr; }
  .table-wrap, .detail-panel { max-height: none; }
  .sp-toolbar { flex-direction: column; }
  .sp-chart-box { height: 380px; }
  .meta-grid { grid-template-columns: 1fr; }
}
'''


def build_static_site(output_dir: Path, jobs: list[JobRecord]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(parents=True, exist_ok=True)

    (output_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (output_dir / "app.js").write_text(APP_JS, encoding="utf-8")
    (output_dir / "sitpred.js").write_text(SITPRED_JS, encoding="utf-8")
    (output_dir / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (output_dir / "data" / "jobs.json").write_text(
        json.dumps([job.to_dict() for job in jobs], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
