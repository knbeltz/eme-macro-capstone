import pandas as pd
import pytest

from eme_pipeline.providers import bcrp_daily_monthly,imf_credit,imf_cpi,wb_pages


class FakeClient:
    def __init__(self,payload): self.payload=payload; self.calls=[]
    def json(self,*args,**kwargs):
        self.calls.append((args,kwargs))
        return self.payload
    def get(self,*args,**kwargs):
        self.calls.append((args,kwargs))
        return self.payload.encode()


def test_imf_credit_unscaled_and_calendar_dates():
    csv='COUNTRY,INDICATOR,TYPE_OF_TRANSFORMATION,FREQUENCY,TIME_PERIOD,OBS_VALUE,SCALE\nBRA,ODCORP_A_ACO_PS_ODCS,XDC,M,2001-M12,381622216144.155,6\n'
    f=imf_credit(FakeClient(csv),'BRA')
    assert f.date.iloc[0]=='2001-12'
    assert f.value.iloc[0]==pytest.approx(381622216144.155)
    with pytest.raises(ValueError,match='metadata mismatch'):
        imf_credit(FakeClient(csv),'MEX')


def test_imf_metadata_only_does_not_count_as_data():
    csv='COUNTRY,INDICATOR,TYPE_OF_TRANSFORMATION,FREQUENCY,TIME_PERIOD,OBS_VALUE,SCALE\n,,,,,,\n'
    with pytest.raises(ValueError): imf_credit(FakeClient(csv),'BRA')


def test_daily_aggregation_counts_locale_and_sparse_month():
    payload={'config':{'series':[{'name':'Spread'}]},'periods':[
        {'name':f'{d:02d}.Set.00','values':['100']} for d in range(1,16)] + [
        {'name':'01.Oct.00','values':['100']},{'name':'02.Oct.00','values':['n.d.']}]}
    f=bcrp_daily_monthly(FakeClient(payload),'PER').set_index('date')
    assert f.loc['2000-09','value']==100
    assert f.loc['2000-09','observed_days']==15
    assert pd.isna(f.loc['2000-10','value'])
    assert f.loc['2000-10','observed_days']==1
    payload['periods'].append(payload['periods'][0])
    with pytest.raises(ValueError,match='Duplicate'): bcrp_daily_monthly(FakeClient(payload),'PER')


def test_wb_pagination_and_api_error():
    class Pages:
        def json(self,provider,country,url,params):
            return [{'pages':2},[params['page']]]
    assert wb_pages(Pages(),'BRA','/test',{})==[1,2]
    with pytest.raises(ValueError,match='API error'):
        wb_pages(FakeClient([{'message':[{'value':'Invalid indicator'}]}]),'BRA','/test',{})


def test_cpi_no_percent_growth_substitution():
    csv='COUNTRY,INDEX_TYPE,COICOP_1999,TYPE_OF_TRANSFORMATION,FREQUENCY,TIME_PERIOD,OBS_VALUE,STATUS\nARG,CPI,_T,YOY_PCH_PA_PT,M,2017-M01,10,\n'
    with pytest.raises(ValueError,match='metadata mismatch'):
        imf_cpi(FakeClient(csv),'ARG')
