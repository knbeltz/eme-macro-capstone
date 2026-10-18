"""Additional candidate audits and generated research findings (no HTTP access)."""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import TARGET, coverage,clean
from .config import COUNTRIES
from .http import Client
from .providers import BCRP_CODES,IMF_BASE


def candidates(audits,registry,missing):
    c=Client(offline=True)
    comparisons=[]; errors=[]
    def add(iso,var,raw,meta,suitable):
        stats=coverage(raw)
        audits.append(dict(country=COUNTRIES.get(iso,'United States'),iso3=iso,variable=var,selected=False,
                           **meta,**stats,suitable_for_research=suitable,retrieval_status='candidate_not_selected'))
        registry.append(dict(country=COUNTRIES.get(iso,'United States'),iso3=iso,variable=var,selected=False,**meta))
        for date in TARGET.difference(clean(raw).dropna().index):
            missing.append(dict(country=COUNTRIES.get(iso,'United States'),iso3=iso,variable=var,source=meta['source'],selected=False,date=str(date),reason='candidate_not_observed'))
    for iso,code in BCRP_CODES.items():
        p=Path(f'data/normalized/{iso}/sovereign_spread_bp_monthly_catalog.csv')
        if not p.exists(): continue
        raw=pd.read_csv(p)
        add(iso,'sovereign_spread_bp',raw,dict(source='BCRP native monthly catalog',dataset_id='EMBIG monthly',series_code=code,
            direct_api_url=f'https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/1960-1/2026-10/ing',
            units='basis points',frequency='M',definition='EMBIG monthly average; stripped definition unconfirmed',
            licensing='BCRP reproduction with attribution; underlying JPM index rights',notes='Alternative only; shorter history; no splice'),
            'short_history_and_stripped_definition_unconfirmed')
        d=pd.read_csv(f'data/normalized/{iso}/sovereign_spread_bp.csv').set_index('date')
        j=d[['value']].join(raw.set_index('date')[['value']],lsuffix='_daily',rsuffix='_monthly').dropna()
        comparisons.append(dict(iso3=iso,overlap_months=len(j),mean_absolute_difference_bp=float((j.value_daily-j.value_monthly).abs().mean()),
                                 max_absolute_difference_bp=float((j.value_daily-j.value_monthly).abs().max())))
    for iso in COUNTRIES:
        key=f'{iso}.ODCS.NSRF_22D.XDC.M'
        url=f'{IMF_BASE}/data/IMF.STA,MFS_NSRF,1.0.3/{key}'
        try:
            f=pd.read_csv(io.BytesIO(c.get('imf',iso,url)),dtype=str)
            f=f[f.TIME_PERIOD.notna() & f.OBS_VALUE.notna()].copy()
            f['date']=f.TIME_PERIOD.str.replace('-M','-',regex=False)
            f['value']=pd.to_numeric(f.OBS_VALUE,errors='coerce'); f['frequency']=f.FREQUENCY
            add(iso,'nominal_private_credit',f,dict(source='IMF MFS nonstandard legacy candidate',dataset_id='IMF.STA:MFS_NSRF(1.0.3)',series_code=key,
               direct_api_url=url,units='Domestic currency, as exported',frequency='M',definition='ODCS, claims on private sector, nonstandard country-reported definition',
               licensing='IMF data terms',notes='Discontinued vintage, not harmonized. No splice with MFS_ODC; institutional and valuation differences unresolved.'),
               'nonstandard_perimeter_and_series_break_review_required')
        except (RuntimeError,ValueError,AttributeError,KeyError) as exc:
            errors.append(dict(iso3=iso,url=url,error=str(exc)))
    p=Path('data/normalized/ARG/domestic_cpi_gem.csv')
    if p.exists():
        add('ARG','domestic_cpi',pd.read_csv(p),dict(source='World Bank GEM rejected CPI candidate',dataset_id='15',series_code='CPTOTNSXN',
            direct_api_url='https://api.worldbank.org/v2/country/ARG/indicator/CPTOTNSXN?source=15&date=1960M01:2026M10&format=json&per_page=1000&page=1',
            units='CPI level; base unspecified',frequency='M',definition='NSA CPI',licensing='CC BY 4.0',notes='No observed CPI values in target sample in returned response; current IMF national CPI selected instead.'),'no_target_observations')
    for iso in ['BRA','POL']:
        key=f'{iso}.S13BONDSML_RT_PT_A_PT.M'
        url=f'{IMF_BASE}/data/IMF.STA,MFS_IR,9.0.0/{key}'
        try:
            response=pd.read_csv(io.BytesIO(c.get('imf',iso,url)),dtype=str)
            if response.TIME_PERIOD.notna().any():
                errors.append(dict(iso3=iso,url=url,error='Yield response changed; inspect actual observations and denomination before admitting'))
                continue
            add(iso,'government_yield_candidate',pd.DataFrame(columns=['date','value','frequency']),
                dict(source='IMF MFS IR metadata-only yield query',dataset_id='IMF.STA:MFS_IR(9.0.0)',series_code=key,
                     direct_api_url=url,units='Codelist: percent per annum; no observed units returned',frequency='Requested M; no observations',
                     definition='Government bond medium/long-term yield candidate; no observed series returned',licensing='IMF data terms',
                     notes='HTTP 200 contained metadata only. Historical availability unresolved. Not a validated USD yield or spread.',
                     denomination_currency='Not established',issuer='Government, codelist concept only',maturity_or_duration='Medium/long term; not established',
                     sovereign_category='Unclassified; denomination unverified',bond_identifier=key,roll_policy='Not established'),
                'no_observations_returned_definition_unverified')
        except (RuntimeError,ValueError,KeyError) as exc:
            errors.append(dict(iso3=iso,url=url,error=str(exc)))
    # FRED Treasury yields are benchmarks, not country sovereign risk indicators.
    fred_url='https://fred.stlouisfed.org/graph/fredgraph.csv'
    try:
        f=pd.read_csv(io.BytesIO(c.get('fred','USA',fred_url,{'id':'GS2,GS5,GS7,GS10','cosd':'1999-01-01','coed':'2019-12-31'})))
        for code in ['GS2','GS5','GS7','GS10']:
            raw=pd.DataFrame({'date':pd.to_datetime(f.observation_date).dt.to_period('M').astype(str),'value':f[code],'frequency':'M'})
            add('USA',code,raw,dict(source='FRED / Federal Reserve Board H.15',dataset_id='H.15',series_code=code,
                direct_api_url=fred_url+'?id=GS2%2CGS5%2CGS7%2CGS10&cosd=1999-01-01&coed=2019-12-31',units='percent per annum',frequency='M',
                definition=f'{code[2:]} year constant-maturity Treasury yield; business-day average; NSA',licensing='Public domain; citation requested',
                notes='Not a sovereign spread; not subtracted from local-currency yields. Server returned broader history; target window audited explicitly.',
                denomination_currency='USD',issuer='United States Treasury',maturity_or_duration=code[2:]+' years constant maturity',
                bond_identifier=code,roll_policy='Constant maturity series; not an individual security'),'benchmark_only')
    except (RuntimeError,ValueError,KeyError) as exc:
        errors.append(dict(iso3='USA',url=fred_url,error=str(exc)))
    # Actual USD sovereign-yield candidate: retain observations but do not invent a bond roll.
    url='https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD31894DD/json/1999-1-1/2019-12-31/ing'
    try:
        data=c.json('bcrp','PER',url)
        daily=pd.Series([pd.to_numeric(p['values'][0],errors='coerce') for p in data['periods']],
                        index=pd.DatetimeIndex([pd.to_datetime(p['name'].replace('.Set.','.Sep.'),format='%d.%b.%y') for p in data['periods']]))
        groups=daily.groupby(daily.index.to_period('M'))
        avg=groups.mean().where(groups.count()>=15)
        raw=pd.DataFrame({'date':avg.index.astype(str),'value':avg.values,'frequency':'M','source_frequency':'D'})
        add('PER','usd_sovereign_yield_percent',raw,dict(source='BCRP / Ministry of Economy and Finance',dataset_id='Daily interest rates',series_code='PD31894DD',
            direct_api_url=url,units='percent per annum',frequency='D, monthly mean minimum 15 days',
            definition='Category C: Peruvian government 10-year USD bond yield',licensing='BCRP reproduction with attribution',
            notes=f'First nonmissing daily observation {daily.dropna().index.min().date()}; last {daily.dropna().index.max().date()}. ISIN, coupon type, residual maturity and roll rules unverified. No spread constructed.',
            sovereign_category='C',denomination_currency='USD',issuer='Republic of Peru',maturity_or_duration='10 years, generic label; residual maturity unverified',
            bond_identifier='PD31894DD; ISIN not established',roll_policy='Unknown; no securities spliced by pipeline'),
            'bond_identifier_fixed_rate_maturity_and_roll_unverified')
    except (RuntimeError,ValueError,KeyError) as exc:
        errors.append(dict(iso3='PER',url=url,error=str(exc)))
    pd.DataFrame(comparisons).to_csv('reports/spread_source_comparison.csv',index=False)
    Path('reports/optional_candidate_errors.json').write_text(json.dumps(errors,indent=2))


