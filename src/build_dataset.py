# Builds the country-level dataset for our DS203 HDI classification project.
#
# What it does:
#   1. downloads the UNDP HDI table (our target) and the World Bank indicators + country list
#   2. keeps only actual countries (drops regional / world totals)
#   3. picks one value per country and indicator: the 2023 value, or if that's missing,
#      the latest value from 2020-2022 (we never use anything after 2023)
#   4. merges everything on the ISO3 country code and builds the target and DominantSector
#   5. saves the result to data/hdi_dataset_2023.csv
#
# The raw downloads are kept in data/raw/ so the build can be re-run without internet.
#
# How to run (from the project folder):
#   python src/build_dataset.py              -> uses the files in data/raw/ if they exist
#   python src/build_dataset.py --refresh    -> downloads everything again

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUT_DIR = PROJECT_DIR / "data"

REF_YEAR = 2023
HDI_URL = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
           "HDR25_Composite_indices_complete_time_series.csv")
WB_API = "https://api.worldbank.org/v2"

# World Bank indicator code -> short column name we use
INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",
    "FP.CPI.TOTL.ZG": "inflation",
    "SL.UEM.TOTL.ZS": "unemployment",
    "SP.DYN.IMRT.IN": "infant_mortality",
    "EG.ELC.ACCS.ZS": "electricity_access",
    "IT.NET.USER.ZS": "internet_users",
    "NV.AGR.TOTL.ZS": "agriculture_share",
    "NV.IND.TOTL.ZS": "industry_share",
    "NE.TRD.GNFS.ZS": "trade",
}

# we download a few extra years so we can compare different look-back windows
FIRST_YEAR = 2015


def get_world_bank(path, params):
    # the World Bank API returns JSON split into pages, so keep asking until we have every page
    rows = []
    page = 1
    while True:
        params_with_page = dict(params, format="json", per_page=20000, page=page)
        response = requests.get(f"{WB_API}/{path}", params=params_with_page, timeout=120)
        response.raise_for_status()
        info, data = response.json()
        if data:
            rows.extend(data)
        if page >= info["pages"]:
            return rows
        page += 1


def download_raw_data(refresh):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # small log of where each file came from and when we downloaded it
    log_file = RAW_DIR / "access_log.json"
    if log_file.exists():
        log = json.loads(log_file.read_text())
    else:
        log = {}

    # 1) UNDP HDI table
    hdi_file = RAW_DIR / "HDR25_Composite_indices_complete_time_series.csv"
    if refresh or not hdi_file.exists():
        response = requests.get(HDI_URL, timeout=300)
        response.raise_for_status()
        hdi_file.write_bytes(response.content)
        log["undp_hdi"] = {"url": HDI_URL, "accessed": str(date.today())}
    if "undp_hdi" not in log:
        log["undp_hdi"] = {"url": HDI_URL, "accessed": str(date.today())}

    # 2) World Bank country list (gives us the region of each country)
    countries_file = RAW_DIR / "wb_countries.csv"
    if refresh or not countries_file.exists():
        countries = get_world_bank("country", {})
        rows = []
        for c in countries:
            rows.append({
                "iso3": c["id"],
                "wb_name": c["name"],
                "region": c["region"]["value"],
                "region_id": c["region"]["id"],
            })
        pd.DataFrame(rows).to_csv(countries_file, index=False)
        log["wb_countries"] = {"url": f"{WB_API}/country?format=json", "accessed": str(date.today())}

    # 3) World Bank indicators, saved in long format (one row per country, indicator and year)
    indicators_file = RAW_DIR / "wb_indicators_long.csv"
    if refresh or not indicators_file.exists():
        rows = []
        for code in INDICATORS:
            data = get_world_bank(f"country/all/indicator/{code}", {"date": f"{FIRST_YEAR}:{REF_YEAR}"})
            for x in data:
                if x["countryiso3code"]:
                    rows.append({
                        "iso3": x["countryiso3code"],
                        "indicator": code,
                        "year": int(x["date"]),
                        "value": x["value"],
                    })
            print(f"  downloaded {code}: {len(data)} rows")
        pd.DataFrame(rows).to_csv(indicators_file, index=False)
        log["wb_indicators"] = {
            "url": f"{WB_API}/country/all/indicator/<code>?format=json&date={FIRST_YEAR}:{REF_YEAR}",
            "codes": list(INDICATORS),
            "accessed": str(date.today()),
        }

    log_file.write_text(json.dumps(log, indent=2))
    return hdi_file, countries_file, indicators_file


def pick_year(long_df, lookback):
    # for every country + indicator, take the 2023 value if it exists,
    # otherwise the most recent value within the look-back window
    oldest_year = REF_YEAR - lookback
    d = long_df.dropna(subset=["value"])
    d = d[(d["year"] >= oldest_year) & (d["year"] <= REF_YEAR)]
    d = d.sort_values("year").groupby(["iso3", "indicator"]).tail(1)   # latest year per pair

    values = d.pivot(index="iso3", columns="indicator", values="value")
    years = d.pivot(index="iso3", columns="indicator", values="year")

    values = values.rename(columns=INDICATORS)
    years = years.rename(columns={code: f"{name}_year" for code, name in INDICATORS.items()})
    return values, years


