# Data and sources overview

Prepared October 26, 2026. This document describes the observations delivered in this project, their construction, and their saved sources. Coverage dates refer to the delivered sample, not the full historical coverage available from a provider.

## Dataset structure

The research sample is **January 2000–December 2019**, at monthly frequency. Dates are represented as `YYYY-MM`.

- [Final combined panel](../data/processed/eme_us_monthly_panel.csv): 2,880 rows, comprising 240 months for each of 12 emerging-market countries. U.S. variables are joined by month and repeat across all countries for that month.
- [EME-only panel](../data/processed/eme_monthly_panel.csv): the original country variables, without the U.S. extension.
- [Standalone U.S. dataset](../data/processed/us_monthly_macro.csv): 240 monthly rows.
- [Standalone monthly FF4 dataset](../data/processed/us_ff4_monthly.csv): 240 monthly rows, including event counts.

The United States is represented by shared monthly variables in the combined panel; it is not an additional country block in the 2,880-row panel. The standalone U.S. file supplies its own monthly observations. A country-month row may contain missing values. Missing source observations are not interpolated or carried forward.

## Emerging-market variables and sources

| Data | CSV columns | Source and definition |
|---|---|---|
| Nominal exchange rate | `nominal_fx` | World Bank Global Economic Monitor (GEM), source 15, indicator `DPANUSSPB`: period-average new local-currency units per USD. Earlier observations are expressed in the new currency units. |
| Domestic CPI | `domestic_cpi` | World Bank GEM `CPTOTNSXN`, all-items CPI, not seasonally adjusted. Argentina instead uses IMF CPI `ARG.CPI._T.IX.M`, available in this sample from December 2016. |
| U.S. CPI for real exchange rates | `us_cpi` | World Bank GEM `CPTOTNSXN` for the United States; not seasonally adjusted. |
| Real exchange rate and log | `real_fx`, `log_real_fx` | Calculated as `nominal_fx × us_cpi / domestic_cpi`; then its natural logarithm. This is a bilateral USD real exchange rate. An increase denotes depreciation under this quotation. |
| Industrial production and log | `industrial_production`, `log_ip` | World Bank GEM `IPTOTSAKD`, seasonally adjusted production in constant USD, base year 2005 according to the inspected catalog; then its natural logarithm. Country-specific scope and comparability require review. |
| Nominal private credit | `nominal_private_credit` | IMF MFS_ODC, dataset `IMF.STA:MFS_ODC(10.0.0)`, key `{ISO3}.ODCORP_A_ACO_PS_ODCS.XDC.M`: claims on the private sector by other depository corporations, in domestic currency. |
| Real private credit | `real_private_credit` | `nominal_private_credit / (domestic_cpi / 100)`. |
| Annual real credit growth | `real_credit_growth_yoy` | `100 × (real_private_credit[t] / real_private_credit[t−12] − 1)`, using calendar-month lags. |
| Sovereign spread | `sovereign_spread_bp` | BCRP-published EMBIG daily series, attributed to Reuters/J.P. Morgan, averaged by calendar month with at least 15 nonmissing daily observations. Values are basis points. |
| Identification and spread description | `country`, `iso3`, `date`, `sovereign_spread_type` | Country/month identifiers and a source-definition label; these are metadata rather than additional economic measures. |

The arbitrary CPI base affects real levels but cancels from growth calculations. Real exchange-rate levels should not be interpreted as cross-country purchasing-power comparisons. Nonpositive inputs are excluded where logarithms or positive denominators are required.

### Coverage by country

**All 12 countries have nominal exchange rates, industrial production and its log, and the shared GEM U.S. CPI for every month from January 2000 through December 2019.** The table gives coverage of the remaining variables. There are no internal missing months within the available ranges shown.

