# JIAF 2025/2026 severity aggregation pipeline — all countries in one pass.
#
# Combines the two earlier steps into a single script:
#   1. For every country workbook (2025 and 2026), load & clean the intersectoral-
#      severity sheet and compute national sector-severity aggregates (from the
#      "JIAF 2025 Severity Aggregation Pipeline" notebook).
#   2. Union the per-country aggregates into one CSV with leading "Year" and
#      "Country" columns (from union_severity_aggregates.py) — no intermediate
#      per-country CSVs needed.
#
# Input:  the country .xlsx workbooks in jiaf_2025_data/ and jiaf_2026_data/ (JIAF 2025 & 2026)
# Output: jiaf_all_countries_2025_2026_severity_aggregates.csv — one row per (year, country, need)
#
# Countries/years without population data (Syria both years; Yemen 2026) carry empty
# population-weighted columns.
import importlib.util
import subprocess
import sys

if importlib.util.find_spec("openpyxl") is None:  # required to read .xlsx workbooks
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])

import pandas as pd

BASE = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/jiaf-data-processing-pipeline"
OUT_PATH = f"{BASE}/jiaf_all_countries_2025_2026_severity_aggregates.csv"

CONFIGS_2025 = {
    "drc": {
        "label": "the DRC",
        "xlsx": f"{BASE}/jiaf_2025_data/jiaf_drc_2025.xlsx",
        "severity_sheet": "WS - 3.2 Intersectoral Severity",
        "header_row": 1,          # header row index within the sheet
        "zone_col": "Admin 3",    # finest admin level (health zones)
        "final_col": "Sévérité définitive",
        "shock_col": "Severité chocs",
        "scale_max": 4,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {
            "CCCM": "CCCM (Camp Coordination & Management)",
            "Éducation": "Education",
            "Nutrition": "Nutrition",
            "Sécurité alimentaire": "Food security",
            "Santé": "Health",
            "Protection globale": "General protection",
            "Abri-AME": "Shelter / NFI",
            "WASH": "WASH",
            "PG": "Child protection",
            "PE": "Education (PE)",
            "GBV": "Gender-based violence",
            "L’action anti-mines": "Mine action",
            "HLP": "Housing, land & property",
        },
    },
    "sudan": {
        "label": "Sudan",
        "xlsx": f"{BASE}/jiaf_2025_data/jiaf_sudan_2025.xlsx",
        "severity_sheet": "Severity",
        "header_row": 1,
        "zone_col": "Admin 2",    # finest admin level (localities)
        "final_col": "Final Severity",
        "shock_col": None,         # Sudan's severity sheet has no shock-severity column
        "scale_max": 5,
        "population": {"sheet": "PiN", "key_col": "Admin 2 P-Code", "col": "Total Population"},
        "sectors": {
            "Site Management": "CCCM (Site Management)",
            "Education": "Education",
            "Food Security and Livlihoods": "Food security & livelihoods",
            "Health": "Health",
            "Nutrition": "Nutrition",
            "Protection": "Protection (aggregate)",
            "Shelter NFI": "Shelter / NFI",
            "WASH": "WASH",
            "CP": "Child protection",
            "GBV": "Gender-based violence",
            "Mine Action": "Mine action",
            "General Protection": "General protection",
        },
    },
    "afghanistan": {
        "label": "Afghanistan",
        "xlsx": f"{BASE}/jiaf_2025_data/jiaf_afghanistan_2025.xlsx",
        "severity_sheet": "Severity",
        "header_row": 1,
        "zone_col": "Admin 2",    # finest admin level (districts)
        "final_col": "Final Severity",
        "shock_col": None,         # no shock-severity column
        "scale_max": 4,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {
            "EDU": "Education",
            "SHL": "Shelter / NFI",
            "FSC": "Food security",
            "HEA": "Health",
            "NUT": "Nutrition",
            "PRO": "Protection (aggregate)",
            "WSH": "WASH",
            "PRO-GP": "General protection",
            "PRO-CP": "Child protection",
            "PRO-GBV": "Gender-based violence",
            "PRO-HLP": "Housing, land & property",
            "PRO-MA": "Mine action",
        },
    },
    "somalia": {
        "label": "Somalia",
        "xlsx": f"{BASE}/jiaf_2025_data/jiaf_somalia_2025.xlsx",
        "severity_sheet": "Severity",
        "header_row": 1,
        "zone_col": "Admin 2",    # finest admin level (districts)
        "final_col": "Final Severity",
        "shock_col": "Shock convergence",
        "scale_max": 4,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {
            "CCCM": "CCCM",
            "Education": "Education",
            "Nutrition": "Nutrition",
            "Food Security": "Food security",
            "Health": "Health",
            "Overarching Protection": "Protection (aggregate)",
            "Shelter": "Shelter / NFI",
            "WASH": "WASH",
            "Child Protection (CP)": "Child protection",
            "Gender-based Violence (GBV)": "Gender-based violence",
            "Mine Action": "Mine action",
            "HLP": "Housing, land & property",
        },
    },
    "haiti": {
        "label": "Haiti",
        "xlsx": f"{BASE}/jiaf_2025_data/jiaf_haiti_2025.xlsx",
        "severity_sheet": "Severity",
        "header_row": 1,
        "zone_col": "Admin 2",    # finest admin level (communes)
        "final_col": "Final Severity",
        "shock_col": None,         # no shock-severity column
        "scale_max": 5,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {
            "CCCM": "CCCM",
            "Education": "Education",
            "Nutrition": "Nutrition",
            "Food Security": "Food security",
            "Health": "Health",
            "Overarching Protection": "Protection (aggregate)",
            "Shelter": "Shelter / NFI",
            "WASH": "WASH",
            "General Protection": "General protection",
            "Child Protection (CP)": "Child protection",
            "Gender-based Violence (GBV)": "Gender-based violence",
            "Migrants": "Migrants",
        },
    },
    "syria": {
        "label": "Syria",
        "xlsx": f"{BASE}/jiaf_2025_data/syria_jiaf_needs_and_severity_syria_2025.xlsx",
        "severity_sheet": "JIAF PiN and Severity",
        "header_row": 1,
        "skip_hxl": True,             # HXL hashtag row sits directly below the headers
        "admin1_col": "admin1Name_en",
        "zone_col": "admin3Name_en",  # finest admin level (sub-districts)
        "final_col": "Inter-sector Severity_HNO_2025",
        "shock_col": None,
        "scale_max": 4,              # observed final-severity range 2-4 (sector scores reach 5)
        "population": None,          # workbook carries no population — unweighted aggregates only
        "sectors": {
            "CCCM_severity": "CCCM",
            "Education_severity": "Education",
            "Health_severity": "Health",
            "Nutrition_severity": "Nutrition",
            "NFI_severity": "Non-food items (NFI)",
            "Shelter_severity": "Shelter",
            "Food_severity": "Food security",
            "WASH_severity": "WASH",
            "ERL_severity": "Early recovery & livelihoods",
            "Protection_severity": "Protection (aggregate)",
            "Protection_CP_severity": "Child protection",
            "Protection_GBV_severity": "Gender-based violence",
            "Protection_MA_severity": "Mine action",
        },
    },
    "yemen": {
        "label": "Yemen",
        "xlsx": f"{BASE}/jiaf_2025_data/yemen-hnrp-2025.xlsx",
        "severity_sheet": "Yemen_2025_People_in_Need",
        "header_row": 1,
        "skip_hxl": True,             # HXL hashtag row sits directly below the headers
        "admin1_col": "Governorate",
        "zone_col": "District",       # finest admin level (districts)
        "final_col": "Final Severity",
        "shock_col": None,
        "scale_max": 4,              # observed final-severity range 3-4 (sector scores reach 5)
        # one 'Severity' column per sector: dedup keeps 'Severity' (overall, col 4) and
        # suffixes the rest '.1'..'.13' in sheet order — renamed here for readability
        "renames": {
            "Severity": "Final Severity",
            "Severity.1": "RMMS Severity",                # col 17
            "Severity.2": "WASH Severity",                # col 23
            "Severity.3": "Shelter Severity",            # col 29
            "Severity.4": "Nutrition Severity",          # col 35
            "Severity.5": "Education Severity",         # col 41
            "Severity.6": "FSAC Severity",              # col 47
            "Severity.7": "CCCM Severity",              # col 53
            "Severity.8": "Health Severity",            # col 59
            "Severity.9": "RRM Severity",                # col 65
            "Severity.10": "Protection Severity",       # col 71
            "Severity.11": "GBV Severity",               # col 77
            "Severity.12": "Mine Action Severity",     # col 83
            "Severity.13": "Child Protection Severity", # col 89
        },
        "population": {"sum_cols": ["IDPs", "Resident"]},  # population = IDPs + residents
        "sectors": {
            "RMMS Severity": "RMMS",
            "WASH Severity": "WASH",
            "Shelter Severity": "Shelter",
            "Nutrition Severity": "Nutrition",
            "Education Severity": "Education",
            "FSAC Severity": "Food security & agriculture",
            "CCCM Severity": "CCCM",
            "Health Severity": "Health",
            "RRM Severity": "Rapid response (RRM)",
            "Protection Severity": "Protection (aggregate)",
            "GBV Severity": "Gender-based violence",
            "Mine Action Severity": "Mine action",
            "Child Protection Severity": "Child protection",
        },
    },
}