def add_dominant_sector(df):
    # services share = 100 - agriculture - industry, then pick whichever sector is largest.
    # left missing if: a share is missing, the two shares are from different years,
    # or the numbers don't make sense (outside 0-100, or services comes out negative)
    agri = df["agriculture_share"]
    ind = df["industry_share"]
    services = 100 - agri - ind

    valid = (agri.notna() & ind.notna()
             & agri.between(0, 100) & ind.between(0, 100) & (services >= 0)
             & (df["agriculture_share_year"] == df["industry_share_year"]))

    shares = pd.DataFrame({"Agriculture": agri, "Industry": ind, "Services": services})
    dominant = pd.Series(np.nan, index=df.index, dtype=object)
    dominant[valid] = shares[valid].idxmax(axis=1)

    df["DominantSector"] = dominant
    df["services_share_est"] = services.where(valid)
    return df


def hdi_to_class(hdi):
    # 0 = Low (< 0.550), 1 = Medium/High (0.550 - 0.799), 2 = Very High (>= 0.800)
    return np.select([hdi < 0.550, hdi < 0.800], [0, 1], default=2)


def build(lookback, refresh):
    hdi_file, countries_file, indicators_file = download_raw_data(refresh)
    log = json.loads((RAW_DIR / "access_log.json").read_text())

    # UNDP table: drop the aggregate rows (their codes start with ZZ, e.g. "World")
    hdi = pd.read_csv(hdi_file, encoding="latin-1")
    hdi = hdi[~hdi["iso3"].str.startswith("ZZ")]
    hdi = hdi[["iso3", "country", f"hdi_{REF_YEAR}"]].rename(columns={f"hdi_{REF_YEAR}": "hdi"})

    # World Bank countries: drop aggregates (they have region id "NA")
    wb_countries = pd.read_csv(countries_file, keep_default_na=False)
    wb_countries = wb_countries[wb_countries["region_id"] != "NA"]
    wb_countries["region"] = wb_countries["region"].str.strip()   # some names come with extra spaces

    values, years = pick_year(pd.read_csv(indicators_file), lookback)

    # check which countries don't match between the two sources
    only_in_undp = sorted(set(hdi["iso3"]) - set(wb_countries["iso3"]))
    only_in_wb = sorted(set(wb_countries["iso3"]) - set(hdi["iso3"]))

    # merge everything on ISO3
    df = hdi.merge(wb_countries[["iso3", "region"]], on="iso3", how="inner")
    df = df.merge(values, left_on="iso3", right_index=True, how="left")
    df = df.merge(years, left_on="iso3", right_index=True, how="left")

    # countries without an HDI value can't be labelled, so they are dropped
    n_matched = len(df)
    no_hdi = df[df["hdi"].isna()][["iso3", "country"]].to_dict("records")
    df = df[df["hdi"].notna()].copy()

    df = add_dominant_sector(df)
    df["hdi_class"] = hdi_to_class(df["hdi"])

    features = list(INDICATORS.values())
    columns = (["iso3", "country", "hdi", "hdi_class", "region"] + features
               + ["DominantSector", "services_share_est"] + [f"{f}_year" for f in features])
    df = df[columns].sort_values("iso3").reset_index(drop=True)
    for f in features:
        df[f"{f}_year"] = df[f"{f}_year"].astype("Int64")

    df.to_csv(OUT_DIR / f"hdi_dataset_{REF_YEAR}.csv", index=False)

    # summary printed at the end (these numbers also go in DATA_DICTIONARY.md)
    summary = {
        "reference_year": REF_YEAR,
        "lookback_years": lookback,
        "hdi_release": "UNDP HDR 2025 (HDR25), composite indices time series",
        "sources": log,
        "undp_countries": int(len(hdi)),
        "unmatched_hdi_not_in_wb": only_in_undp,
        "unmatched_wb_not_in_hdi": only_in_wb,
        "matched_countries": n_matched,
        "lost_no_hdi_label": no_hdi,
        "final_countries": int(len(df)),
        "class_counts": {int(k): int(v) for k, v in df["hdi_class"].value_counts().sort_index().items()},
        "missing_rate": {c: round(float(df[c].isna().mean()), 3) for c in features + ["region", "DominantSector"]},
        "values_substituted_from_earlier_year": {f: int((df[f"{f}_year"] < REF_YEAR).sum()) for f in features},
        "dominant_sector_counts": df["DominantSector"].value_counts(dropna=False).to_dict(),
    }
    return df, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="download the raw data again")
    parser.add_argument("--lookback", type=int, default=3,
                        help="how many years before 2023 we're allowed to fall back to (default 3)")
    args = parser.parse_args()

    df, summary = build(args.lookback, args.refresh)
    summary.pop("sources")
    print(json.dumps(summary, indent=2, default=str))
