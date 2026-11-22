# Databricks notebook source
import pandas as pd

# COMMAND ----------

cerf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/CERF_donor_cont_allocations.csv")
global_cbpf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_contributions.csv")
cerf_sum = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/cbpf_projects_2025_2026.csv")


# COMMAND ----------

df.columns

# COMMAND ----------

df.head()

# COMMAND ----------

df.shape

# COMMAND ----------

df['sector_regex'].unique()

# COMMAND ----------

df['sector_regex'].value_counts()

# COMMAND ----------

df.groupby('sector_regex')['budget_per_person'].mean()

# COMMAND ----------

sector_means = df.groupby('sector_regex')['budget_per_person'].transform('mean')
df['budget_per_person_diff_from_sector_mean'] = df['budget_per_person'] - sector_means
df['sector_mean'] = sector_means
df[['sector_regex', 'budget_per_person', 'budget_per_person_diff_from_sector_mean', 'sector_mean']].sort_values('budget_per_person_diff_from_sector_mean', ascending=False).head()

# COMMAND ----------

import numpy as np
import pandas as pd
import re
import unicodedata

# Load the all-country file and keep eligible projects only
d_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/cbpf_projects_2025_2026.csv")
ac = d_all[d_all["eligible"] == True].copy().reset_index(drop=True)
ac["ben_per_usd"] = ac["people_targeted"] / ac["Budget"]

# --- Multilingual (EN/FR) sector tagger, accent-insensitive ---
def _deaccent(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()

SECTOR_KW = {
    "Health":        ["health", "sante", "sanitaire", "medical", "medic", "clinic", "hospital"],
    "Nutrition":     ["nutrition", "nutritional"],
    "Food Security": ["food", "securite alimentaire", "agricult", "agricol", "livelihood"],
    "Protection":    ["protection", "gbv", "gender-based", "psychosocial", "mhpss", "droits humains", "human rights"],
    "WASH":          ["wash", "water", "eau", "eha", "sanitation", "assainissement", "hygien"],
    "Shelter/NFI":   ["shelter", "abri", " nfi", "non-food items"],
    "Education":     ["education", "educatif"],
    "CCCM":          ["cccm", "camp coordination", "camp management", "gestion de camp"],
    "Mine Action":   ["mine action", "demining", "demai", "mines"],
}
def tag_sector(title):
    t = re.sub(r"[^a-z ]+", " ", _deaccent(title))
    hits = [sec for sec, kws in SECTOR_KW.items() if any(kw in t for kw in kws)]
    if len(hits) >= 2:
        return hits[0]
    if len(hits) == 1:
        return hits[0]
    if re.search(r"multisector|multi sector|integrated|integre", t):
        return "Multisector"
    return "Untagged"

ac["sector_tag"] = ac["ProjectTitle"].map(tag_sector)
#print(f"eligible projects: {len(ac)} | funds: {ac['PooledFundName'].nunique()}")
#display(ac["sector_tag"].value_counts().rename("projects").to_frame())
#display(ac["PooledFundName"].value_counts().head(10).rename("eligible projects").to_frame())

# COMMAND ----------

ac['sector_tag'].value_counts()

# COMMAND ----------

ac = ac[~ac['sector_tag'].isin(['Untagged', 'Multisector', 'Mine Action'])].reset_index(drop=True)
ac['sector_tag'].value_counts()

# COMMAND ----------

sector_means = ac.groupby('sector_tag')['budget_per_person'].transform('mean')
ac['budget_per_person_diff_from_sector_mean'] = ac['budget_per_person'] - sector_means
ac['sector_mean'] = sector_means

# COMMAND ----------

pd.set_option("display.max_columns", None)
ac.sort_values('budget_per_person_diff_from_sector_mean', ascending=False).head()

# COMMAND ----------

sev = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/jiaf_severity_aggregates.csv")
sev.head()

# COMMAND ----------

sev.columns

# COMMAND ----------

ac["sector_tag"].value_counts()

# COMMAND ----------

sev['Need'].value_counts()

# COMMAND ----------

sev['Need'] = sev['Need'].astype(str).str.replace('Protection (aggregate)', 'Protection', regex=False)
sev['Need'] = sev['Need'].astype(str).str.replace('Shelter / NFI', 'Shelter/NFI', regex=False)

# COMMAND ----------

# --- Case-insensitive join: ac <-> sev on AllocationYear=Year, PooledFundName=Country, sector_tag = sector ---

# Normalize join keys in ac
ac_join = ac.copy()
ac_join["_fund_lc"] = ac_join["PooledFundName"].astype(str).str.strip().str.lower()
ac_join["_year"] = ac_join["AllocationYear"].astype(int)

# Normalize join keys in sev
sev_join = sev.copy()
sev_join["_country_lc"] = sev_join["Country"].astype(str).str.strip().str.lower()
sev_join["_year"] = sev_join["Year"].astype(int)

# Find the sector column in sev (adjust name if needed) and normalize it
sector_col = "Need"
sev_join["_sector_lc"] = sev_join[sector_col].astype(str).str.strip().str.lower()
ac_join["_sector_lc"] = ac_join["sector_tag"].astype(str).str.strip().str.lower()

# Merge, keeping the "Need" measure from sev
merged = ac_join.merge(
    sev_join[["_year", "_country_lc", "_sector_lc", "Need"]],
    left_on=["_year", "_fund_lc", "_sector_lc"],
    right_on=["_year", "_country_lc", "_sector_lc"],
    how="left",
)

print(f"ac rows: {len(ac_join)} | merged rows: {len(merged)} | matched Need: {merged['Need'].notna().sum()}")
merged[["PooledFundName", "AllocationYear", "sector_tag", "Need", "budget_per_person"]].head(15)


# COMMAND ----------

# DBTITLE 1,Final: ac + Pop-weighted severity
# --- Final dataframe: ac + 'Pop-weighted severity' from sev (year + country + sector join) ---
ac_final = ac_join.merge(
    sev_join[["_year", "_country_lc", "_sector_lc", "Pop-weighted severity"]],
    left_on=["_year", "_fund_lc", "_sector_lc"],
    right_on=["_year", "_country_lc", "_sector_lc"],
    how="left",
).drop(columns=["_fund_lc", "_year", "_sector_lc", "_country_lc"])

print(f"ac rows: {len(ac)} | ac_final rows: {len(ac_final)} | matched severity: {ac_final['Pop-weighted severity'].notna().sum()}")
ac_final[["ChfProjectCode", "PooledFundName", "AllocationYear", "sector_tag", "Pop-weighted severity", "budget_per_person", 'budget_per_person_diff_from_sector_mean', 'sector_mean']].head(10)

# COMMAND ----------

ac_final['eff_score'] = ac_final['sector_mean'] / ac_final['budget_per_person']

# COMMAND ----------

ac_final.sort_values('eff_score', ascending=True).head(10)

# COMMAND ----------

ac_final.to_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/efficiency_final.csv", index=False)
print(f"Saved {len(ac_final)} rows to ac_final.csv")