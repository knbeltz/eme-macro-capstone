"""Download monthly FRED levels using Python's standard library.

Run from the project folder: python3 data_verification/FRED_data_test.py
Defaults to 2000-01 through 2019-12; override with --start and --end (YYYY-MM).
Uses published monthly series, without interpolation or frequency conversion.
"""

import argparse
import calendar
import csv
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

# Make the project package available when running this file directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eme_pipeline.settings import get_fred_api_key, FRED_KEY_PATTERN

BASE_URL = "https://api.stlouisfed.org/fred"
SERIES = {
    "FEDFUNDS": "Effective federal funds rate",
    "PCE": "Nominal personal consumption expenditures",
    "PCEC96": "Real personal consumption expenditures",
    "INDPRO": "Industrial production: total index",
    "CPIAUCSL": "Consumer price index: all urban consumers, all items",
    "LOANINV": "Bank credit, all commercial banks",
    "LOANS": "Loans and leases in bank credit, all commercial banks",
    "INVEST": "Securities in bank credit, all commercial banks",
}


def parse_month(value):
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise argparse.ArgumentTypeError("Use YYYY-MM")
    try:
        return date.fromisoformat(value + "-01")
    except ValueError:
        raise argparse.ArgumentTypeError("Use a valid month in YYYY-MM") from None


def month_range(start, end):
    current = start
    while current <= end:
        yield current.isoformat()[:7]
        if current.year == end.year and current.month == end.month:
            break
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


def fetch_json(endpoint, key, **params):
    url = f"{BASE_URL}/{endpoint}?" + urlencode(
        dict(params, api_key=key, file_type="json"))
    for attempt in range(5):
        try:
            with urlopen(url, timeout=60) as response:
                payload = json.load(response)
            if "error_code" in payload:
                raise RuntimeError("FRED returned an API error")
            return payload
        except HTTPError as exc:
            # Never include the request URL: it contains the API key.
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise RuntimeError(f"FRED request failed (HTTP {exc.code})") from None
        except (URLError, TimeoutError):
            if attempt == 4:
                raise RuntimeError("FRED connection failed after five attempts") from None
        time.sleep(2 ** attempt)


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def download(key, start, end, output_dir):
    months = list(month_range(start, end))
    last_day = end.replace(day=calendar.monthrange(end.year, end.month)[1])
    values, metadata, raw, coverage = {}, {}, {}, []
    for series_id in SERIES:
        info = fetch_json("series", key, series_id=series_id)["seriess"][0]
        if info["frequency_short"] != "M":
            raise RuntimeError(f"Expected monthly frequency for {series_id}")
        metadata[series_id] = info
        observations, pages, offset = [], [], 0
        while True:
            page = fetch_json(
                "series/observations", key, series_id=series_id,
                observation_start=start.isoformat(), observation_end=last_day.isoformat(),
                units="lin", sort_order="asc", limit=100000, offset=offset)
            batch = page["observations"]
            pages.append(page)
            observations.extend(batch)
            offset += len(batch)
            if offset >= int(page["count"]):
                break
            if not batch:
                raise RuntimeError(f"Incomplete pagination for {series_id}")
        column = {}
        for observation in observations:
            period = observation["date"][:7]
            if observation["date"] != period + "-01" or period not in months or period in column:
                raise RuntimeError(f"Unexpected or duplicate monthly date for {series_id}")
            value = observation["value"]
            if value != ".":
                float(value)  # Validate numeric values while preserving published precision.
            column[period] = "" if value == "." else value
        values[series_id], raw[series_id] = column, pages
        available = [month for month in months if column.get(month, "") != ""]
        coverage.append(dict(series_id=series_id, expected_months=len(months),
                             available_months=len(available), missing_months=len(months)-len(available),
                             first_available=available[0] if available else "",
                             last_available=available[-1] if available else ""))
        print(f"{series_id}: {len(available)}/{len(months)} months")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "fred_monthly.csv", ["month", *SERIES],
              ({"month": month, **{s: values[s].get(month, "") for s in SERIES}} for month in months))
    write_csv(output_dir / "coverage.csv", list(coverage[0]), coverage)
    provenance = dict(retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                      start_month=months[0], end_month=months[-1],
                      series_metadata=metadata, raw_api_responses=raw)
    (output_dir / "metadata_and_raw.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"Saved {len(months)} monthly rows to {output_dir.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=parse_month, default=parse_month("2000-01"))
    parser.add_argument("--end", type=parse_month, default=parse_month("2019-12"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "test_data_output" / "fred_output")
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must be on or before --end")
    key = get_fred_api_key()
    if not isinstance(key, str) or not re.fullmatch(FRED_KEY_PATTERN, key):
        parser.error("Set a valid FRED_API_KEY in the environment or run python3 setup_fred.py")
    try:
        download(key, args.start, args.end, args.output_dir)
    except (RuntimeError, ValueError, KeyError) as exc:
        parser.exit(1, f"Download failed: {exc}\n")


if __name__ == "__main__":
    main()