| Country (ISO3) | Domestic CPI, real FX and log real FX | Nominal private credit | Real private credit | Annual real credit growth | Sovereign spread |
|---|---|---|---|---|---|
| Brazil (BRA) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | 2000-01–2019-12 |
| Mexico (MEX) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | 2000-01–2019-12 |
| Chile (CHL) | 2000-01–2019-12 | 2000-01–2019-12 | 2000-01–2019-12 | 2000-01–2019-12 | 2000-01–2019-12 |
| Colombia (COL) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | 2000-01–2019-12 |
| Peru (PER) | 2000-01–2019-12 | 2006-01–2019-12 | 2006-01–2019-12 | 2007-01–2019-12 | 2000-01–2019-12 |
| Argentina (ARG) | 2016-12–2019-12 | 2010-01–2019-12 | 2016-12–2019-12 | 2017-12–2019-12 | 2000-01–2019-12 |
| South Africa (ZAF) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | Unavailable |
| Türkiye (TUR) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | Unavailable |
| Poland (POL) | 2000-01–2019-12 | 2004-01–2019-12 | 2004-01–2019-12 | 2005-01–2019-12 | Unavailable |
| Malaysia (MYS) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | Unavailable |
| Philippines (PHL) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | Unavailable |
| Thailand (THA) | 2000-01–2019-12 | 2001-12–2019-12 | 2001-12–2019-12 | 2002-12–2019-12 | Unavailable |

Annual credit growth generally starts 12 months after real credit becomes available. Earlier saved observations supply the lags needed for Chile's January 2000 growth observation. Argentina's CPI availability limits both real credit and real exchange-rate coverage even though some nominal inputs extend further back.

### Sovereign-spread series

| Country | BCRP daily series code |
|---|---|
| Brazil | `PD04711XD` |
| Mexico | `PD04713XD` |
| Chile | `PD38581XD` |
| Colombia | `PD04715XD` |
| Peru | `PD04709XD` |
| Argentina | `PD04710XD` |

The other six countries have no admitted sovereign-spread observations in the delivered panel. The selected series are labeled **EMBIG; stripped definition unconfirmed**. The 15-observation threshold screens sparse months; it does not establish complete trading-day coverage. No substitute spread or bond splice is used.

## United States variables and sources

FRED series are retrieved through the official FRED API. The original producer is indicated below. All ranges are inclusive.

| Data | CSV columns | Delivered coverage | Source |
|---|---|---|---|
| Effective federal funds rate | `us_federal_funds_rate` | 2000-01–2019-12 (240 months) | FRED `FEDFUNDS`; Federal Reserve; monthly rate level in percent, not seasonally adjusted |
| Nominal personal consumption expenditure and log | `us_pce_nominal`, `us_log_pce` | 2000-01–2019-12 (240) | FRED `PCE`; BEA; billions of dollars at a seasonally adjusted annual rate; log calculated locally |
| Real personal consumption expenditure and log | `us_pce_real`, `us_log_pce_real` | 2007-01–2019-12 (156) | FRED `PCEC96`; BEA; billions of chained 2017 dollars at a seasonally adjusted annual rate in the saved snapshot |
| Industrial production and log | `us_industrial_production`, `us_log_ip` | 2000-01–2019-12 (240) | FRED `INDPRO`; Federal Reserve; seasonally adjusted index, 2017=100 in the inspected metadata |
| CPI for credit deflation | `us_cpi` in the U.S. file; `us_credit_cpi` in the combined panel | 2000-01–2019-12 (240) | FRED `CPIAUCSL`; BLS; seasonally adjusted CPI |
| Selected nominal credit proxy | `us_nominal_credit`, `us_credit_loans_h8` | 2000-01–2019-12 (240) | FRED `LOANS`; Federal Reserve H.8 commercial-bank loans and leases; billions of USD, seasonally adjusted |
| Commercial and industrial loans | `us_credit_ci_h8` | 2000-01–2019-12 (240) | FRED `BUSLOANS`; Federal Reserve H.8 |
| Consumer loans | `us_credit_consumer_h8` | 2000-01–2019-12 (240) | FRED `CONSUMER`; Federal Reserve H.8 |
| Real estate loans | `us_credit_real_estate_h8` | 2000-01–2019-12 (240) | FRED `REALLN`; Federal Reserve H.8 |
| Total bank credit | `us_total_bank_credit_h8` | 2000-01–2019-12 (240) | FRED `LOANINV`; Federal Reserve H.8 |
| Real credit | `us_real_credit` | 2000-01–2019-12 (240) | Selected nominal credit divided by `(CPIAUCSL / 100)` |
| Annual real credit growth | `us_credit_growth_yoy` | 2000-01–2019-12 (240) | `100 × (ln(real_credit[t]) − ln(real_credit[t−12]))` |
| Monthly real credit growth | `us_credit_growth_mom` | 2000-01–2019-12 (240) | `100 × (ln(real_credit[t]) − ln(real_credit[t−1]))` |
| Annual arithmetic real credit growth | `us_credit_growth_yoy_pct` | 2000-01–2019-12 (240) | `100 × (real_credit[t] / real_credit[t−12] − 1)`; matches the EME growth convention |
| Credit source descriptions | `us_credit_series_id`, `us_credit_measure` | 2000-01–2019-12 (240) | Metadata identifying the selected `LOANS` proxy |

