import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

from eme_pipeline.audit import EXTENDED, TARGET
from eme_pipeline.fred import Fred, MissingFredKey
from eme_pipeline.http import Client
from eme_pipeline.us import build, merge_us, transform_us, validate_metadata


def levels():
    return pd.DataFrame(index=EXTENDED,data={
        'us_pce_nominal':100.,'us_pce_real':90.,'us_industrial_production':80.,
        'us_cpi':200.,'us_nominal_credit':np.exp(np.arange(len(EXTENDED))*.01),
        'us_federal_funds_rate':0.})


def test_us_log_growth_calendar_and_no_lookahead():
    f=levels()
    result=transform_us(f)
    assert result.loc['2000-01','us_credit_growth_yoy']==pytest.approx(12.)
    assert result.loc['2000-01','us_credit_growth_mom']==pytest.approx(1.)
    assert result.loc['2000-01','us_real_credit']==pytest.approx(f.loc['2000-01','us_nominal_credit']/2)
    assert result.loc['2000-01','us_credit_growth_yoy_pct']==pytest.approx(100*np.expm1(.12))
    assert result.us_federal_funds_rate.eq(0).all()
    assert result.us_log_pce.eq(np.log(100)).all()
    f.loc['2002-06','us_nominal_credit']=100000
    changed=transform_us(f)
    pd.testing.assert_frame_equal(result.loc[:'2002-05'],changed.loc[:'2002-05'])
    f=f.drop(pd.Period('1999-01',freq='M'))
    assert pd.isna(transform_us(f).loc['2000-01','us_credit_growth_yoy'])
    assert transform_us(f).loc['2000-02','us_credit_growth_yoy']==pytest.approx(12.)


def test_us_nonpositive_inputs_are_missing_not_infinite():
    f=levels(); f.loc['2000-01',['us_cpi','us_pce_nominal']]=0
    result=transform_us(f)
    assert pd.isna(result.loc['2000-01','us_log_pce'])
    assert pd.isna(result.loc['2000-01','us_credit_growth_yoy'])


def test_merge_retains_rows_order_and_original_cpi():
    eme=pd.DataFrame({'iso3':['BRA','MEX','BRA','MEX'],
        'date':['2000-02','2000-01','2000-01','2000-02'],
        'us_cpi':[70.,71.,71.,70.],'nominal_fx':[1.,2.,3.,4.]})
    us=pd.DataFrame({'date':['2000-01','2000-02'],'us_cpi':[170.,171.],
                     'us_federal_funds_rate':[5.,6.]})
    merged=merge_us(eme,us)
    pd.testing.assert_frame_equal(merged[eme.columns],eme)
    assert merged.us_credit_cpi.tolist()==[171.,170.,170.,171.]
    assert merged.groupby('date').us_federal_funds_rate.nunique().eq(1).all()
    with pytest.raises(ValueError,match='Duplicate U.S.'):
        merge_us(eme,pd.concat([us,us]))


def test_fred_metadata_units_and_frequency():
    metadata={'frequency_short':'M','seasonal_adjustment_short':'SAAR','units':'Billions of Dollars'}
    validate_metadata('PCE',metadata)
    with pytest.raises(ValueError,match='unit mismatch'):
        validate_metadata('PCE',{**metadata,'units':'Index 2017=100'})
    with pytest.raises(ValueError,match='native monthly'):
        validate_metadata('PCE',{**metadata,'frequency_short':'Q'})