CONFIGS_2026 = {
    "drc": {
        "label": "the DRC",
        "xlsx": f"{BASE}/jiaf_2026_data/jiaf_drc_2026_revised.xlsx",
        "severity_sheet": "WS - 3.2 Intersectoral Severity",
        "header_row": 2,          # two group-label rows sit above the header row
        "zone_col": "Admin 3",    # finest admin level (health zones)
        "final_col": "Sévérité définitive",
        "shock_col": None,         # 2026 sheet has no shock-severity column
        "scale_max": 5,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {
            "CCCM": "CCCM (Camp Coordination & Management)",
            "Éducation": "Education",
            "Nutrition": "Nutrition",
            "SECAL": "Food security",
            "Santé": "Health",
            "Protection": "General protection",
            "Abris&NFI": "Shelter / NFI",
            "EHA": "WASH",
            "PG": "Child protection",
            "PE": "Education (PE)",
            "VBG": "Gender-based violence",
            "LAM": "Mine action",
            "LTP": "Housing, land & property",
        },
    },
    "sudan": {
        "label": "Sudan",
        "xlsx": f"{BASE}/jiaf_2026_data/jiaf_sudan_2026.xlsx",
        "severity_sheet": "Cluster Severity",
        "header_row": 2,          # two group-label rows sit above the header row
        "zone_col": "Admin 2",    # finest admin level (localities)
        "final_col": "Final Severity",
        "shock_col": None,
        "scale_max": 5,
        "population": {"sheet": "Cluster PIN", "key_col": "Admin 2 P-Code", "col": "Total Population"},
        "sectors": {  # the RCF column exists in 2026 but is not one of the tracked needs
            "Site Management": "CCCM (Site Management)",
            "Education": "Education",
            "Food Security and Livlihoods": "Food security & livelihoods",
            "Health": "Health",
            "Nutrition": "Nutrition",
            "Protection": "Protection (aggregate)",
            "Shelter NFI": "Shelter / NFI",
            "WASH": "WASH",
            "GBV": "Gender-based violence",
            "Mine Action": "Mine action",
            "General Protection": "General protection",
        },
    },
    "afghanistan": {
        "label": "Afghanistan",
        "xlsx": f"{BASE}/jiaf_2026_data/jiaf_afghanistan_2026.xlsx",
        "severity_sheet": "WS - 3.2 Intersectoral Severity",
        "header_row": 2,          # two group-label rows sit above the header row
        "zone_col": "Admin 2",    # finest admin level (districts)
        "final_col": "Final Severity",
        "shock_col": None,
        "scale_max": 4,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {  # 2026 has no sub-sector protection columns; CCCM is empty and skipped
            "CCCM": "CCCM",
            "Education": "Education",
            "Shelter": "Shelter / NFI",
            "Food Security": "Food security",
            "Health": "Health",
            "Nutrition": "Nutrition",
            "Protection": "Protection (aggregate)",
            "WASH": "WASH",
        },
    },
    "somalia": {
        "label": "Somalia",
        "xlsx": f"{BASE}/jiaf_2026_data/jiaf_somalia_2026.xlsx",
        "severity_sheet": "Severity",
        "header_row": 1,
        "zone_col": "Admin 2",    # finest admin level (districts)
        "final_col": "Inter-cluster Severity",
        "shock_col": None,
        "scale_max": 4,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {  # 2026 has no CP / GBV / Mine Action / HLP sub-sector columns
            "CCCM": "CCCM",
            "Education": "Education",
            "Nutrition": "Nutrition",
            "Food Security": "Food security",
            "Health": "Health",
            "Overarching Protection": "Protection (aggregate)",
            "Shelter": "Shelter / NFI",
            "WASH": "WASH",
        },
    },
    "haiti": {
        "label": "Haiti",
        "xlsx": f"{BASE}/jiaf_2026_data/jiaf_haiti_2026.xlsx",
        "severity_sheet": "WS - 3.2 Intersectoral Severity",
        "header_row": 1,
        "zone_col": "Admin 2",    # finest admin level (communes)
        "final_col": "Final Severity",
        "shock_col": None,
        "scale_max": 5,
        "population": {"col": "Population"},  # population is a column of the severity sheet
        "sectors": {  # 2026 has no CP / GBV / Mine Action / Migrants sub-sector columns
            "CCCM": "CCCM",
            "Education": "Education",
            "Nutrition": "Nutrition",
            "Food Security": "Food security",
            "Health": "Health",
            "Protection": "Protection (aggregate)",
            "Shelter": "Shelter / NFI",
            "WASH": "WASH",
        },
    },
    "syria": {
        "label": "Syria",
        "xlsx": f"{BASE}/jiaf_2026_data/syria_hnrp_needs_severity_target_2026 (1).xlsx",
        "severity_sheet": "Syria PiN Target Priortized",
        "header_row": 1,             # a grand-totals row sits above the header row
        "admin1_col": "admin1Name_en",
        "zone_col": "admin3Name_en",  # finest admin level (sub-districts)
        "final_col": "Inter-sector Severity HNRP 2026",
        "shock_col": None,
        "scale_max": 4,
        "population": None,          # workbook carries no population — unweighted aggregates only
        "sectors": {  # note the double spaces in 'FSAL  severity', 'MPC  severity', 'Protection  severity'
            "CCCM severity": "CCCM",
            "Education severity": "Education",
            "FSAL  severity": "Food security",
            "Health severity": "Health",
            "MPC  severity": "Multi-purpose cash",
            "NFIs severity": "Non-food items (NFI)",
            "Nutrition severity": "Nutrition",
            "Protection  severity": "Protection (aggregate)",
            "Shelter severity": "Shelter",
            "WASH severity": "WASH",
        },
    },
    "yemen": {
        "label": "Yemen",
        "xlsx": f"{BASE}/jiaf_2026_data/yemen_jiaf_hnrp_2026.xlsx",
        "severity_sheet": "HNO 2026",
        "header_row": 1,
        "skip_hxl": True,             # HXL hashtag row sits directly below the headers
        "admin1_col": "Governorate",
        "zone_col": "District",       # finest admin level (districts)
        "final_col": "Final Severity",
        "shock_col": None,
        "scale_max": 4,
        # one 'Severity' column per sector: dedup keeps 'Severity' (overall, col 4) and
        # suffixes the rest '.1'..'.13' in sheet order — renamed here for readability
        "renames": {
            "Severity": "Final Severity",
            "Severity.1": "WASH Severity",                # col 15
            "Severity.2": "Shelter Severity",            # col 21
            "Severity.3": "Nutrition Severity",          # col 27
            "Severity.4": "Education Severity",         # col 33
            "Severity.5": "FSAC Severity",              # col 39
            "Severity.6": "CCCM Severity",              # col 45
            "Severity.7": "Health Severity",            # col 51
            "Severity.8": "Protection Severity",       # col 57
            "Severity.9": "GBV Severity",               # col 63
            "Severity.10": "Mine Action Severity",     # col 69
            "Severity.11": "Child Protection Severity", # col 75
            "Severity.12": "RRM Severity",              # col 81
            "Severity.13": "RMMS Severity",             # col 87
        },
        "population": None,   # 2026 workbook has no population columns — unweighted only
        "sectors": {
            "WASH Severity": "WASH",
            "Shelter Severity": "Shelter",
            "Nutrition Severity": "Nutrition",
            "Education Severity": "Education",
            "FSAC Severity": "Food security & agriculture",
            "CCCM Severity": "CCCM",
            "Health Severity": "Health",
            "Protection Severity": "Protection (aggregate)",
            "GBV Severity": "Gender-based violence",
            "Mine Action Severity": "Mine action",
            "Child Protection Severity": "Child protection",
            "RRM Severity": "Rapid response (RRM)",
            "RMMS Severity": "RMMS",
        },
    },
}

