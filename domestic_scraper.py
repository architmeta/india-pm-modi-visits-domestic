#!/usr/bin/env python3
"""
PM India Domestic Visits Scraper
==================================
STEP 1 — Install (one time):
    pip install requests beautifulsoup4 pandas

STEP 2 — Run:
    python domestic_scraper.py

First run:  scrapes ALL 81 pages → saves pm_domestic_visits.csv
Every run after: checks page 1 only for new entries

OUTPUT COLUMNS:
  title          — Full original visit title
  state          — ONE state per row (multi-state visits are split)
  start_date     — e.g. "Mar 28, 2026"
  end_date       — e.g. "Mar 28, 2026"
  duration_days  — Number of days
  year           — 4-digit year
  multi_state    — YES if split from multi-state visit, NO otherwise
  source_url     — Page URL
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import re
import time
from datetime import datetime

OUTPUT_CSV  = Path("pm_domestic_visits.csv")
BASE_URL    = "https://www.pmindia.gov.in/en/pm-visits/?visittype=domestic_visit"
TOTAL_PAGES = 81

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":         "https://www.pmindia.gov.in/en/",
}

STATE_SEPARATORS = re.compile(r"\s*[,&]\s*|\s+and\s+", re.IGNORECASE)

# Date pattern seen on site: (Mar 28, 2026 - Mar 28, 2026)
DATE_PATTERN = re.compile(r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}")


def extract_states_from_title(title: str) -> list:
    """Split 'PM's visit to Assam & West Bengal' → ['Assam', 'West Bengal']"""
    match = re.search(r"visit to (.+?)(?:\s*\[|$)", title, re.IGNORECASE)
    if not match:
        return [title.strip()]
    destination = match.group(1).strip()
    parts = STATE_SEPARATORS.split(destination)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if parts else [destination]


def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str.strip(), "%b %d, %Y")
    except Exception:
        return None


def calculate_duration(start_str: str, end_str: str) -> int:
    start = parse_date(start_str)
    end   = parse_date(end_str)
    if start and end:
        return max(1, (end - start).days + 1)
    return 1


def extract_year(date_str: str) -> str:
    match = re.search(r"(\d{4})", date_str)
    return match.group(1) if match else "Unknown"


def fetch_page(url: str) -> BeautifulSoup:
    """Visit homepage first to collect cookies, then fetch target URL."""
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
    """One row per state. Multi-state visits flagged YES."""
    states   = extract_states_from_title(title)
    is_multi = "YES" if len(states) > 1 else "NO"
    duration = calculate_duration(start_date, end_date) if start_date else 1
    year     = extract_year(start_date) if start_date else "Unknown"
    return [
        {
            "title":         title,
            "state":         state,
            "start_date":    start_date,
            "end_date":      end_date,
            "duration_days": duration,
            "year":          year,
            "multi_state":   is_multi,
            "source_url":    source_url,
        }
        for state in states
    ]


def parse_visits_from_page(soup: BeautifulSoup, page_url: str) -> list:
    """
    The PMO domestic visits page shows entries like:

      PM's visit to Uttar Pradesh
      (Mar 28, 2026 - Mar 28, 2026)

    Each entry is typically inside an <li> or similar container.
    We find all anchors with visit titles, then grab the date
    from the surrounding text.
    """
    all_rows = []
    seen     = set()

    # Walk every anchor on the page
    for anchor in soup.find_all("a", href=True):
        title = anchor.get_text(strip=True)

        # Must contain "visit" and not be a nav/menu link
        if not title or "visit" not in title.lower():
            continue
        if len(title) < 10:   # skip tiny nav links like "Visit"
            continue
        if title in seen:
            continue
        seen.add(title)

        # Climb up the DOM to find the date — usually in a sibling or parent
        date_text = ""
        node = anchor.parent
        for _ in range(8):
            if node is None:
                break
            text = node.get_text(" ", strip=True)
            dates = DATE_PATTERN.findall(text)
            if dates:
                date_text = text
                break
            node = node.parent

        dates = DATE_PATTERN.findall(date_text)
        start_date = dates[0] if len(dates) >= 1 else ""
        end_date   = dates[1] if len(dates) >= 2 else start_date

        rows = split_into_rows(title, start_date, end_date, page_url)
        all_rows.extend(rows)

    return all_rows


def build_page_url(page_num: int) -> str:
    if page_num == 1:
        return BASE_URL
    return f"{BASE_URL}&page={page_num - 1}"


def scrape_all_pages() -> pd.DataFrame:
    all_rows = []
    for page_num in range(1, TOTAL_PAGES + 1):
        url = build_page_url(page_num)
        print(f"  Scraping page {page_num}/{TOTAL_PAGES}: {url}")
        try:
            soup = fetch_page(url)
            rows = parse_visits_from_page(soup, url)
            all_rows.extend(rows)
            print(f"    → {len(rows)} rows")
        except Exception as e:
            print(f"    ⚠  Page {page_num} failed: {e}")
        time.sleep(1.2)

    df = pd.DataFrame(all_rows)
    print(f"\n  Total rows scraped: {len(df)}")
    return df


