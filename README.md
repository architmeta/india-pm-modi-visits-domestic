# India PM Domestic Visits Data

Automated scraper that collects and tracks all domestic visits made by the
Prime Minister of India, sourced from the official PMO website.

**Data source:** https://www.pmindia.gov.in/en/pm-visits/?visittype=domestic_visit

---

## What this repo contains

| File | Description |
|---|---|
| `domestic_scraper.py` | Python scraper — run this to collect data |
| `pm_domestic_visits.csv` | Output dataset — one row per state per visit |
| `.github/workflows/india-pm-domestic-visits.yml` | Auto-runs the scraper on the 1st and 15th of every month |
| `.gitignore` | Keeps junk files out of the repo |

---

## CSV output columns

| Column | Description | Example |
|---|---|---|
| `title` | Full original visit title from the PMO website | PM's visit to Assam & West Bengal |
| `state` | **One state per row** — multi-state visits are split | Assam |
| `start_date` | Start date of the visit | Mar 13, 2026 |
| `end_date` | End date of the visit | Mar 14, 2026 |
| `duration_days` | Number of days (inclusive) | 2 |
| `year` | 4-digit year extracted from date | 2026 |
| `multi_state` | YES if split from a multi-state visit, NO otherwise | YES |
| `source_url` | URL of the page this entry was scraped from | https://www.pmindia.gov.in/... |

---

## Data note — multi-state visits

When a single visit covers multiple states (e.g. "PM's visit to Rajasthan,
Gujarat, Tamil Nadu and Puducherry"), the scraper creates **one row per state**,
all sharing the same title and date string.

The `multi_state` column flags these rows as `YES`.

> **For journalists and researchers:** Rows marked `multi_state = YES` are part
> of a single trip. The original date string is preserved unchanged. Please verify
> the full itinerary and exact dates for each state independently using official
> PMO press releases or MEA records before publishing.

---

## How to run it locally

**Step 1 — Install Python** (one time only)
Download from [python.org](https://www.python.org/downloads/). On Windows,
check "Add Python to PATH" during installation.

**Step 2 — Install the required libraries** (one time only)
