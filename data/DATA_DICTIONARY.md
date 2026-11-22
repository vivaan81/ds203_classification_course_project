# Data Dictionary: `hdi_dataset_2023.csv`

One row per country, reference year **2023**. 193 countries.
Built by `src/build_dataset.py`. To rebuild:

```bash
PYTHONPATH= .venv/bin/python src/build_dataset.py            # uses cached raw files in data/raw/
PYTHONPATH= .venv/bin/python src/build_dataset.py --refresh  # re-download from sources
```

## Sources (accessed 2026-11-22)

| Source | What | URL |
|---|---|---|
| UNDP Human Development Report 2025 (HDR25), composite indices time series | HDI score for 2023 (target) | https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv |
| World Bank World Development Indicators, API v2 | 9 predictor indicators | `https://api.worldbank.org/v2/country/all/indicator/<code>?format=json&date=2015:2023` |
| World Bank country API | Region, aggregate flag | https://api.worldbank.org/v2/country?format=json |

Raw downloads are saved unchanged in `data/raw/`. Access dates are recorded in `data/raw/access_log.json`.

## Columns

| Column | Type | Description | Role |
|---|---|---|---|
| `iso3` | str | ISO 3166-1 alpha-3 code (merge key) | Identifier, **not a predictor** |
| `country` | str | Country name (UNDP spelling) | Identifier, **not a predictor** |
| `hdi` | float | UNDP HDI score, 2023 | Target source, **never a predictor** |
| `hdi_class` | int | Target: `0` Low (HDI < 0.550), `1` Medium/High (0.550 ≤ HDI < 0.800), `2` Very High (HDI ≥ 0.800) | **Target** |
| `region` | cat | World Bank geographic region (7 levels) | Categorical predictor |
| `gdp_growth` | float | `NY.GDP.MKTP.KD.ZG`: GDP growth, annual % | Numerical predictor |
| `inflation` | float | `FP.CPI.TOTL.ZG`: inflation, consumer prices, annual % | Numerical predictor |
| `unemployment` | float | `SL.UEM.TOTL.ZS`: unemployment, % of labor force (modeled ILO estimate) | Numerical predictor |
| `infant_mortality` | float | `SP.DYN.IMRT.IN`: infant deaths per 1,000 live births | Numerical predictor |
| `electricity_access` | float | `EG.ELC.ACCS.ZS`: access to electricity, % of population | Numerical predictor |
| `internet_users` | float | `IT.NET.USER.ZS`: individuals using the Internet, % of population | Numerical predictor |
| `agriculture_share` | float | `NV.AGR.TOTL.ZS`: agriculture, forestry and fishing value added, % of GDP | Numerical predictor |
| `industry_share` | float | `NV.IND.TOTL.ZS`: industry (incl. construction) value added, % of GDP | Numerical predictor |
| `trade` | float | `NE.TRD.GNFS.ZS`: trade, % of GDP | Numerical predictor |
| `DominantSector` | cat | Engineered: Agriculture / Industry / Services, whichever share is largest (rules below) | Categorical predictor |
| `services_share_est` | float | 100 − agriculture − industry (only when valid) | Helper for DominantSector, **not a predictor** (it's redundant with the two shares) |
| `<feature>_year` | int | Year the value was taken from (2023, or earlier under the look-back rule) | Provenance, **not a predictor** |

Excluded by design to prevent target leakage: HDI category, life expectancy, expected and mean years of schooling, GNI per capita. World Bank *income level* is also excluded, because it is defined from GNI per capita.

## Construction rules

1. **Aggregates removed.** UNDP rows with `iso3` starting `ZZ` (regional and world totals) and World Bank entries with region `Aggregates` are dropped.
2. **Country matching** is an inner join on ISO3. All 195 UNDP countries matched a World Bank country, so no manual code corrections were needed. 22 World Bank economies have no UNDP HDI and are excluded: ABW, ASM, BMU, CHI, CUW, CYM, FRO, GIB, GRL, GUM, IMN, MAC, MAF, MNP, NCL, PRI, PYF, SXM, TCA, VGB, VIR, XKX. These are mostly territories, plus Kosovo.
3. **Lost for missing HDI label:** 2 countries, North Korea (PRK) and Monaco (MCO).
4. **Year selection.** Each predictor uses its 2023 value. If that is missing, it uses the most recent value from **2020–2022** (a 3-year look-back). Values after 2023 are never used. The year actually used is in `<feature>_year`.
   - Values substituted from an earlier year: gdp_growth 1, inflation 3, unemployment 3, internet_users 6, agriculture_share 3, industry_share 3, trade 3.
   - Strict 2023 only would leave 102 missing cells. The 3-year look-back leaves 80, and 5 years would leave 70. 3 years was chosen to balance coverage against year mismatch.
5. **DominantSector.** Services = 100 − agriculture − industry. The category is the largest of the three shares. It is set to missing if either input is missing, if the two inputs come from different years, or if any share falls outside [0, 100].
6. **Missing predictor values are preserved** (not imputed) for the preprocessing exercise.
7. **Extreme values are kept.** They are verified real events: inflation in Lebanon (221%), Sudan (139%), Argentina (134%) and Zimbabwe (105%); GDP growth in Sudan (−29%, conflict) and Guyana (+34%, oil boom); trade above 280% of GDP for trade hubs (Luxembourg, Hong Kong, San Marino, Singapore, Djibouti).

## Summary

- Final countries: **193**
- Class counts: Low **26**, Medium/High **93**, Very High **74**. Imbalanced, with the minority class at 13%.
- Missing rate: trade 11.9%, inflation 7.8%, unemployment 7.3%, internet 4.1%, agriculture/industry/DominantSector 3.6%, GDP growth 2.1%, infant mortality 1.0%, electricity 0%, region 0%.
- DominantSector: Services 176, Industry 8 (oil and gas economies), Agriculture 2 (Niger, Chad), missing 7. The feature is highly imbalanced, so expect limited predictive value.

Running the build script prints these summary figures to the terminal.
