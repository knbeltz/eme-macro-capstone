"""U.S. extension; preserve the existing EME data and transformation conventions."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import TARGET, EXTENDED, clean, coverage, positive
from .fred import Fred, MissingFredKey, BASE
from .providers import IMF_BASE, imf_credit

SERIES = {
    'FEDFUNDS': ('us_federal_funds_rate','NSA','Percent'),
    'PCE': ('us_pce_nominal','SAAR','Billions of Dollars'),
    'PCEC96': ('us_pce_real','SAAR','Billions of Chained'),
    'INDPRO': ('us_industrial_production','SA','Index'),
    'CPIAUCSL': ('us_cpi','SA','Index'),
    'LOANS': ('us_credit_loans_h8','SA','Billions of U.S. Dollars'),
    'BUSLOANS': ('us_credit_ci_h8','SA','Billions of U.S. Dollars'),
    'CONSUMER': ('us_credit_consumer_h8','SA','Billions of U.S. Dollars'),
    'REALLN': ('us_credit_real_estate_h8','SA','Billions of U.S. Dollars'),
    'LOANINV': ('us_total_bank_credit_h8','SA','Billions of U.S. Dollars'),
}
WEEKLY_CANDIDATES = ['TOTLL','TOTBKCR']
EMPTY = pd.DataFrame(columns=['date','value','frequency'])
PRIMARY_COLUMNS = ['date','us_federal_funds_rate','us_pce_nominal','us_log_pce',
    'us_pce_real','us_industrial_production','us_log_ip','us_nominal_credit','us_cpi',
    'us_real_credit','us_credit_growth_yoy']


def validate_metadata(series_id, metadata):
    _, seasonal, units_prefix = SERIES[series_id]
    if metadata.get('frequency_short') != 'M':
        raise ValueError(f'{series_id}: expected native monthly frequency')
    if metadata.get('seasonal_adjustment_short') != seasonal:
        raise ValueError(f'{series_id}: seasonal adjustment mismatch')
    if not metadata.get('units','').startswith(units_prefix):
        raise ValueError(f'{series_id}: unit mismatch')


def transform_us(frame):
    f = frame.reindex(EXTENDED).copy()
    f['us_log_pce'] = np.log(positive(f.us_pce_nominal))
    f['us_log_ip'] = np.log(positive(f.us_industrial_production))
    f['us_log_pce_real'] = np.log(positive(f.us_pce_real))
    f['us_real_credit'] = positive(f.us_nominal_credit) / (positive(f.us_cpi) / 100)
    log_credit = np.log(positive(f.us_real_credit))
    f['us_credit_growth_yoy'] = 100 * (log_credit - log_credit.shift(12))
    f['us_credit_growth_mom'] = 100 * (log_credit - log_credit.shift(1))
    # Explicit optional counterpart to the original EME arithmetic growth formula.
    f['us_credit_growth_yoy_pct'] = 100 * (f.us_real_credit / positive(f.us_real_credit.shift(12)) - 1)
    return f.replace([np.inf,-np.inf],np.nan)


def merge_us(eme, us):
    """Append monthly U.S. data; retain every original EME column and row."""
    if us.date.duplicated().any():
        raise ValueError('Duplicate U.S. months would multiply panel rows')
    if eme.duplicated(['iso3','date']).any():
        raise ValueError('Original EME panel contains duplicate country-months')
    # Existing us_cpi is GEM NSA CPI for RER. CPIAUCSL must not overwrite it.
    right = us.rename(columns={'us_cpi':'us_credit_cpi'})
    collisions = (set(eme.columns) & set(right.columns)) - {'date'}
    if collisions:
        raise ValueError(f'Unexpected column collisions: {sorted(collisions)}')
    combined = eme.merge(right, on='date', how='left', validate='many_to_one', sort=False)
    pd.testing.assert_frame_equal(combined[eme.columns], eme, check_exact=True)
    return combined


def fred_registry(series_id, variable, metadata, status):
    return dict(country='United States',iso3='USA',variable=variable,series_id=series_id,
        source='FRED official API',dataset_id='FRED',
        original_producer=('U.S. Bureau of Economic Analysis' if series_id in ['PCE','PCEC96'] else
                           'U.S. Bureau of Labor Statistics' if series_id=='CPIAUCSL' else
                           'Board of Governors of the Federal Reserve System'),
        source_page=f'https://fred.stlouisfed.org/series/{series_id}',
        metadata_api_url=f'{BASE}/series?series_id={series_id}&file_type=json&api_key=REDACTED',
        observations_api_url=f'{BASE}/series/observations?series_id={series_id}&observation_start=1999-01-01&observation_end=2019-12-31&units=lin&sort_order=asc&limit=1000&offset=0&file_type=json&api_key=REDACTED',
        title=metadata.get('title',''),units=metadata.get('units',''),
        frequency=metadata.get('frequency',''),frequency_short=metadata.get('frequency_short',''),
        seasonal_adjustment=metadata.get('seasonal_adjustment',''),
        source_first_available_date=metadata.get('observation_start',''),
        source_last_available_date=metadata.get('observation_end',''),
        last_updated=metadata.get('last_updated',''),
        snapshot_realtime_start=metadata.get('realtime_start',''),
        snapshot_realtime_end=metadata.get('realtime_end',''),
        vintage_policy='Currently revised historical values at saved request snapshot; not real-time historical observations',
        license='Federal statistical sources; cite original producer and FRED; see saved series notes and FRED terms',
        notes=metadata.get('notes',''),status=status)


def build(client, output_root=Path('.')):
    root = Path(output_root)
    reports = root/'reports'; reports.mkdir(parents=True,exist_ok=True)
    processed = root/'data/processed'; processed.mkdir(parents=True,exist_ok=True)
    normalized = root/'data/normalized/USA'; normalized.mkdir(parents=True,exist_ok=True)
    eme_path = processed/'eme_monthly_panel.csv'
    original_bytes = eme_path.read_bytes()
    original_hash = hashlib.sha256(original_bytes).hexdigest()
    eme = pd.read_csv(io.BytesIO(original_bytes))
    f = pd.DataFrame(index=EXTENDED)
    registry=[]; audits=[]; statuses=[]; missing=[]
    fred = Fred(client)

    def record(variable, raw, meta, status, selected=False, error=''):
        stats = coverage(raw)
        row = dict(**meta,selected=selected,**stats,error=error)
        audits.append(row)
        registry.append(dict(**meta,selected=selected,error=error))
        statuses.append(dict(variable=variable,series_id=meta['series_id'],status=status,error=error))
        for month in TARGET.difference(clean(raw).dropna().index):
            missing.append(dict(variable=variable,series_id=meta['series_id'],date=str(month),reason=status if status!='retrieved' else 'missing_source_observation'))

    # Search the same standardized IMF aggregate first; do not treat metadata rows as observations.
    imf_key='USA.ODCORP_A_ACO_PS_ODCS.XDC.M'
    imf_url=f'{IMF_BASE}/data/IMF.STA,MFS_ODC,10.0.0/{imf_key}'
    imf_raw=EMPTY.copy(); imf_status='not_retrieved'; imf_error=''
    try:
        imf_raw=imf_credit(client,'USA')
        clean(imf_raw)
        imf_status='retrieved' if imf_raw.value.notna().any() else 'no_observations_returned'
    except Exception as exc:
        imf_error=str(exc)
        imf_status='download_or_validation_failure'
        try:
            content=client.get('imf','USA',imf_url,headers={'Accept':'application/vnd.sdmx.data+csv;version=1.0.0'})
            parsed=pd.read_csv(io.BytesIO(content),dtype=str)
            if 'TIME_PERIOD' in parsed and not parsed.TIME_PERIOD.notna().any():
                imf_status='metadata_only_no_observations'
                imf_error='HTTP response contains dataset metadata, no observation rows. Historical availability not established.'
        except Exception:
            pass
    imf_meta=dict(country='United States',iso3='USA',variable='us_credit_imf_candidate',series_id=imf_key,
        source='IMF MFS ODC',dataset_id='IMF.STA:MFS_ODC(10.0.0)',
        observations_api_url=imf_url,units='Domestic currency, unscaled export',frequency='Requested monthly',
        notes='Same aggregate key as EME credit. No automatic splice or conversion from quarterly credit.',status=imf_status)
    record('us_credit_imf_candidate',imf_raw,imf_meta,imf_status,error=imf_error)
    if not imf_raw.empty:
        imf_raw.to_csv(normalized/'us_credit_imf_candidate.csv',index=False)

    # Fetch native monthly variants only. Keep weekly candidates as metadata-only discovery.
    for series_id, (variable,_,_) in SERIES.items():
        raw=EMPTY.copy(); metadata={}; status='not_retrieved'; error=''
        try:
            metadata=fred.metadata(series_id)
            validate_metadata(series_id,metadata)
            raw=fred.monthly(series_id,metadata)
            status='retrieved'
            raw.to_csv(normalized/f'{series_id}.csv',index=False)
        except MissingFredKey as exc:
            status='credentials_missing_or_invalid'; error=str(exc)
        except Exception as exc:
            status='download_or_validation_failure'; error=str(exc)
        f[variable]=clean(raw).reindex(EXTENDED)
        meta=fred_registry(series_id,variable,metadata,status)
        record(variable,raw,meta,status,selected=series_id in ['FEDFUNDS','PCE','PCEC96','INDPRO','CPIAUCSL'],error=error)
        print(series_id,status,'target months:',coverage(raw)['observed_months'],flush=True)
    for series_id in WEEKLY_CANDIDATES:
        metadata={}; error=''; status='metadata_only_weekly_candidate'
        try:
            metadata=fred.metadata(series_id)
        except Exception as exc:
            status='metadata_not_retrieved'; error=str(exc)
        registry.append(dict(**fred_registry(series_id,'credit_candidate_not_selected',metadata,status),selected=False,error=error))

    if imf_status=='retrieved':
        credit_id=imf_key
        f['us_nominal_credit']=clean(imf_raw).reindex(EXTENDED)
        credit_type='IMF same-aggregate candidate; country-specific perimeter review required'
    else:
        credit_id='LOANS'
        # An explicit proxy, never described as private-nonfinancial credit.
        f['us_nominal_credit']=f.us_credit_loans_h8
        credit_type='H.8 commercial-bank loans and leases proxy; not harmonized private-sector credit'
    for row in registry+audits:
        if row['series_id']==credit_id:
            row['selected']=True
    credit_registry = next(row.copy() for row in registry if row['series_id']==credit_id)
    credit_registry.update(variable='us_nominal_credit', selected=True,
                           comparability=credit_type)
    registry.append(credit_registry)
    f=transform_us(f)
    f['us_credit_series_id']=credit_id
    f['us_credit_measure']=credit_type
    transformations={
        'us_nominal_credit':f'Selected stock from {credit_id}; H.8 values retained in billions USD if LOANS',
        'us_real_credit':'us_nominal_credit / (CPIAUCSL / 100)',
        'us_credit_growth_yoy':'100 * (ln(real_credit[t]) - ln(real_credit[t-12]))',
        'us_credit_growth_mom':'100 * (ln(real_credit[t]) - ln(real_credit[t-1]))',
        'us_credit_growth_yoy_pct':'100 * (real_credit[t] / real_credit[t-12] - 1); EME-compatible arithmetic formula',
        'us_log_pce':'ln(nominal PCE); SAAR level retained',
        'us_log_ip':'ln(INDPRO)', 'us_log_pce_real':'ln(PCEC96)',
    }
    for variable,formula in transformations.items():
        raw=pd.DataFrame(dict(date=f.index.astype(str),value=f[variable].values,frequency='M'))
        units = ('100 log difference' if variable in ['us_credit_growth_yoy','us_credit_growth_mom'] else
                 'percent change' if variable=='us_credit_growth_yoy_pct' else
                 'natural log of source level' if variable.startswith('us_log_') else
                 credit_registry.get('units','') if variable=='us_nominal_credit' else
                 'billions of CPI-base-period dollars (LOANS), or source currency units (IMF)')
        audits.append(dict(variable=variable,source='Derived from selected inputs',series_id=credit_id if 'credit' in variable else '',
                           selected=True,transformation=formula,units=units,frequency='Monthly',**coverage(raw),status='derived'))
        if variable != 'us_nominal_credit':
            registry.append(dict(variable=variable,source='Derived from selected inputs',
                selected=True,units=units,frequency='Monthly',transformation=formula,
                status='derived',notes='No imputation. See raw input rows for definitions and snapshot dates.'))
        for month in TARGET[f[variable].reindex(TARGET).isna()]:
            missing.append(dict(variable=variable,series_id=credit_id if 'credit' in variable else '',date=str(month),reason='missing_or_nonpositive_input_or_calendar_lag'))
    lag_rows=[]
    for month in TARGET:
        lag=month-12
        lag_rows.append(dict(date=str(month),lag_date=str(lag),
            current_credit_observed=pd.notna(f.at[month,'us_nominal_credit']),
            current_cpi_observed=pd.notna(f.at[month,'us_cpi']),
            lag_credit_observed=pd.notna(f.at[lag,'us_nominal_credit']),
            lag_cpi_observed=pd.notna(f.at[lag,'us_cpi']),
            growth_available=pd.notna(f.at[month,'us_credit_growth_yoy'])))
    sample=f.reindex(TARGET).copy()
    sample.insert(0,'date',sample.index.astype(str))
    sample=sample.reset_index(drop=True)
    sample=sample[PRIMARY_COLUMNS+[col for col in sample if col not in PRIMARY_COLUMNS]]
    from .ff4 import saved_monthly, append_ff4
    ff4 = saved_monthly(root)
    if ff4 is not None:
        sample = append_ff4(sample, ff4)
    combined=merge_us(eme,sample)
    sample.to_csv(processed/'us_monthly_macro.csv',index=False)
    combined.to_csv(processed/'eme_us_monthly_panel.csv',index=False)
    pd.DataFrame(audits).to_csv(reports/'us_series_coverage.csv',index=False)
    pd.DataFrame(registry).to_csv(reports/'us_source_registry.csv',index=False)
    pd.DataFrame(missing).to_csv(reports/'us_missing_months.csv',index=False)
    pd.DataFrame(lag_rows).to_csv(reports/'us_credit_lag_coverage.csv',index=False)
    (reports/'us_download_status.json').write_text(json.dumps(statuses,indent=2))
    if eme_path.read_bytes()!=original_bytes:
        raise RuntimeError('Original EME panel changed during U.S. extension')
    integrity=dict(eme_path=str(eme_path),original_eme_sha256=original_hash,
        after_eme_sha256=hashlib.sha256(eme_path.read_bytes()).hexdigest(),
        original_eme_unchanged=True,eme_rows=len(eme),combined_rows=len(combined),
        us_months=len(sample),credit_series_id=credit_id,credit_measure=credit_type,
        combined_cpi_rule='Original EME us_cpi retained; CPIAUCSL appended as us_credit_cpi')
    (reports/'us_integration_integrity.json').write_text(json.dumps(integrity,indent=2))
    flags=[]
    for series_id,(variable,_,_) in SERIES.items():
        if series_id=='FEDFUNDS':
            continue  # Do not use rate growth ratios as a level-series quality screen.
        values=positive(f[variable])
        ratio=values/values.shift(1)
        for month in TARGET.intersection(ratio.index[(ratio>1.2)|(ratio<0.8)]):
            flags.append(dict(series_id=series_id,date=str(month),ratio=float(ratio.loc[month]),
                              flag='Large monthly level movement; review economic and reporting explanations'))
    pd.DataFrame(flags,columns=['series_id','date','ratio','flag']).to_csv(reports/'us_observation_flags.csv',index=False)
    pd.DataFrame([dict(series_id='H.8 loan and bank-credit series',date='2010-03',
        issue='FAS 166/167 off-balance-sheet vehicle consolidation during 2010 Q1; review levels around March 31',
        treatment='Source levels retained; computed growth is not a separately break-adjusted lending flow',
        source_url='https://www.federalreserve.gov/releases/h8/h8notes.htm')]).to_csv(reports/'us_structural_breaks.csv',index=False)
    write_us_report(reports, sample, registry, imf_status, credit_id, credit_type)
    return sample


def write_us_report(reports,sample,registry,imf_status,credit_id,credit_type):
    lines=['# U.S. data retrieval findings','',
        '| Variable | Observed target months | First | Last |','|---|---:|---|---|']
    for variable in PRIMARY_COLUMNS[1:]:
        observed=sample.loc[sample[variable].notna(),'date']
        lines.append(f'| {variable} | {len(observed)}/240 | {observed.min() if len(observed) else "—"} | {observed.max() if len(observed) else "—"} |')
    lines += ['',f'Selected nominal credit stock: `{credit_id}`. {credit_type}.',
        f'IMF standardized U.S. credit attempt: `{imf_status}`. See us_credit_comparability.md for lender, borrower, timing and transformation differences.', '',
        'Nominal PCE is retained as requested. Real PCE is an additional series, generally more appropriate when interpreting consumption-volume responses; the final VAR specification is not decided here. Missing optional real-PCE observations are not filled using quarterly values or another series.', '',
        'Observed federal funds rates are not identified monetary policy shocks. No VAR, shock estimates, stationarity transformations or artificial shock observations have been produced.', '',
        'No exact replication of Beltrán (2025) is claimed: the final paper’s full variable definitions and vintage have not been reconciled. H.8 loan coverage, nominal versus real consumption, CPI seasonal adjustment and credit growth conventions require explicit modeling choices.', '',
        'Source metadata are monthly and duplicate-free for the successfully admitted series. H.8 documentation identifies accounting/institutional breaks, including 2010 Q1 FAS 166/167 consolidation. These are recorded in us_structural_breaks.csv; large adjacent level movements are separately screened in us_observation_flags.csv. No claim that all historical breaks have been removed is made.', '',
        'Data use currently revised historical values at the saved API snapshot, not information sets available at historical FOMC announcements. Source last-updated dates and snapshot real-time dates are recorded in us_source_registry.csv. ALFRED would require a separate real-time design.', '',
        'The original EME CSV is unchanged (SHA256 evidence in us_integration_integrity.json). U.S. CPIAUCSL is named us_cpi in the standalone U.S. file and us_credit_cpi in the combined panel to preserve the existing GEM-based us_cpi used for EME RER.', '',
        'Files: data/processed/us_monthly_macro.csv; data/processed/eme_us_monthly_panel.csv; reports/us_series_coverage.csv; reports/us_source_registry.csv; reports/us_credit_lag_coverage.csv. Monthly gaps, if any, are enumerated in us_missing_months.csv.']
    (reports/'us_research_findings.md').write_text('\n'.join(lines)+'\n')
