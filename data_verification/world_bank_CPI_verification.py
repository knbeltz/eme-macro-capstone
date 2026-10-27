#!/usr/bin/env python3
"""Download World Bank GEM monthly data, January 2000–December 2019.

Uses only Python's standard library. Run: python3 download_gem.py
Monthly observations are used directly, without interpolation or aggregation
across countries. Missing observations are written as blank CSV cells.
Also saves United States headline CPI (not seasonally adjusted) separately
for the same months, using GEM indicator CPTOTNSXN (index, not inflation).
"""

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.worldbank.org/v2"
SOURCE = "15"  # Global Economic Monitor
COUNTRIES = {
    "BRA": "Brazil", "MEX": "Mexico", "CHL": "Chile",
    "COL": "Colombia", "PER": "Peru", "ZAF": "South Africa",
    "TUR": "Turkey", "POL": "Poland", "MYS": "Malaysia",
    "PHL": "Philippines", "THA": "Thailand",
}
INDICATORS = ("DPANUSSPB", "IPTOTSAKD")
US_CPI_INDICATOR = "CPTOTNSXN"
MONTHS = [f"{year}M{month:02d}" for year in range(2000, 2020)
          for month in range(1, 13)]


def fetch_json(url):
    """Retry temporary connection/server failures, with bounded timeouts."""
    for attempt in range(5):
        try:
            request = Request(url, headers={"User-Agent": "GEM-monthly-download/1.0"})
            with urlopen(request, timeout=90) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            if isinstance(exc, HTTPError) and exc.code < 500 and exc.code != 429:
                raise
            if attempt == 4:
                raise RuntimeError(f"Download failed: {url}") from exc
            time.sleep(2 ** attempt)


def fetch_pages(path, params):
    records, responses = [], []
    page = 1
    while True:
        url = f"{BASE_URL}/{path}?{urlencode(dict(params, format='json', per_page=10000, page=page))}"
        payload = fetch_json(url)
        if (not isinstance(payload, list) or len(payload) != 2
                or not isinstance(payload[0], dict) or "message" in payload[0]):
            raise RuntimeError(f"Unexpected World Bank response: {payload!r}")
        responses.append({"url": url, "response": payload})
        records.extend(payload[1] or [])
        if page >= int(payload[0]["pages"]):
            return records, responses
        page += 1


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "test_data_output" / "gem_output")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {}
    for indicator in (*INDICATORS, US_CPI_INDICATOR):
        items, _ = fetch_pages(f"indicator/{indicator}", {"source": SOURCE})
        if len(items) != 1 or str(items[0]["source"]["id"]) != SOURCE:
            raise RuntimeError(f"Could not identify GEM metadata for {indicator}")
        metadata[indicator] = items[0]

    records, raw = fetch_pages(
        f"country/{';'.join(COUNTRIES)}/indicator/{';'.join(INDICATORS)}",
        {"source": SOURCE, "date": "2000M01:2019M12"},
    )
    values = {}
    for record in records:
        # GEM can return an empty countryiso3code; country.id carries ISO3.
        country = record.get("countryiso3code") or record["country"]["id"]
        indicator, period = record["indicator"]["id"], record["date"]
        if country not in COUNTRIES or indicator not in INDICATORS or period not in MONTHS:
            raise RuntimeError(f"Unexpected country, series, or non-monthly date: {record!r}")
        key = (country, period, indicator)
        if key in values:
            raise RuntimeError(f"Duplicate observation: {key}")
        values[key] = record["value"]

    panel, coverage = [], []
    for country, name in COUNTRIES.items():
        for period in MONTHS:
            panel.append({"country_code": country, "country": name,
                          "month": period.replace("M", "-"),
                          **{indicator: values.get((country, period, indicator))
                             for indicator in INDICATORS}})
        for indicator in INDICATORS:
            present = [period for period in MONTHS
                       if values.get((country, period, indicator)) is not None]
            coverage.append({"country_code": country, "country": name,
                             "indicator": indicator, "expected_months": len(MONTHS),
                             "available_months": len(present),
                             "missing_months": len(MONTHS) - len(present),
                             "first_available": present[0].replace("M", "-") if present else "",
                             "last_available": present[-1].replace("M", "-") if present else ""})

    cpi_records, cpi_raw = fetch_pages(
        f"country/USA/indicator/{US_CPI_INDICATOR}",
        {"source": SOURCE, "date": "2000M01:2019M12"},
    )
    raw.extend(cpi_raw)
    cpi_values = {}
    for record in cpi_records:
        country = record.get("countryiso3code") or record["country"]["id"]
        period = record["date"]
        if (country != "USA" or record["indicator"]["id"] != US_CPI_INDICATOR
                or period not in MONTHS):
            raise RuntimeError(f"Unexpected US CPI observation: {record!r}")
        if period in cpi_values:
            raise RuntimeError(f"Duplicate US CPI observation: {period}")
        cpi_values[period] = record["value"]
    cpi_panel = [{"country_code": "USA", "country": "United States",
                  "month": period.replace("M", "-"),
                  US_CPI_INDICATOR: cpi_values.get(period)} for period in MONTHS]
    present = [period for period in MONTHS if cpi_values.get(period) is not None]
    coverage.append({"country_code": "USA", "country": "United States",
                     "indicator": US_CPI_INDICATOR, "expected_months": len(MONTHS),
                     "available_months": len(present),
                     "missing_months": len(MONTHS) - len(present),
                     "first_available": present[0].replace("M", "-") if present else "",
                     "last_available": present[-1].replace("M", "-") if present else ""})
    write_csv(args.output_dir / "usa_cpi_monthly_2000_2019.csv",
              ["country_code", "country", "month", US_CPI_INDICATOR], cpi_panel)
    write_csv(args.output_dir / "gem_monthly_2000_2019.csv",
              ["country_code", "country", "month", *INDICATORS], panel)
    write_csv(args.output_dir / "coverage.csv", list(coverage[0]), coverage)
    provenance = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                  "source_id": SOURCE, "indicators": metadata,
                  "raw_api_responses": raw}
    (args.output_dir / "metadata_and_raw.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(panel):,} country-month rows to {args.output_dir.resolve()}")
    print(f"Saved {len(cpi_panel)} United States monthly CPI rows")
    for row in coverage:
        print(f"{row['country_code']} {row['indicator']}: "
              f"{row['available_months']}/240 available; {row['missing_months']} missing")


if __name__ == "__main__":
    main()