"""Official FRED API adapter. No public-CSV fallback or implicit aggregation."""
import re

import pandas as pd

from .audit import clean
from .settings import get_fred_api_key, FRED_KEY_PATTERN

BASE = 'https://api.stlouisfed.org/fred'


class MissingFredKey(RuntimeError):
    pass


class Fred:
    def __init__(self, client):
        self.client = client

    def query(self, path, params):
        key = None if self.client.offline else get_fred_api_key()
        # Offline replays use the credential-independent cache identity.
        if not key and not self.client.offline:
            raise MissingFredKey('FRED_API_KEY is not configured. Run .venv/bin/python setup_fred.py; FRED observations remain missing.')
        if key and not FRED_KEY_PATTERN.fullmatch(key):
            raise MissingFredKey('FRED_API_KEY has an invalid format; no request sent.')
        result = self.client.json('fred_api', 'USA', f'{BASE}/{path}',
            {**params, 'api_key': key or 'offline-cache', 'file_type': 'json'},
            sensitive_params=('api_key',))
        if 'error_code' in result:
            raise ValueError(f'FRED API error {result["error_code"]}; inspect the redacted raw response.')
        return result

    def metadata(self, series_id):
        result = self.query('series', {'series_id': series_id})
        series = result.get('seriess', [])
        if len(series) != 1 or series[0].get('id') != series_id:
            raise ValueError(f'Unexpected FRED metadata for {series_id}')
        return series[0]

    def monthly(self, series_id, metadata, start='1999-01-01', end='2019-12-31', limit=1000):
        if metadata.get('frequency_short') != 'M':
            raise ValueError(f'{series_id} is not native monthly data; no aggregation requested')
        rows = []
        offset = 0
        while True:
            result = self.query('series/observations', dict(series_id=series_id,
                observation_start=start, observation_end=end, units='lin',
                sort_order='asc', limit=limit, offset=offset))
            page = result.get('observations')
            if not isinstance(page, list):
                raise ValueError(f'Missing FRED observations for {series_id}')
            if result.get('units') != 'lin':
                raise ValueError(f'Unexpected FRED transformation for {series_id}')
            rows.extend(page)
            offset += len(page)
            if offset >= int(result['count']):
                break
            if not page:
                raise ValueError('FRED pagination stopped before the declared count')
        records = []
        for row in rows:
            if not re.fullmatch(r'\d{4}-\d{2}-01', row['date']):
                raise ValueError(f'Unexpected monthly date in {series_id}')
            if not start <= row['date'] <= end:
                raise ValueError(f'Out-of-window observation in {series_id}')
            value = float('nan') if row['value'] == '.' else float(row['value'])
            records.append(dict(date=row['date'][:7], value=value, frequency='M',
                realtime_start=row.get('realtime_start'), realtime_end=row.get('realtime_end')))
        frame = pd.DataFrame(records, columns=['date','value','frequency','realtime_start','realtime_end'])
        clean(frame)  # Reject duplicate months; do not collapse them silently.
        return frame
