"""Import USMPD event changes and aggregate them to calendar months."""
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd

from .audit import TARGET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
EVENT_PATH = Path('data/normalized/USA/usmpd_ff4_events.csv')


def read_events(path, sheet='Monetary Events'):
    """Read only Date and FF4; workbook prose is source metadata, not commands."""
    with zipfile.ZipFile(path) as archive:
        book = ET.fromstring(archive.read('xl/workbook.xml'))
        selected = next((s for s in book.findall('m:sheets/m:sheet', NS)
                         if s.attrib['name'] == sheet), None)
        if selected is None:
            raise ValueError(f'Missing sheet: {sheet}')
        rel_id = selected.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        target = next(r.attrib['Target'] for r in relationships if r.attrib['Id'] == rel_id)
        member = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(s.itertext()) for s in ET.fromstring(
                archive.read('xl/sharedStrings.xml')).findall('m:si', NS)]
        def value(cell):
            if cell.find('m:f', NS) is not None:
                raise ValueError('Formula in source Date/FF4 cell')
            if cell.attrib.get('t') == 'inlineStr':
                return ''.join(cell.find('m:is', NS).itertext())
            v = cell.find('m:v', NS)
            return strings[int(v.text)] if v is not None and cell.attrib.get('t') == 's' else (v.text if v is not None else None)
        rows = ET.fromstring(archive.read(member)).findall('m:sheetData/m:row', NS)
        headers = {value(c): ''.join(filter(str.isalpha, c.attrib['r'])) for c in rows[0]}
        columns = [headers['Date'], headers['FF4']]
        records = []
        origin = '1904-01-01' if book.find('m:workbookPr', NS).attrib.get('date1904') in ('1', 'true') else '1899-12-30'
        for row in rows[1:]:
            cells = {''.join(filter(str.isalpha, c.attrib['r'])): c for c in row}
            date = value(cells[columns[0]]) if columns[0] in cells else None
            if date is None:
                continue
            date = pd.to_datetime(float(date), unit='D', origin=origin)
            raw = value(cells[columns[1]]) if columns[1] in cells else None
            records.append((date.strftime('%Y-%m-%d'), float(raw) if raw is not None else np.nan))
    events = pd.DataFrame(records, columns=['date', 'ff4_change_pp'])
    if events.date.duplicated().any():
        raise ValueError('Duplicate event dates')
    if np.isinf(events.ff4_change_pp).any():
        raise ValueError('Nonfinite FF4 value')
    return events.sort_values('date').reset_index(drop=True)


def monthly_ff4(events):
    """Sum event changes, then difference monthly totals; retain missing events."""
    f = events.copy()
    f['month'] = pd.to_datetime(f.date, errors='raise').dt.to_period('M')
    calendar = pd.period_range(TARGET[0] - 1, TARGET[-1], freq='M')
    grouped = f.groupby('month').ff4_change_pp
    counts = grouped.size().reindex(calendar, fill_value=0)
    observed = grouped.count().reindex(calendar, fill_value=0)
    totals = grouped.sum(min_count=1).reindex(calendar)
    totals = totals.mask(counts.eq(0), 0.).mask(observed.lt(counts))
    result = pd.DataFrame({'us_ff4_monthly_change_pp': totals,
        'us_ff4_mom_change_pp': totals.diff(),
        'us_ff4_event_count': counts, 'us_ff4_observed_event_count': observed})
    result = result.reindex(TARGET)
    result.insert(0, 'date', result.index.astype(str))
    return result.reset_index(drop=True)


def append_ff4(frame, monthly):
    columns = monthly.columns.drop('date')
    # Replace only this extension's columns, making refreshes repeatable.
    original = frame.drop(columns=columns, errors='ignore')
    result = original.merge(monthly, on='date', how='left', sort=False, validate='many_to_one')
    pd.testing.assert_frame_equal(result[original.columns], original, check_exact=True)
    return result


def saved_monthly(root=Path('.')):
    path = Path(root) / EVENT_PATH
    return monthly_ff4(pd.read_csv(path)) if path.exists() else None
