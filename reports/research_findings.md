# Research findings

Audit of retrieved observations, 2000–2019. Numerical coverage does not certify economic comparability. All research_cleared flags remain false pending the metadata checks below.

| Country | Complete-case months | Numerically complete | Missing requirements |
|---|---:|---|---|
| Brazil | 205 | False | real_credit_growth_yoy: 35 missing months |
| Mexico | 205 | False | real_credit_growth_yoy: 35 missing months |
| Chile | 240 | True | None; metadata review pending |
| Colombia | 205 | False | real_credit_growth_yoy: 35 missing months |
| Peru | 156 | False | real_credit_growth_yoy: 84 missing months |
| Argentina | 25 | False | real_fx: 203 missing months; real_credit_growth_yoy: 215 missing months |
| South Africa | 0 | False | sovereign_spread_bp: 240 missing months; real_credit_growth_yoy: 35 missing months |
| Türkiye | 0 | False | sovereign_spread_bp: 240 missing months; real_credit_growth_yoy: 35 missing months |
| Poland | 0 | False | sovereign_spread_bp: 240 missing months; real_credit_growth_yoy: 60 missing months |
| Malaysia | 0 | False | sovereign_spread_bp: 240 missing months; real_credit_growth_yoy: 35 missing months |
| Philippines | 0 | False | sovereign_spread_bp: 240 missing months; real_credit_growth_yoy: 35 missing months |
| Thailand | 0 | False | sovereign_spread_bp: 240 missing months; real_credit_growth_yoy: 35 missing months |

Spreads are the principal cross-country obstacle: no validated free country spread was retrieved for ZAF, TUR, POL, MYS, PHL or THA. This is unresolved discovery, not proof that no such observations exist. Standardized IMF credit also has late starts; the growth transformation needs both credit and CPI twelve months earlier. Argentina has a separate CPI coverage constraint.

BCRP daily EMBIG histories are freely downloadable for BRA, MEX, CHL, COL, PER and ARG. Monthly arithmetic averages are calculated over available daily observations, requiring at least 15 observed days. These are labeled category B because stripped status is not explicitly established by the inspected BCRP descriptions. Native monthly BCRP series have shorter histories and differ slightly on overlap; they are audited separately and never spliced.

| Window | Countries with all four numerically complete |
|---|---|
| 2000-01–2019-12 | CHL |
| 2007-01–2019-12 | BRA, MEX, CHL, COL, PER |
| 2010-01–2019-12 | BRA, MEX, CHL, COL, PER |
| 2017-01–2019-12 | BRA, MEX, CHL, COL, PER |

A shorter window improves numerical coverage but does not resolve missing spread sources or establish comparability. An unbalanced panel using observed complete cases, or separate country VARs over contiguous usable spans, is more practical than forcing a balanced twelve-country 2000–2019 panel. VARs cannot simply skip internal missing months: choose contiguous spans and allow additional lags and instrument availability to reduce estimation samples. Few countries and a short sample constrain inference; no models are estimated here.

For comparability with Beltrán (2025), the preferred financial variable remains documented J.P. Morgan EMBI Global country stripped spreads with matching aggregation. BCRP EMBIG is the closest downloaded candidate, conditional on confirming the exact definition. USD bond-yield spreads are a separate robustness measure; local-currency yields, CDS, and corporate index spreads are not interchangeable substitutes. The accessible 2023 working-paper version is informative, but the final 2025 paper’s exact data vintage and replication materials have not been verified.

Remaining review: country-specific industrial coverage and breaks; CPI rebasing and national coverage; private-credit borrower/institution perimeter; credit valuation and redenomination treatment; EMBIG stripped definition and constituent/duration metadata. GEM industrial production is labeled constant USD, seasonally adjusted, base 2005 by its catalog: the output preserves this measure and does not claim it is a newly verified physical-volume index. No country has been certified estimation-ready.

See sovereign_spread_options.md for ranked candidates and access distinctions, source_registry.csv for URLs and definitions, series_coverage.csv for exact month lists, and credit_lag_coverage.csv for calendar lag evidence.
