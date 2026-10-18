"""Provider adapters. Codes below were inspected in saved live catalogs."""
import io
import re
import xml.etree.ElementTree as ET

import pandas as pd

WB_BASE = 'https://api.worldbank.org/v2'
IMF_BASE = 'https://api.imf.org/external/sdmx/2.1'
GEM_CODES = {'nominal_fx':'DPANUSSPB', 'domestic_cpi':'CPTOTNSXN',
             'industrial_production':'IPTOTSAKD', 'us_cpi':'CPTOTNSXN'}
BCRP_CODES = {'PER':'PN01129XM','ARG':'PN01130XM','BRA':'PN01131XM',
              'CHL':'PN01132XM','COL':'PN01133XM','MEX':'PN01135XM'}
BCRP_DAILY_CODES={'PER':'PD04709XD','ARG':'PD04710XD','BRA':'PD04711XD',
                  'MEX':'PD04713XD','COL':'PD04715XD','CHL':'PD38581XD'}


def bcrp_daily_monthly(client,iso):
    code=BCRP_DAILY_CODES[iso]
    url=f'https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/1999-1-1/2019-12-31/ing'
    data=client.json('bcrp',iso,url)
    dates=[pd.to_datetime(p['name'].replace('.Set.','.Sep.'),format='%d.%b.%y') for p in data['periods']]
    if pd.Index(dates).duplicated().any(): raise ValueError('Duplicate daily BCRP records')
    values=[pd.to_numeric(p['values'][0],errors='coerce') for p in data['periods']]
    daily=pd.Series(values,index=pd.DatetimeIndex(dates))
    grouped=daily.groupby(daily.index.to_period('M'))
    means=grouped.mean()
    counts=grouped.count()
    # Conservative minimum count, not a claim to validate the index trading calendar.
    means=means.where(counts>=15)
    return pd.DataFrame({'date':means.index.astype(str),'value':means.values,
                         'frequency':'M','status':'daily_mean_min_15',
                         'observed_days':counts.values,'source_frequency':'D'})


def wb_pages(client, country, path, params):
    rows = []
    page = 1
    while True:
        data = client.json('worldbank',country,WB_BASE + path,
                           {**params,'format':'json','per_page':1000,'page':page})
        if not isinstance(data,list) or len(data)!=2 or not isinstance(data[0],dict):
            raise ValueError(f'World Bank API error: {data!r}')
        rows.extend(data[1] or [])
        if page >= int(data[0]['pages']):
            return rows
        page += 1


def gem(client, iso, variable):
    code = GEM_CODES[variable]
    # Explicit monthly bounds avoid annual default results. Availability is query-window bounded.
    rows = wb_pages(client,iso,f'/country/{iso}/indicator/{code}',
                    {'source':15,'date':'1960M01:2026M10'})
    result=[]
    for row in rows:
        if not re.fullmatch(r'\d{4}M\d{2}',row['date']):
            raise ValueError(f'Nonmonthly GEM period: {row["date"]}')
        result.append({'date':row['date'].replace('M','-'),'value':row['value'],
                       'status':row.get('obs_status',''),'frequency':'M'})
    return pd.DataFrame(result,columns=['date','value','status','frequency'])


def bcrp(client, iso):
    code = BCRP_CODES[iso]
    url=f'https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/1960-1/2026-10/ing'
    data=client.json('bcrp',iso,url)
    if len(data['config']['series']) != 1:
        raise ValueError('Unexpected BCRP series count')
    months={m:i+1 for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}
    rows=[]
    for p in data['periods']:
        match=re.fullmatch(r'([A-Za-z]{3})\.(\d{4})',p['name'])
        if not match or match[1] not in months:
            raise ValueError(f'Nonmonthly BCRP period: {p["name"]}')
        rows.append({'date':f'{match[2]}-{months[match[1]]:02d}',
                     'value':pd.to_numeric(p['values'][0],errors='coerce'),
                     'frequency':'M','status':''})
    return pd.DataFrame(rows,columns=['date','value','frequency','status'])


