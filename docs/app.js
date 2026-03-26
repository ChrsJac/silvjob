const state = { jobs: [], filtered: [], selected: null };

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
  btn.textContent = "Loading…";
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
