"""Save real provider discovery responses before selecting series."""
import json
import sys
import xml.etree.ElementTree as ET
from eme_pipeline.http import Client

c = Client()
if '--legacy-credit' in sys.argv:
    from eme_pipeline.config import COUNTRIES
    for iso in COUNTRIES:
        url=f'https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_NSRF,1.0.3/{iso}.ODCS.NSRF_22D.XDC.M'
        try:
            b=c.get('imf',iso,url,headers={'Accept':'text/csv'})
            print(iso,len(b),flush=True)
        except Exception as exc: print(iso,str(exc)[:200],flush=True)
    sys.exit()
if '--extra' in sys.argv:
    jobs=[
      ('imf','ARG','https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI,5.0.0/ARG.CPI._T.IX.M',None),
      ('imf','BRA','https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_NSRF,1.0.3/BRA.ODCS.NSRF_22D.XDC.M',None),
      ('imf','POL','https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR,9.0.0/POL.S13BONDSML_RT_PT_A_PT.M',None),
      ('academic','metadata','https://columbia.edu/~mu2166/uribe_yue_jie/uribe_yue_data.zip',None),
    ]
    for provider,country,url,params in jobs:
        try:
            b=c.get(provider,country,url,params,headers={'Accept':'text/csv'} if provider=='imf' else None)
            print(url,len(b),b[:1800].decode(errors='replace'),flush=True)
        except Exception as exc: print(url,str(exc)[:300],flush=True)
    sys.exit()
if '--alternatives' in sys.argv:
    jobs=[
      ('bcrp','PER','https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04709XD/json/1999-1-1/2019-12-31/ing',None),
      ('bcrp','PER','https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD31894DD/json/1999-1-1/2019-12-31/ing',None),
      ('bis','metadata','https://stats.bis.org/api/v2/structure/dataflow/BIS/all/latest',None),
      ('imf','BRA', 'https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_NSRF,1.0.3/BRA.ODCS.NSRF_22D.XDC.M',None),
      ('imf','BRA','https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR,9.0.0/BRA.S13BONDSML_RT_PT_A_PT.M',None),
      ('fred','USA','https://fred.stlouisfed.org/graph/fredgraph.csv',{'id':'GS2,GS5,GS7,GS10','cosd':'1999-01-01','coed':'2019-12-31'}),
      ('academic','metadata','https://www.columbia.edu/~mu2166/uribe_yue_jie/uribe_yue_data.zip',None),
    ]
    for provider,country,url,params in jobs:
        try:
            b=c.get(provider,country,url,params,headers={'Accept':'text/csv'} if provider=='imf' else None)
            print(provider,url,len(b),b[:1200].decode(errors='replace'),flush=True)
        except Exception as exc: print(url,str(exc)[:300],flush=True)
    sys.exit()
if '--credit' in sys.argv:
    url='https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_ODC,10.0.0/BRA.ODCORP_A_ACO_PS_ODCS..M'
    try:
        b=c.get('imf','BRA',url,{'startPeriod':'1999-01','endPeriod':'2019-12'},headers={'Accept':'text/csv'})
        print(len(b),b[:6000].decode(errors='replace'))
    except Exception as exc:
        print(exc)
    sys.exit()
if '--structures' in sys.argv:
    flows = ET.fromstring(c.get('imf','metadata','https://api.imf.org/external/sdmx/2.1/dataflow'))
    for flow in flows.iter():
        if flow.tag.endswith('Dataflow') and flow.get('id') in ['MFS_ODC','MFS_DC','MFS_IR','MFS_NSRF','CPI']:
            ref = next(e for e in flow.iter() if e.tag.endswith('Ref'))
            url = 'https://api.imf.org/external/sdmx/2.1/datastructure/{agencyID}/{id}/{version}'.format(**ref.attrib)
            try:
                b = c.get('imf','metadata',url,{'references':'all'})
                print(flow.get('id'),len(b),flush=True)
            except Exception as exc:
                print(str(exc),flush=True)
    sys.exit()
jobs = [
    ('worldbank', 'metadata', 'https://api.worldbank.org/v2/sources', {'format':'json','per_page':1000}),
    ('worldbank', 'metadata', 'https://api.worldbank.org/v2/sources/15/indicators', {'format':'json','per_page':1000}),
    ('worldbank', 'BRA', 'https://api.worldbank.org/v2/country/BRA/indicator/DPANUSSPB', {'format':'json','source':15,'date':'1999M01:2019M12','per_page':1000}),
    ('bcrp', 'PER', 'https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01129XM/json/1999-1/2019-12/ing', None),
    ('imf', 'metadata', 'https://api.imf.org/external/sdmx/2.1/dataflow', None),
    ('bis', 'metadata', 'https://stats.bis.org/api/v2/structure/dataflow/BIS/all/latest', None),
]
for provider, country, url, params in jobs:
    try:
        b = c.get(provider, country, url, params)
        print(provider, country, len(b), b[:1200].decode(errors='replace'))
    except Exception as exc:
        print(provider, type(exc).__name__, str(exc)[:250])
