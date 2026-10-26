"""Add local USMPD FF4 monthly changes to the existing final results."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import pandas as pd

from eme_pipeline.ff4 import EVENT_PATH, append_ff4, monthly_ff4, read_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    args = parser.parse_args()
    events = read_events(args.workbook)
    monthly = monthly_ff4(events)
    source = Path('data/raw/usmpd/USMPD.xlsx')
    source.parent.mkdir(parents=True, exist_ok=True)
    if args.workbook.resolve() != source.resolve():
        shutil.copyfile(args.workbook, source)
    EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(EVENT_PATH, index=False)
    monthly.to_csv('data/processed/us_ff4_monthly.csv', index=False)
    for name in ['us_monthly_macro.csv', 'eme_us_monthly_panel.csv']:
        path = Path('data/processed') / name
        if path.exists():
            append_ff4(pd.read_csv(path), monthly).to_csv(path, index=False)
    Path('reports/us_ff4_source.json').write_text(json.dumps({
        'source_file': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sheet': 'Monetary Events', 'source_column': 'FF4', 'units': 'percentage points',
        'monthly_rule': 'Sum event FF4 changes; no-event months zero; any missing event makes monthly total missing',
        'mom_rule': 'Monthly total minus previous calendar month total; December 1999 included for January 2000',
        'sample': '2000-01 through 2019-12',
        'source_event_count': len(events),
    }, indent=2) + '\n')
    print(f'Added FF4 data for {len(monthly)} months to existing U.S./combined results.')


if __name__ == '__main__':
    main()
