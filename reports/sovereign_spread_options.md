# Sovereign spread discovery and ranking

Audit date: October 18, 2026. A public description or country list is not evidence of retrieved history. “Not discovered” below does not mean historically unavailable. No category A series has been certified in this run.

## Search tiers and evidence

1. **Academic replication data.** [Uribe–Yue's author page](https://www.columbia.edu/~mu2166/uribe_yue_jie/uribe_yue_jie.html) links a ZIP, but requests with and without `www` returned 403. No observations or frequency are asserted from that archive. The accessible [Beltrán working-paper version](https://www.cemla.org/actividades/2023-final/2023-11-xxviii-meeting-of-the-central%E2%80%93bank%E2%80%93researchers-network/papers/4.1.2Beltran.pdf) motivates the EMBI choice; the final 2025 replication package and exact vintage were not verified.
2. **Public research catalogs.** World Bank [catalog 410](https://reproducibility.worldbank.org/catalog/410) explicitly excludes proprietary EMBI observations despite listing countries and a daily-data filename. [Catalog 644](https://reproducibility.worldbank.org/catalog/644) also requires independently authorized access. These inspected packages do not supply the requested free observations. This is not a claim about every academic package.
3. **Central-bank public data.** BCRP's [daily catalog](https://estadisticas.bcrp.gob.pe/estadisticas/series/diarias) supplied actual country EMBIG observations for six countries. [BCRP terms](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/condiciones-de-uso) permit reproduction with source attribution; this is not an unrestricted license to the underlying J.P. Morgan index. Chile's [BDE API](https://si3.bcentral.cl/estadisticas/Principal1/Web_Services/acceso_api_en.html) requires free registration and an activated token; no credentials were used. Historical Chile EMBIG tables predate the BCRP native monthly start, but that alone does not establish a complete API series.
4. **IMF SDMX government yields.** Current MFS_IR codelists were inspected. Test requests for `S13BONDSML_RT_PT_A_PT` for BRA and POL returned dataset metadata with no observations. A successful HTTP response is not successful observation retrieval. Denomination and maturity were not established; no spreads were calculated. This does not rule out other IMF yield keys.
5. **BIS SDMX.** The corrected v2 structure query returned the live dataflow catalog. Debt-security series describe stocks/issues and do not establish bond yields. No country USD sovereign-yield history was identified. BIS quarterly credit is not promoted to monthly data.
6. **FRED.** Actual GS2, GS5, GS7 and GS10 monthly Treasury observations were downloaded; all cover 2000–2019. They are percent yields and business-day averages, not country risk indicators. No verified country sovereign-spread substitute was retrieved. Corporate/emerging-market aggregate indices and bank lending-deposit spreads are not accepted as sovereign spreads.
7. **Other free sources.** No additional documented free API with the required twelve country histories was verified. The inspected BCRP Peru USD sovereign-yield series is a genuine category C candidate, discussed below. Broader discovery remains open for six economies.

## Classification

| Category | Meaning | Treatment |
|---|---|---|
| A | J.P. Morgan EMBI Global country stripped spread | Preferred; no freely retrieved series certified to this exact definition |
| B | Other USD sovereign spread | Downloaded BCRP EMBIG provisionally placed here until stripped definition is confirmed |
| C | USD sovereign yield | Peru 10-year candidate retrieved; no spread admitted without instrument/roll verification |
| D | Local-currency government yield | Separate financial variable; never Treasury-subtracted as an external sovereign spread |
| E | Sovereign CDS | Separate credit-risk instrument; none selected |
| F | Other risk indicator | Not an interchangeable substitute |

## Ranked choices by country

Rank 1 refers to the most usable **downloaded** candidate. Authorized category A data would remain preferable for every country if obtained and validated.

| Country | Rank 1 free candidate | Target observations | Rank 2 / remaining action |
|---|---|---:|---|
| Brazil | BCRP `PD04711XD`, daily EMBIG → monthly mean, B pending stripped confirmation | 240/240 | Native monthly `PN01131XM`: 161/240; do not splice. Authorized EMBIG stripped data for exact comparability |
| Mexico | BCRP `PD04713XD`, same treatment | 240/240 | Native monthly `PN01135XM`: 161/240; distinguish EMBI+ from EMBIG |
| Chile | BCRP `PD38581XD`, same treatment | 240/240 | Native monthly `PN01132XM`: 36/240. BDE token source merits validation; access not exercised |
| Colombia | BCRP `PD04715XD`, same treatment | 240/240 | Native monthly `PN01133XM`: 161/240 |
| Peru | BCRP `PD04709XD`, same treatment | 240/240 | Native monthly `PN01129XM`: 161/240. Category C `PD31894DD` is a separate robustness candidate |
| Argentina | BCRP `PD04710XD`, same treatment | 240/240 | Native monthly `PN01130XM`: 161/240. Defaults/restructurings can alter index constituents; inspect methodology |
| South Africa | No verified free country series downloaded | Not established | Seek authorized category A or documented USD sovereign bonds with full instrument histories; no invented identifier |
| Türkiye | No verified free country series downloaded | Not established | Same priority; local lira yields cannot substitute for USD spreads |
| Poland | No verified free country series downloaded | Not established | Same priority; IMF tested generic bond-yield key returned no observations |
| Malaysia | No verified free country series downloaded | Not established | Same priority; distinguish currency and index composition |
| Philippines | No verified free country series downloaded | Not established | Same priority; no validated daily/monthly sovereign spread key identified |
| Thailand | No verified free country series downloaded | Not established | Same priority; no validated daily/monthly sovereign spread key identified |

Each daily download uses `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/1999-1-1/2019-12-31/ing`. The exact executed URLs are saved in the raw manifests and source registry. Dates were parsed explicitly, including the provider's `Set` September abbreviation despite English output selection. Monthly means require 15 observed days and retain actual counts. These are daily-derived monthly observations, not native monthly source data. All target months passed that screen for the six downloaded series.

## Instrument metadata and yield construction

For the six EMBIG indices, denomination is USD external debt; issuer is the country sovereign/sovereign-guaranteed basket. Series identifiers are in the table. Maturity/duration varies; numerical historical duration, constituent bond identifiers, fixed-rate coverage and the provider's detailed roll rules were not retrieved. Therefore the registry explicitly records unknowns. The pipeline performs no individual-bond replacement. First/last **returned monthly** observations and exact missing months are in `series_coverage.csv`; query-window limits are not presented as global series inception dates.

The BCRP **Peru 10-year USD government bond yield** `PD31894DD` has real daily observations beginning July 30, 2009 in the downloaded window. Issuer: Republic of Peru; currency: USD; quoted horizon: 10 years; units: percent; frequency: daily. The ISIN, coupon type, actual residual maturity/duration, yield convention and security replacement history remain unknown. The 15-day monthly screen excludes the partial initial month. Coverage is separately audited as `usd_sovereign_yield_percent`, with BCRP attribution terms. No category C yield is inserted into the spread column.

If those metadata are established, a separate spread could be calculated as `100 * (USD sovereign yield percent - maturity-comparable Treasury yield percent)`. GS10 is only a candidate comparator: a generic “10-year” label does not prove an exact match. Match observation dates, maturity/duration and averaging before subtraction; retain differences in liquidity, sovereign credit/default risk, callable features and bond-specific terms. Document each roll and avoid jumps caused solely by replacing securities. This measure would not become EMBI-equivalent.

The source-comparison report shows differences between BCRP native monthly values and means of its daily values. These may reflect calendars, revisions or aggregation conventions; their cause was not established. The pipeline uses one consistent daily aggregation rule for all six countries and retains both versions for inspection.
