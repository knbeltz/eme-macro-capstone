import numpy as np
import pandas as pd
import pytest

from eme_pipeline.audit import (TARGET,EXTENDED,clean,coverage,transform,
                                usd_spread_bp,complete_cases)


def raw(dates, values, frequency='M'):
    return pd.DataFrame({'date':dates,'value':values,'frequency':frequency})


def test_calendar():
    assert len(TARGET)==240 and len(EXTENDED)==252
    assert str(TARGET[0])=='2000-01' and str(TARGET[-1])=='2019-12'


def test_duplicates_quarantine():
    f=raw(['2000-01','2000-01'],[1,2])
    with pytest.raises(ValueError,match='Duplicate'): clean(f)
    result=coverage(f)
    assert result['duplicate_count']==1 and result['observed_months']==0


def test_frequency():
    with pytest.raises(ValueError,match='Frequency'): clean(raw(['2000-01'],[5],'Q'))
    with pytest.raises(ValueError,match='Nonmonthly'): clean(raw(['2000Q1'],[5]))


def test_missing_exact_months_and_null():
    c=coverage(raw(['2000-01','2000-03'],[1,np.nan]))
    assert c['observed_months']==1 and c['missing_months']==239
    assert '2000-02' in c['missing_month_dates']
    assert c['coverage_pct']==pytest.approx(100/240)


def test_transformations_no_fill():
    f=pd.DataFrame(index=EXTENDED, data={'nominal_fx':2.,'domestic_cpi':200.,
                    'us_cpi':100.,'industrial_production':10.,'nominal_private_credit':400.})
    f.loc['2000-01','nominal_private_credit']=440
    out=transform(f)
    assert out.loc['2000-01','real_fx']==1
    assert out.loc['2000-01','log_real_fx']==0
    assert out.loc['2000-01','log_ip']==pytest.approx(np.log(10))
    assert out.loc['2000-01','real_private_credit']==220
    assert out.loc['2000-01','real_credit_growth_yoy']==pytest.approx(10)
    f.loc['1999-02','nominal_private_credit']=np.nan
    assert pd.isna(transform(f).loc['2000-02','real_credit_growth_yoy'])


def test_nonpositive_inputs():
    f=pd.DataFrame(index=EXTENDED, data={'nominal_fx':2.,'domestic_cpi':0.,
                    'us_cpi':100.,'industrial_production':-1.,'nominal_private_credit':10.})
    out=transform(f)
    assert out[['real_fx','log_ip','real_private_credit']].isna().all().all()


def test_basis_points():
    args=dict(currency='USD',units='percent',fixed_rate=True,sovereign_maturity=10,treasury_maturity=10)
    assert usd_spread_bp(6,2,**args)==400
    for key,value in [('currency','BRL'),('units','fraction'),('fixed_rate',False),('sovereign_maturity',2)]:
        with pytest.raises(ValueError): usd_spread_bp(6,2,**{**args,key:value})


def test_eligibility_uses_intersection():
    f=pd.DataFrame({'a':[1,np.nan],'b':[np.nan,1]})
    assert complete_cases(f,['a','b']).sum()==0


def test_saved_panel():
    from pathlib import Path
    path=Path('data/processed/eme_monthly_panel.csv')
    if not path.exists(): pytest.skip('Run data_finder.py to validate integration artifact')
    f=pd.read_csv(path)
    assert len(f)==2880 and not f.duplicated(['iso3','date']).any()
    for _,g in f.groupby('iso3'):
        assert g.date.tolist()==TARGET.astype(str).tolist()
    valid=f[['nominal_fx','domestic_cpi','us_cpi']].gt(0).all(axis=1)
    np.testing.assert_allclose(f.loc[valid,'real_fx'],
        f.loc[valid,'nominal_fx']*f.loc[valid,'us_cpi']/f.loc[valid,'domestic_cpi'])
