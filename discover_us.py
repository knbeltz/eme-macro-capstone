"""Inspect current U.S. series metadata and save actual IMF credit responses."""
import argparse
import json
from pathlib import Path

from eme_pipeline.http import Client
from eme_pipeline.fred import Fred
from eme_pipeline.providers import imf_credit, IMF_BASE

FRED_IDS = ['FEDFUNDS','PCE','PCEC96','INDPRO','CPIAUCSL',
            'TOTLL','BUSLOANS','CONSUMER','REALLN','TOTBKCR','LOANS','LOANINV']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    client=Client(offline=args.offline)
    fred=Fred(client)
    entries=[]
    for series_id in FRED_IDS:
        try:
            metadata=fred.metadata(series_id)
            entries.append(metadata)
            print(series_id,metadata.get('frequency_short'),metadata.get('units'),
                  metadata.get('seasonal_adjustment_short'),metadata.get('observation_start'),
                  metadata.get('observation_end'),flush=True)
        except Exception as exc:
            entries.append(dict(id=series_id,error=str(exc)))
            print(series_id,str(exc),flush=True)
    Path('reports').mkdir(exist_ok=True)
    Path('reports/us_discovery.json').write_text(json.dumps(entries,indent=2))
    try:
        frame=imf_credit(client,'USA')
        path=Path('data/normalized/USA/us_nominal_credit_imf.csv')
        path.parent.mkdir(parents=True,exist_ok=True)
        frame.to_csv(path,index=False)
        print('IMF ODC:',len(frame),frame.date.min(),frame.date.max(),flush=True)
    except Exception as exc:
        print('IMF ODC:',str(exc),flush=True)
    # Legacy candidate is archived for comparison, never spliced into current MFS.
    url=f'{IMF_BASE}/data/IMF.STA,MFS_NSRF,1.0.3/USA.ODCS.NSRF_22D.XDC.M'
    try:
        response=client.get('imf','USA',url,headers={'Accept':'text/csv'})
        print('IMF legacy response bytes:',len(response),flush=True)
    except Exception as exc:
        print('IMF legacy:',str(exc),flush=True)


if __name__=='__main__': main()
