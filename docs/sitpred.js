/* sitpred.js – SIT Activity Trends tab
 *
 * Loads docs/data/sitpred.json and renders three views:
 *   1. Presence Over Time  – line chart, institution × year (tour appearances)
 *   2. By Institution      – horizontal bar, total tour appearances in range
 *   3. Retired/Emeritus    – bar chart by year
 *
 * Methodology note displayed on the page:
 *   Institutions are matched from the 2021 Directory and may not reflect
 *   the person's exact affiliation in every tour year. Historical data
 *   may be incomplete per the site's own leaderboard note.
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

// ── Institution name normalisation ───────────────────────────────────────────

// Keywords that mark an institution boundary; used to stop "of X" extension
// from greedily capturing a following department/school name.
const SP_INST_STOP = "(?:University|College|Institute|Academy|School|Department|Division|Center|Faculty)";
// Regex for one word token that may contain dots, apostrophes, or hyphens
const SP_WORD_TOK  = "[\\w.'\"\\-]+";

// Pre-built regexes for spExtractInstitutionCore
const _SP_UNI_RE = new RegExp(
  "\\b((?:" + SP_WORD_TOK + "\\s+){0,5}University" +
  "(?:\\s+of\\s+" + SP_WORD_TOK +
  "(?:\\s+(?!" + SP_INST_STOP + "\\b)" + SP_WORD_TOK + ")?)?)\\b"
);
const _SP_COL_RE = new RegExp("\\b((?:" + SP_WORD_TOK + "\\s+){0,5}College)\\b");
const _SP_INS_RE = new RegExp(
  "\\b((?:" + SP_WORD_TOK + "\\s+){0,5}Institute(?:\\s+of\\s+" + SP_WORD_TOK + ")?)\\b"
);
const _SP_INST_RE = /\b(?:University|College|Institute|Academy)\b/i;
const _SP_DEPT_RE = /\b(?:School|Department|Dept\.?|College|Division|Center|Programme?|Faculty|Laboratory|Lab|Institute|Unit|Station)\b/i;

/**
 * Extract the core "X University [of Y]" / "X College" / "X Institute" name
 * from a string that may contain trailing city/address noise.
 */
function spExtractInstitutionCore(s) {
  let m = s.match(_SP_UNI_RE);
  if (m) return m[1].trim();
  m = s.match(_SP_COL_RE);
  if (m) return m[1].trim();
  m = s.match(_SP_INS_RE);
  if (m) return m[1].trim();
  return s;
}

/**
 * Normalise a verbose institution string into a short, canonical name.
 *
 * Handles patterns like:
 *   "School of Forestry, Northern Arizona University"
 *       → "Northern Arizona University"
 *   "School of Forest, Fisheries and Geomatics Sciences, University of Florida"
 *       → "University of Florida"
 *   "School of Renewable Natural Resources, Louisiana State University Baton Rouge , Louisiana"
 *       → "Louisiana State University"
 *   "Forestry Department, Paul Smith's College 7777 NY-30"
 *       → "Paul Smith's College"
 *   "Rocky Mountain Research Station, USDA Forest Service 2500 S. Pine Knoll Drive"
 *       → "USDA Forest Service"
 */
function spNormalizeInstitution(name) {
  if (!name) return name;

  const parts = name.split(/,\s*/);

  if (parts.length >= 2) {
    // Find the rightmost comma-separated part that names a university/college/institute.
    for (let i = parts.length - 1; i > 0; i--) {
      const p = parts[i].trim();
      if (_SP_INST_RE.test(p) && p.length > 6) {
        // Strip trailing street-address numbers (e.g. " 7777 NY-30")
        let inst = p.replace(/\s+\d[\w\s\-.]*$/, "").trim();
        inst = spExtractInstitutionCore(inst);
        if (inst.length > 4) return inst;
      }
    }

    // If the first part starts with a known department/school keyword, discard it
    // and return the remainder (with trailing address/state noise removed).
    if (_SP_DEPT_RE.test(parts[0])) {
      let rest = parts.slice(1).join(", ").trim();
      rest = rest.replace(/\s+\d[\w\s\-.]*$/, "").trim();          // trailing address
      rest = rest.replace(/,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*$/, "").trim(); // trailing city/state
      if (rest.length > 4) return rest;
    }
  }

  // Single-part name or no simplification found — strip trailing junk only.
  return name
    .replace(/\s+\d[\w\s\-.]*$/, "")
    .replace(/,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*$/, "")
    .replace(/[,\s]+$/, "")
    .trim() || name;
}

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
  const insts = new Set(recs.filter(r => r.institution).map(r => spNormalizeInstitution(r.institution))).size;
  const tourYears = new Set(recs.map(r => r.year)).size;
  const el = document.getElementById("spStats");
  if (el) el.textContent =
    `${recs.length} appearances · ${insts} institutions · ${tourYears} tour years`;
}

// ── View 1: Institution attendance over time (line chart) ────────────────────

function spRenderPresenceChart() {
  const recs = spActiveRecords().filter(r => r.institution);

  // Build { normInstitution → { year → count } } — raw appearances, not unique people
  const presMap = {};
  for (const r of recs) {
    const inst = spNormalizeInstitution(r.institution);
    if (!presMap[inst]) presMap[inst] = {};
    presMap[inst][r.year] = (presMap[inst][r.year] || 0) + 1;
  }

  // Rank institutions by total appearances in the range
  const ranked = Object.entries(presMap).map(([inst, yearMap]) => ({
    inst,
    total: Object.values(yearMap).reduce((s, n) => s + n, 0),
  })).filter(x => x.total >= SP.minAppearances)
     .sort((a, b) => b.total - a.total)
     .slice(0, 15);

  const yearLabels = spYearsInRange();
  const datasets = ranked.map((x, i) => ({
    label: x.inst,
    data: yearLabels.map(y => presMap[x.inst][y] || 0),
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
        text: "Institution Attendance on SIT by Tour Year (top 15 institutions)" },
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
           title: { display: true, text: "Attendees" } },
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

  // Count raw tour appearances per normalized institution
  const instCounts = {};
  for (const r of recs) {
    const inst = spNormalizeInstitution(r.institution);
    instCounts[inst] = (instCounts[inst] || 0) + 1;
  }

  const sorted = Object.entries(instCounts)
    .map(([inst, count]) => ({ inst, count }))
    .filter(x => x.count >= SP.minAppearances)
    .sort((a, b) => b.count - a.count)
    .slice(0, 25);

  spDrawChart("bar",
    {
      labels: sorted.map(x => x.inst.length > 45 ? x.inst.slice(0, 43) + "…" : x.inst),
      datasets: [{
        label: "Tour Appearances",
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
          text: "SIT Tour Appearances by Institution in Selected Range (top 25)" },
        tooltip: {
          callbacks: {
            title: items => sorted[items[0].dataIndex].inst,
            label: item => `${item.raw} tour appearance${item.raw !== 1 ? "s" : ""}`,
          },
        },
      },
      scales: {
        x: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 },
             title: { display: true, text: "Tour Appearances" } },
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
    byYear[r.year] = (byYear[r.year] || 0) + 1;
  }

  const yearLabels = spYearsInRange();
  spDrawChart("bar",
    {
      labels: yearLabels,
      datasets: [{
        label: "Retired/Emeritus Attendees",
        data: yearLabels.map(y => byYear[y] || 0),
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
  const instRecs = activeRecs.filter(r => spNormalizeInstitution(r.institution) === institution);
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
