#!/usr/bin/env python3
"""Verify IMF ARG.CPI._T.IX.M coverage; export January 2000–December 2019.

Run: python3 verify_argentina_cpi.py
Uses only the Python standard library. Fetches the full series without a date
filter so the earliest observation is not imposed by the request. Missing
months remain blank; no interpolation, splicing, or inflation conversion.
"""

import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SERIES = "ARG.CPI._T.IX.M"
URL = f"https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/+/{SERIES}"


def fetch():
    for attempt in range(4):
        try:
            req = Request(URL, headers={"Accept": "application/vnd.sdmx.data+json;version=2.0.0",
                                        "User-Agent": "Argentina-CPI-coverage/1.0"})
            with urlopen(req, timeout=90) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def parse(payload):
    data = payload["data"]
    datasets = data["dataSets"]
    if len(datasets) != 1 or len(datasets[0].get("series", {})) != 1:
        raise ValueError("Expected exactly one IMF dataset and series")
    dataset = datasets[0]
    structure = data["structures"][dataset["structure"]]
    key, series = next(iter(dataset["series"].items()))
    dims = structure["dimensions"]["series"]
    codes = [dim["values"][int(i)]["id"] for dim, i in zip(dims, key.split(":"))]
    if ".".join(codes) != SERIES:
        raise ValueError(f"Unexpected series: {codes}")
    obs_dims = structure["dimensions"]["observation"]
    if len(obs_dims) != 1 or obs_dims[0]["id"] != "TIME_PERIOD":
        raise ValueError("Unexpected observation dimensions")
    periods = obs_dims[0]["values"]
    values = {}
    for index, obs in series["observations"].items():
        item = periods[int(index)]
        period = item.get("value", item.get("id"))
        match = re.fullmatch(r"(\d{4})-?M(\d{2})", period)
        if not match or not 1 <= int(match[2]) <= 12:
            raise ValueError(f"Unexpected monthly period: {period}")
        month = f"{match[1]}-{match[2]}"
        if month in values:
            raise ValueError(f"Duplicate month: {month}")
        values[month] = obs[0]
    if not any(v is not None and v != "" for v in values.values()):
        raise ValueError("API returned no nonmissing observations")
    return values, structure


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "argentina_cpi_output")
    args = parser.parse_args()
    payload = fetch()
    retrieved = datetime.now(timezone.utc).isoformat()
    values, structure = parse(payload)
    available = sorted(m for m, v in values.items() if v is not None and v != "")
    months = [f"{y}-{m:02d}" for y in range(2000, 2020) for m in range(1, 13)]
    present = [m for m in months if m in available]
    rows = [{"country": "Argentina", "series": SERIES, "month": m,
             "cpi_index": values.get(m),
             "availability": "available" if m in available else "missing",
             "source_url": URL, "retrieved_at_utc": retrieved} for m in months]
    summary = {"series": SERIES, "requested_start": months[0],
               "requested_end": months[-1], "expected_months": len(months),
               "available_months": len(present), "missing_months": len(months)-len(present),
               "first_available_in_window": present[0] if present else "",
               "last_available_in_window": present[-1] if present else "",
               "first_available_full_series": available[0],
               "last_available_full_series": available[-1],
               "full_series_observations": len(available),
               "starts_december_2016": available[0] == "2016-12",
               "observations_before_december_2016": sum(m < "2016-12" for m in available),
               "source_url": URL, "retrieved_at_utc": retrieved}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "argentina_cpi_monthly_2000_2019.csv", rows)
    write_csv(args.output_dir / "coverage.csv", [summary])
    (args.output_dir / "raw_api_response.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output_dir / "provenance.json").write_text(json.dumps({
        "coverage": summary, "structure_links": structure.get("links", []),
        "scope": "Exact series only; absence does not establish absence in other IMF series.",
        "missing_policy": "Blank values; no interpolation or splicing."
    }, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
