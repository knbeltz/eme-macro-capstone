#!/usr/bin/env python3
"""Download exact IMF MFS_ODC monthly private-sector claims, 2000–2019.

Run: python3 download_imf_odc.py
Requires only Python's standard library. Values are preserved exactly as the
IMF CSV API returns them; SCALE and other attributes remain in the raw CSV.
No interpolation, currency conversion, or substitute indicators are used.
XDC means expressed in domestic currency, not necessarily claims denominated
exclusively in domestic currency. These are monetary amounts, not indices.
"""
import argparse
import csv
import io
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

COUNTRIES = {'BRA': 'Brazil', 'MEX': 'Mexico', 'CHL': 'Chile',
             'COL': 'Colombia', 'PER': 'Peru', 'ARG': 'Argentina',
             'ZAF': 'South Africa', 'TUR': 'Turkey', 'POL': 'Poland',
             'MYS': 'Malaysia', 'PHL': 'Philippines', 'THA': 'Thailand'}
INDICATOR = 'ODCORP_A_ACO_PS_ODCS'
BASE = 'https://api.imf.org/external/sdmx/2.1'
MONTHS = [f'{y}-{m:02d}' for y in range(2000, 2020) for m in range(1, 13)]


def fetch(url, accept='text/csv'):
    for attempt in range(5):
        try:
            with urlopen(Request(url, headers={'Accept': accept,
                         'User-Agent': 'IMF-ODC-research/1.0'}), timeout=90) as r:
                return r.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            if isinstance(exc, HTTPError) and exc.code < 500 and exc.code != 429:
                raise
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', type=Path,
                   default=Path(__file__).resolve().parent / 'test_data_output' / 'imf_odc_output')
    args = p.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    key = '+'.join(COUNTRIES) + f'.{INDICATOR}.XDC.M'
    url = f'{BASE}/data/IMF.STA,MFS_ODC/{key}?' + urlencode(
        {'startPeriod': '2000-01', 'endPeriod': '2019-12'})
    raw = fetch(url)
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    required = {'COUNTRY', 'INDICATOR', 'TYPE_OF_TRANSFORMATION',
                'FREQUENCY', 'TIME_PERIOD', 'OBS_VALUE'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('IMF did not return the expected SDMX CSV columns')
    values, scales, rows = {}, {c: set() for c in COUNTRIES}, list(reader)
    if not rows:
        raise ValueError('IMF returned no observations; coverage is not established')
    for r in rows:
        c = r['COUNTRY']
        if (c not in COUNTRIES or r['INDICATOR'] != INDICATOR or
            r['TYPE_OF_TRANSFORMATION'] != 'XDC' or r['FREQUENCY'] != 'M'):
            raise ValueError(f'Unexpected series: {r}')
        month = re.sub(r'^(\d{4})-?M(\d{2})$', r'\1-\2', r['TIME_PERIOD'])
        if month not in MONTHS:
            raise ValueError(f'Unexpected time period: {month}')
        k = (c, month)
        if k in values:
            raise ValueError(f'Duplicate observation: {k}')
        value = r['OBS_VALUE'].strip()
        if value and not Decimal(value).is_finite():
            raise ValueError(f'Nonfinite observation: {k}')
        values[k] = value
        if r.get('SCALE', ''):
            scales[c].add(r['SCALE'])
    # Save the original response for attributes, flags, and reproducibility.
    (out / 'imf_raw.csv').write_bytes(raw)
    metadata_url = f'{BASE}/dataflow/IMF.STA/MFS_ODC/latest?references=all'
    (out / 'imf_structure.xml').write_bytes(fetch(metadata_url, 'application/xml'))
    write_csv(out / 'claims_private_sector_monthly_2000_2019.csv',
              ['date', *COUNTRIES],
              [dict(date=m, **{c: values.get((c, m), '') for c in COUNTRIES})
               for m in MONTHS])
    coverage = []
    for c, name in COUNTRIES.items():
        observed = [m for m in MONTHS if values.get((c, m), '') != '']
        coverage.append(dict(iso3=c, country=name, series=f'{c}.{INDICATOR}.XDC.M',
            first_month=observed[0] if observed else '',
            last_month=observed[-1] if observed else '', observations=len(observed),
            expected_months=240, missing_months=240-len(observed),
            scale_attribute=';'.join(sorted(scales[c]))))
    write_csv(out / 'coverage.csv', list(coverage[0]), coverage)
    write_csv(out / 'missing_months.csv', ['iso3', 'country', 'date'],
              [dict(iso3=c, country=name, date=m) for c, name in COUNTRIES.items()
               for m in MONTHS if values.get((c, m), '') == ''])
    (out / 'provenance.json').write_text(json.dumps({
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'data_url': url, 'metadata_url': metadata_url,
        'dataset': 'IMF.STA:MFS_ODC', 'indicator': INDICATOR,
        'value_handling': 'Exact OBS_VALUE strings; no scale multiplication or division.',
        'missing_handling': 'Blank cells; no interpolation or substitute series.',
        'interpretation': 'Claims on private sector (ODCS), expressed in domestic currency; not an index.'
    }, indent=2) + '\n', encoding='utf-8')
    for r in coverage:
        print(f"{r['country']:15} {r['observations']:3}/240  "
              f"{r['first_month']} to {r['last_month']}  missing={r['missing_months']}")
    print(f'Files saved to {out}')


if __name__ == '__main__':
    main()