Saved 1999 credit and CPI observations supply the lags required for growth at the start of 2000. The saved real-PCE response leaves January 2000–December 2006 missing; no replacement series is used to fill those 84 months.

The two U.S. CPI series have different roles: the original GEM `us_cpi` remains in the combined panel for real exchange rates, while the FRED seasonally adjusted CPI is appended as `us_credit_cpi` for U.S. credit deflation.

## USMPD FF4 addition

The source is the supplied **United States Monetary Policy Event-Study Database (USMPD)** workbook, archived as [USMPD.xlsx](../data/raw/usmpd/USMPD.xlsx). Its README identifies the Federal Reserve Bank of San Francisco's Center for Monetary Research, a September 17, 2026 update, and LSEG Tick History and author calculations as the underlying source. The source reference is Acosta, Ajello, Bauer, Loria, and Miranda-Agrippino (2025), *Financial Market Effects of FOMC Communication: Evidence from a New Event-Study Database*, FRBSF Working Paper 2025-30.

The importer uses only `Date` and `FF4` from **Monetary Events**. This sheet uses the combined window from 10 minutes before the statement to 60 minutes after the start of the press conference; when no press conference occurred, it uses the statement window. It does not add overlapping statement and press-conference sheets together.

FF4 already measures an event-window change in the fourth monthly federal funds futures contract's implied rate. The workbook reports interest-rate changes in **percentage points**.

| CSV column | Construction | Delivered coverage |
|---|---|---|
| `us_ff4_monthly_change_pp` | Sum of all FF4 event changes in the calendar month | 2000-01–2019-12; 240 months |
| `us_ff4_mom_change_pp` | Current monthly total minus previous monthly total | 2000-01–2019-12; December 1999 supplies the initial comparison |
| `us_ff4_event_count` | Number of source events in the month | 2000-01–2019-12 |
| `us_ff4_observed_event_count` | Number of those events with nonmissing FF4 | 2000-01–2019-12 |

For example, event changes of `0.02` and `−0.05` produce a monthly total of `−0.03` percentage points, equivalent to −3 basis points. A month with no events receives a zero total by construction. A month containing an event with missing FF4 would remain missing. In the delivered sample there are 170 events, 77 months with no events, and no missing monthly totals.

The monthly total is the aggregated event-change measure. Its month-to-month difference is a separate transformation of those totals, not a change in a monthly futures-rate level. Neither column is a percentage-growth calculation. Both repeat across countries in the combined panel because they measure U.S. events shared by all countries.

## Where to locate sources and audit records

Paths below are relative to the project root.

