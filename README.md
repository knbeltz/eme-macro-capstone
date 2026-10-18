# Monthly emerging-market macroeconomic data audit

This pipeline retrieves real observations and produces a **provisional research panel**, not a certified complete twelve-country dataset. The checked run on October 18, 2026 has 2,880 country-month rows for January 2000–December 2019. Empty fields remain empty. Chile has 240 numerical complete cases; no country is yet cleared for estimation because important source-definition checks remain unresolved. See [research findings](reports/research_findings.md) for country results and shorter-sample comparisons.

## Reproduce

Python 3.11+ is required; this run used Python 3.14. No credentials are required by the selected endpoints.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Inspect current catalogs and save original responses before downloading:
.venv/bin/python discover.py
.venv/bin/python discover.py --structures
.venv/bin/python discover.py --alternatives
.venv/bin/python discover.py --extra
.venv/bin/python discover.py --legacy-credit
# Retrieve selected series and normalize the provider responses:
.venv/bin/python download.py
# Build panel, raw/derived/candidate audits and research findings:
.venv/bin/python data_finder.py
.venv/bin/python -m pytest -q
```

The raw responses supplied with this workspace support a network-free replay:

```sh
.venv/bin/python download.py --offline
.venv/bin/python data_finder.py
.venv/bin/python -m pytest -q
```

Successful HTTP responses are cached. Re-running normally reuses them; it does not silently replace the data vintage. To obtain a fresh vintage, run in a separate copy without `data/raw/` and `data/normalized/`, retaining this copy for comparison. `requirements.txt` permits compatible Python 3.11+ dependency resolution; `requirements-tested.txt` records the exact packages tested on Python 3.14.

`discover.py` logs HTTP status, including failed discovery attempts; optional candidates are not all usable. Download failures cause a nonzero exit and are written to `reports/download_status.json`. A failed normalized series is quarantined as `.stale.csv` so it cannot silently enter the panel. HTTP 200 alone does not establish data availability: some IMF queries return only dataset metadata, with no observations.

## Files

- `data/raw/{provider}/{country}/`: exact response bytes (`.body`) and matching JSON manifest with exact request URL, retrieval timestamp, HTTP status, hash, and errors. Catalogs live under `metadata/`. Request parameters include pagination. No secrets are stored.
- `data/normalized/`: replayable intermediate CSVs retaining provider attributes where returned. Dates outside the target sample are retained for audits and lag construction.
- `data/processed/eme_monthly_panel.csv`: the requested columns, 240 rows per country. Dates are calendar months, represented as `YYYY-MM`.
- `reports/series_coverage.csv`: selected raw inputs, transformations, and inspected alternatives. Filter `selected=True` for inputs to the delivered panel. Earliest/latest refer to **nonmissing observations returned**, with query-window bounds documented; they are not claims about the source's entire historical universe.
- `reports/missing_months.csv`: exact missing country-variable-source-months, with selected/candidate distinction. Derived failures include absent and nonpositive inputs.
- `reports/country_eligibility.csv`: numerical completeness across the four variables and a separate `research_cleared` flag. Never use the former as proof of economic comparability.
- `reports/credit_lag_coverage.csv`: both current and twelve-month-lag credit/CPI availability.
- `reports/source_registry.csv`: definitions, keys, licensing, endpoints, caveats and instrument metadata when known.
- `reports/sovereign_spread_options.md`: ranked options and access/definition limitations for all twelve countries.
- `reports/sample_scenarios.csv`: observed intersections for alternative windows; no imputation.
- `reports/spread_source_comparison.csv`: daily-derived versus native monthly EMBIG overlap differences.
- `reports/observation_flags.csv`: adjacent raw-series changes above 100% or below -50%, flagged for review without deleting observations. Economic movements can trigger these flags; they do not prove a break.
- `reports/research_findings.md`: the seven requested research conclusions, with unresolved work explicit.

## Source selection and transformations

**Exchange rates:** World Bank GEM source 15, `DPANUSSPB`, was discovered in the live catalog. It is new local currency per USD, period average, with earlier observations expressed in the new currency. `real_fx = nominal_fx * us_cpi / domestic_cpi`, and `log_real_fx = ln(real_fx)`. This is bilateral USD real FX, not REER. A higher value denotes depreciation under this quotation. CPI base constants make RER levels arbitrary across countries; use within-country logs/changes or an explicitly documented rebasing for comparisons. Do not interpret cross-country levels as purchasing-power parity.

**CPI:** GEM `CPTOTNSXN`, not seasonally adjusted, is selected for the US and eleven domestic series. The inspected catalog does not specify its base. Argentina's GEM response has no target observations; the alternative IMF key `ARG.CPI._T.IX.M`, from current CPI version 5.0.0, supplies the national index from December 2016. The earlier CPI is not spliced in. Raw responses retain reference-period and other attributes.

**Industrial production:** GEM `IPTOTSAKD`, seasonally adjusted, is described by the catalog as manufacturing, mining and utilities in constant USD, base year 2005. The panel preserves returned levels and computes `log_ip`. It does **not** relabel these levels as a verified physical-volume index. Country-specific coverage can differ, and national source validation remains necessary, particularly for possible manufacturing-only proxies. No seasonally unadjusted or manufacturing series is silently substituted.

**Credit:** IMF current `IMF.STA:MFS_ODC(10.0.0)`, `{ISO3}.ODCORP_A_ACO_PS_ODCS.XDC.M`: assets, claims on the private sector by other depository corporations, in domestic-currency valuation. This is a stock, not new lending or credit/GDP. Commercial banks and other deposit-taking institutions belong to the lender sector; nondeposit-taking financial institutions are excluded as lenders. Household, private NFC and other financial corporation borrower detail and country-specific institutional coverage are not fully established by the aggregate key. These limitations are recorded, not assumed away.

The current IMF CSV export supplies domestic-currency `OBS_VALUE` in unscaled units; `SCALE` is retained as a presentation attribute, not multiplied into values a second time. For example, Brazil December 2001 is about BRL 381.6 billion in the response. Validate export conventions again if changing API formats. `real_private_credit = nominal_private_credit / (domestic_cpi / 100)`; the arbitrary CPI reference scales levels but cancels from growth. `real_credit_growth_yoy = 100 * (real_credit[t] / real_credit[t-12] - 1)` uses calendar reindexing before lagging. No implicit filling is used.

Legacy nonstandard IMF `NSRF_22D` credit candidates are separately downloaded and audited. Their longer early history is not a license to splice them into standardized MFS_ODC. Reconcile the overlaps, currency valuation, lender and borrower perimeters, and any changes before implementing such a bridge.

**Spreads:** six BCRP country EMBIG daily series were verified and downloaded. The single daily series for each country is averaged by month with at least 15 nonmissing daily observations; holidays are not filled. This minimum is a sparse-month screen, **not** a verified trading-calendar completeness test. Original daily bytes and monthly observation counts are retained. Native BCRP monthly series have later start dates and modest overlap differences, recorded separately. The chosen monthly series is entirely derived from daily data, with no splice.

These spreads are labeled **B: EMBIG; stripped definition unconfirmed**. The examined descriptions do not establish the specific stripped-spread convention needed for category A. Category C Peruvian USD 10-year sovereign yields were also retrieved, but no constructed spread is admitted because exact bond identifiers, fixed coupons, residual maturity and roll rules were not verified. FRED GS2/GS5/GS7/GS10 benchmarks were retrieved and audited; no local-currency yield is subtracted from them.

## Known breaks, quality and access issues

- Türkiye: the central bank documents removal of six zeros in January 2005. The selected GEM FX definition explicitly expresses earlier data in new currency units; do not divide it by a million again. Credit redenomination and currency-valuation comparability still require country metadata review.
- Argentina: the IMF documented serious earlier official CPI quality issues and later changes in geographic coverage/methodology. Only the retrieved current national index is selected. Official FX is not a substitute for an unobserved parallel-market exchange rate.
- Malaysia and Argentina have historical exchange-rate regime changes; a peg or a regime change is not itself a missing observation. Their empirical implications need modeling decisions. Country notes have not been exhaustively reconciled for all twelve economies.
- Credit includes valuation effects, particularly FX-denominated claims converted into domestic currency, as well as write-offs/reclassifications. Growth is not automatically a lending-flow or credit-supply shock measure.
- IMF IFS has moved to topic datasets. This pipeline uses the current discovered MFS and CPI dataflows, not legacy `dataservices.imf.org` endpoints. The public dataflow endpoint worked in this run even though the official Swagger portal requires sign-in.
- The first BIS discovery attempt used an unsupported route and returned 501; the corrected documented v2 structure route worked. The manifest preserves both outcomes. The catalog's debt-security stocks/issuance and quarterly credit are not substitutes for monthly sovereign yield spreads or monthly private credit.
- Columbia replication ZIP retrieval returned HTTP 403 in this environment. World Bank catalogs explicitly exclude the inspected proprietary EMBI files. These are access restrictions, not evidence of historical missingness. Chile BDE offers free registration/token access, but no credentials were supplied and no historical observations from it are claimed.

The selected downloads contain no credentials. If adding credentialed adapters, read credentials from environment variables (for example `FRED_API_KEY` or `BCCH_API_TOKEN`), redact them from logs, and do not put credential-bearing URLs in the cache manifest.

## Validation and limitations

Tests cover the 240-month calendar, duplicate quarantine, missing dates/nulls, frequency rejection, RER/log/credit transformations, twelve-month missing-lag propagation, unit/currency and basis-point guards, complete-case intersections, and the delivered panel. Requests use bounded connect/read timeouts, retry/backoff for transient failures and 429s, and 250ms spacing; World Bank pagination is explicit. Other selected endpoints return whole series; no undocumented pagination is assumed.

No interpolating, carrying forward, extrapolating, fabricated observations, or automatic bond splicing occurs. `research_cleared=False` deliberately distinguishes a numerical audit from full methodological validation. The pipeline does not fetch monetary policy shock instruments, estimate VARs, or claim to replicate Beltrán's results; those are outside the four-variable data deliverable.

Primary references: [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures), [GEM catalog](https://datacatalog.worldbank.org/infrastructure-data/search/dataset/0037798/global-economic-monitor), [IMF API](https://data.imf.org/en/Resource-Pages/IMF-API), [IFS transition](https://data.imf.org/ifs), [MFS ODC](https://data.imf.org/Datasets/MFS_ODC), [BCRP API](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api), [BCRP daily catalog](https://estadisticas.bcrp.gob.pe/estadisticas/series/diarias), [BIS API](https://stats.bis.org/api-doc/v2/), [TCMB currency reform](https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB%2BEN/Main%2BMenu/About%2Bthe%2BBank/History/Our%2BHistory/), [IMF Argentina CPI statement](https://www.imf.org/en/news/articles/2015/09/14/01/49/pr1333).