def scrape_latest_page() -> pd.DataFrame:
    url = build_page_url(1)
    print(f"  Checking latest entries: {url}")
    soup = fetch_page(url)
    rows = parse_visits_from_page(soup, url)
    print(f"  → {len(rows)} rows on page 1")
    return pd.DataFrame(rows)


def sort_newest_first(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_sort_year"] = df["year"].apply(lambda y: int(y) if str(y).isdigit() else 0)
    df["_sort_date"] = pd.to_datetime(df["start_date"], format="%b %d, %Y", errors="coerce")
    df.sort_values(by=["_sort_year", "_sort_date"], ascending=[False, False],
                   inplace=True, na_position="last")
    df.drop(columns=["_sort_year", "_sort_date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def print_multi_state_summary(df: pd.DataFrame):
    if "multi_state" not in df.columns:
        return
    multi = df[df["multi_state"] == "YES"].copy()
    if multi.empty:
        print("\n  (No multi-state visits detected)")
        return
    print("\n" + "=" * 70)
    print("  DATA NOTE — MULTI-STATE VISITS")
    print("=" * 70)
    grouped = multi.groupby(["title", "start_date"])["state"].apply(list).reset_index()
    for _, row in grouped.iterrows():
        print(f"  {row['start_date']}  |  {row['title'][:55]}")
        print(f"  States: {' → '.join(row['state'])}\n")
    print("=" * 70)


# ─── COLUMNS present in every CSV — used to guard against KeyError ────────────
EXPECTED_COLS = ["title", "state", "start_date", "end_date",
                 "duration_days", "year", "multi_state", "source_url"]


def run():
    # Delete old CSV if it exists but is empty / missing the 'state' column
    # so we start fresh cleanly
    if OUTPUT_CSV.exists():
        try:
            check = pd.read_csv(OUTPUT_CSV, dtype=str, nrows=1)
            if "state" not in check.columns:
                print("⚠  Existing CSV is missing 'state' column — deleting and starting fresh.")
                OUTPUT_CSV.unlink()
        except Exception:
            OUTPUT_CSV.unlink()

    is_first_run = not OUTPUT_CSV.exists()

    if is_first_run:
        print(f"\n=== FIRST RUN — scraping all {TOTAL_PAGES} pages ===\n")
        df_all = scrape_all_pages()

        if df_all.empty:
            print("\n⚠  No data scraped. Possible causes:")
            print("   1. The site blocked the request — try again in a few minutes")
            print("   2. The page HTML structure has changed")
            return

        df_all.drop_duplicates(subset=["title", "state", "start_date"],
                               keep="last", inplace=True)
        df_all = sort_newest_first(df_all)
        df_all.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅  Saved {len(df_all)} rows → {OUTPUT_CSV.resolve()}")
        print_multi_state_summary(df_all)

    else:
        print("\n=== UPDATE RUN — checking page 1 for new entries ===\n")
        df_existing = pd.read_csv(OUTPUT_CSV, dtype=str).fillna("")
        df_latest   = scrape_latest_page()

        if df_latest.empty:
            print("\n✅  Nothing scraped from page 1. CSV is up to date.")
            return

        # Safe check — in case existing CSV somehow lacks state column
        for col in EXPECTED_COLS:
            if col not in df_existing.columns:
                df_existing[col] = ""

        existing_keys = set(zip(
            df_existing["title"].str.strip(),
            df_existing["state"].str.strip(),
            df_existing["start_date"].str.strip(),
        ))
        df_latest["_key"] = list(zip(
            df_latest["title"].str.strip(),
            df_latest["state"].str.strip(),
            df_latest["start_date"].str.strip(),
        ))
        df_new = df_latest[~df_latest["_key"].isin(existing_keys)].drop(columns=["_key"])

        if df_new.empty:
            print("\n✅  No new entries. CSV is up to date.")
        else:
            df_combined = pd.concat([df_new, df_existing], ignore_index=True)
            df_combined = sort_newest_first(df_combined)
            df_combined.to_csv(OUTPUT_CSV, index=False)
            print(f"\n✅  Added {len(df_new)} new rows. Total: {len(df_combined)}")
            print_multi_state_summary(df_new)

    print("\n--- Most recent 5 entries ---")
    df_view = pd.read_csv(OUTPUT_CSV, dtype=str)
    cols = [c for c in ["state", "title", "start_date", "year",
                         "duration_days", "multi_state"] if c in df_view.columns]
    print(df_view.head(5)[cols].to_string())


if __name__ == "__main__":
    run()
