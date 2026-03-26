# SilvDocJobs

SilvDocJobs is a lightweight pipeline for scraping doctorate-relevant forestry and silviculture jobs and publishing them to a clean static site with GitHub Pages.

## What this version is designed to do

- focus on positions relevant to a Ph.D. in forestry, especially silviculture, quantitative silviculture, forest biometrics, growth and yield, forest ecology, forest management, extension, and related postdoc or research roles
- store only salary values that appear in the listing itself
- use `$--.--` when no salary is listed
- show `date posted`
- show `organization`
- show `job title`
- show a cleaned description copied from the source listing
- link back to the real posting
- publish a simple read-only site your lab mates can browse

## Recommended deployment model

Use **GitHub Actions** for scraping and **GitHub Pages** for the public site.

That is cleaner than Shiny for this use case because:
- your site is mostly read-only
- the data are small
- you do not need a server process
- GitHub Pages is free for static content
- a scheduled Action can refresh the data automatically

Use Shiny only if you later want authenticated users, server-side joins, database-backed faceting, or complex analytics.

## Current source mix

This repo includes:
- Texas A&M Natural Resources Job Board
- UGA Warnell Jobs
- UGA Jobs
- HigherEdJobs Ecology and Forestry
- AcademicJobsOnline
- Academic Keys Forestry
- Chronicle Ecology and Forestry
- Ecophys Jobs Postdoc
- SAF Career Center Faculty

## Academic job boards worth adding or keeping

For your target, the most useful additional boards beyond direct university HR pages are:
1. **HigherEdJobs** environmental science/ecology/forestry faculty pages
2. **Chronicle of Higher Education Jobs** ecology/forestry pages
3. **Academic Keys** forestry/ecology pages
4. **AcademicJobsOnline** for postdocs and some faculty postings
5. **Ecophys Jobs** for forest ecophysiology and adjacent postdocs
6. **SAF Career Center** when it is up
7. **Warnell Jobs** because it often republishes forestry and natural resources positions
8. **MSU Forestry careers page** as a supplement, but it is broader and not doctorate-only

## Texas A&M board

The public Texas A&M natural resources board is:
`https://jobs.rwfm.tamu.edu/`

Its public search pages expose results with published date, salary, education, location, and view pages with a full description, which makes it one of the strongest sources for this project.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --log-level INFO
```

That generates:
- `docs/data/jobs.json`
- `docs/index.html`
- `docs/app.js`
- `docs/styles.css`

## Local preview

```bash
python -m http.server 8000
```

Then open:
`http://localhost:8000/docs/`

## Publish on GitHub Pages

1. Push this repo to GitHub.
2. In the repo settings, enable **Pages**.
3. Set the build source to **Deploy from a branch**.
4. Choose the `main` branch and `/docs` folder.
5. The included GitHub Action will scrape and rebuild the site on a schedule.

## Important limitation

Some aggregators and university pages change markup. The Texas A&M and Warnell parsers are the best starting points in this repo. The broader academic boards use a generic parser and should be hardened source-by-source if you decide they are worth the maintenance cost.

## Ethics and practical use

- Keep the crawl frequency modest.
- Do not estimate salary from external knowledge. This repo only records salary when it appears in the posting text.
- Description cleaning is conservative. It removes obvious UI boilerplate but does not rewrite the listing.