def imf_credit(client, iso):
    key=f'{iso}.ODCORP_A_ACO_PS_ODCS.XDC.M'
    url=f'{IMF_BASE}/data/IMF.STA,MFS_ODC,10.0.0/{key}'
    raw=client.get('imf',iso,url,headers={'Accept':'application/vnd.sdmx.data+csv;version=1.0.0'})
    if raw.lstrip().startswith(b'<'):
        # Generic/structure-specific SDMX XML accepted when server ignores CSV negotiation.
        root=ET.fromstring(raw)
        records=[]
        for series in root.iter():
            if series.tag.split('}')[-1] != 'Series':
                continue
            attrs=dict(series.attrib)
            for child in series:
                if child.tag.split('}')[-1] in ['SeriesKey','Attributes']:
                    attrs.update({e.get('id'):e.get('value') for e in child if e.get('id')})
            for obs in series:
                if obs.tag.split('}')[-1]!='Obs': continue
                a={**attrs,**obs.attrib}
                for e in obs:
                    tag=e.tag.split('}')[-1]
                    if tag=='ObsDimension': a['TIME_PERIOD']=e.get('value')
                    elif tag=='ObsValue': a['OBS_VALUE']=e.get('value')
                    elif tag=='Attributes': a.update({v.get('id'):v.get('value') for v in e})
                records.append(a)
        frame=pd.DataFrame(records)
    else:
        frame=pd.read_csv(io.BytesIO(raw),dtype=str)
    if frame.empty:
        return pd.DataFrame(columns=['date','value','frequency','status'])
    for column,value in [('COUNTRY',iso),('INDICATOR','ODCORP_A_ACO_PS_ODCS')]:
        if column not in frame or not frame[column].eq(value).all(): raise ValueError(f'Credit metadata mismatch: {column}')
    required=['TIME_PERIOD','OBS_VALUE','FREQUENCY','TYPE_OF_TRANSFORMATION']
    if any(x not in frame for x in required):
        raise ValueError(f'IMF missing unit/frequency metadata: {frame.columns.tolist()}')
    if not frame['FREQUENCY'].eq('M').all(): raise ValueError('IMF frequency mismatch')
    if 'TYPE_OF_TRANSFORMATION' in frame and not frame['TYPE_OF_TRANSFORMATION'].eq('XDC').all():
        raise ValueError('Credit must be domestic currency levels')
    frame['date']=frame['TIME_PERIOD'].str.replace('-M','-',regex=False)
    if not frame.date.str.fullmatch(r'\d{4}-\d{2}').all(): raise ValueError('Nonmonthly IMF periods')
    # Current IMF CSV exports contain unscaled values (BRA 2001-12 ~381.6bn).
    # SCALE is a display attribute, not a second multiplier on OBS_VALUE.
    frame['value']=pd.to_numeric(frame.OBS_VALUE,errors='coerce')
    frame['frequency']=frame['FREQUENCY']
    frame['status']=frame['OBS_STATUS'] if 'OBS_STATUS' in frame else (frame['STATUS'] if 'STATUS' in frame else '')
    return frame


def imf_cpi(client,iso):
    url=f'{IMF_BASE}/data/IMF.STA,CPI,5.0.0/{iso}.CPI._T.IX.M'
    raw=client.get('imf',iso,url,headers={'Accept':'text/csv'})
    f=pd.read_csv(io.BytesIO(raw),dtype=str)
    for column,value in [('COUNTRY',iso),('INDEX_TYPE','CPI'),('COICOP_1999','_T'),('TYPE_OF_TRANSFORMATION','IX'),('FREQUENCY','M')]:
        if column not in f or not f[column].eq(value).all(): raise ValueError(f'CPI metadata mismatch: {column}')
    f['date']=f.TIME_PERIOD.str.replace('-M','-',regex=False)
    if not f.date.str.fullmatch(r'\d{4}-\d{2}').all(): raise ValueError('Nonmonthly CPI')
    f['value']=pd.to_numeric(f.OBS_VALUE,errors='coerce')
    f['frequency']='M'
    f['status']=f.STATUS
    return f
