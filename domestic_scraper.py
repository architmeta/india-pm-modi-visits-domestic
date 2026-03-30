#!/usr/bin/env python3
"""
PM India Domestic Visits Scraper
==================================
STEP 1 — Install (one time):
    pip install requests beautifulsoup4 pandas

STEP 2 — Run:
    python domestic_scraper.py

First run: scrapes ALL 81 pages → saves pm_domestic_visits.csv
Every subsequent run: checks page 1 only for new entries

OUTPUT COLUMNS:
  title          — Full original visit title
  state          — ONE state per row (multi-state visits are split)
  start_date     — e.g. "Mar 28, 2026"
  end_date       — e.g. "Mar 28, 2026"
  duration_days  — Number of days (1 for single-day visits)
  year           — 4-digit year
  multi_state    — YES if split from a multi-state visit, NO otherwise
  source_url     — Page URL the entry came from

DATA NOTE — multi_state column:
  YES = this row was split from a single visit that covered multiple states.
        All rows from the same trip share the same title and date.
        Verify the full itinerary independently using PMO press releases.
  NO  = single state listed for this visit.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import re
import time
from datetime import datetime

# ─── Output file ──────────────────────────────────────────────────────────────
OUTPUT_CSV = Path("pm_domestic_visits.csv")

# ─── Base URL ─────────────────────────────────────────────────────────────────
BASE_URL = "https://www.pmindia.gov.in/en/pm-visits/?visittype=domestic_visit"

# ─── Total pages on the site (update if more are added) ──────────────────────
TOTAL_PAGES = 81

# ─── Browser headers ──────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.pmindia.gov.in/en/",
}

# ─── Separators used between multiple states in a title ──────────────────────
STATE_SEPARATORS = re.compile(r"\s*[,&]\s*|\s+and\s+", re.IGNORECASE)

# ─── Known Indian states/UTs for clean extraction ────────────────────────────
KNOWN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry", "Pondicherry",
    "Chandigarh", "Andaman and Nicobar", "Lakshadweep", "Dadra and Nagar Haveli",
    "Daman and Diu", "Keralam", "J&K",
]


def extract_states_from_title(title: str) -> list:
    """
    Extract the destination part from a title like
    "PM's visit to Assam & West Bengal" → ["Assam", "West Bengal"]

    Strategy:
    1. Grab everything after "visit to"
    2. Split on separators (comma, &, and)
    3. Strip whitespace and filter empties
    4. If nothing found, return the full destination as one item
    """
    # Grab the destination portion after "visit to"
    match = re.search(r"visit to (.+?)(?:\s*\[|$)", title, re.IGNORECASE)
    if not match:
        return [title.strip()]

    destination = match.group(1).strip()

    # Split on separators
    parts = STATE_SEPARATORS.split(destination)
    parts = [p.strip() for p in parts if p.strip()]

    return parts if parts else [destination]


def parse_date(date_str: str):
    """Parse 'Mar 28, 2026' → datetime object."""
    try:
        return datetime.strptime(date_str.strip(), "%b %d, %Y")
    except Exception:
        return None


def calculate_duration(start_str: str, end_str: str) -> int:
    """Return inclusive day count between two date strings."""
    start = parse_date(start_str)
    end   = parse_date(end_str)
    if start and end:
        return max(1, (end - start).days + 1)
    return 1


def extract_year(date_str: str) -> str:
    """Pull a 4-digit year from any date string."""
    match = re.search(r"(\d{4})", date_str)
    return match.group(1) if match else "Unknown"


def fetch_page(url: str) -> BeautifulSoup:
    """Open a session via homepage (for cookies), then fetch the target URL."""
    session = requests.Session()
    try:
        session.get("https://www.pmindia.gov.in/en/", headers=HEADERS, timeout=30)
    except Exception:
        pass
    time.sleep(1)
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def split_into_rows(title: str, start_date: str, end_date: str, source_url: str) -> list:
    """
    KEY FUNCTION — one state per row.

    If a visit title mentions multiple states (e.g. "Assam & West Bengal"),
    this creates one row per state, all sharing the same title and dates.
    The multi_state flag = YES for those rows, NO for single-state visits.

    Example input:  "PM's visit to Rajasthan, Gujarat, Tamil Nadu and Puducherry"
    Example output: 4 rows, one for each state, multi_state = YES
    """
    states     = extract_states_from_title(title)
    is_multi   = "YES" if len(states) > 1 else "NO"
    duration   = calculate_duration(start_date, end_date) if start_date else 1
    year       = extract_year(start_date) if start_date else "Unknown"

    rows = []
    for state in states:
        rows.append({
            "title":         title,
            "state":         state,          # ← ONE state per row
            "start_date":    start_date,
            "end_date":      end_date,
            "duration_days": duration,
            "year":          year,
            # DATA NOTE:
            # multi_state = YES means this state was part of a multi-state trip.
            # All rows from the same trip share the same title and date string.
            # Verify the full itinerary independently via PMO press releases.
            "multi_state":   is_multi,
            "source_url":    source_url,
        })
    return rows


def parse_visits_from_page(soup: BeautifulSoup, page_url: str) -> list:
    """
    Parse all visit entries from one page of the domestic visits listing.
    Tries multiple CSS selectors to be resilient to site redesigns.
    """
    all_rows = []

    # Try standard list-item selectors first
    items = soup.select("ul.view-content li, .view-content .views-row, li.views-row")

    # Fallback: any <li> that has a link and a date
    if not items:
        items = soup.find_all("li")

    for item in items:
        anchor = item.find("a")
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        if not title or "visit" not in title.lower():
            continue

        # Find the date string — look for spans/divs with date patterns
        date_text = ""
        for elem in item.find_all(["span", "div", "p"]):
            text = elem.get_text(strip=True)
            if re.search(r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}", text):
                date_text = text
                break

        # Extract start and end dates
        date_matches = re.findall(r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}", date_text)
        start_date = date_matches[0] if len(date_matches) >= 1 else ""
        end_date   = date_matches[1] if len(date_matches) >= 2 else start_date

        # Split into one row per state
        rows = split_into_rows(title, start_date, end_date, page_url)
        all_rows.extend(rows)

    return all_rows


def build_page_url(page_num: int) -> str:
    """
    Page 1 = base URL (no page param)
    Page 2+ = base URL + &page=N (0-indexed)
    """
    if page_num == 1:
        return BASE_URL
    return f"{BASE_URL}&page={page_num - 1}"


def scrape_all_pages() -> pd.DataFrame:
    """Scrape all TOTAL_PAGES pages and return combined DataFrame."""
    all_rows = []
    for page_num in range(1, TOTAL_PAGES + 1):
        url = build_page_url(page_num)
        print(f"  Scraping page {page_num}/{TOTAL_PAGES}: {url}")
        try:
            soup = fetch_page(url)
            rows = parse_visits_from_page(soup, url)
            all_rows.extend(rows)
            print(f"    → {len(rows)} rows (after state splitting)")
        except Exception as e:
            print(f"    ⚠  Page {page_num} failed: {e}")
        time.sleep(1.2)

    df = pd.DataFrame(all_rows)
    print(f"\n  Total rows scraped: {len(df)}")
    return df


def scrape_latest_page() -> pd.DataFrame:
    """Scrape only page 1 for incremental updates."""
    url = build_page_url(1)
    print(f"  Checking latest entries: {url}")
    soup = fetch_page(url)
    rows = parse_visits_from_page(soup, url)
    print(f"  → {len(rows)} rows on page 1")
    return pd.DataFrame(rows)


def sort_newest_first(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by year descending, then start_date descending."""
    df = df.copy()
    df["_sort_year"] = df["year"].apply(lambda y: int(y) if str(y).isdigit() else 0)
    df["_sort_date"] = pd.to_datetime(df["start_date"], format="%b %d, %Y", errors="coerce")
    df.sort_values(
        by=["_sort_year", "_sort_date"],
        ascending=[False, False],
        inplace=True,
        na_position="last",
    )
    df.drop(columns=["_sort_year", "_sort_date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def print_multi_state_summary(df: pd.DataFrame):
    """Print journalist note listing all multi-state trips."""
    multi = df[df["multi_state"] == "YES"].copy() if "multi_state" in df.columns else pd.DataFrame()
    if multi.empty:
        print("\n  (No multi-state visits detected)")
        return

    print("\n" + "=" * 70)
    print("  DATA NOTE — MULTI-STATE VISITS DETECTED")
    print("=" * 70)
    print(
        "  These visits listed multiple states in one title.\n"
        "  Each state has its own row with the SAME date string.\n"
        "  Verify independently using PMO press releases.\n"
        "  Column 'multi_state' = YES flags these rows.\n"
    )
    grouped = multi.groupby(["title", "start_date"])["state"].apply(list).reset_index()
    for _, row in grouped.iterrows():
        states_str = " → ".join(row["state"])
        print(f"  {row['start_date']}  |  {row['title'][:55]}")
        print(f"  States: {states_str}\n")
    print("=" * 70)


def run():
    is_first_run = not OUTPUT_CSV.exists()

    if is_first_run:
        print(f"\n=== FIRST RUN — scraping all {TOTAL_PAGES} pages ===\n")
        df_all = scrape_all_pages()

        if df_all.empty:
            print("\n⚠  No data scraped. Page structure may have changed.")
            print("   Check parse_visits_from_page() and update CSS selectors.")
            return

        df_all.drop_duplicates(subset=["title", "state", "start_date"], keep="last", inplace=True)
        df_all = sort_newest_first(df_all)
        df_all.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅  Saved {len(df_all)} rows → {OUTPUT_CSV.resolve()}")
        print_multi_state_summary(df_all)

    else:
        print("\n=== UPDATE RUN — checking page 1 for new entries ===\n")
        df_existing = pd.read_csv(OUTPUT_CSV, dtype=str).fillna("")
        df_latest   = scrape_latest_page()

        if df_latest.empty:
            print("\n✅  Nothing on page 1. CSV is up to date.")
            return

        existing_keys = set(
            zip(
                df_existing["title"].str.strip(),
                df_existing["state"].str.strip(),
                df_existing["start_date"].str.strip(),
            )
        )
        df_latest["_key"] = list(
            zip(
                df_latest["title"].str.strip(),
                df_latest["state"].str.strip(),
                df_latest["start_date"].str.strip(),
            )
        )
        df_new = df_latest[~df_latest["_key"].isin(existing_keys)].drop(columns=["_key"])

        if df_new.empty:
            print("\n✅  No new entries. CSV is up to date.")
        else:
            df_combined = pd.concat([df_new, df_existing], ignore_index=True)
            df_combined = sort_newest_first(df_combined)
            df_combined.to_csv(OUTPUT_CSV, index=False)
            print(f"\n✅  Added {len(df_new)} new rows. Total: {len(df_combined)} → {OUTPUT_CSV.resolve()}")
            print_multi_state_summary(df_new)

    print("\n--- Most recent 5 entries ---")
    print(
        pd.read_csv(OUTPUT_CSV, dtype=str).head(5)[
            ["state", "title", "start_date", "year", "duration_days", "multi_state"]
        ].to_string()
    )


if __name__ == "__main__":
    run()
