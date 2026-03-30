#!/usr/bin/env python3
"""
PM India Domestic Visits Scraper
Install:  pip install requests beautifulsoup4 pandas
Run:      python domestic_scraper.py

OUTPUT COLUMNS:
  serial_no  — website chronological order (1 = most recent)
  period     — "Mar 28, 2026 - Mar 28, 2026"
  year       — 2026
  state      — State or UT name
  city       — City/town name (blank when a state was listed directly)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import re
import time

OUTPUT_CSV  = Path("pm_domestic_visits.csv")
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

DATE_RE   = re.compile(
    r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\s*[-–]\s*([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})"
)
STATE_SEP = re.compile(r"\s*&\s*|\s+and\s+", re.IGNORECASE)

# ── All Indian States and UTs ─────────────────────────────────────────────────
STATES = {s.lower(): s for s in [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Jammu", "Kashmir", "Ladakh",
    "Puducherry", "Pondicherry", "Chandigarh", "Andaman and Nicobar",
    "Lakshadweep", "Keralam", "Dadra and Nagar Haveli", "Daman and Diu",
]}

# ── City → State mapping ──────────────────────────────────────────────────────
CITY_TO_STATE = {
    # Andhra Pradesh
    "visakhapatnam": "Andhra Pradesh", "vizag": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh", "amaravati": "Andhra Pradesh",
    "tirupati": "Andhra Pradesh", "guntur": "Andhra Pradesh",
    "nellore": "Andhra Pradesh", "kurnool": "Andhra Pradesh",
    # Arunachal Pradesh
    "itanagar": "Arunachal Pradesh",
    # Assam
    "guwahati": "Assam", "dispur": "Assam", "jorhat": "Assam",
    "dibrugarh": "Assam", "silchar": "Assam", "tezpur": "Assam",
    # Bihar
    "patna": "Bihar", "gaya": "Bihar", "muzaffarpur": "Bihar",
    "bhagalpur": "Bihar", "darbhanga": "Bihar", "nalanda": "Bihar",
    "bodh gaya": "Bihar",
    # Chhattisgarh
    "raipur": "Chhattisgarh", "bilaspur": "Chhattisgarh",
    "durg": "Chhattisgarh", "bhilai": "Chhattisgarh",
    # Delhi / NCR
    "new delhi": "Delhi", "delhi": "Delhi",
    "noida": "Uttar Pradesh", "greater noida": "Uttar Pradesh",
    "gurgaon": "Haryana", "gurugram": "Haryana", "faridabad": "Haryana",
    # Goa
    "panaji": "Goa", "panjim": "Goa", "margao": "Goa", "vasco": "Goa",
    # Gujarat
    "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
    "rajkot": "Gujarat", "gandhinagar": "Gujarat", "bhavnagar": "Gujarat",
    "jamnagar": "Gujarat", "anand": "Gujarat", "morbi": "Gujarat",
    "amreli": "Gujarat", "somnath": "Gujarat", "dwarka": "Gujarat",
    "bharuch": "Gujarat", "navsari": "Gujarat", "vapi": "Gujarat",
    "dahod": "Gujarat", "kevadia": "Gujarat", "statue of unity": "Gujarat",
    # Haryana
    "ambala": "Haryana", "hisar": "Haryana", "panipat": "Haryana",
    "rohtak": "Haryana", "sonipat": "Haryana", "karnal": "Haryana",
    "kurukshetra": "Haryana", "surajkund": "Haryana",
    # Himachal Pradesh
    "shimla": "Himachal Pradesh", "manali": "Himachal Pradesh",
    "dharamsala": "Himachal Pradesh", "dharamshala": "Himachal Pradesh",
    "mandi": "Himachal Pradesh", "hamirpur": "Himachal Pradesh",
    "solan": "Himachal Pradesh", "una": "Himachal Pradesh",
    # Jharkhand
    "ranchi": "Jharkhand", "jamshedpur": "Jharkhand",
    "dhanbad": "Jharkhand", "bokaro": "Jharkhand", "hazaribagh": "Jharkhand",
    # Karnataka
    "bengaluru": "Karnataka", "bangalore": "Karnataka",
    "mysuru": "Karnataka", "mysore": "Karnataka",
    "mangaluru": "Karnataka", "mangalore": "Karnataka",
    "hubli": "Karnataka", "dharwad": "Karnataka", "belagavi": "Karnataka",
    "kalaburagi": "Karnataka", "tumkur": "Karnataka", "shivamogga": "Karnataka",
    # Kerala
    "thiruvananthapuram": "Kerala", "trivandrum": "Kerala",
    "kochi": "Kerala", "cochin": "Kerala", "kozhikode": "Kerala",
    "calicut": "Kerala", "thrissur": "Kerala", "kannur": "Kerala",
    "kollam": "Kerala", "alappuzha": "Kerala", "palakkad": "Kerala",
    "kasaragod": "Kerala", "trippunithura": "Kerala", "varkala": "Kerala",
    # Madhya Pradesh
    "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh", "gwalior": "Madhya Pradesh",
    "ujjain": "Madhya Pradesh", "sagar": "Madhya Pradesh",
    "rewa": "Madhya Pradesh", "satna": "Madhya Pradesh",
    "omkareshwar": "Madhya Pradesh", "maheshwar": "Madhya Pradesh",
    "amarkantak": "Madhya Pradesh", "bhabra": "Madhya Pradesh",
    "mhow": "Madhya Pradesh", "sarangpur": "Madhya Pradesh",
    "sehore": "Madhya Pradesh", "tekanpur": "Madhya Pradesh",
    # Maharashtra
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra",
    "nashik": "Maharashtra", "aurangabad": "Maharashtra",
    "solapur": "Maharashtra", "kolhapur": "Maharashtra", "thane": "Maharashtra",
    "navi mumbai": "Maharashtra", "amravati": "Maharashtra",
    "latur": "Maharashtra", "nanded": "Maharashtra", "jalgaon": "Maharashtra",
    "wardha": "Maharashtra", "shirdi": "Maharashtra",
    "ins vikrant": "Maharashtra", "maharastra": "Maharashtra",
    "sona": "Maharashtra",
    # Manipur
    "imphal": "Manipur",
    # Meghalaya
    "shillong": "Meghalaya",
    # Mizoram
    "aizawl": "Mizoram",
    # Nagaland
    "kohima": "Nagaland", "dimapur": "Nagaland",
    # Odisha
    "bhubaneswar": "Odisha", "bhubaneshwar": "Odisha",
    "cuttack": "Odisha", "puri": "Odisha",
    "rourkela": "Odisha", "berhampur": "Odisha", "sambalpur": "Odisha",
    "konark": "Odisha", "khurda": "Odisha", "koraput": "Odisha",
    # Punjab
    "amritsar": "Punjab", "ludhiana": "Punjab", "jalandhar": "Punjab",
    "patiala": "Punjab", "pathankot": "Punjab",
    "ropar": "Punjab", "rupnagar": "Punjab",
    "bhatinda": "Punjab", "faridkot": "Punjab",
    # Rajasthan
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "udaipur": "Rajasthan",
    "kota": "Rajasthan", "ajmer": "Rajasthan", "bikaner": "Rajasthan",
    "alwar": "Rajasthan", "bharatpur": "Rajasthan", "sikar": "Rajasthan",
    "barmer": "Rajasthan", "jaisalmer": "Rajasthan", "nathdwara": "Rajasthan",
    "churu": "Rajasthan", "jhunjhunu": "Rajasthan",
    "pokhran": "Rajasthan", "tonk": "Rajasthan",
    # Sikkim
    "gangtok": "Sikkim",
    # Tamil Nadu
    "chennai": "Tamil Nadu", "madras": "Tamil Nadu",
    "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "tiruchirappalli": "Tamil Nadu", "trichy": "Tamil Nadu",
    "tiruchy": "Tamil Nadu", "salem": "Tamil Nadu", "tirunelveli": "Tamil Nadu",
    "vellore": "Tamil Nadu", "erode": "Tamil Nadu", "thoothukudi": "Tamil Nadu",
    "kancheepuram": "Tamil Nadu", "thanjavur": "Tamil Nadu",
    "rameswaram": "Tamil Nadu", "ooty": "Tamil Nadu",
    "hosur": "Tamil Nadu", "kanyakumari": "Tamil Nadu",
    "vedaranyam": "Tamil Nadu",
    # Telangana
    "hyderabad": "Telangana", "warangal": "Telangana",
    "nizamabad": "Telangana", "karimnagar": "Telangana",
    "secunderabad": "Telangana", "gajwel": "Telangana",
    # Tripura
    "agartala": "Tripura",
    # Uttar Pradesh
    "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
    "agra": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
    "banaras": "Uttar Pradesh", "kashi": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh", "allahabad": "Uttar Pradesh",
    "meerut": "Uttar Pradesh", "bareilly": "Uttar Pradesh",
    "aligarh": "Uttar Pradesh", "moradabad": "Uttar Pradesh",
    "ghaziabad": "Uttar Pradesh", "mathura": "Uttar Pradesh",
    "vrindavan": "Uttar Pradesh", "ayodhya": "Uttar Pradesh",
    "gorakhpur": "Uttar Pradesh", "jhansi": "Uttar Pradesh",
    "mirzapur": "Uttar Pradesh", "sonbhadra": "Uttar Pradesh",
    "rae bareli": "Uttar Pradesh", "lakhimpur": "Uttar Pradesh",
    "sitapur": "Uttar Pradesh", "balrampur": "Uttar Pradesh",
    "kushinagar": "Uttar Pradesh", "sarnath": "Uttar Pradesh",
    "amethi": "Uttar Pradesh", "amroha": "Uttar Pradesh",
    "badaun": "Uttar Pradesh", "baghpat": "Uttar Pradesh",
    "bahraich": "Uttar Pradesh", "ballia": "Uttar Pradesh",
    "barabanki": "Uttar Pradesh", "basti": "Uttar Pradesh",
    "bijnor": "Uttar Pradesh", "deoria": "Uttar Pradesh",
    "fatehpur": "Uttar Pradesh", "gonda": "Uttar Pradesh",
    "hardoi": "Uttar Pradesh", "jaunpur": "Uttar Pradesh",
    "kannauj": "Uttar Pradesh", "maharajganj": "Uttar Pradesh",
    "mahoba": "Uttar Pradesh", "mau": "Uttar Pradesh",
    "orai": "Uttar Pradesh", "phoolpur": "Uttar Pradesh",
    "saharanpur": "Uttar Pradesh", "sant kabir nagar": "Uttar Pradesh",
    "shahjahanpur": "Uttar Pradesh",
    # Uttarakhand
    "dehradun": "Uttarakhand", "haridwar": "Uttarakhand",
    "rishikesh": "Uttarakhand", "nainital": "Uttarakhand",
    "mussoorie": "Uttarakhand", "roorkee": "Uttarakhand",
    "pithoragarh": "Uttarakhand", "uttarkashi": "Uttarakhand",
    "kedarnath": "Uttarakhand", "badrinath": "Uttarakhand",
    "rudrapur": "Uttarakhand",
    # West Bengal
    "kolkata": "West Bengal", "calcutta": "West Bengal",
    "howrah": "West Bengal", "siliguri": "West Bengal",
    "durgapur": "West Bengal", "asansol": "West Bengal",
    "darjeeling": "West Bengal", "cooch behar": "West Bengal",
    # Union Territories
    "chandigarh": "Chandigarh",
    "puducherry": "Puducherry", "pondicherry": "Puducherry",
    "port blair": "Andaman and Nicobar",
    "andaman": "Andaman and Nicobar", "nicobar": "Andaman and Nicobar",
    "silvassa": "Dadra and Nagar Haveli",
    "dadra": "Dadra and Nagar Haveli", "nagar haveli": "Dadra and Nagar Haveli",
    "diu": "Daman and Diu", "daman": "Daman and Diu",
    # Jammu and Kashmir / Ladakh
    "srinagar": "Jammu and Kashmir",
    "jammu": "Jammu and Kashmir",
    "akhnoor": "Jammu and Kashmir", "chanderkote": "Jammu and Kashmir",
    "gurez valley": "Jammu and Kashmir", "katra": "Jammu and Kashmir",
    "kashmir": "Jammu and Kashmir", "kashmir valley": "Jammu and Kashmir",
    "leh": "Ladakh", "kargil": "Ladakh",
    # Bihar cities (additional)
    "ara": "Bihar", "banka": "Bihar", "bhabua": "Bihar",
    "buxar": "Bihar", "jehanabad": "Bihar", "katihar": "Bihar",
    "motihari": "Bihar", "nawada": "Bihar", "patna sahib": "Bihar",
    "saharsa": "Bihar", "sasaram": "Bihar", "siwan": "Bihar",
    # Jharkhand cities (additional)
    "dumka": "Jharkhand", "khunti": "Jharkhand", "sahibganj": "Jharkhand",
    # Arunachal Pradesh (additional)
    "aalo": "Arunachal Pradesh",
    # Andhra Pradesh (additional)
    "amaravathi": "Andhra Pradesh",
    # Chhattisgarh (additional)
    "raigarh": "Chhattisgarh",
    # Gujarat (additional)
    "kutch": "Gujarat",
}


def is_state(name: str) -> bool:
    return name.lower() in STATES


def get_state_for_city(city: str) -> str:
    return CITY_TO_STATE.get(city.lower().strip(), "")


def clean_name(raw: str) -> str:
    name = re.split(r"[\(\[0-9]", raw)[0].strip()
    name = name.strip(".,;:-").strip()
    if not re.match(r"^[A-Za-z\s\-']+$", name):
        return ""
    return name.strip()


def get_locations_from_title(title: str) -> list:
    m = re.search(r"visit to (.+?)(?:\s*\[|$)", title, re.IGNORECASE)
    if not m:
        return []
    dest = re.sub(r"\[.*?\]", "", m.group(1)).strip()
    parts = STATE_SEP.split(dest)

    locations = []
    for part in parts:
        name = clean_name(part.strip())
        if not name or len(name) < 2:
            continue
        if is_state(name):
            locations.append({
                "state": STATES[name.lower()],
                "city":  "",
            })
        else:
            state_for_city = get_state_for_city(name)
            locations.append({
                "state": state_for_city,
                "city":  name.title(),
            })
    return locations


def get_soup(url: str) -> BeautifulSoup:
    s = requests.Session()
    try:
        s.get("https://www.pmindia.gov.in/en/", headers=HEADERS, timeout=30)
    except Exception:
        pass
    time.sleep(1)
    r = s.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def parse_page(soup: BeautifulSoup, page_url: str) -> list:
    rows = []
    seen = set()

    body = (
        soup.find("div", class_=re.compile(r"view-content|region-content", re.I))
        or soup.find("main")
        or soup.body
    )
    if not body:
        return rows

    for a in body.find_all("a", href=True):
        title = a.get_text(strip=True)
        if not title or "visit" not in title.lower() or len(title) < 15:
            continue
        clean_title = re.sub(r"\s*\[.*?\]", "", title).strip()
        if clean_title in seen:
            continue
        seen.add(clean_title)

        container = a.parent
        period = ""
        for _ in range(6):
            if container is None:
                break
            m = DATE_RE.search(container.get_text(" "))
            if m:
                period = f"{m.group(1).strip()} - {m.group(2).strip()}"
                break
            container = container.parent

        if not period:
            continue

        yr_m = re.search(r"(\d{4})", period)
        year = yr_m.group(1) if yr_m else "Unknown"

        locations = get_locations_from_title(clean_title)
        if not locations:
            continue

        for loc in locations:
            rows.append({
                "period": period,
                "year":   year,
                "state":  loc["state"],
                "city":   loc["city"],
            })

    return rows


def page_url(n: int) -> str:
    return f"https://www.pmindia.gov.in/en/pm-visits/page/{n}/?visittype=domestic_visit"


def scrape_all() -> pd.DataFrame:
    all_rows = []
    for n in range(1, TOTAL_PAGES + 1):
        url = page_url(n)
        print(f"  Page {n:>2}/{TOTAL_PAGES}  →  ", end="", flush=True)
        try:
            soup = get_soup(url)
            rows = parse_page(soup, url)
            all_rows.extend(rows)
            print(f"{len(rows)} rows")
        except Exception as e:
            print(f"FAILED: {e}")
        time.sleep(1.2)
    print(f"\n  Grand total: {len(all_rows)} rows")
    return pd.DataFrame(all_rows)


def scrape_latest() -> pd.DataFrame:
    soup = get_soup(page_url(1))
    rows = parse_page(soup, page_url(1))
    print(f"  Page 1 → {len(rows)} rows")
    return pd.DataFrame(rows)


def add_serial_numbers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "serial_no", range(1, len(df) + 1))
    return df


def run(force_full: bool = False):
    if OUTPUT_CSV.exists():
        try:
            check = pd.read_csv(OUTPUT_CSV, nrows=1)
            required = {"period", "year", "state", "city"}
            if not required.issubset(set(check.columns)):
                print("⚠  Old CSV has wrong columns — deleting and re-scraping.")
                OUTPUT_CSV.unlink()
        except Exception:
            OUTPUT_CSV.unlink()

    first_run = not OUTPUT_CSV.exists() or force_full

    if first_run:
        print(f"\n=== FULL SCRAPE — all {TOTAL_PAGES} pages ===\n")
        df = scrape_all()
        if df.empty:
            print("\n⚠  Nothing scraped. Try again in a few minutes.")
            return
        df.drop_duplicates(subset=["period", "state", "city"], keep="last", inplace=True)
        df = add_serial_numbers(df)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅  Saved {len(df)} rows → {OUTPUT_CSV.resolve()}")

    else:
        print("\n=== UPDATE — checking page 1 ===\n")
        existing = pd.read_csv(OUTPUT_CSV, dtype=str).fillna("")
        latest   = scrape_latest()
        if latest.empty:
            print("\n✅  Nothing new.")
            return

        for col in ["period", "state", "city"]:
            if col not in existing.columns:
                existing[col] = ""

        old_keys = set(zip(
            existing["period"].str.strip(),
            existing["state"].str.strip(),
            existing["city"].str.strip(),
        ))
        latest["_k"] = list(zip(
            latest["period"].str.strip(),
            latest["state"].str.strip(),
            latest["city"].str.strip(),
        ))
        new_rows = latest[~latest["_k"].isin(old_keys)].drop(columns=["_k"])

        if new_rows.empty:
            print("\n✅  No new entries.")
        else:
            combined = pd.concat(
                [new_rows, existing.drop(columns=["serial_no"], errors="ignore")],
                ignore_index=True
            )
            combined.drop_duplicates(subset=["period", "state", "city"],
                                     keep="first", inplace=True)
            combined = add_serial_numbers(combined)
            combined.to_csv(OUTPUT_CSV, index=False)
            print(f"\n✅  Added {len(new_rows)} rows. Total: {len(combined)}")

    print("\n--- Most recent 5 entries ---")
    df_show = pd.read_csv(OUTPUT_CSV, dtype=str)
    print(df_show.head(5)[["serial_no", "period", "year", "state", "city"]].to_string())


if __name__ == "__main__":
    run(force_full=True)