def test_fred_pagination_nulls_and_no_implicit_aggregation(monkeypatch):
    monkeypatch.setattr('eme_pipeline.fred.get_fred_api_key',lambda:'a'*32)
    class Fake:
        offline=False
        calls=[]
        def json(self,provider,country,url,params,**kwargs):
            self.calls.append(params)
            return dict(count=2,units='lin',observations=[dict(
                date='2000-01-01' if params['offset']==0 else '2000-02-01',
                value='1' if params['offset']==0 else '.')])
    fake=Fake(); fred=Fred(fake)
    raw=fred.monthly('PCE',{'frequency_short':'M'},limit=1)
    assert raw.date.tolist()==['2000-01','2000-02']
    assert pd.isna(raw.value.iloc[1])
    assert [c['offset'] for c in fake.calls]==[0,1]
    assert all('frequency' not in c and c['units']=='lin' for c in fake.calls)
    with pytest.raises(ValueError,match='native monthly'):
        fred.monthly('TOTLL',{'frequency_short':'W'})


def test_fred_duplicate_months_rejected(monkeypatch):
    monkeypatch.setattr('eme_pipeline.fred.get_fred_api_key',lambda:'a'*32)
    class Fake:
        offline=False
        def json(self,*args,**kwargs):
            return dict(count=2,units='lin',observations=[{'date':'2000-01-01','value':'1'}]*2)
    with pytest.raises(ValueError,match='Duplicate'):
        Fred(Fake()).monthly('PCE',{'frequency_short':'M'})


def test_missing_key_keeps_extension_runnable_and_eme_unchanged(tmp_path,monkeypatch):
    monkeypatch.setattr('eme_pipeline.fred.get_fred_api_key',lambda:None)
    class Unavailable:
        offline=False
        def get(self,*args,**kwargs):
            raise RuntimeError('IMF unavailable in this test')
    processed=tmp_path/'data/processed'; processed.mkdir(parents=True)
    original=pd.DataFrame({'iso3':'BRA','date':TARGET.astype(str),'us_cpi':100.})
    path=processed/'eme_monthly_panel.csv'; original.to_csv(path,index=False)
    before=path.read_bytes()
    sample=build(Unavailable(),tmp_path)
    assert path.read_bytes()==before
    assert len(sample)==240 and sample.us_federal_funds_rate.isna().all()
    statuses=json.loads((tmp_path/'reports/us_download_status.json').read_text())
    assert any(s['status']=='credentials_missing_or_invalid' for s in statuses)


@pytest.mark.parametrize('http_status',[200,400])
def test_http_credential_redaction_and_key_independent_cache(tmp_path,monkeypatch,http_status):
    secret='a'*32
    client=Client(tmp_path)
    response=requests.Response(); response.status_code=http_status
    response.url='https://api.stlouisfed.org/fred/series?api_key='+secret
    response._content=json.dumps({'echo':secret}).encode()
    monkeypatch.setattr(client.session,'get',lambda *a,**kw:response)
    monkeypatch.setattr('eme_pipeline.http.time.sleep',lambda *args:None)
    if http_status==400:
        with pytest.raises(RuntimeError) as exc:
            client.get('fred_api','USA','https://api.stlouisfed.org/fred/series',
                       {'api_key':secret},sensitive_params=('api_key',))
        assert secret not in str(exc.value)
    else:
        saved=client.get('fred_api','USA','https://api.stlouisfed.org/fred/series',
                         {'api_key':secret},sensitive_params=('api_key',))
        assert secret.encode() not in saved
        client.offline=True
        assert client.get('fred_api','USA','https://api.stlouisfed.org/fred/series',
                          {'api_key':'different-key'},sensitive_params=('api_key',))==saved
    for file in tmp_path.rglob('*'):
        if file.is_file():
            assert secret not in file.name and secret.encode() not in file.read_bytes()


def test_http_retry_logs_redact_credentials(tmp_path,monkeypatch,caplog):
    secret='a'*32
    client=Client(tmp_path)
    def fail(*args,**kwargs):
        logging.getLogger('urllib3.connectionpool').warning('Retrying URL api_key=%s',secret)
        raise requests.ConnectionError('Failed URL api_key='+secret)
    monkeypatch.setattr(client.session,'get',fail)
    monkeypatch.setattr('eme_pipeline.http.time.sleep',lambda *args:None)
    with pytest.raises(RuntimeError):
        client.get('fred_api','USA','https://api.stlouisfed.org/fred/series',
                   {'api_key':secret},sensitive_params=('api_key',))
    assert secret not in caplog.text
    assert '[REDACTED]' in caplog.text


