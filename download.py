"""Retrieve verified series without stopping unrelated downloads on a provider failure."""
import json
import argparse
from pathlib import Path
from eme_pipeline.http import Client
from eme_pipeline.config import COUNTRIES
from eme_pipeline.providers import gem,bcrp,imf_credit,imf_cpi,BCRP_CODES,bcrp_daily_monthly

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Reparse saved responses without network access')
    args=parser.parse_args()
    c=Client(offline=args.offline)
    status=[]
    for iso in [*COUNTRIES,'USA']:
        jobs=[('us_cpi',gem)] if iso=='USA' else [(v,gem) for v in ['nominal_fx','domestic_cpi','industrial_production']]+[('nominal_private_credit',imf_credit)]
        if iso=='ARG':
            jobs=[('domestic_cpi_gem',gem) if v=='domestic_cpi' else (v,fn) for v,fn in jobs]
            jobs.append(('domestic_cpi',imf_cpi))
        if iso in BCRP_CODES:
            jobs.extend([('sovereign_spread_bp_monthly_catalog',bcrp),('sovereign_spread_bp',bcrp_daily_monthly)])
        for variable, fn in jobs:
            path=Path('data/normalized')/iso/(variable+'.csv')
            try:
                data=fn(c,iso,'domestic_cpi' if variable=='domestic_cpi_gem' else variable) if fn==gem else fn(c,iso)
                path=Path('data/normalized')/iso/(variable+'.csv')
                path.parent.mkdir(parents=True,exist_ok=True)
                data.to_csv(path,index=False)
                entry=dict(iso3=iso,variable=variable,status='retrieved',rows=len(data))
            except Exception as exc:
                if path.exists(): path.rename(path.with_suffix('.stale.csv'))
                entry=dict(iso3=iso,variable=variable,status='download_or_parse_failure',error=str(exc))
            status.append(entry)
            Path('reports/download_status.json').write_text(json.dumps(status,indent=2))
            print(entry,flush=True)
    if any(x['status']!='retrieved' for x in status):
        raise SystemExit(1)

if __name__=='__main__': main()