CONFIGS = {2025: CONFIGS_2025, 2026: CONFIGS_2026}


def read_sheet(cfg, sheet):
    raw = pd.read_excel(cfg["xlsx"], sheet_name=sheet, header=None)
    hdr = cfg["header_row"]
    # some workbooks (Syria, Yemen) carry an HXL hashtag row right below the headers
    data_start = hdr + 2 if cfg.get("skip_hxl") else hdr + 1
    df = raw.iloc[data_start:].copy()
    # strip names, then disambiguate repeats (Yemen has one 'Severity' column per sector)
    seen, names = {}, []
    for c in raw.iloc[hdr]:
        c = str(c).strip()
        if c in seen:
            seen[c] += 1
            names.append(f"{c}.{seen[c]}")
        else:
            seen[c] = 0
            names.append(c)
    df.columns = names
    df = df.rename(columns=cfg.get("renames", {}))
    return df.dropna(how="all")


def load_country(country, cfg):
    """Load & clean one country's severity sheet, attaching Population."""
    severity = read_sheet(cfg, cfg["severity_sheet"])
    for col in list(cfg["sectors"]) + [cfg["final_col"]] + ([cfg["shock_col"]] if cfg["shock_col"] else []):
        severity[col] = pd.to_numeric(severity[col], errors="coerce")

    # Population: a column of the severity sheet (DRC), summed per locality across
    # population groups from the PiN sheet (Sudan), a sum of columns (Yemen 2025:
    # IDPs + residents), or absent entirely (Syria; Yemen 2026 — unweighted only).
    pop_cfg = cfg["population"]
    if pop_cfg is None:
        severity["Population"] = float("nan")
    elif "sum_cols" in pop_cfg:
        severity["Population"] = sum(pd.to_numeric(severity[c], errors="coerce") for c in pop_cfg["sum_cols"])
    elif "sheet" in pop_cfg:
        pin = read_sheet(cfg, pop_cfg["sheet"])
        pin[pop_cfg["col"]] = pd.to_numeric(pin[pop_cfg["col"]], errors="coerce")
        pop = pin.groupby(pop_cfg["key_col"])[pop_cfg["col"]].sum().rename("Population")
        severity = severity.merge(pop, left_on=pop_cfg["key_col"], right_index=True, how="left")
    else:
        severity["Population"] = pd.to_numeric(severity[pop_cfg["col"]], errors="coerce")

    admin1_col = cfg.get("admin1_col", "Admin 1")
    has_pop = severity["Population"].notna().any()
    missing_pop = severity["Population"].isna().sum()
    print(
        f"[{country}] Loaded {len(severity)} {cfg['zone_col']} areas across "
        f"{severity[admin1_col].nunique()} admin-1 units"
        + (f" — WARNING: {missing_pop} areas without population" if has_pop and missing_pop else "")
        + ("" if has_pop else " — no population data, unweighted aggregates only")
    )
    return severity