def findings(eligibility,scenarios):
    e=pd.DataFrame(eligibility); s=pd.DataFrame(scenarios)
    lines=['# Research findings','',
      'Audit of retrieved observations, 2000–2019. Numerical coverage does not certify economic comparability. All research_cleared flags remain false pending the metadata checks below.', '',
      '| Country | Complete-case months | Numerically complete | Missing requirements |',
      '|---|---:|---|---|']
    for r in eligibility:
        lines.append(f'| {r["country"]} | {r["complete_case_months"]} | {r["all_four_complete"]} | {r["reason"] or "None; metadata review pending"} |')
    lines += ['', 'Spreads are the principal cross-country obstacle: no validated free country spread was retrieved for ZAF, TUR, POL, MYS, PHL or THA. This is unresolved discovery, not proof that no such observations exist. Standardized IMF credit also has late starts; the growth transformation needs both credit and CPI twelve months earlier. Argentina has a separate CPI coverage constraint.', '',
      'BCRP daily EMBIG histories are freely downloadable for BRA, MEX, CHL, COL, PER and ARG. Monthly arithmetic averages are calculated over available daily observations, requiring at least 15 observed days. These are labeled category B because stripped status is not explicitly established by the inspected BCRP descriptions. Native monthly BCRP series have shorter histories and differ slightly on overlap; they are audited separately and never spliced.', '',
      '| Window | Countries with all four numerically complete |', '|---|---|']
    for start,g in s.groupby('start',sort=True):
        countries=', '.join(g.loc[g.all_four_complete,'iso3']) or 'None'
        lines.append(f'| {start}–2019-12 | {countries} |')
    lines += ['',
      'A shorter window improves numerical coverage but does not resolve missing spread sources or establish comparability. An unbalanced panel using observed complete cases, or separate country VARs over contiguous usable spans, is more practical than forcing a balanced twelve-country 2000–2019 panel. VARs cannot simply skip internal missing months: choose contiguous spans and allow additional lags and instrument availability to reduce estimation samples. Few countries and a short sample constrain inference; no models are estimated here.', '',
      'For comparability with Beltrán (2025), the preferred financial variable remains documented J.P. Morgan EMBI Global country stripped spreads with matching aggregation. BCRP EMBIG is the closest downloaded candidate, conditional on confirming the exact definition. USD bond-yield spreads are a separate robustness measure; local-currency yields, CDS, and corporate index spreads are not interchangeable substitutes. The accessible 2023 working-paper version is informative, but the final 2025 paper’s exact data vintage and replication materials have not been verified.', '',
      'Remaining review: country-specific industrial coverage and breaks; CPI rebasing and national coverage; private-credit borrower/institution perimeter; credit valuation and redenomination treatment; EMBIG stripped definition and constituent/duration metadata. GEM industrial production is labeled constant USD, seasonally adjusted, base 2005 by its catalog: the output preserves this measure and does not claim it is a newly verified physical-volume index. No country has been certified estimation-ready.', '',
      'See sovereign_spread_options.md for ranked candidates and access distinctions, source_registry.csv for URLs and definitions, series_coverage.csv for exact month lists, and credit_lag_coverage.csv for calendar lag evidence.']
    Path('reports/research_findings.md').write_text('\n'.join(lines)+'\n')
