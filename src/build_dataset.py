# makes the dataset for our DS203 project (one row per country)
#
# HDI comes from UNDP, all the other indicators and the regions come from the World Bank.
# for each indicator we take the 2023 value. if a country doesn't have one, we go back to
# the latest value from 2020-2022. nothing after 2023 is used.
# totals like "World" or "South Asia" are removed, then everything is joined on ISO3
# and saved to data/hdi_dataset_2023.csv
#
# run it from the project folder:
#   python src/build_dataset.py
# this uses the files already in data/raw/, so it works without internet.
# add --refresh to download everything again

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

# World Bank codes and the shorter names we use for them
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

# earlier than we need, so that we can try different look-back windows
FIRST_YEAR = 2015


def get_world_bank(path, params):
    # the API only gives one page at a time, so loop until the last one
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

    # keep a note of where each file came from and when we got it
    log_file = RAW_DIR / "access_log.json"
    if log_file.exists():
        log = json.loads(log_file.read_text())
    else:
        log = {}

    # HDI table from UNDP
    hdi_file = RAW_DIR / "HDR25_Composite_indices_complete_time_series.csv"
    if refresh or not hdi_file.exists():
        response = requests.get(HDI_URL, timeout=300)
        response.raise_for_status()
        hdi_file.write_bytes(response.content)
        log["undp_hdi"] = {"url": HDI_URL, "accessed": str(date.today())}
    if "undp_hdi" not in log:
        log["undp_hdi"] = {"url": HDI_URL, "accessed": str(date.today())}

    # World Bank country list, we need this for the regions
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

    # the indicators (one row per country, indicator and year)
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
    # use the 2023 value if there is one, if not go back to the
    # most recent year that has a value (up to `lookback` years)
    oldest_year = REF_YEAR - lookback
    d = long_df.dropna(subset=["value"])
    d = d[(d["year"] >= oldest_year) & (d["year"] <= REF_YEAR)]
    d = d.sort_values("year").groupby(["iso3", "indicator"]).tail(1)   # last row = latest year

    values = d.pivot(index="iso3", columns="indicator", values="value")
    years = d.pivot(index="iso3", columns="indicator", values="year")

    values = values.rename(columns=INDICATORS)
    years = years.rename(columns={code: f"{name}_year" for code, name in INDICATORS.items()})
    return values, years


def add_dominant_sector(df):
    # whatever isn't agriculture or industry is counted as services, and the biggest one wins.
    # we leave it missing if we don't have both shares, if they are from different years,
    # or if the numbers don't make sense (outside 0-100, or services below 0)
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
    # 0 = Low (below 0.550), 1 = Medium/High, 2 = Very High (0.800 and above)
    return np.select([hdi < 0.550, hdi < 0.800], [0, 1], default=2)


def build(lookback, refresh):
    hdi_file, countries_file, indicators_file = download_raw_data(refresh)
    log = json.loads((RAW_DIR / "access_log.json").read_text())

    # codes starting with ZZ aren't countries (e.g. "World"), so remove them
    hdi = pd.read_csv(hdi_file, encoding="latin-1")
    hdi = hdi[~hdi["iso3"].str.startswith("ZZ")]
    hdi = hdi[["iso3", "country", f"hdi_{REF_YEAR}"]].rename(columns={f"hdi_{REF_YEAR}": "hdi"})

    # in the World Bank list the non-countries have region id "NA"
    # (keep_default_na=False, or else pandas reads that "NA" as a missing value)
    wb_countries = pd.read_csv(countries_file, keep_default_na=False)
    wb_countries = wb_countries[wb_countries["region_id"] != "NA"]
    wb_countries["region"] = wb_countries["region"].str.strip()   # some regions have extra spaces

    values, years = pick_year(pd.read_csv(indicators_file), lookback)

    # countries that are in one source but not in the other
    only_in_undp = sorted(set(hdi["iso3"]) - set(wb_countries["iso3"]))
    only_in_wb = sorted(set(wb_countries["iso3"]) - set(hdi["iso3"]))

    # put it all together using ISO3
    df = hdi.merge(wb_countries[["iso3", "region"]], on="iso3", how="inner")
    df = df.merge(values, left_on="iso3", right_index=True, how="left")
    df = df.merge(years, left_on="iso3", right_index=True, how="left")

    # no HDI means no class, so these countries have to go
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

    # gets printed at the end, we copied these numbers into DATA_DICTIONARY.md
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
