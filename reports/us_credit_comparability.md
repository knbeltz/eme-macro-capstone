# U.S. credit comparability assessment

The current selection is **FRED `LOANS`, monthly seasonally adjusted loans and leases in bank credit at all commercial banks**, in billions of U.S. dollars. It is an explicit **proxy**, not certified domestic private-nonfinancial credit. `us_nominal_credit` retains the original stock units; `us_credit_series_id` and `us_credit_measure` identify its meaning in each dataset row. The selected source and successful coverage are recorded in `us_source_registry.csv` and `us_series_coverage.csv`.

## Search and selection

The standardized IMF MFS ODC key used for the EME countries was tested for the United States: `USA.ODCORP_A_ACO_PS_ODCS.XDC.M`, current saved dataflow `IMF.STA:MFS_ODC(10.0.0)`. The server returned dataset metadata without observations. The inspected legacy NSRF private-credit query also returned metadata only. These outcomes do not prove historical U.S. private credit does not exist; they establish that these tested requests supplied no usable series.

Actual FRED metadata and monthly observations were then retrieved through the official API. Monthly H.8 variants were identified through their published FRED series pages. The following candidates were assessed:

| Candidate | Concept and frequency | Decision |
|---|---|---|
| IMF MFS ODC same aggregate as EME | Claims on private sector by other depository corporations; monthly requested | Conceptual first choice; no observations returned |
| `TOTLL` | Loans and leases; weekly | Not treated as native monthly data; monthly counterpart `LOANS` used |
| `LOANS` | Broad loans and leases; monthly | Selected proxy; avoids treating securities holdings as lending |
| `BUSLOANS` | Commercial and industrial loans; monthly | Retained optional component; omits household and many real-estate loans |
| `CONSUMER` | Consumer loans; monthly | Retained optional component; not all household borrowing |
| `REALLN` | Real-estate-secured loans; monthly | Retained optional component; mixes residential and business purposes |
| `TOTBKCR` | Total bank credit; weekly | Not treated as native monthly data |
| `LOANINV` | Total bank credit; monthly | Retained optional diagnostic; not selected because securities are included |

The component series are not added together and declared a verified household-plus-private-NFC aggregate. Loan purpose and collateral categories do not establish borrower residency, ownership and institutional sector. A narrower constructed sum would also omit relevant lending categories.

## Lender and borrower coverage

| Dimension | Existing EME selection | U.S. selected proxy |
|---|---|---|
| Lenders | IMF other depository corporations; country perimeter still requires review | H.8 commercial-bank universe |
| Nonbank deposit takers | May belong to ODC sector | Thrifts and credit unions excluded from H.8 |
| Nondeposit-taking lenders | Excluded from the selected ODC lender sector | Excluded as lenders |
| Borrowers | Claims on private sector; household/NFC/OFC perimeter not independently reconciled | Households and businesses plus other borrowers; not restricted to domestic private nonfinancial borrowers |
| Instruments | Claims aggregate; not verified as loans-only | Loans and leases; securities investments outside this aggregate |
| Timing/adjustment | Selected XDC stock; country timing and adjustment metadata require review | Seasonally adjusted monthly average stock |

The [H.8 methodology](https://www.federalreserve.gov/releases/h8/about.htm) defines its reporting universe and monthly averaging. It covers domestic commercial-bank offices and specified foreign-related offices; it excludes several other deposit-taking institutions. These lender differences prevent treating the two measures as harmonized.

The [H.8 release footnotes](https://www.federalreserve.gov/releases/h8/current/default.htm) show that broad loans include financial-sector and some public/foreign exposures. Loans to commercial banks and federal funds/reverse repos are separately excluded from this aggregate. Consumer, C&I and real-estate categories do not jointly establish a clean private-nonfinancial borrower perimeter. Therefore the proxy is not used as evidence that an equivalent monthly private-sector series has been found.

## Growth and CPI conventions

The requested primary U.S. measure is:

```text
real_credit[t] = nominal_credit[t] / (CPIAUCSL[t] / 100)
growth_yoy[t] = 100 × (ln(real_credit[t]) − ln(real_credit[t−12]))
```

The calendar is reindexed before applying lags. Missing or nonpositive inputs produce missing growth, without filling. `us_credit_growth_mom` uses a one-month log difference and is not annualized.

The existing EME growth measure uses an **arithmetic percentage change**, not a log difference. These formulas approximate one another for small changes but are not identical. The optional `us_credit_growth_yoy_pct` applies the existing EME formula to U.S. credit, allowing a consistent transformation without altering the EME file. Sectoral comparability remains unresolved even when growth formulas match.

U.S. CPIAUCSL is seasonally adjusted, whereas the EME pipeline uses nonseasonally-adjusted domestic CPI. CPI base constants cancel from growth, but adjustment conventions can still affect movements. The standalone U.S. file calls CPIAUCSL `us_cpi`; the combined file calls it `us_credit_cpi`, preserving the existing GEM-based `us_cpi` used for EME RER.

## Breaks and interpretation

The Federal Reserve's [H.8 historical notes](https://www.federalreserve.gov/releases/h8/h8notes.htm) identify 2010 Q1 off-balance-sheet consolidation under FAS 166/167, including loan-category effects. The March 2010 review flag is retained in `us_structural_breaks.csv`. H.8 publishes separately adjusted growth measures; the requested growth computed here from stock levels is not automatically that adjusted measure. Acquisitions, accounting changes, charge-offs, and reclassifications can affect measured growth. No automatic break correction or splice is applied.

This is outstanding credit growth, not gross new loans, a transaction-adjusted lending flow, or an identified credit-supply shock. It is appropriate only as a clearly labeled robustness/proxy series until a harmonized borrower/lender definition is established. The final definitions and data vintage in Beltrán (2025) have not been fully reconciled; no exact replication claim is made.
