# Corrected BCRP EMBIG monthly dataset, 2000–2019

The primary CSV now uses arithmetic monthly means of available daily BCRP EMBIG spread levels, in basis points. All six Latin American countries have 240 populated months. No forward filling or interpolation is used. Other six requested country columns remain blank because no country EMBIG series was found in BCRP's catalog.

Daily catalog: https://estadisticas.bcrp.gob.pe/estadisticas/series/diarias/tasas-de-interes-internacionales
Attribution: Reuters, JPMorgan. Despite the category heading “variación en pbs”, the selected series are spread LEVELS in basis points, not daily changes.

Brazil PD04711XD; Mexico PD04713XD; Chile PD38581XD; Colombia PD04715XD; Peru PD04709XD; Argentina PD04710XD. One historical series per country is used throughout the interval to avoid mixing historical and replacement series.

These are derived monthly averages, not downloads of the official monthly-frequency series. The initial result overlooked the daily history. BCRP's monthly-frequency catalog has shorter histories; its replacement series also differ from historical series. The initial monthly-only CSV is preserved as embig_published_monthly_only_2000_2019.csv. Its selected_observations.csv, source_observations.csv, raw/ and metadata.json refer to that initial result, not the corrected primary CSV.

For corrected provenance use daily_observations.csv, monthly_daily_aggregation.csv (including daily counts), raw_daily/, and daily_metadata.json. published_vs_daily_monthly.csv compares derived means with both official monthly series versions where they overlap. Differences may reflect source revisions or averaging conventions; agreement should not be assumed.

Reproduce corrected files: python3 download_bcrp_daily_monthly.py
The older download_bcrp_embig.py reproduces the shorter monthly-only extraction and will overwrite the primary CSV; rerun download_bcrp_daily_monthly.py afterward to restore the complete derived panel.