def test_delivered_us_panel_and_original_eme_integrity():
    path=Path('data/processed/us_monthly_macro.csv')
    if not path.exists():
        pytest.skip('Run us_data_finder.py to generate integration artifacts')
    us=pd.read_csv(path)
    original_path=Path('data/processed/eme_monthly_panel.csv')
    eme=pd.read_csv(original_path)
    combined=pd.read_csv('data/processed/eme_us_monthly_panel.csv')
    assert us.date.tolist()==TARGET.astype(str).tolist()
    assert len(us)==240 and not us.date.duplicated().any()
    assert len(combined)==len(eme)==2880
    # CSV serialization may introduce machine-precision round-trip differences;
    # direct merge_us additionally checks exact in-memory preservation.
    pd.testing.assert_frame_equal(combined[eme.columns],eme,rtol=1e-14,atol=0)
    for col in us.columns.drop(['date','us_cpi']):
        assert combined.groupby('date')[col].nunique(dropna=False).eq(1).all()
    expected=eme.date.map(us.set_index('date').us_cpi)
    pd.testing.assert_series_equal(combined.us_credit_cpi,expected,check_names=False)
    np.testing.assert_allclose(us.us_log_pce,np.log(us.us_pce_nominal),equal_nan=True)
    np.testing.assert_allclose(us.us_log_ip,np.log(us.us_industrial_production),equal_nan=True)
    np.testing.assert_allclose(us.us_real_credit,us.us_nominal_credit/(us.us_cpi/100),equal_nan=True)
    integrity=json.loads(Path('reports/us_integration_integrity.json').read_text())
    assert hashlib.sha256(original_path.read_bytes()).hexdigest()==integrity['original_eme_sha256']==integrity['after_eme_sha256']


def test_saved_1999_credit_lags_match_delivered_growth():
    path=Path('data/processed/us_monthly_macro.csv')
    if not path.exists():
        pytest.skip('Generate U.S. artifacts first')
    us=pd.read_csv(path)
    if not us.us_credit_series_id.eq('LOANS').all():
        pytest.skip('This check is specific to the selected H.8 proxy')
    loans=pd.read_csv('data/normalized/USA/LOANS.csv').set_index('date').value.reindex(EXTENDED.astype(str))
    cpi=pd.read_csv('data/normalized/USA/CPIAUCSL.csv').set_index('date').value.reindex(EXTENDED.astype(str))
    real=loans/(cpi/100)
    expected=100*(np.log(real)-np.log(real.shift(12)))
    np.testing.assert_allclose(us.us_credit_growth_yoy,expected.reindex(TARGET.astype(str)),equal_nan=True)


def test_real_api_cache_replays_without_a_key(tmp_path,monkeypatch):
    if not Path('data/processed/us_monthly_macro.csv').exists():
        pytest.skip('Generate U.S. artifacts first')
    monkeypatch.setattr('eme_pipeline.fred.get_fred_api_key',lambda:None)
    processed=tmp_path/'data/processed'; processed.mkdir(parents=True)
    original=Path('data/processed/eme_monthly_panel.csv').read_bytes()
    (processed/'eme_monthly_panel.csv').write_bytes(original)
    def no_network(*args,**kwargs):
        raise AssertionError('Offline replay attempted a network request')
    client=Client(Path('data/raw'),offline=True)
    monkeypatch.setattr(client.session,'get',no_network)
    sample=build(client,tmp_path)
    statuses=json.loads((tmp_path/'reports/us_download_status.json').read_text())
    assert all(s['status']=='retrieved' for s in statuses if s['series_id'] in ['FEDFUNDS','PCE','INDPRO','CPIAUCSL','LOANS'])
    assert len(sample)==240
    assert (processed/'eme_monthly_panel.csv').read_bytes()==original
