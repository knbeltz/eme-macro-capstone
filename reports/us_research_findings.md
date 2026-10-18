# U.S. data retrieval findings

| Variable | Observed target months | First | Last |
|---|---:|---|---|
| us_federal_funds_rate | 240/240 | 2000-01 | 2019-12 |
| us_pce_nominal | 240/240 | 2000-01 | 2019-12 |
| us_log_pce | 240/240 | 2000-01 | 2019-12 |
| us_pce_real | 156/240 | 2007-01 | 2019-12 |
| us_industrial_production | 240/240 | 2000-01 | 2019-12 |
| us_log_ip | 240/240 | 2000-01 | 2019-12 |
| us_nominal_credit | 240/240 | 2000-01 | 2019-12 |
| us_cpi | 240/240 | 2000-01 | 2019-12 |
| us_real_credit | 240/240 | 2000-01 | 2019-12 |
| us_credit_growth_yoy | 240/240 | 2000-01 | 2019-12 |

Selected nominal credit stock: `LOANS`. H.8 commercial-bank loans and leases proxy; not harmonized private-sector credit.
IMF standardized U.S. credit attempt: `metadata_only_no_observations`. See us_credit_comparability.md for lender, borrower, timing and transformation differences.

Nominal PCE is retained as requested. Real PCE is an additional series, generally more appropriate when interpreting consumption-volume responses; the final VAR specification is not decided here. Missing optional real-PCE observations are not filled using quarterly values or another series.

Observed federal funds rates are not identified monetary policy shocks. No VAR, shock estimates, stationarity transformations or artificial shock observations have been produced.

No exact replication of Beltrán (2025) is claimed: the final paper’s full variable definitions and vintage have not been reconciled. H.8 loan coverage, nominal versus real consumption, CPI seasonal adjustment and credit growth conventions require explicit modeling choices.

Source metadata are monthly and duplicate-free for the successfully admitted series. H.8 documentation identifies accounting/institutional breaks, including 2010 Q1 FAS 166/167 consolidation. These are recorded in us_structural_breaks.csv; large adjacent level movements are separately screened in us_observation_flags.csv. No claim that all historical breaks have been removed is made.

Data use currently revised historical values at the saved API snapshot, not information sets available at historical FOMC announcements. Source last-updated dates and snapshot real-time dates are recorded in us_source_registry.csv. ALFRED would require a separate real-time design.

The original EME CSV is unchanged (SHA256 evidence in us_integration_integrity.json). U.S. CPIAUCSL is named us_cpi in the standalone U.S. file and us_credit_cpi in the combined panel to preserve the existing GEM-based us_cpi used for EME RER.

Files: data/processed/us_monthly_macro.csv; data/processed/eme_us_monthly_panel.csv; reports/us_series_coverage.csv; reports/us_source_registry.csv; reports/us_credit_lag_coverage.csv. Monthly gaps, if any, are enumerated in us_missing_months.csv.
