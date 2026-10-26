"""Recover 2000–2019 monthly EMBIG averages from BCRP daily spread levels.

Run python3 download_bcrp_daily_monthly.py (standard library only).
This file is self-contained; no other Python scripts are required.
Uses one historical series per country throughout; no interpolation or splicing.
"""
from collections import defaultdict
from decimal import Decimal
import csv
import datetime as dt
import json
from pathlib import Path
import time
import urllib.request

BASE = 'https://estadisticas.bcrp.gob.pe/estadisticas/series'
COUNTRIES = ['Brazil', 'Mexico', 'Chile', 'Colombia', 'Peru', 'Argentina',
             'South Africa', 'Turkey', 'Poland', 'Malaysia', 'Philippines', 'Thailand']
MONTHS = {m: i for i, m in enumerate(
    ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'], 1)}

CODES = {'Brazil': 'PD04711XD', 'Mexico': 'PD04713XD', 'Chile': 'PD38581XD',
         'Colombia': 'PD04715XD', 'Peru': 'PD04709XD', 'Argentina': 'PD04710XD'}
MONTHS = {**MONTHS, 'Set': 9}


def fetch(url):
    """Read the public BCRP JSON API, retrying temporary failures."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'BCRP-academic-data-download/1.0'})
            with urllib.request.urlopen(req, timeout=90) as response:
                return json.loads(response.read().decode('utf-8-sig'))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def write_csv(path, columns, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    out = Path(__file__).parent / 'bcrp_output'
    (out / 'raw_daily').mkdir(parents=True, exist_ok=True)
    dates = [f'{year}-{month:02}' for year in range(2000, 2020) for month in range(1, 13)]
    codes = list(CODES.values())
    url = f'{BASE}/api/{"-".join(codes)}/json/2000-1-1/2019-12-31/esp'
    data = fetch(url)
    (out / 'raw_daily' / 'daily_2000_2019.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    assert len(data['config']['series']) == len(codes)
    labels = {'Brasil': 'Brazil', 'México': 'Mexico', 'Chile': 'Chile',
              'Colombia': 'Colombia', 'Perú': 'Peru', 'Argentina': 'Argentina'}
    # BCRP reorders batch responses; bind values using returned labels.
    returned_countries = []
    for series in data['config']['series']:
        matches = [country for label, country in labels.items() if f'EMBIG {label} (pbs)' in series['name']]
        assert len(matches) == 1, series
        returned_countries.append(matches[0])
    assert set(returned_countries) == set(CODES)
    buckets = defaultdict(list)
    daily_rows = []
    seen = set()
    for p in data['periods']:
        day, mon, year = p['name'].split('.')
        year = int(year) + 2000 if len(year) == 2 else int(year)
        date = dt.date(year, MONTHS[mon], int(day)).isoformat()
        if not '2000-01-01' <= date <= '2019-12-31':
            continue
        assert date not in seen, date
        seen.add(date)
        assert len(p['values']) == len(codes)
        for country, value in zip(returned_countries, p['values']):
            code = CODES[country]
            value = value.strip()
            if value.lower() in ('', 'n.d.', 'n.d', 'nd', 's/i', '-'):
                continue
            number = Decimal(value)
            assert number.is_finite() and number >= 0
            buckets[country, date[:7]].append(number)
            daily_rows.append({'date': date, 'country': country, 'spread_bps': value, 'series_code': code})
    averages = {key: sum(values) / len(values) for key, values in buckets.items()}
    assert all((country, date) in averages for country in CODES for date in dates), 'Incomplete monthly coverage'
    rows = [{'date': date, **{country: format(averages[country, date], '.8f') if (country, date) in averages else '' for country in COUNTRIES}} for date in dates]
    # Preserve the initial published-monthly-only result as a separate artifact.
    primary = out / 'embig_monthly_2000_2019.csv'
    original = out / 'embig_published_monthly_only_2000_2019.csv'
    if primary.exists() and not original.exists():
        original.write_bytes(primary.read_bytes())
    write_csv(primary, ['date'] + COUNTRIES, rows)
    write_csv(out / 'embig_six_countries_monthly_2000_2019.csv', ['date'] + list(CODES),
              [{k: v for k, v in row.items() if k == 'date' or k in CODES} for row in rows])
    write_csv(out / 'daily_observations.csv', ['date', 'country', 'spread_bps', 'series_code'], daily_rows)
    details = [{'date': date, 'country': country, 'spread_bps': format(averages[country, date], '.8f'),
                'daily_observations': len(buckets[country, date]), 'series_code': code,
                'method': 'Arithmetic mean of available daily spread levels'}
               for date in dates for country, code in CODES.items()]
    write_csv(out / 'monthly_daily_aggregation.csv', list(details[0]), details)
    coverage = [{'country': c, 'first_month': '2000-01' if c in CODES else '',
                 'last_month': '2019-12' if c in CODES else '', 'observations': 240 if c in CODES else 0,
                 'missing_months': 0 if c in CODES else 240, 'series_code': CODES.get(c, ''),
                 'method': 'Mean of available daily levels' if c in CODES else 'No BCRP country EMBIG series found'} for c in COUNTRIES]
    write_csv(out / 'coverage.csv', list(coverage[0]), coverage)
    comparison = []
    source = out / 'source_observations.csv'
    if source.exists():
        with source.open() as f:
            for row in csv.DictReader(f):
                avg = averages[row['country'], row['date']]
                comparison.append({'date': row['date'], 'country': row['country'],
                    'published_series': row['series_code'], 'published_bps': row['spread_bps'],
                    'daily_mean_bps': format(avg, '.8f'),
                    'difference_bps': format(avg - Decimal(row['spread_bps']), '.8f')})
        write_csv(out / 'published_vs_daily_monthly.csv', list(comparison[0]), comparison)
    metadata = {'url': url, 'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'series': dict(zip(returned_countries, data['config']['series'])), 'codes': CODES,
                'method': 'Unweighted arithmetic mean of nonmissing BCRP daily spread levels; no forward fill; eight decimal places in output.'}
    (out / 'daily_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'README.md').write_text('''# Corrected BCRP EMBIG monthly dataset, 2000–2019

The primary CSV now uses arithmetic monthly means of available daily BCRP EMBIG spread levels, in basis points. All six Latin American countries have 240 populated months. No forward filling or interpolation is used. Other six requested country columns remain blank because no country EMBIG series was found in BCRP's catalog.

Daily catalog: https://estadisticas.bcrp.gob.pe/estadisticas/series/diarias/tasas-de-interes-internacionales
Attribution: Reuters, JPMorgan. Despite the category heading “variación en pbs”, the selected series are spread LEVELS in basis points, not daily changes.

Brazil PD04711XD; Mexico PD04713XD; Chile PD38581XD; Colombia PD04715XD; Peru PD04709XD; Argentina PD04710XD. One historical series per country is used throughout the interval to avoid mixing historical and replacement series.

These are derived monthly averages, not downloads of the official monthly-frequency series. The initial result overlooked the daily history. BCRP's monthly-frequency catalog has shorter histories; its replacement series also differ from historical series. The initial monthly-only CSV is preserved as embig_published_monthly_only_2000_2019.csv. Its selected_observations.csv, source_observations.csv, raw/ and metadata.json refer to that initial result, not the corrected primary CSV.

For corrected provenance use daily_observations.csv, monthly_daily_aggregation.csv (including daily counts), raw_daily/, and daily_metadata.json. published_vs_daily_monthly.csv compares derived means with both official monthly series versions where they overlap. Differences may reflect source revisions or averaging conventions; agreement should not be assumed.

Reproduce corrected files: python3 download_bcrp_daily_monthly.py
The older download_bcrp_embig.py reproduces the shorter monthly-only extraction and will overwrite the primary CSV; rerun download_bcrp_daily_monthly.py afterward to restore the complete derived panel.
''', encoding='utf-8')
    print(f'Created {len(rows)} monthly rows; {len(details)} populated country-months from {len(daily_rows)} daily observations.')
    print('Minimum daily observations per country-month:', min(r['daily_observations'] for r in details))
    for version in ('PN011', 'PN436'):
        diffs = [abs(Decimal(r['difference_bps'])) for r in comparison if r['published_series'].startswith(version)]
        print(version, 'comparison count', len(diffs), 'mean absolute difference', float(sum(diffs) / len(diffs)) if diffs else None)


if __name__ == '__main__':
    main()