| Location | Contents |
|---|---|
| `data/raw/` | Archived provider response bytes and request manifests; provider/country subdirectories |
| `data/raw/fred_api/USA/` | Saved official FRED API metadata and observations |
| `data/raw/usmpd/USMPD.xlsx` | Archived supplied FF4 workbook |
| `data/normalized/{ISO3}/` | Replayable country-specific source CSVs |
| `data/normalized/USA/usmpd_ff4_events.csv` | Imported event dates and FF4 values, including dates outside the target sample |
| `data/processed/` | Delivered panels and standalone monthly outputs |
| [EME source registry](source_registry.csv) | Exact provider API URLs, dataset/series codes, units, definitions and source notes |
| [EME series coverage](series_coverage.csv) | Returned historical bounds, in-sample coverage, missing counts and retrieval status; filter `selected=True` for admitted inputs |
| [U.S. source registry](us_source_registry.csv) | FRED source pages, original producers, units, seasonal adjustment, API URLs and saved vintage metadata |
| [U.S. series coverage](us_series_coverage.csv) | Raw and derived U.S. coverage and transformations |
| [FF4 source record](us_ff4_source.json) | Workbook SHA256, selected sheet, units and aggregation rules |
| [EME missing months](missing_months.csv), [U.S. missing months](us_missing_months.csv) | Explicit missing-observation records |
| [EME credit lag coverage](credit_lag_coverage.csv), [U.S. credit lag coverage](us_credit_lag_coverage.csv) | Availability of current and lagged inputs used in annual growth |

Provider entry points recorded by the project include [World Bank GEM](https://datacatalog.worldbank.org/infrastructure-data/search/dataset/0037798/global-economic-monitor), [IMF MFS_ODC](https://data.imf.org/Datasets/MFS_ODC), [BCRP daily series](https://estadisticas.bcrp.gob.pe/estadisticas/series/diarias), [FRED](https://fred.stlouisfed.org/), and [USMPD](https://sffed.us/usmpd). The local registries are the authoritative record of the exact requests used in this project.

## Interpretation and limitations

- This is a provisional research dataset. Numerical availability does not establish that every country's definitions, institutional coverage and historical breaks are comparable. Research-clearance flags remain separate from complete-case counts.
- The EME credit measure covers claims by other depository corporations on the private sector. The U.S. selected measure is an H.8 commercial-bank loans-and-leases proxy. Their lender and borrower perimeters are not fully harmonized. See [U.S. credit comparability](us_credit_comparability.md).
- Primary U.S. credit growth uses log differences; EME credit growth uses arithmetic percentage changes. Use the optional U.S. arithmetic column when that convention is required.
- EME domestic CPI is not seasonally adjusted; U.S. credit CPI is seasonally adjusted. GEM industrial-production scope and the sovereign-spread definition still require source review.
- Argentina's earlier CPI is not spliced into the selected national series. Missing early real variables are retained as missing.
- Saved observations reflect the providers' historical data at the archived snapshot, including revisions; they are not historical real-time information sets.
- The effective federal funds rate is an observed rate level. FF4 measures high-frequency event changes. The pipeline does not establish exogeneity, estimate a VAR, or certify a replication of a particular paper.

For additional country and source caveats, see [EME research findings](research_findings.md), [U.S. research findings](us_research_findings.md), and [sovereign-spread options](sovereign_spread_options.md).

## Reproduction

See the [project README](../README.md) for complete setup and download instructions. With the saved source caches present:

```sh
.venv/bin/python download.py --offline
.venv/bin/python data_finder.py --include-us --us-offline
```

To import or refresh the FF4 source and append it to the existing U.S. and combined outputs:

```sh
.venv/bin/python ff4_data_finder.py "data/raw/usmpd/USMPD.xlsx"
```

The U.S. builder also retains the FF4 extension when its normalized event source exists. All coverage figures in this document describe the saved files inspected on the preparation date; regenerate and review this overview if source selection or coverage changes.
