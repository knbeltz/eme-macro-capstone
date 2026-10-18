import numpy as np
import pandas as pd

TARGET=pd.period_range('2000-01','2019-12',freq='M')
EXTENDED=pd.period_range('1999-01','2019-12',freq='M')


def clean(frame):
    """Reject ambiguous duplicates and frequency mismatches; never silently average."""
    if frame.empty: return pd.Series(dtype=float,index=pd.PeriodIndex([],freq='M'))
    if not frame.frequency.eq('M').all(): raise ValueError('Frequency mismatch')
    if not frame.date.astype(str).str.fullmatch(r'\d{4}-\d{2}').all(): raise ValueError('Nonmonthly dates')
    index=pd.PeriodIndex(frame.date,freq='M')
    if index.duplicated().any(): raise ValueError('Duplicate monthly observations')
    return pd.Series(pd.to_numeric(frame.value,errors='raise').to_numpy(),index=index).sort_index().replace([np.inf,-np.inf],np.nan)


def coverage(frame, target=TARGET):
    duplicate_count=0 if frame.empty else int(pd.PeriodIndex(frame.date,freq='M').duplicated().sum())
    genuinely_monthly=bool(not frame.empty and frame.frequency.eq('M').all()
                          and ('source_frequency' not in frame or frame.source_frequency.eq('M').all()))
    try: series=clean(frame)
    except ValueError: series=pd.Series(dtype=float,index=pd.PeriodIndex([],freq='M'))
    observed=series.dropna()
    inside=observed.reindex(target).dropna()
    missing=target.difference(inside.index)
    return dict(earliest_available_observation=str(observed.index.min()) if len(observed) else '',
                latest_available_observation=str(observed.index.max()) if len(observed) else '',
                first_in_sample=str(inside.index.min()) if len(inside) else '',
                last_in_sample=str(inside.index.max()) if len(inside) else '',
                observed_months=len(inside),missing_months=len(missing),
                missing_month_dates=';'.join(map(str,missing)),coverage_pct=100*len(inside)/len(target),
                duplicate_count=duplicate_count,genuinely_monthly=genuinely_monthly)


def positive(series): return series.where(series>0)


def transform(frame):
    f=frame.reindex(EXTENDED).copy()
    f['real_fx']=positive(f.nominal_fx)*positive(f.us_cpi)/positive(f.domestic_cpi)
    f['log_real_fx']=np.log(positive(f.real_fx))
    f['log_ip']=np.log(positive(f.industrial_production))
    f['real_private_credit']=positive(f.nominal_private_credit)/(positive(f.domestic_cpi)/100)
    # Calendar reindexing must precede shift: twelve rows must mean twelve months.
    f['real_credit_growth_yoy']=100*(f.real_private_credit/positive(f.real_private_credit.shift(12))-1)
    return f.replace([np.inf,-np.inf],np.nan)


def usd_spread_bp(sovereign_yield, treasury_yield, *, currency, units, fixed_rate,
                  sovereign_maturity, treasury_maturity, max_maturity_gap=0.5):
    if currency!='USD' or units!='percent' or not fixed_rate:
        raise ValueError('Requires fixed-rate USD sovereign yield and percent units')
    if abs(sovereign_maturity-treasury_maturity)>max_maturity_gap:
        raise ValueError('Maturity mismatch')
    return 100*(sovereign_yield-treasury_yield)


def complete_cases(frame, required):
    return frame[required].notna().all(axis=1)