def sector_aggregates(cfg, severity):
    """National severity aggregates for each need (Step 2 of the notebook)."""
    rows = []
    for col, need_name in cfg["sectors"].items():
        s = severity[[cfg["zone_col"], "Population", col]].dropna(subset=[col])
        if len(s) == 0:
            continue
        sev, pop = s[col], s["Population"]
        has_pop = pop.notna().any()
        rows.append({
            "Need": need_name,
            "Areas assessed": len(s),
            "Pop-weighted severity": round((sev * pop).sum() / pop.sum(), 2) if has_pop else None,
            "Unweighted mean": round(sev.mean(), 2),
            "% areas at severity 3+": round(100 * (sev >= 3).mean(), 1),
            "Population in areas at severity 3+": int(pop[sev >= 3].sum()) if has_pop else None,
        })
    if not rows:
        return pd.DataFrame(columns=[
            "Need", "Areas assessed", "Pop-weighted severity", "Unweighted mean",
            "% areas at severity 3+", "Population in areas at severity 3+",
        ])
    sort_col = "Pop-weighted severity" if any(r["Pop-weighted severity"] is not None for r in rows) else "Unweighted mean"
    return pd.DataFrame(rows).sort_values(sort_col, ascending=False).reset_index(drop=True)


def print_composite_summary(country, cfg, severity):
    """One-line composite final-severity summary per country (Step 3 of the notebook)."""
    final = severity.dropna(subset=[cfg["final_col"]])
    if final.empty:
        print(f"[{country}] no areas with a final severity class")
        return
    if final["Population"].notna().any():
        weighted = (final[cfg["final_col"]] * final["Population"]).sum() / final["Population"].sum()
        detail = f"population-weighted final severity {weighted:.2f}"
    else:
        detail = f"unweighted mean final severity {final[cfg['final_col']].mean():.2f} (no population data)"
    print(f"[{country}] {len(final)} areas with a final class — {detail} / {cfg['scale_max']}")


# --- run all countries & years and union into one CSV ---
frames = []
for year in sorted(CONFIGS):
    for country in sorted(CONFIGS[year]):
        cfg = CONFIGS[year][country]
        severity = load_country(f"{country} {year}", cfg)
        aggregates = sector_aggregates(cfg, severity)
        aggregates.insert(0, "Country", country)
        aggregates.insert(0, "Year", year)
        frames.append(aggregates)
        print_composite_summary(f"{country} {year}", cfg, severity)
        print(f"[{country} {year}] aggregated {len(aggregates)} sector rows\n")

union = pd.concat(frames, ignore_index=True)
union.to_csv(OUT_PATH, index=False)
print(
    f"Saved {len(union)} rows across {union['Country'].nunique()} countries "
    f"and {union['Year'].nunique()} years to {OUT_PATH}"
)
