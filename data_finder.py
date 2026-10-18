"""Build the requested panel and audit reports from retrieved observations.

Run download.py first. This command performs no network access.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from eme_pipeline.audit import TARGET, EXTENDED, clean,coverage,transform,complete_cases
from eme_pipeline.config import COUNTRIES,RAW_VARIABLES,REQUIRED
from eme_pipeline.providers import GEM_CODES,BCRP_CODES,BCRP_DAILY_CODES,IMF_BASE,WB_BASE
from eme_pipeline.reporting import candidates,findings

EMPTY=pd.DataFrame(columns=['date','value','frequency','status'])


def metadata(iso,var):
    if iso=='ARG' and var=='domestic_cpi':
        return dict(source='IMF CPI',dataset_id='IMF.STA:CPI(5.0.0)',series_code='ARG.CPI._T.IX.M',
          direct_api_url=f'{IMF_BASE}/data/IMF.STA,CPI,5.0.0/ARG.CPI._T.IX.M',units='Index December 2016=100',frequency='M',
          definition='National all-items consumer price index; no historical splice',
          licensing='IMF data terms: https://www.imf.org/en/about/copyright-and-terms#data',
          notes='Returned reference period 2016M12; only available observations used. Earlier official CPI quality issues and geographical/methodological breaks documented by IMF. Not backfilled with incompatible earlier CPI.')
    if var in GEM_CODES:
        code=GEM_CODES[var]
        definitions={'nominal_fx':'New LCU per USD, period average, extended backward in new currency units',
          'domestic_cpi':'All-items CPI, not seasonally adjusted; base not specified by returned catalog',
          'us_cpi':'All-items US CPI, not seasonally adjusted; base not specified by returned catalog',
          'industrial_production':'Manufacturing, mining and utilities; constant US dollars, seasonally adjusted; catalog base year 2005'}
        return dict(source='World Bank GEM',dataset_id='15',series_code=code,
          direct_api_url=f'{WB_BASE}/country/{"USA" if var=="us_cpi" else iso}/indicator/{code}?source=15&date=1960M01:2026M10&format=json&per_page=1000&page=1',
          units={'nominal_fx':'new LCU/USD','domestic_cpi':'CPI level; base unspecified','us_cpi':'CPI level; base unspecified','industrial_production':'constant USD; catalog base 2005'}[var],
          frequency='M',definition=definitions[var],licensing='CC BY 4.0 (GEM catalog)',
          notes='Availability bounded by requested 1960-01:2026-10 window. Country-specific breaks/industry scope require review; no imputation.')
    if var=='nominal_private_credit':
        key=f'{iso}.ODCORP_A_ACO_PS_ODCS.XDC.M'
        return dict(source='IMF MFS ODC',dataset_id='IMF.STA:MFS_ODC(10.0.0)',series_code=key,
          direct_api_url=f'{IMF_BASE}/data/IMF.STA,MFS_ODC,10.0.0/{key}',units='Domestic currency; unscaled OBS_VALUE as exported',frequency='M',
          definition='Other depository corporations, assets, claims on private sector, domestic-currency valuation',
          licensing='IMF data terms: https://www.imf.org/en/about/copyright-and-terms#data',
          commercial_banks='Included conceptually; national perimeter requires review',
          other_depository_corporations='Included',
          nonbank_financial_institutions='Deposit-taking nonbanks may be included as lenders; nondeposit-taking lenders excluded',
          households='Private-sector concept; national borrower coverage not independently verified',
          private_nonfinancial_corporations='Private-sector concept; national borrower coverage not independently verified',
          other_financial_corporations='Borrower inclusion unresolved; do not assume private nonfinancial credit',
          valuation_effects='FX conversion, write-offs and reclassifications can affect stocks; not adjusted',
          notes='Includes commercial banks and other deposit takers. Excludes nondeposit-taking lenders. Borrower household/private NFC/OFC detail and country institutional perimeter require review. Includes FX-valued claims: not a transaction-flow measure. SCALE retained in raw CSV; not applied a second time.')
    code=BCRP_DAILY_CODES.get(iso,'')
    return dict(source='BCRP / Reuters / J.P. Morgan' if code else 'No verified free series selected',
      dataset_id='BCRP EMBIG daily, monthly mean' if code else '',series_code=code,
      direct_api_url=f'https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/1999-1-1/2019-12-31/ing' if code else '',
      units='basis points' if code else '',frequency='D aggregated to M; minimum 15 observed days' if code else '',
      definition='EMBIG country spread against US Treasury of similar duration; monthly average; stripped status not explicitly established' if code else 'Unresolved discovery',
      licensing='BCRP permits reproduction with attribution; underlying index rights remain J.P. Morgan' if code else 'Unknown',
      notes='Category B pending confirmation of stripped definition. Daily mean, no splicing. Availability bounded by 1999-2019 query. USD external sovereign/guaranteed issuer basket; duration and exact constituents unknown; no individual-bond roll performed.' if code else 'Not established as historically unavailable; no validated downloadable country series found in this run.',
      sovereign_category='B; A unconfirmed' if code else '',denomination_currency='USD' if code else '',
      issuer=f'{COUNTRIES[iso]} sovereign/sovereign-guaranteed index basket' if code else '',
      maturity_or_duration='Varying; numerical duration not provided' if code else '',bond_identifier=code,
      roll_policy='Index maintained by J.P. Morgan; constituents/roll rules not retrieved' if code else '')


def main():
    panel=[]; audits=[]; missing=[]; registry=[]; eligibility=[]; lag_rows=[]; scenarios=[]; flags=[]
    for iso,country in COUNTRIES.items():
        f=pd.DataFrame(index=EXTENDED)
        for var in RAW_VARIABLES:
            path=Path('data/normalized')/('USA' if var=='us_cpi' else iso)/(var+'.csv')
            raw=pd.read_csv(path) if path.exists() else EMPTY.copy()
            meta=metadata(iso,var)
            stats=coverage(raw)
            status='retrieved' if path.exists() else ('not_discovered' if var=='sovereign_spread_bp' and iso not in BCRP_CODES else 'not_retrieved')
            row=dict(country=country,iso3=iso,variable=var,selected=True,**meta,**stats,retrieval_status=status,
                     suitable_for_research='requires_metadata_review' if path.exists() else 'no_verified_observations')
            if iso=='ARG' and var in ['domestic_cpi','us_cpi'] and var!='us_cpi': row['suitable_for_research']='CPI_quality_and_break_review_required'
            audits.append(row); registry.append(dict(country=country,iso3=iso,variable=var,selected=True,**meta))
            try: f[var]=clean(raw).reindex(EXTENDED)
            except ValueError: f[var]=float('nan')
            for date in TARGET[f[var].reindex(TARGET).isna()]:
                missing.append(dict(country=country,iso3=iso,variable=var,source=meta['source'],selected=True,date=str(date),reason=status if status!='retrieved' else 'no_valid_observation_in_retrieved_series'))
        f=transform(f)
        for var in RAW_VARIABLES:
            values=f[var].where(f[var]>0)
            ratio=values/values.shift(1)
            for date in ratio.index[(ratio>2)|(ratio<0.5)]:
                flags.append(dict(iso3=iso,variable=var,date=str(date),flag='large_adjacent_change_requires_review',
                                  ratio=float(ratio.loc[date]),interpretation='Possible economic movement, break or unit change; not automatically removed'))
        for var in ['real_fx','log_real_fx','log_ip','real_private_credit','real_credit_growth_yoy']:
            df=pd.DataFrame({'date':f.index.astype(str),'value':f[var].values,'frequency':'M','status':''})
            audits.append(dict(country=country,iso3=iso,variable=var,selected=True,source='Derived from selected raw series',**coverage(df),suitable_for_research='inherits_raw_metadata_limitations',retrieval_status='derived'))
            for date in TARGET[f[var].reindex(TARGET).isna()]:
                missing.append(dict(country=country,iso3=iso,variable=var,source='Derived from selected raw series',selected=True,date=str(date),reason='missing_or_nonpositive_input_or_12_month_lag'))
        for date in TARGET:
            lag=date-12
            lag_rows.append(dict(iso3=iso,date=str(date),lag_date=str(lag),
               current_credit_observed=pd.notna(f.at[date,'nominal_private_credit']),
               current_cpi_observed=pd.notna(f.at[date,'domestic_cpi']),
               lag_credit_observed=pd.notna(f.at[lag,'nominal_private_credit']),
               lag_cpi_observed=pd.notna(f.at[lag,'domestic_cpi']),growth_available=pd.notna(f.at[date,'real_credit_growth_yoy'])))
        sample=f.reindex(TARGET).copy()
        counts={v:int(sample[v].notna().sum()) for v in REQUIRED}
        mask=complete_cases(sample,REQUIRED)
        eligibility.append(dict(country=country,iso3=iso,complete_case_months=int(mask.sum()),
            all_four_complete=bool(mask.all()),research_cleared=False,
            reason='; '.join(f'{v}: {240-n} missing months' for v,n in counts.items() if n<240),
            metadata_limitations='Country-specific credit perimeter/IP coverage review pending; EMBIG stripped definition unconfirmed'+('; Argentina CPI quality/breaks' if iso=='ARG' else '')))
        for start in ['2000-01','2007-01','2010-01','2017-01']:
            sub=sample.loc[start:]
            scenarios.append(dict(iso3=iso,start=start,end='2019-12',months=len(sub),complete_case_months=int(complete_cases(sub,REQUIRED).sum()),
                                  all_four_complete=bool(complete_cases(sub,REQUIRED).all()),
                                  spread_observed_months=int(sub.sovereign_spread_bp.notna().sum())))
        sample['sovereign_spread_type']=sample.sovereign_spread_bp.map(lambda x:'B: EMBIG; stripped definition unconfirmed' if pd.notna(x) else '')
        sample['country']=country; sample['iso3']=iso; sample['date']=sample.index.astype(str)
        panel.append(sample.reset_index(drop=True))
    candidates(audits,registry,missing)
    findings(eligibility,scenarios)
    Path('data/processed').mkdir(parents=True,exist_ok=True)
    Path('reports').mkdir(exist_ok=True)
    cols=['country','iso3','date','nominal_fx','domestic_cpi','us_cpi','real_fx','log_real_fx','sovereign_spread_bp','sovereign_spread_type','industrial_production','log_ip','nominal_private_credit','real_private_credit','real_credit_growth_yoy']
    pd.concat(panel)[cols].to_csv('data/processed/eme_monthly_panel.csv',index=False)
    for name,rows in [('series_coverage',audits),('country_eligibility',eligibility),('missing_months',missing),('source_registry',registry),('credit_lag_coverage',lag_rows),('sample_scenarios',scenarios)]:
        pd.DataFrame(rows).to_csv(f'reports/{name}.csv',index=False)
    pd.DataFrame(flags,columns=['iso3','variable','date','flag','ratio','interpretation']).to_csv('reports/observation_flags.csv',index=False)
    print(pd.DataFrame(eligibility)[['iso3','complete_case_months','all_four_complete','reason']].to_string(index=False))

if __name__=='__main__': main()
