# India PM Domestic Visits Data

Automated scraper that collects and tracks all domestic visits made by the
Prime Minister of India, sourced from the official PMO website.

**Data source:** https://www.pmindia.gov.in/en/pm-visits/?visittype=domestic_visit

---

## What makes this dataset useful

The official PMO domestic visits page lists visits as plain text entries. 
Some visits have state-level breakdown others by cities. Unlike foreign trips,
no cost data is mentioned. This scraper transforms that raw listing into a clean,
analysis-ready dataset by:

- **Organizing every visit by state** — each visit in the original source is
  listed with a title like "PM's visit to Rajasthan, Gujarat and Tamil Nadu"
  with no row-level geography. This scraper assigns a **state to every row**,
  starting from the visit title.
- **Splitting multi-state visits** — a single trip covering multiple states
  becomes one row per state, all linked by the same title and date.
- **Adding city-level context** — cities mentioned in visit titles are
  preserved in the data, helping identify specific locations within a state
  even when only a city name (not a state) appears in the original listing.
- **Inferring states from city names** — where the PMO title mentions only a
  city (e.g. "Varanasi", "Ahmedabad"), the scraper maps it to the correct
  state automatically.
- **Preserving chronology** — year, start date, end date, and duration are
  all extracted and stored as structured columns.

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
| `pm_domestic_visits.csv` | Output dataset — one row per state per visit |
| `.github/workflows/india-pm-domestic-visits.yml` | Auto-runs the scraper on the 1st and 15th of every month |
| `.gitignore` | Keeps junk files out of the repo |

---

## CSV output columns

| Column | Description | Example |
|---|---|---|
| `title` | Full original visit title from the PMO website | PM's visit to Assam & West Bengal |
| `state` | **One state per row** — multi-state visits are split | Assam |
| `city` | City mentioned in the visit title, if any | Guwahati |
| `start_date` | Start date of the visit | Mar 13, 2026 |
| `end_date` | End date of the visit | Mar 14, 2026 |
| `duration_days` | Number of days (inclusive) | 2 |
| `year` | 4-digit year extracted from date | 2026 |
| `multi_state` | YES if split from a multi-state visit, NO otherwise | YES |
| `source_url` | URL of the page this entry was scraped from | https://www.pmindia.gov.in/en/pm-visits/?visittype=domestic_visit; https://www.pmindia.gov.in/en/pm-visits/page/2/?visittype=domestic_visit; untill page 81|

---

## Data note — multi-state visits

When a single visit covers multiple states (e.g. "PM's visit to Rajasthan,
Gujarat, Tamil Nadu and Puducherry"), the scraper creates **one row per state**,
all sharing the same title and date string.

The `multi_state` column flags these rows as `YES`.

> **For journalists and researchers:** Rows marked `multi_state = YES` are part
> of a single trip. The original date string is preserved unchanged. Please
> verify the full itinerary and exact dates for each state independently using
> official PMO press releases or MEA records before publishing.

---

## Known limitations and possible improvements

- **City coverage is partial.** Not all visit titles mention a city — some
  list only a state name. The `city` column will be blank for those rows.
  A fuller city-to-state mapping layer would improve geographic precision.
- **No cost data.** The domestic visits listing does not include expenditure
  figures. This is a limitation of the source, not the scraper.
- **State inference may miss edge cases.** For unusual or historical city
  names not in the mapping dictionary, the `state` field may fall back to
  the raw title text. These can be corrected manually or by extending the
  mapping.

---

## How to run it locally

**Step 1 — Install Python** (one time only)
Download from [python.org](https://www.python.org/downloads/). On Windows,
check "Add Python to PATH" during installation.

**Step 2 — Install the required libraries** (one time only)

```bash
pip install requests beautifulsoup4 pandas
