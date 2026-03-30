# India PM Domestic Visits Data

Automated scraper that collects and tracks all domestic visits made by the
Prime Minister of India, sourced from the official PMO website.

**Data source:** https://www.pmindia.gov.in/en/pm-visits/?visittype=domestic_visit

---

## What makes this dataset useful

The official PMO domestic visits page lists visits as plain text entries. Some
visits are described by states, others by cities, and unlike foreign trips, no
cost data is mentioned. This scraper transforms that raw listing into a clean,
analysis-ready dataset by:

- **Normalising every visit to official states/UTs** — the scraper resolves
  geography so that each row’s `state` value is one of India’s 28 states or 8
  union territories (or marked as `Unknown` where the title cannot be safely
  resolved).
- **Organizing every visit by state** — each visit in the original source is
  listed with a title like “PM's visit to Rajasthan, Gujarat and Tamil Nadu”
  with no row-level geography. The scraper assigns a **state to every row**
  starting from the visit title.
- **Splitting multi-state visits** — a single trip covering multiple states
  becomes one row per state/UT, all linked by the same title and date.
- **Adding city-level context** — cities mentioned in visit titles are
  preserved in a separate `city` column, helping identify specific locations
  within a state even when only a city name (not a state) appears in the
  original listing.
- **Inferring states from city names** — where the PMO title mentions only a
  city (e.g. “Varanasi”, “Ahmedabad”), the scraper maps it to the correct
  state/UT using a maintained city–state dictionary.
- **Preserving chronology** — year and full period strings are parsed and
  stored as structured columns to allow temporal analysis.

> **Note on costs:** Unlike the international visits archive, the PMO domestic
> visits page does not publish trip costs or expenditure figures in the
> listing. Cost data is therefore not included in this dataset. Researchers
> requiring expenditure information should consult RTI filings or official
> Parliamentary records.

---

## What this repo contains

| File | Description |
|---|---|
| `domestic_scraper.py` | Python scraper — run this to collect data |
| `pm_domestic_visits.csv` | Output dataset — one row per state/UT per visit |
| `.github/workflows/india-pm-domestic-visits.yml` | Auto-runs the scraper on the 1st and 15th of every month |
| `.gitignore` | Keeps junk files out of the repo |

---

## CSV output columns

**Note:** The current scraper stores the full visit period as a single string.
If you need `start_date`, `end_date`, or `duration_days`, you can derive those
from `period` in a separate analysis script.

| Column | Description | Example |
|---|---|---|
| `serial_no` | Row order, most recent visit = 1 | 1 |
| `period` | Full date range string from the listing | Mar 13, 2026 - Mar 14, 2026 |
| `year` | 4-digit year extracted from the period | 2026 |
| `state` | One of 28 states or 8 UTs, or `Unknown` when unresolved | Assam |
| `city` | City mentioned in the visit title, if any | Guwahati |

---

## Data note — multi-state visits

When a single visit covers multiple states (e.g. “PM's visit to Rajasthan,
Gujarat, Tamil Nadu and Puducherry”), the scraper internally resolves all
mentioned locations and creates **one logical row per state/UT**.

> **For journalists and researchers:** Where a title clearly indicates a
> multi-state trip, all associated rows share the same `period` and `year`.
> The original period string is preserved unchanged from the PMO listing.
> Please verify the full itinerary and exact dates for each stop independently
> using official PMO press releases or MEA records before publishing.

---

## Known limitations and possible improvements

- **City coverage is partial.** Not all visit titles mention a city — some
  list only a state or broader region. The `city` column will be blank for
  those rows. A fuller, maintained city-to-state mapping layer would improve
  geographic precision over time.
- **No cost data.** The domestic visits listing does not include expenditure
  figures. This is a limitation of the source, not the scraper.
- **Unresolved locations.** For unusual, ambiguous, or historical place names
  not in the mapping dictionary, the `state` field is set to `Unknown` and the
  text is preserved in `city`. These rows can be corrected manually or by
  extending the mapping and re-running the scraper.
- **Serial numbers are positional.** `serial_no` reflects scrape order and will
  shift as new visits are added. Use `period + state + city` (or your own
  derived key) as a stable identifier for joins across different export dates.

---

## How to run it locally

**Step 1 — Install Python** (one time only)  
Download from [python.org](https://www.python.org/downloads/). On Windows,
check “Add Python to PATH” during installation.

**Step 2 — Install the required libraries** (one time only)

```bash
pip install requests beautifulsoup4 pandas
