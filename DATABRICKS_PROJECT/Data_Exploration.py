# Databricks notebook source
import pandas as pd

# COMMAND ----------

# DBTITLE 1,Cluster-to-need-group encoding dictionary
# CERF projectclusters -> JIAF need-group encoding
# Keys are the individual cluster tokens found in CERF_donor_cont_allocations.csv
# (16 unique values after splitting composites; note "Water, Sanitation and Hygiene"
# contains commas, so split carefully before using this mapping).
# None = no JIAF need-group counterpart (excluded from sector comparisons).
cluster_to_need_group = {
    # Health & livelihoods
    "Health":                                   "Health",
    "Nutrition":                                "Nutrition",
    "Agriculture":                              "Food security",
    "Food Assistance":                         "Food security",
    "Food Aid":                                 "Food security",  # legacy label for Food Assistance
    # Protection
    "Protection":                               "General protection",
    # Settlement & services
    "Camp Coordination and Camp Management":    "CCCM (Camp Coordination & Management",
    "Shelter and Non-Food Items":              "Shelter / NFI",
    "Water, Sanitation and Hygiene":            "WASH",
    "Education":                               "Education",
    # No JIAF counterpart -> None
    "Common Services":                         None,
    "Early Recovery":                          None,
    "Multi-Purpose Cash":                      None,
    "Multi-Sector":                            None,
    "Multi-sector refugee assistance":         None,
    "To be determined":                        None,
}

# JIAF need groups with NO matching CERF cluster (CERF reports these only at
# a coarser level, or not at all):
#   "Housing, land & property"    -> folded into CERF "Protection"
#   "Child protection"            -> folded into CERF "Protection"
#   "Gender-based violence"       -> folded into CERF "Protection"
#   "Mine action"                 -> folded into CERF "Protection"
#   "Education (PE)"              -> folded into CERF "Education"

# COMMAND ----------

cerf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/CERF_donor_cont_allocations.csv")
global_cbpf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_contributions.csv")
cerf_sum = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")



# COMMAND ----------

jiaf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/jiaf_drc_2025_severity.csv")

# COMMAND ----------

jiaf_df.columns

# COMMAND ----------

jiaf_df.head()

# COMMAND ----------

jiaf_df['Population'].head()

# COMMAND ----------

cerf_df.columns

# COMMAND ----------

global_cbpf_df.columns

# COMMAND ----------

# Exploring windowFullName and project sector, project cluster
# Create bar graph showing distribution of number of windowFullName counts across each project cluster, then every project sector

# COMMAND ----------

import matplotlib.pyplot as plt

# Bar graph: totalAmountApproved summed by projectsectors for
# countryName = 'Democratic Republic of the Congo' and year = '2025'
drc_2026_df = cerf_df[
    (cerf_df["countryName"] == "Democratic Republic of the Congo")
    & (cerf_df["year"].astype(str) == "2026")
]

sector_totals = (
    drc_2026_df.groupby("projectsectors")["totalAmountApproved"]
    .sum()
    .sort_values(ascending=False)
)

plt.figure(figsize=(12, 6))
plt.bar(sector_totals.index.astype(str), sector_totals.values)
plt.title(
    "Total Amount Approved by Project Sector\n"
    "Democratic Republic of the Congo (2025)"
)
plt.xlabel("Project Sector")
plt.ylabel("Total Amount Approved")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

# COMMAND ----------

import matplotlib.pyplot as plt

# Bar graph: totalAmountApproved summed by projectclusters for
# countryName = 'Democratic Republic of the Congo' and year = '2025'
drc_2026_df = cerf_df[
    (cerf_df["countryName"] == "Democratic Republic of the Congo")
    & (cerf_df["year"].astype(str) == "2026")
]

sector_totals = (
    drc_2026_df.groupby("projectclusters")["totalAmountApproved"]
    .sum()
    .sort_values(ascending=False)
)

plt.figure(figsize=(12, 6))
plt.bar(sector_totals.index.astype(str), sector_totals.values)
plt.title(
    "Total Amount Approved by Project Cluster\n"
    "Democratic Republic of the Congo (2025)"
)
plt.xlabel("Project Cluster")
plt.ylabel("Total Amount Approved")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

# COMMAND ----------

pip install openpyxl


# COMMAND ----------

drc_2025 = pd.read_excel('/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/jiaf_drc_2025.xlsx')
drc_2025.head()

# COMMAND ----------

jiaf_pin = spark.read.csv(f"/jiaf_drc_2025_pin.csv", header=True, inferSchema=True)
jiaf_severity = spark.read.csv(f"/jiaf_drc_2025_severity.csv", header=True, inferSchema=True)
jiaf_trend = spark.read.csv(f"/jiaf_drc_2025_pin_trend.csv", header=True, inferSchema=True)

# COMMAND ----------

# DBTITLE 1,Sector comparison intro
# MAGIC %md
# MAGIC ## Sector-level comparison — CERF DRC funding vs JIAF 2025 sector severity
# MAGIC
# MAGIC **Question:** how does CERF's 2025 DRC funding split across sectors compare with where JIAF 2025 sector severity is highest?
# MAGIC
# MAGIC **Method**
# MAGIC - CERF side: DRC rows (`countryCode = 'COD'`) for 2025 (the JIAF snapshot year), 2026 for context. Many `projectsectors` values are composite (e.g. `Protection, Health`, `Water, Sanitation and Hygiene, Education`), so each project's full budget is attributed to **every** sector it lists — sector sums overlap by design (attribution sums to more than the actual total).
# MAGIC - JIAF side: per-sector severity across the 332 health zones — mean score, % of zones at severity >= 3, and % of population living in those zones.
# MAGIC - Sector mapping: Health→Santé, Protection→Protection globale, WASH→WASH, Nutrition→Nutrition, Food Assistance & Agriculture→Sécurité alimentaire, Shelter and Non-Food Items→Abri-AME, Education→Éducation, Camp Coordination and Camp Management→CCCM. Common Services and Multi-Purpose Cash have no JIAF counterpart.
# MAGIC - This is a national-level side-by-side comparison, **not** a join — the two sources share no geographic key.

# COMMAND ----------

# DBTITLE 1,CERF sector attribution
import pandas as pd, re

# Self-contained reload (safe if the session restarted)
cerf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/CERF_donor_cont_allocations.csv")
jiaf_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/jiaf_drc_2025_severity.csv")
cod_df = cerf_df[cerf_df["countryCode"] == "COD"]

# Canonical CERF sector vocabulary; extract from composite labels without
# breaking "Water, Sanitation and Hygiene" (which itself contains ", ")
CANONICAL = ["Health", "Protection", "Agriculture", "Common Services",
             "Water, Sanitation and Hygiene", "Food Assistance", "Multi-Sector",
             "Shelter and Non-Food Items", "Nutrition", "Education",
             "Camp Coordination and Camp Management", "Multi-Purpose Cash"]
_pattern = "|".join(re.escape(s) for s in CANONICAL)

def extract_sectors(label):
    if pd.isna(label):
        return []
    return sorted(set(re.findall(_pattern, str(label))))

# Attribution rows: a composite project's full budget counts toward EACH listed sector
_attr_rows = []
for _, _r in cod_df.iterrows():
    for _s in extract_sectors(_r["projectsectors"]):
        _attr_rows.append({"sector": _s, "year": int(_r["year"]), "amount": float(_r["totalAmountApproved"])})
attr_df = pd.DataFrame(_attr_rows)

agg_df = attr_df.groupby(["sector", "year"])["amount"].agg(["sum", "count"]).reset_index()
cerf_total_2025 = cod_df[cod_df["year"] == 2025]["totalAmountApproved"].sum()

a25_df = (agg_df[agg_df["year"] == 2025]
          .assign(funding_M=lambda d: (d["sum"] / 1e6).round(2))
          .sort_values("funding_M", ascending=False))
print(f"CERF DRC 2025 actual total: {cerf_total_2025/1e6:.2f}M | attribution total (overlaps composites): {a25_df['sum'].sum()/1e6:.2f}M")
display(a25_df[["sector", "count", "funding_M"]].rename(columns={"count": "projects_attribution"}))

# COMMAND ----------

# DBTITLE 1,CERF vs severity comparison table
# JIAF sector severity stats across the 332 health zones, then merge with CERF funding
sector_cols = ["CCCM", "Éducation", "Nutrition", "Sécurité alimentaire", "Santé",
               "Protection globale", "Abri-AME", "WASH"]
_pop = jiaf_df["Population"].fillna(0)

_jrows = []
for _c in sector_cols:
    _s = jiaf_df[_c]
    _scored = _s.dropna()
    _jrows.append({
        "jiaf_sector": _c,
        "zones_scored": int(_scored.count()),
        "mean_severity": round(_scored.mean(), 2),
        "pct_zones_sev3plus": round(100 * (_scored >= 3).mean(), 1),
        "pct_pop_in_sev3plus": round(100 * _pop[(_s >= 3).fillna(False)].sum() / _pop.sum(), 1),
    })
jiaf_stats_df = pd.DataFrame(_jrows)

cerf_to_jiaf = {
    "Health": "Santé", "Protection": "Protection globale",
    "Water, Sanitation and Hygiene": "WASH", "Nutrition": "Nutrition",
    "Food Assistance": "Sécurité alimentaire", "Agriculture": "Sécurité alimentaire",
    "Shelter and Non-Food Items": "Abri-AME", "Education": "Éducation",
    "Camp Coordination and Camp Management": "CCCM",
}

_a25 = agg_df[agg_df["year"] == 2025].copy()
_a25["jiaf_sector"] = _a25["sector"].map(cerf_to_jiaf)
_a26 = agg_df[agg_df["year"] == 2026].copy()
_a26["jiaf_sector"] = _a26["sector"].map(cerf_to_jiaf)

comparison_df = jiaf_stats_df.merge(
    _a25.groupby("jiaf_sector").agg(cerf_projects_2025=("count", "sum"),
                                    cerf_funding_2025_M=("sum", lambda x: round(x.sum() / 1e6, 2))),
    left_on="jiaf_sector", right_index=True, how="left").fillna(0)
comparison_df["share_2025_pct"] = (100 * comparison_df["cerf_funding_2025_M"] / (cerf_total_2025 / 1e6)).round(1)
comparison_df["cerf_funding_2026_M"] = (comparison_df["jiaf_sector"]
    .map(_a26.groupby("jiaf_sector")["sum"].sum() / 1e6).fillna(0).round(2))

# Sectors in CERF 2025 with no JIAF counterpart
_unmapped = _a25[_a25["jiaf_sector"].isna()]
print("CERF 2025 sectors with no JIAF counterpart:",
      _unmapped[["sector", "count"]].assign(funding_M=(_unmapped["sum"] / 1e6).round(2)).to_dict("records"))

display(comparison_df[["jiaf_sector", "cerf_projects_2025", "cerf_funding_2025_M", "share_2025_pct",
                       "cerf_funding_2026_M", "mean_severity", "pct_zones_sev3plus", "pct_pop_in_sev3plus"]]
        .sort_values("mean_severity", ascending=False))

# COMMAND ----------

# DBTITLE 1,Funding vs severity chart
import matplotlib.pyplot as plt

_df = comparison_df.sort_values("mean_severity", ascending=False)
_x = range(len(_df))
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar([i - 0.2 for i in _x], _df["share_2025_pct"], width=0.4, label="Share of CERF 2025 funding (%)", color="#4472C4")
ax.bar([i + 0.2 for i in _x], _df["pct_pop_in_sev3plus"], width=0.4, label="Population in severity\u22653 zones (%)", color="#ED7D31")
ax.set_xticks(list(_x))
ax.set_xticklabels(_df["jiaf_sector"], rotation=30, ha="right")
ax.set_ylabel("percent")
ax.set_title("DRC: CERF 2025 sector funding share vs JIAF 2025 sector severity (population in severe zones)")
ax.legend()
plt.tight_layout()
plt.show()

# Reading: sectors where the orange bar (need) far exceeds the blue bar (funding share)
# are candidates for further investigation.

# COMMAND ----------

# DBTITLE 1,Ranking intro
# MAGIC %md
# MAGIC ## Project ranking — people targeted per budget (DRC 2026 CBPF Reserve cohort)
# MAGIC
# MAGIC **Metric:** `people_targeted_plan / Budget` — planned beneficiaries (Men + Women + Boys + Girls) per $1M of assigned budget. The inverse (`budget_per_person`) is also shown, matching Project.md's `budget_per_person_targeted`.
# MAGIC
# MAGIC **Cohort:** the 76 eligible projects (approval date present, positive budget, four complete nonnegative demographic counts summing > 0, excluding `HFU Management Cost` category rows). "Population" here means planned direct beneficiaries — project files carry no zone population.
# MAGIC
# MAGIC **Reading the extremes:** the top-10 table lists projects reaching the most people per dollar; the bottom-10 lists projects with the fewest planned beneficiaries per dollar (highest budget per person) — candidates for the Smart Beneficiary Targeting flags in Project.md.

# COMMAND ----------

# DBTITLE 1,Top/bottom 10 people-per-budget ranking
# Build the eligible DRC 2026 Reserve cohort and rank by people-per-budget
_demo = ["Men", "Women", "Boys", "Girls"]
_reserve_df = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
_reserve_df = _reserve_df[(_reserve_df["PooledFundName"] == "DRC")
                          & (_reserve_df["AllocationYear"] == 2026)
                          & (_reserve_df["AllocationSourceName"] == "Reserve")].copy()

_ok = _reserve_df["ApprovedDate"].notna() & _reserve_df["Budget"].notna() & (_reserve_df["Budget"] > 0)
for _c in _demo:
    _ok &= _reserve_df[_c].notna() & (_reserve_df[_c] >= 0)
_ok &= _reserve_df[_demo].sum(axis=1) > 0

elig_projects = _reserve_df[_ok & (_reserve_df["AllocationTypeCategory"] != "HFU Management Cost")].copy()
elig_projects["people_targeted_plan"] = elig_projects[_demo].sum(axis=1)
elig_projects["people_per_1M"] = elig_projects["people_targeted_plan"] / (elig_projects["Budget"] / 1e6)
elig_projects["budget_per_person"] = elig_projects["Budget"] / elig_projects["people_targeted_plan"]

_rank_cols = ["ChfProjectCode", "ProjectTitle", "OrganizationName", "Budget",
              "people_targeted_plan", "people_per_1M", "budget_per_person"]

# Change the n highest and lowest
top10_high_reach = elig_projects.nlargest(5, "people_per_1M")[_rank_cols]
top10_low_reach = elig_projects.nsmallest(5, "people_per_1M")[_rank_cols]

print(f"Eligible projects: {len(elig_projects)} | ratio range: "
      f"{elig_projects['people_per_1M'].min():,.0f} to {elig_projects['people_per_1M'].max():,.0f} people per $1M "
      f"(${elig_projects['budget_per_person'].min():.2f} to ${elig_projects['budget_per_person'].max():,.2f} per person)")

print("\nTOP 10 HIGHEST — most people targeted per $1M:")
display(top10_high_reach.style.format({"Budget": "{:,.2f}", "people_targeted_plan": "{:,.0f}",
                                      "people_per_1M": "{:,.0f}", "budget_per_person": "${:,.2f}"}))

print("\nTOP 10 LOWEST — fewest people targeted per $1M (highest budget per person):")
display(top10_low_reach.style.format({"Budget": "{:,.2f}", "people_targeted_plan": "{:,.0f}",
                                      "people_per_1M": "{:,.0f}", "budget_per_person": "${:,.2f}"}))

# COMMAND ----------

import re
import numpy as np

# Filter the global CBPF project summary to DRC
# (add & cerf_sum["AllocationYear"].isin([2025, 2026]) if you only want the pilot years)
drc_cbpf = cerf_sum[cerf_sum["PooledFundName"] == "DRC"].copy()

# Convert ProjectDuration strings like "12 Months" or "3 Months, 12 Days" to days
DAYS_PER_MONTH = 30.44  # average month length (365.25 / 12)

def duration_to_days(s):
    if pd.isna(s) or not str(s).strip():
        return np.nan
    text = str(s).lower()
    months = re.search(r"(\d+)\s*month", text)
    days = re.search(r"(\d+)\s*day", text)
    if not (months or days):
        return np.nan
    total = 0.0
    if months:
        total += int(months.group(1)) * DAYS_PER_MONTH
    if days:
        total += int(days.group(1))
    return round(total, 1)

drc_cbpf["project_duration_days"] = drc_cbpf["ProjectDuration"].apply(duration_to_days)

# Optional: exact calendar days between project start and end dates instead
# drc_cbpf["duration_days_exact"] = (
#     pd.to_datetime(drc_cbpf["ProjectEndDate"]) - pd.to_datetime(drc_cbpf["ProjectStartDate"])
# ).dt.days

print(f"DRC CBPF projects: {len(drc_cbpf)}")
print(f"Rows with a parsed duration: {drc_cbpf['project_duration_days'].notna().sum()}")
drc_cbpf[["ChfProjectCode", "AllocationYear", "ProjectDuration", "project_duration_days"]].head(100)

# COMMAND ----------

# Join project duration (converted to days) into the eligible 2026 ranking cohort
# — readable display: truncated text, compact numbers, short headers

# 1) 2026 only, one row per project code
drc_cbpf_2026 = drc_cbpf[drc_cbpf["AllocationYear"] == 2026].copy()
duration_2026 = (
    drc_cbpf_2026[["ChfProjectCode", "project_duration_days"]]
    .drop_duplicates("ChfProjectCode")
)
print(f"2026 DRC projects with duration parsed: {len(duration_2026)}")

# 2) Join into the ranked cohort from the cell above
ranked_with_duration = elig_projects.merge(
    duration_2026, on="ChfProjectCode", how="left", validate="one_to_one"
)
print(f"Joined rows: {len(ranked_with_duration)} | missing duration: "
      f"{ranked_with_duration['project_duration_days'].isna().sum()}")

# 3) Compact table for display
def tidy(df):
    out = pd.DataFrame({
        "project": df["ChfProjectCode"],
        "title": df["ProjectTitle"].astype(str).str.slice(0, 40) + "…",
        "org": df["OrganizationName"].astype(str).str.slice(0, 18) + "…",
        "budget": df["Budget"] / 1e6,
        "targeted": df["people_targeted_plan"],
        "people_per_$1M": df["people_per_1M"],
        "$_per_person": df["budget_per_person"],
        "duration_days": df["project_duration_days"],
        "$_person_day": df["budget_per_person"] / df["project_duration_days"],
    })
    return out

_fmt = {"budget": "${:,.2f}M", "targeted": "{:,.0f}", "people_per_$1M": "{:,.0f}",
        "$_per_person": "${:,.2f}", "duration_days": "{:,.0f}",
        "$_person_day": "${:,.2f}"}

def show(df, title):
    print(f"\n{title}")
    display(tidy(df).style.format(_fmt).hide(axis="index"))

show(ranked_with_duration.nlargest(5, "people_per_1M"),
     "TOP 5 HIGHEST — most people targeted per $1M")
show(ranked_with_duration.nsmallest(5, "people_per_1M"),
     "TOP 5 LOWEST — fewest people targeted per $1M (highest $ per person)")

# COMMAND ----------

import matplotlib.pyplot as plt

df = ranked_with_duration.dropna(subset=["project_duration_days"]).copy()
top5 = df.nlargest(5, "people_per_1M")
bottom5 = df.nsmallest(5, "people_per_1M")
extremes = pd.concat([top5, bottom5])

fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

# Left: budget per person vs. duration, extremes highlighted
ax = axes[0]
ax.scatter(df["project_duration_days"], df["budget_per_person"],
           alpha=0.45, color="#4472C4", label="eligible projects")
ax.scatter(top5["project_duration_days"], top5["budget_per_person"],
           color="#2E8B57", s=95, edgecolor="black", label="top 5 (most people per $1M)")
ax.scatter(bottom5["project_duration_days"], bottom5["budget_per_person"],
           color="#D62728", s=95, edgecolor="black", label="bottom 5 (fewest people per $1M)")
for _, r in extremes.iterrows():
    ax.annotate(str(r["ChfProjectCode"]).split("-")[-1],
                (r["project_duration_days"], r["budget_per_person"]),
                fontsize=7, xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("project duration (days)")
ax.set_ylabel("budget per person ($)")
ax.set_yscale("log")
ax.set_title("DRC 2026 CBPF eligible cohort: budget/person vs. duration")
ax.legend(fontsize=8)

# Right: $ per person per day for the 10 extremes, log scale + value labels
ax = axes[1]
labels = [str(c).split("-")[-1] for c in extremes["ChfProjectCode"]]
values = (extremes["budget_per_person"] / extremes["project_duration_days"]).values
colors = ["#2E8B57"] * 5 + ["#D62728"] * 5
bars = ax.bar(labels, values, color=colors)
ax.set_yscale("log")
ax.set_ylim(top=max(values) * 3)  # headroom for the labels
ax.set_ylabel("$ per person per day (log scale)")
ax.set_title("Cost per person per day — top 5 (green) vs bottom 5 (red)")
ax.tick_params(axis="x", rotation=45)
for bar, v in zip(bars, values):
    ax.annotate(f"${v:,.0f}", (bar.get_x() + bar.get_width() / 2, v),
                ha="center", va="bottom", fontsize=8)

plt.tight_layout()
plt.show()

# COMMAND ----------

# Cluster the DRC 2025-2026 CBPF eligible projects to define peer groups
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score
import matplotlib.pyplot as plt

# 1) Eligible cohort, both years (same input checks as the ranking cell)
_demo = ["Men", "Women", "Boys", "Girls"]
_base = cerf_sum[(cerf_sum["PooledFundName"] == "DRC")
                 & (cerf_sum["AllocationYear"].isin([2025, 2026]))].copy()
_ok = (_base["ApprovedDate"].notna() & _base["Budget"].notna() & (_base["Budget"] > 0)
       & (_base["AllocationTypeCategory"] != "HFU Management Cost"))
for _c in _demo:
    _ok &= _base[_c].notna() & (_base[_c] >= 0)
_ok &= _base[_demo].sum(axis=1) > 0
cohort = _base[_ok].copy()
cohort["people_targeted"] = cohort[_demo].sum(axis=1)
cohort["budget_per_person"] = cohort["Budget"] / cohort["people_targeted"]
cohort["cost_per_person_day"] = cohort["budget_per_person"] / cohort["project_duration_days"] if "project_duration_days" in cohort else np.nan
cohort["allocation_type"] = (cohort["ChfProjectCode"].str.extract(r"-([RS])-")[0]
                             .map({"R": "Reserve", "S": "Standard"}))
if "drc_cbpf" in globals():
    _dur = (drc_cbpf[["ChfProjectCode", "project_duration_days"]]
            .drop_duplicates("ChfProjectCode"))
    cohort = cohort.merge(_dur, on="ChfProjectCode", how="left")
    cohort["cost_per_person_day"] = cohort["budget_per_person"] / cohort["project_duration_days"]
print(f"cohort: {len(cohort)} projects "
      f"({(cohort['AllocationYear']==2025).sum()} in 2025, {(cohort['AllocationYear']==2026).sum()} in 2026)")

# 2) Features: plan characteristics + cost-efficiency metrics
X = pd.DataFrame({
    "log_budget": np.log1p(cohort["Budget"]),
    "log_targeted": np.log1p(cohort["people_targeted"]),
    "log_duration": np.log1p(cohort["project_duration_days"]),
    "women_share": cohort["Women"] / cohort["people_targeted"],
    "children_share": (cohort["Boys"] + cohort["Girls"]) / cohort["people_targeted"],
    "is_standard": (cohort["allocation_type"] == "Standard").astype(int),
    "log_budget_per_person": np.log1p(cohort["budget_per_person"]),
    "log_cost_per_person_day": np.log1p(cohort["cost_per_person_day"]),
})

# 3) Choose k by silhouette
_pre = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
Xz = _pre.fit_transform(X)
_scores = {}
for _k in range(2, 11):
    _km = KMeans(n_clusters=_k, n_init=10, random_state=42).fit(Xz)
    _scores[_k] = silhouette_score(Xz, _km.labels_)
best_k = max(_scores, key=_scores.get)

plt.figure(figsize=(6, 3.5))
plt.plot(list(_scores), list(_scores.values()), marker="o")
plt.axvline(best_k, color="red", ls="--", label=f"best k = {best_k}")
plt.xlabel("k"); plt.ylabel("silhouette"); plt.legend(); plt.tight_layout(); plt.show()

# 4) Final fit, cluster profile, MLflow tracking
final = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                  ("km", KMeans(n_clusters=best_k, n_init=10, random_state=42))])
labels = final.fit_predict(X)
cohort["cluster"] = labels

_db = davies_bouldin_score(Xz, labels)
profile = (cohort.groupby("cluster")
           .agg(projects=("ChfProjectCode", "count"),
                median_budget=("Budget", "median"),
                median_targeted=("people_targeted", "median"),
                median_duration_days=("project_duration_days", "median"),
                median_budget_per_person=("budget_per_person", "median"),
                median_cost_per_person_day=("cost_per_person_day", "median"),
                pct_2026=("AllocationYear", lambda s: round(100 * (s == 2026).mean())))
           .round(2))
print(f"k={best_k} | silhouette={_scores[best_k]:.3f} | davies-bouldin={_db:.3f}")
display(profile)

import mlflow
from mlflow.models import infer_signature
with mlflow.start_run(run_name="drc-cbpf-project-clustering"):
    mlflow.log_params({"k": best_k, "n_rows": len(X), "n_features": X.shape[1]})
    mlflow.log_metric("silhouette", _scores[best_k])
    mlflow.log_metric("davies_bouldin", _db)
    mlflow.sklearn.log_model(final, name="kmeans_pipeline",
                             signature=infer_signature(X, pd.Series(labels)),
                             input_example=X.head(5))

# 5) PCA scatter colored by cluster
_p = PCA(n_components=2, random_state=42).fit_transform(Xz)
plt.figure(figsize=(7, 5))
plt.scatter(_p[:, 0], _p[:, 1], c=labels, cmap="tab10", alpha=0.85)
plt.xlabel("PCA 1"); plt.ylabel("PCA 2")
plt.title(f"DRC 2025-2026 CBPF eligible projects, {best_k} clusters")
plt.tight_layout(); plt.show()

# COMMAND ----------

# $_person_day: DRC vs global (all other CBPF funds), 2025-2026
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Self-contained reload (safe if the session restarted)
gs_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")

DAYS_PER_MONTH = 30.44
def duration_to_days(s):
    if pd.isna(s) or not str(s).strip():
        return np.nan
    text = str(s).lower()
    months = re.search(r"(\d+)\s*month", text)
    days = re.search(r"(\d+)\s*day", text)
    if not (months or days):
        return np.nan
    total = 0.0
    if months:
        total += int(months.group(1)) * DAYS_PER_MONTH
    if days:
        total += int(days.group(1))
    return round(total, 1)

demo = ["Men", "Women", "Boys", "Girls"]
g = gs_all[gs_all["AllocationYear"].isin([2025, 2026])].copy()
ok = (g["ApprovedDate"].notna() & g["Budget"].notna() & (g["Budget"] > 0)
      & (g["AllocationTypeCategory"] != "HFU Management Cost"))
for c in demo:
    ok &= g[c].notna() & (g[c] >= 0)
ok &= g[demo].sum(axis=1) > 0
g = g[ok].copy()
g["duration_days"] = g["ProjectDuration"].apply(duration_to_days)
g["people_targeted"] = g[demo].sum(axis=1)
g["budget_per_person"] = g["Budget"] / g["people_targeted"]
g["cost_per_person_day"] = g["budget_per_person"] / g["duration_days"]
g["group"] = np.where(g["PooledFundName"] == "DRC", "DRC", "Global (non-DRC)")

print(f"eligible 2025-2026 projects: {len(g)} across {g['PooledFundName'].nunique()} funds "
      f"(DRC: {(g['group']=='DRC').sum()})")
print(f"projects with duration -> $_person_day computable: "
      f"{g['cost_per_person_day'].notna().sum()}")

summary = (g.dropna(subset=["cost_per_person_day"])
           .groupby("group")["cost_per_person_day"]
           .agg(projects="count", median="median", mean="mean",
                q25=lambda s: s.quantile(.25), q75=lambda s: s.quantile(.75))
           .round(2))
display(summary)

fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

# Left: distributions by year, DRC vs global (log scale)
ax = axes[0]
labels, data = [], []
for yr in [2025, 2026]:
    for grp in ["DRC", "Global (non-DRC)"]:
        labels.append(f"{grp.split(' ')[0]} {yr}")
        data.append(g[(g["AllocationYear"] == yr) & (g["group"] == grp)]
                    ["cost_per_person_day"].dropna().values)
ax.boxplot(data, labels=labels, showfliers=False)
ax.set_yscale("log")
ax.set_ylabel("$ per person per day (log)")
ax.set_title("Cost per person per day — DRC vs global, 2025-2026")
ax.tick_params(axis="x", rotation=20)

# Right: median $_person_day by fund (funds with >= 10 projects), DRC highlighted
ax = axes[1]
fund_stats = (g.dropna(subset=["cost_per_person_day"])
              .groupby("PooledFundName")
              .agg(median_cppd=("cost_per_person_day", "median"),
                   n=("ChfProjectCode", "count"))
              .query("n >= 10").sort_values("median_cppd"))
colors = ["#D62728" if f == "DRC" else "#4472C4" for f in fund_stats.index]
ax.barh(fund_stats.index, fund_stats["median_cppd"], color=colors)
ax.set_xlabel("median $ per person per day")
ax.set_title(f"Median cost per person per day by fund ({len(fund_stats)} funds with >= 10 projects)")
drc_rank = list(fund_stats.index).index("DRC") + 1 if "DRC" in fund_stats.index else None
if drc_rank:
    ax.set_title(ax.get_title() + f" — DRC rank {drc_rank}/{len(fund_stats)} (cheapest first)")

plt.tight_layout()
plt.show()

# COMMAND ----------

# $_person_day by OrganizationType — DRC vs global, 2025-2026
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Self-contained reload (safe if the session restarted)
gs_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")

DAYS_PER_MONTH = 30.44
def duration_to_days(s):
    if pd.isna(s) or not str(s).strip():
        return np.nan
    text = str(s).lower()
    months = re.search(r"(\d+)\s*month", text)
    days = re.search(r"(\d+)\s*day", text)
    if not (months or days):
        return np.nan
    total = 0.0
    if months:
        total += int(months.group(1)) * DAYS_PER_MONTH
    if days:
        total += int(days.group(1))
    return round(total, 1)

demo = ["Men", "Women", "Boys", "Girls"]
g = gs_all[gs_all["AllocationYear"].isin([2025, 2026])].copy()
ok = (g["ApprovedDate"].notna() & g["Budget"].notna() & (g["Budget"] > 0)
      & (g["AllocationTypeCategory"] != "HFU Management Cost"))
for c in demo:
    ok &= g[c].notna() & (g[c] >= 0)
ok &= g[demo].sum(axis=1) > 0
g = g[ok].copy()
g["duration_days"] = g["ProjectDuration"].apply(duration_to_days)
g["people_targeted"] = g[demo].sum(axis=1)
g["budget_per_person"] = g["Budget"] / g["people_targeted"]
g["cost_per_person_day"] = g["budget_per_person"] / g["duration_days"]
g["group"] = np.where(g["PooledFundName"] == "DRC", "DRC", "Global (non-DRC)")
g = g.dropna(subset=["cost_per_person_day"])

OT_ORDER = ["International NGO", "National NGO", "UN Agency", "Others"]
print(f"projects with $_person_day: {len(g)} "
      f"(DRC {(g['group']=='DRC').sum()}, global {(g['group']=='Global (non-DRC)').sum()})")

# 1) DRC vs global medians by organization type
med = (g.pivot_table(index="OrganizationType", columns="group",
                     values="cost_per_person_day", aggfunc="median")
       .reindex(OT_ORDER).round(2))
med["DRC_vs_global"] = (med["DRC"] / med["Global (non-DRC)"]).round(2)
counts = (g.pivot_table(index="OrganizationType", columns="group",
                        values="ChfProjectCode", aggfunc="count")
          .reindex(OT_ORDER))
med.insert(0, "n_global", counts["Global (non-DRC)"])
med.insert(1, "n_DRC", counts["DRC"])
med.columns = ["n_global", "n_DRC", "median_global", "median_DRC", "DRC_vs_global"]
display(med)

# 2) Grouped box plots (log scale)
fig, ax = plt.subplots(figsize=(11, 5.5))
for i, name in enumerate(OT_ORDER):
    for grp, color, offset in [("DRC", "#D62728", -0.2), ("Global (non-DRC)", "#4472C4", 0.2)]:
        vals = g[(g["OrganizationType"] == name) & (g["group"] == grp)]["cost_per_person_day"].values
        if len(vals) == 0:
            continue
        bp = ax.boxplot(vals, positions=[i + offset], widths=0.32,
                        patch_artist=True, showfliers=False)
        for box in bp["boxes"]:
            box.set_facecolor(color)
        for element in ["whiskers", "caps"]:
            for line in bp[element]:
                line.set_color("black")
ax.set_xticks(range(len(OT_ORDER)))
ax.set_xticklabels(OT_ORDER)
ax.set_yscale("log")
ax.set_ylabel("$ per person per day (log)")
ax.set_title("Cost per person per day by organization type — DRC vs global, 2025-2026")
ax.legend(handles=[Patch(facecolor="#D62728", label="DRC"),
                   Patch(facecolor="#4472C4", label="Global (non-DRC)")])
plt.tight_layout()
plt.show()

# COMMAND ----------

# Overhead (support cost share) + $_person_day, full CBPF history, DRC vs global
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

gs_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
DAYS_PER_MONTH = 30.44
def dur_days(s):
    if pd.isna(s) or not str(s).strip():
        return np.nan
    t = str(s).lower()
    m = re.search(r"(\d+)\s*month", t)
    d = re.search(r"(\d+)\s*day", t)
    if not (m or d):
        return np.nan
    return round((int(m.group(1)) * DAYS_PER_MONTH if m else 0) + (int(d.group(1)) if d else 0), 1)

demo = ["Men", "Women", "Boys", "Girls"]
g = gs_all.copy()
ok = (g["ApprovedDate"].notna() & g["Budget"].notna() & (g["Budget"] > 0)
      & (g["AllocationTypeCategory"] != "HFU Management Cost"))
for c in demo:
    ok &= g[c].notna() & (g[c] >= 0)
ok &= g[demo].sum(axis=1) > 0
g = g[ok].copy()
g["duration_days"] = g["ProjectDuration"].apply(dur_days)
g["people_targeted"] = g[demo].sum(axis=1)
g["cost_per_person_day"] = g["Budget"] / g["people_targeted"] / g["duration_days"]
g["group"] = np.where(g["PooledFundName"] == "DRC", "DRC", "Global (non-DRC)")
print(f"eligible projects all years: {len(g)} | with $_person_day: "
      f"{g['cost_per_person_day'].notna().sum()}")

# 1) Overhead: support share (recorded only 2014-2022)
win = g[g["AllocationYear"].between(2014, 2022)].copy()
total_cost = win["TotalDirectCost"] + win["TotalSupportCost"]
has_sup = win[(win["TotalSupportCost"] > 0) & (total_cost > 0)].copy()
has_sup["support_share"] = has_sup["TotalSupportCost"] / (has_sup["TotalDirectCost"] + has_sup["TotalSupportCost"])
print(f"2014-2022 window: {len(win)} eligible | {len(has_sup)} with overhead recorded "
      f"({100*len(has_sup)/len(win):.0f}%)")

ot = (has_sup.groupby(["group", "OrganizationType"])["support_share"]
      .agg(n="count", median_share="median").round(3).reset_index())
display(ot.pivot(index="OrganizationType", columns="group", values=["n", "median_share"]))

m = has_sup.dropna(subset=["cost_per_person_day"]).copy()
rho, p = spearmanr(m["support_share"], m["cost_per_person_day"])
print(f"\nOverhead vs $_person_day (2014-2022): Spearman rho={rho:.3f} (p={p:.2g}, n={len(m)})")
m["share_q"] = pd.qcut(m["support_share"], 4)
qt = (m.groupby("share_q", observed=True)
      .agg(n=("cost_per_person_day", "count"),
           median_share=("support_share", "median"),
           median_cppd=("cost_per_person_day", "median")).round(3))
display(qt)

# 2) Trends: $_person_day all years; overhead where recorded
fig, axes = plt.subplots(1, 2, figsize=(15, 5))
ax = axes[0]
for grp, color in [("DRC", "#D62728"), ("Global (non-DRC)", "#4472C4")]:
    s = (g[(g["group"] == grp)].dropna(subset=["cost_per_person_day"])
         .groupby("AllocationYear")["cost_per_person_day"].median())
    ax.plot(s.index, s.values, marker="o", label=grp, color=color)
ax.axvspan(2014, 2022, alpha=0.08, color="gray")
ax.annotate("overhead recorded", (2014, ax.get_ylim()[0] * 1.05), fontsize=8, color="gray")
ax.set_xlabel("allocation year"); ax.set_ylabel("median $ per person per day")
ax.set_title("Cost per person per day by year — DRC vs global (all eligible projects)")
ax.legend()

ax = axes[1]
for grp, color in [("DRC", "#D62728"), ("Global (non-DRC)", "#4472C4")]:
    s = (has_sup[has_sup["group"] == grp].groupby("AllocationYear")["support_share"]
         .agg(["median", "count"]))
    ax.plot(s.index, s["median"], marker="o", label=grp, color=color)
    for yr, row in s.iterrows():
        if row["count"] >= 100:
            ax.annotate(f"{int(row['count'])}", (yr, row["median"]), fontsize=6,
                        xytext=(0, -12), textcoords="offset points", color=color, ha="center")
ax.set_xlabel("allocation year"); ax.set_ylabel("median support-cost share")
ax.set_title("Overhead (support share) by year, 2014-2022 — small numbers = projects with overhead recorded")
ax.legend()

plt.tight_layout()
plt.show()

# COMMAND ----------

# DRC vs South Sudan: overhead + $_person_day, all years
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

gs_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
DAYS_PER_MONTH = 30.44
def dur_days(s):
    if pd.isna(s) or not str(s).strip():
        return np.nan
    t = str(s).lower()
    m = re.search(r"(\d+)\s*month", t)
    d = re.search(r"(\d+)\s*day", t)
    if not (m or d):
        return np.nan
    return round((int(m.group(1)) * DAYS_PER_MONTH if m else 0) + (int(d.group(1)) if d else 0), 1)

demo = ["Men", "Women", "Boys", "Girls"]
g = gs_all.copy()
ok = (g["ApprovedDate"].notna() & g["Budget"].notna() & (g["Budget"] > 0)
      & (g["AllocationTypeCategory"] != "HFU Management Cost"))
for c in demo:
    ok &= g[c].notna() & (g[c] >= 0)
ok &= g[demo].sum(axis=1) > 0
g = g[ok & g["PooledFundName"].isin(["DRC", "South Sudan"])].copy()
g["duration_days"] = g["ProjectDuration"].apply(dur_days)
g["people_targeted"] = g[demo].sum(axis=1)
g["cost_per_person_day"] = g["Budget"] / g["people_targeted"] / g["duration_days"]

FUNDS = ["DRC", "South Sudan"]
COLORS = {"DRC": "#D62728", "South Sudan": "#4472C4"}

# Overhead (support share; recorded only 2014-2022)
h = g[g["AllocationYear"].between(2014, 2022)].copy()
h = h[(h["TotalSupportCost"] > 0) & ((h["TotalDirectCost"] + h["TotalSupportCost"]) > 0)]
h["support_share"] = h["TotalSupportCost"] / (h["TotalDirectCost"] + h["TotalSupportCost"])

print("$_person_day by year (median, n):")
cppd_t = (g.dropna(subset=["cost_per_person_day"])
          .pivot_table(index="AllocationYear", columns="PooledFundName",
                       values="cost_per_person_day", aggfunc=["median", "count"]))
cppd_t.columns = [f"{a}_{b}" for a, b in cppd_t.columns]
display(cppd_t.round(3))

# Two-panel trend chart
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

ax = axes[0]
for fund in FUNDS:
    s = (h[h["PooledFundName"] == fund].groupby("AllocationYear")["support_share"]
         .agg(["median", "count"]))
    s = s[s["count"] >= 10]  # skip DRC 2014 (n=1)
    ax.plot(s.index, s["median"] * 100, marker="o", label=fund, color=COLORS[fund])
ax.set_xlabel("allocation year")
ax.set_ylabel("median support-cost share (%)")
ax.set_title("Overhead by year (2014-2022 — only years with overhead recorded, n>=10)")
ax.legend()

ax = axes[1]
for fund in FUNDS:
    s = (g[(g["PooledFundName"] == fund) & g["cost_per_person_day"].notna()]
         .groupby("AllocationYear")["cost_per_person_day"].median())
    ax.plot(s.index, s.values, marker="o", label=fund, color=COLORS[fund])
ax.set_xlabel("allocation year")
ax.set_ylabel("median $ per person per day")
ax.set_title("$_person_day by year, all history (n>=19 per point)")
ax.legend()

plt.tight_layout()
plt.show()

# COMMAND ----------

# DRC vs South Sudan: $ per targeted person by sector (title-inferred regex sectors, English labels)
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

gs_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
demo = ["Men", "Women", "Boys", "Girls"]
g = gs_all.copy()
ok = (g["ApprovedDate"].notna() & g["Budget"].notna() & (g["Budget"] > 0)
      & (g["AllocationTypeCategory"] != "HFU Management Cost"))
for c in demo:
    ok &= g[c].notna() & (g[c] >= 0)
ok &= g[demo].sum(axis=1) > 0
g = g[ok & g["PooledFundName"].isin(["DRC", "South Sudan"])].copy()

# Regex sector tagger (keywords match FR/EN titles; labels are English)
_RGX_KW = {
    "Health": ["santé", "sante", "health", "ebola", "vaccin", "médic", "medic", "choléra", "cholera", "rougeole"],
    "Nutrition": ["nutrition"],
    "Food Security": ["secal", "food", "alimentaire", "faim", "agricol", "moyens de subsistance", "livelihood"],
    "WASH": ["wash", "eau", "hygiène", "hygiene", "assainissement", "sanitation"],
    "Protection": ["protection", "gbv", "vbg", "psea", "anti-mines", "hlp", "genre"],
    "Education": ["éducation", "education", "scolaire", "école"],
    "Shelter & NFI": ["abri", "shelter", "nfis", "non-food", "ame"],
    "CCCM": ["cccm", "camp"],
}
def _regex_sector(t):
    s = str(t).lower()
    hits = [n for n, w in _RGX_KW.items() if any(x in s for x in w)]
    return hits[0] if len(hits) == 1 else ("Multisector" if hits else "Untagged")

g["sector"] = g["ProjectTitle"].apply(_regex_sector)
g["people_targeted"] = g[demo].sum(axis=1)

# Budget-weighted $ per targeted person: sum(budget) / sum(targeted) per sector x fund
w = (g.groupby(["sector", "PooledFundName"])[["Budget", "people_targeted"]]
     .sum().assign(bpp=lambda d: d["Budget"] / d["people_targeted"])["bpp"].unstack())
n = g.pivot_table(index="sector", columns="PooledFundName", values="Budget", aggfunc="count")
w = w.dropna().sort_values("DRC", ascending=True)
w["DRC_vs_SS"] = (w["DRC"] / w["South Sudan"]).round(2)

print("budget-weighted $ per targeted person by sector:")
display(w[["DRC", "South Sudan", "DRC_vs_SS"]].round(2))
print("project counts (n):")
display(n.astype(int))

# Grouped horizontal bars, sorted by DRC cost
fig, ax = plt.subplots(figsize=(11, 6))
y = np.arange(len(w))
height = 0.38
b1 = ax.barh(y + height / 2, w["DRC"], height, label="DRC", color="#D62728")
b2 = ax.barh(y - height / 2, w["South Sudan"], height, label="South Sudan", color="#4472C4")
for bars, fund in [(b1, "DRC"), (b2, "South Sudan")]:
    for bar, (sector, row) in zip(bars, w.iterrows()):
        cnt = int(n.loc[sector, fund])
        ax.annotate(f"${row[fund]:.0f} (n={cnt})", (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=8)
ax.set_yticks(y)
ax.set_yticklabels(w.index)
ax.set_xlabel("budget-weighted $ per targeted person")
ax.set_title("Cost per targeted person by sector — DRC vs South Sudan, all years\n"
             "(sectors inferred from project titles; DRC CCCM n=2 — treat as unreliable)")
ax.legend(loc="lower right")
plt.tight_layout()
plt.show()

# COMMAND ----------

# $ per targeted person by CBPF fund — 2025-2026 only, exported to CSV
import pandas as pd

gs_all = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
demo = ["Men", "Women", "Boys", "Girls"]
g = gs_all.copy()
ok = (g["ApprovedDate"].notna() & g["Budget"].notna() & (g["Budget"] > 0)
      & (g["AllocationTypeCategory"] != "HFU Management Cost")
      & g["AllocationYear"].isin([2025, 2026]))
for c in demo:
    ok &= g[c].notna() & (g[c] >= 0)
ok &= g[demo].sum(axis=1) > 0
g = g[ok].copy()
g["people_targeted"] = g[demo].sum(axis=1)
g["budget_per_person"] = g["Budget"] / g["people_targeted"]

t = (g.groupby("PooledFundName")
     .agg(projects=("Budget", "count"),
          total_budget_M=("Budget", lambda s: s.sum() / 1e6),
          total_targeted_M=("people_targeted", lambda s: s.sum() / 1e6),
          median_per_project=("budget_per_person", "median")))
t["weighted_per_person"] = (t["total_budget_M"] * 1e6) / (t["total_targeted_M"] * 1e6)
t = t[["projects", "total_budget_M", "total_targeted_M", "weighted_per_person", "median_per_project"]]
t = t.sort_values("weighted_per_person", ascending=False).round(2)

print(f"CBPF funds 2025-2026: {len(t)} | eligible projects: {len(g)}")
display(t)

# Export CSV
out_path = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/cbpf_cost_per_person_2025_2026.csv"
t.reset_index().to_csv(out_path, index=False)
check = pd.read_csv(out_path)
print(f"exported: {out_path} ({len(check)} funds, columns: {list(check.columns)})")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC
# MAGIC Project by Severity
# MAGIC Project Duration
# MAGIC Group by project sector
# MAGIC
# MAGIC What is the main comparison going to be on?
# MAGIC
# MAGIC Aggregate to see the total needs of the DRC? 
# MAGIC

# COMMAND ----------

# DBTITLE 1,Peer comparison method
# MAGIC %md
# MAGIC ## Peer-comparison table with Smart Beneficiary Targeting flags
# MAGIC
# MAGIC **Peer group:** all 76 eligible DRC 2026 CBPF Reserve projects (pooled fund + year cohort — Project.md's sanctioned fallback, since no verified cluster column exists).
# MAGIC
# MAGIC **Flag rule (leave-one-out):** a project is flagged when its `budget_per_person` is below the 10th percentile or above the 90th percentile of the *other 75* peers, so a project never moves its own thresholds. Fixed-cohort reference points: p10 = $10.42, median = $32.36, p90 = $113.88.
# MAGIC
# MAGIC **Comparability context columns:** funding round (`AllocationType`), organization type, budget-size band, and inferred sector (title keywords — *inferred, not verified*; use to judge whether a flagged project really has similar peers, per Project.md's “peer group definition, peer count, median, and example projects”).
# MAGIC
# MAGIC **Reading the flags:** “low $/person” flags unusually cheap reach per person — often mass-preparedness projects; “high $/person” flags unusually expensive reach — the two non-service rows (a study and staff-incentive payments) are the extreme cases.

# COMMAND ----------

# DBTITLE 1,Peer comparison table with flags
import pandas as pd, numpy as np, re

# 1) Eligible pilot cohort (same input checks as the ranking cell)
_demo = ["Men", "Women", "Boys", "Girls"]
_base = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
_base = _base[(_base["PooledFundName"] == "DRC")
             & (_base["AllocationYear"] == 2026)
             & (_base["AllocationSourceName"] == "Reserve")].copy()
_ok = _base["ApprovedDate"].notna() & _base["Budget"].notna() & (_base["Budget"] > 0)
for _c in _demo:
    _ok &= _base[_c].notna() & (_base[_c] >= 0)
_ok &= _base[_demo].sum(axis=1) > 0
peer_df = _base[_ok & (_base["AllocationTypeCategory"] != "HFU Management Cost")].copy()
peer_df["people_targeted_plan"] = peer_df[_demo].sum(axis=1)
peer_df["budget_per_person"] = peer_df["Budget"] / peer_df["people_targeted_plan"]

# 2) Leave-one-out peer percentiles (each project judged against the other 75)
_b = peer_df["budget_per_person"].to_numpy(dtype=float)
peer_df["peer_p10"] = [round(float(np.percentile(np.delete(_b, _i), 10)), 2) for _i in range(len(_b))]
peer_df["peer_p90"] = [round(float(np.percentile(np.delete(_b, _i), 90)), 2) for _i in range(len(_b))]
peer_df["flag"] = np.where(_b > peer_df["peer_p90"], "above peer p90 (high $/person)",
                  np.where(_b < peer_df["peer_p10"], "below peer p10 (low $/person)", "within band"))

# 3) Comparability context columns
_bracket = peer_df["AllocationType"].astype(str).str.extract(r"\[([^\]]+)\]")[0]
peer_df["round"] = (_bracket.str.extract(r"(RA\s?\d+|ST)")[0].fillna(_bracket.str.slice(0, 12))
                    + np.where(_bracket.str.contains("non-US"), " non-US",
                       np.where(_bracket.str.contains("US"), " US", "")))
peer_df["budget_band"] = pd.qcut(np.log10(peer_df["Budget"]), 4,
                                labels=["Q1 small", "Q2", "Q3", "Q4 large"])
_SECTOR_KW = {
    "Santé (inferred)": ["santé", "sante", "health", "ebola", "vaccin", "médic", "medic", "choléra", "cholera", "rougeole"],
    "Nutrition (inferred)": ["nutrition"],
    "Sécurité alimentaire (inferred)": ["secal", "food", "alimentaire", "faim", "agricol", "moyens de subsistance", "livelihood"],
    "WASH (inferred)": ["wash", "eau", "hygiène", "hygiene", "assainissement", "sanitation"],
    "Protection (inferred)": ["protection", "gbv", "vbg", "psea", "anti-mines", "hlp", "genre"],
    "Éducation (inferred)": ["éducation", "education", "scolaire", "école"],
    "Abri-AME (inferred)": ["abri", "shelter", "nfis", "non-food", "ame"],
    "CCCM (inferred)": ["cccm", "camp"],
}
def _infer_sector(_title):
    _t = str(_title).lower()
    _hits = [n for n, words in _SECTOR_KW.items() if any(w in _t for w in words)]
    if len(_hits) == 1:
        return _hits[0]
    return "Multisector (inferred)" if _hits else "Untagged"
peer_df["sector_inferred"] = peer_df["ProjectTitle"].apply(_infer_sector)

peer_table = peer_df[["ChfProjectCode", "ProjectTitle", "OrganizationName", "OrganizationType",
                      "round", "budget_band", "sector_inferred", "Budget", "people_targeted_plan",
                      "budget_per_person", "peer_p10", "peer_p90", "flag"]].copy()

print(f"Cohort: {len(peer_table)} peers | fixed p10 = ${np.percentile(_b, 10):.2f} | "
      f"median = ${np.median(_b):.2f} | p90 = ${np.percentile(_b, 90):.2f}")
print("Flag counts:", peer_table["flag"].value_counts().to_dict())

_flagged = peer_table[peer_table["flag"] != "within band"].sort_values("budget_per_person")
print("\nFLAGGED PROJECTS (sorted by budget per person):")
display(_flagged.style.format({"Budget": "{:,.0f}", "people_targeted_plan": "{:,.0f}",
                               "budget_per_person": "${:,.2f}", "peer_p10": "${:,.2f}", "peer_p90": "${:,.2f}"}))

# COMMAND ----------

# DBTITLE 1,Cluster peer method
# MAGIC %md
# MAGIC ## Cluster-based peer flags — KMeans clusters as peer groups
# MAGIC
# MAGIC **Peer group:** each project's KMeans cluster from the clustering cell above (2025–2026 DRC CBPF eligible cohort; peers may be 2025 or Standard-allocation projects, consistent with Project.md's “comparable allocation years”).
# MAGIC
# MAGIC **Flag rule:** leave-one-out — a pilot project (2026 Reserve) is flagged when its `budget_per_person` falls below the 10th or above the 90th percentile of the *other* projects in its cluster. Clusters with fewer than 10 peers are labeled `insufficient peers` (Project.md's minimum) instead of being flagged.
# MAGIC
# MAGIC **Caveat:** `log_budget_per_person` is one of the clustering features, so clusters partly minimize within-group spread of the flagged metric — these flags read as "unusual among similar-scale, similar-mix projects", not against the full cohort. The cohort-wide table above remains the reference view.

# COMMAND ----------

# DBTITLE 1,Cluster-based peer flags
import numpy as np

# 1) Pilot projects flagged against their KMeans cluster peers (leave-one-out)
_pilot_c = cohort[(cohort["AllocationYear"] == 2026) & (cohort["AllocationSourceName"] == "Reserve")].copy()

_rows = []
for _i, _r in _pilot_c.iterrows():
    _c = _r["cluster"]
    _peers = cohort[(cohort["cluster"] == _c) & (cohort.index != _i)]["budget_per_person"].to_numpy(dtype=float)
    _v = float(_r["budget_per_person"])
    _row = {"ChfProjectCode": _r["ChfProjectCode"], "cluster": int(_c),
            "n_cluster": int((cohort["cluster"] == _c).sum()), "n_peers": len(_peers),
            "budget_per_person": round(_v, 2)}
    if len(_peers) < 10:
        _row.update({"cluster_p10": np.nan, "cluster_p90": np.nan,
                     "flag_cluster": f"insufficient peers ({len(_peers)})"})
    else:
        _p10, _p90 = float(np.percentile(_peers, 10)), float(np.percentile(_peers, 90))
        _row.update({"cluster_p10": round(_p10, 2), "cluster_p90": round(_p90, 2),
                     "flag_cluster": ("below cluster p10 (low $/person)" if _v < _p10
                                      else "above cluster p90 (high $/person)" if _v > _p90
                                      else "within band")})
    _rows.append(_row)

cluster_peer_table = pd.DataFrame(_rows)

print("Cluster sizes (2025-26 cohort):", cohort["cluster"].value_counts().sort_index().to_dict())
print("Pilot projects per cluster:", _pilot_c["cluster"].value_counts().sort_index().to_dict())
print("Cluster flag counts:", cluster_peer_table["flag_cluster"].value_counts().to_dict())

# 2) Side-by-side with the cohort-wide rule
def _direction(_f):
    if _f.startswith("below"):  return "low"
    if _f.startswith("above"):  return "high"
    if _f.startswith("insufficient"): return "insufficient"
    return "within"

cluster_peer_table = cluster_peer_table.merge(
    peer_table[["ChfProjectCode", "flag"]].rename(columns={"flag": "flag_cohort_wide"}),
    on="ChfProjectCode", how="left")
cluster_peer_table["dir_cluster"] = cluster_peer_table["flag_cluster"].apply(_direction)
cluster_peer_table["dir_cohort"] = cluster_peer_table["flag_cohort_wide"].apply(_direction)

_changed = cluster_peer_table[cluster_peer_table["dir_cluster"] != cluster_peer_table["dir_cohort"]]
print(f"\nProjects whose flag direction changed between the cohort-wide and cluster rules: {len(_changed)} of {len(cluster_peer_table)}")

_flagged_cluster = cluster_peer_table[cluster_peer_table["dir_cluster"].isin(["low", "high"])]
print("\nFLAGGED UNDER CLUSTER RULE (sorted by budget per person):")
display(_flagged_cluster[["ChfProjectCode", "cluster", "n_peers", "budget_per_person",
                          "cluster_p10", "cluster_p90", "flag_cluster", "flag_cohort_wide"]]
        .sort_values("budget_per_person")
        .style.format({"budget_per_person": "${:,.2f}", "cluster_p10": "${:,.2f}", "cluster_p90": "${:,.2f}"}))

_insufficient = cluster_peer_table[cluster_peer_table["dir_cluster"] == "insufficient"]
print("\nINSUFFICIENT-PEERS PROJECTS (cannot be judged against a peer group):")
display(_insufficient[["ChfProjectCode", "cluster", "n_cluster", "n_peers", "budget_per_person", "flag_cluster", "flag_cohort_wide"]])

# 3) Projects flagged ONLY under the cluster rule (not cohort-wide)
_new_flags = cluster_peer_table[(cluster_peer_table["dir_cluster"].isin(["low", "high"]))
                                & (cluster_peer_table["dir_cohort"] == "within")]
print(f"\nFlagged only by cluster peers (were 'within band' cohort-wide): {len(_new_flags)}")
display(_new_flags[["ChfProjectCode", "cluster", "n_peers", "budget_per_person", "cluster_p10", "cluster_p90", "flag_cluster"]]
        .sort_values("budget_per_person")
        .style.format({"budget_per_person": "${:,.2f}", "cluster_p10": "${:,.2f}", "cluster_p90": "${:,.2f}"}))

# COMMAND ----------

# DBTITLE 1,Regex method and evaluation intro
# MAGIC %md
# MAGIC ## Method 3 — regex sector peer groups, and three-method evaluation
# MAGIC
# MAGIC **Regex scraping:** `ChfProjectCode` for 2025–2026 carries no sector tokens (all 159 DRC rows are `CBPF-DRC-YY-R-ORG-NNNNN`), so the regex extracts sector labels from `ProjectTitle` (French/English keyword patterns per sector, single-match only; multi-keyword titles → `Multisector`, no match → `Untagged`). Groups are then formed over the same 2025–2026 eligible cohort (145 projects) as the KMeans method, and the pilot (2026 Reserve, 76 projects) is flagged with the same leave-one-out p10/p90 rule and 10-peer minimum.
# MAGIC
# MAGIC **Evaluation:** the three peer-grouping methods — cohort-wide percentiles, KMeans clusters, and regex sector groups — are compared on group structure, flag counts, pairwise agreement, and the consensus flag set (projects flagged by all three, and by at least two).

# COMMAND ----------

# DBTITLE 1,Regex sector groups and three-method evaluation
import numpy as np, itertools

# 1) Regex sector tagger (titles carry the only sector signal for 2025-26 codes)
_RGX_KW = {
    "Santé": ["santé", "sante", "health", "ebola", "vaccin", "médic", "medic", "choléra", "cholera", "rougeole"],
    "Nutrition": ["nutrition"],
    "Sécurité alimentaire": ["secal", "food", "alimentaire", "faim", "agricol", "moyens de subsistance", "livelihood"],
    "WASH": ["wash", "eau", "hygiène", "hygiene", "assainissement", "sanitation"],
    "Protection": ["protection", "gbv", "vbg", "psea", "anti-mines", "hlp", "genre"],
    "Éducation": ["éducation", "education", "scolaire", "école"],
    "Abri-AME": ["abri", "shelter", "nfis", "non-food", "ame"],
    "CCCM": ["cccm", "camp"],
}
def _regex_sector(_t):
    _s = str(_t).lower()
    _hits = [n for n, w in _RGX_KW.items() if any(x in _s for x in w)]
    return _hits[0] if len(_hits) == 1 else ("Multisector" if _hits else "Untagged")

cohort["sector_regex"] = cohort["ProjectTitle"].apply(_regex_sector)

# 2) Regex sector peer groups, leave-one-out flags for the pilot
_rows = []
for _i, _r in cohort[(cohort["AllocationYear"] == 2026) & (cohort["AllocationSourceName"] == "Reserve")].iterrows():
    _g = _r["sector_regex"]
    _peers = cohort[(cohort["sector_regex"] == _g) & (cohort.index != _i)]["budget_per_person"].to_numpy(dtype=float)
    _v = float(_r["budget_per_person"])
    if len(_peers) < 10:
        _f = f"insufficient peers ({len(_peers)})"
    else:
        _p10, _p90 = np.percentile(_peers, 10), np.percentile(_peers, 90)
        _f = "low $/person" if _v < _p10 else "high $/person" if _v > _p90 else "within band"
    _rows.append({"ChfProjectCode": _r["ChfProjectCode"], "sector_regex": _g, "n_peers": len(_peers),
                  "budget_per_person": round(_v, 2), "flag_regex": _f})
regex_peer_table = pd.DataFrame(_rows)

print("sector_regex group sizes (2025-26 cohort, n=%d):" % len(cohort))
print(cohort["sector_regex"].value_counts().to_dict())
print("\nregex flag counts (pilot, n=%d):" % len(regex_peer_table))
print(regex_peer_table["flag_regex"].value_counts().to_dict())

# 3) Three-method evaluation
def _d(_f):
    if _f.startswith("below") or _f.startswith("low"): return "low"
    if _f.startswith("above") or _f.startswith("high"): return "high"
    if _f.startswith("insufficient"): return "insufficient"
    return "within"

_m = regex_peer_table.merge(
    cluster_peer_table[["ChfProjectCode", "cluster", "n_peers", "dir_cluster", "dir_cohort"]],
    on="ChfProjectCode", suffixes=("_regex", "_cluster"))
_m["dir_regex"] = _m["flag_regex"].apply(_d)
_m = _m.rename(columns={"n_peers_regex": "peers_regex", "n_peers_cluster": "peers_cluster",
                        "dir_cohort": "dir_cohort_wide"})
three_method_table = _m

_eval = pd.DataFrame([
    {"method": "cohort-wide", "groups": 1,
     "usable_groups (>=10 peers)": 1,
     "median_peers": int(_m.groupby("dir_cohort_wide").size().pipe(lambda _: 75)),
     "flags_low": int((_m["dir_cohort_wide"] == "low").sum()),
     "flags_high": int((_m["dir_cohort_wide"] == "high").sum()),
     "insufficient": int((_m["dir_cohort_wide"] == "insufficient").sum())},
    {"method": "kmeans clusters", "groups": cohort["cluster"].nunique(),
     "usable_groups (>=10 peers)": int(cohort["cluster"].value_counts()[lambda s: s >= 11].count()),
     "median_peers": int(_m["peers_cluster"].median()),
     "flags_low": int((_m["dir_cluster"] == "low").sum()),
     "flags_high": int((_m["dir_cluster"] == "high").sum()),
     "insufficient": int((_m["dir_cluster"] == "insufficient").sum())},
    {"method": "regex sectors", "groups": cohort["sector_regex"].nunique(),
     "usable_groups (>=10 peers)": int(cohort["sector_regex"].value_counts()[lambda s: s >= 11].count()),
     "median_peers": int(_m["peers_regex"].median()),
     "flags_low": int((_m["dir_regex"] == "low").sum()),
     "flags_high": int((_m["dir_regex"] == "high").sum()),
     "insufficient": int((_m["dir_regex"] == "insufficient").sum())},
])
print("\n=== THREE-METHOD EVALUATION (76 pilot projects) ===")
display(_eval)

print("\nPairwise agreement (flag direction):")
for _a, _b in itertools.combinations(["dir_cohort_wide", "dir_cluster", "dir_regex"], 2):
    print(f"  {_a} vs {_b}: {(_m[_a] == _m[_b]).sum()}/{len(_m)}")

_core = _m[(_m["dir_cohort_wide"].isin(["low", "high"]))
         & (_m["dir_cluster"].isin(["low", "high"]))
         & (_m["dir_regex"].isin(["low", "high"]))]
print(f"\nFlagged low/high by ALL THREE methods: {len(_core)}")
display(_core[["ChfProjectCode", "budget_per_person", "sector_regex", "peers_regex",
               "cluster", "dir_cohort_wide", "dir_cluster", "dir_regex"]]
        .sort_values("budget_per_person"))

_any2 = _m[(_m[["dir_cohort_wide", "dir_cluster", "dir_regex"]].isin(["low", "high"])).sum(axis=1) >= 2]
print(f"Flagged low/high by at least 2 of 3 methods: {len(_any2)} — the recommended review list")
display(_any2[["ChfProjectCode", "budget_per_person", "sector_regex", "cluster",
               "dir_cohort_wide", "dir_cluster", "dir_regex"]]
        .sort_values("budget_per_person"))

# COMMAND ----------

# DBTITLE 1,Export regex sector categories to CSV
# ---------------------------------------------------------------------------
# Regex sector categories -> drc_cbpf_sector_categories.csv
#
# SOURCE FILE: /Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv
#   (the global CBPF project-level fact table — all pooled funds, all allocation years).
#
# SCOPE: only the DRC 2025-2026 eligible cohort — the same 145-project cohort used by
#   the peer-grouping cells above. A row is kept when:
#     - PooledFundName == "DRC" and AllocationYear in {2025, 2026}
#     - ApprovedDate present; Budget present and > 0
#     - AllocationTypeCategory != "HFU Management Cost" (fund management fees excluded)
#     - Men/Women/Boys/Girls all present and >= 0, and their sum > 0
#   Result: 145 projects (76 from 2026, 69 from 2025). Other funds, other years, and
#   rows failing the input checks are NOT included.
#
# WHAT IT DOES:
#   1. Tags each project with `sector_regex` using the same keyword regex as Method 3
#      (evaluation cell above): title matches exactly one of the 8 sector keyword lists
#      -> that sector; multiple matches -> "Multisector"; no match -> "Untagged".
#   2. Adds people_targeted_plan (Men+Women+Boys+Girls) and
#      budget_per_person (Budget / people_targeted_plan).
#   3. Keeps 12 columns (ChfProjectCode, PooledFundName, AllocationYear,
#      AllocationSourceName, AllocationType, OrganizationName, OrganizationType,
#      ProjectTitle, Budget, people_targeted_plan, budget_per_person, sector_regex)
#      and writes them to
#      /Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/drc_cbpf_sector_categories.csv
#   4. Verifies the write: re-reads the CSV, asserts row count and category values
#      match the in-memory frame, and prints category + per-year counts.
#
# CAVEAT: sector_regex is INFERRED from ProjectTitle keywords (single-match only) —
#   not a verified field. Self-contained cell: safe to re-run after a session restart.
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

gs = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_project_summary.csv")
_demo = ["Men", "Women", "Boys", "Girls"]

# Same eligibility as the peer-grouping cells
_ok = (gs["PooledFundName"] == "DRC") & gs["AllocationYear"].isin([2025, 2026])
_ok &= gs["ApprovedDate"].notna() & gs["Budget"].notna() & (gs["Budget"] > 0)
_ok &= gs["AllocationTypeCategory"] != "HFU Management Cost"
for _c in _demo:
    _ok &= gs[_c].notna() & (gs[_c] >= 0)
_ok &= gs[_demo].sum(axis=1) > 0

# Regex sector tagger (identical to the Method 3 cell)
_RGX_KW = {
    "Santé": ["santé", "sante", "health", "ebola", "vaccin", "médic", "medic", "choléra", "cholera", "rougeole"],
    "Nutrition": ["nutrition"],
    "Sécurité alimentaire": ["secal", "food", "alimentaire", "faim", "agricol", "moyens de subsistance", "livelihood"],
    "WASH": ["wash", "eau", "hygiène", "hygiene", "assainissement", "sanitation"],
    "Protection": ["protection", "gbv", "vbg", "psea", "anti-mines", "hlp", "genre"],
    "Éducation": ["éducation", "education", "scolaire", "école"],
    "Abri-AME": ["abri", "shelter", "nfis", "non-food", "ame"],
    "CCCM": ["cccm", "camp"],
}
def _regex_sector(_t):
    _s = str(_t).lower()
    _hits = [n for n, w in _RGX_KW.items() if any(x in _s for x in w)]
    return _hits[0] if len(_hits) == 1 else ("Multisector" if _hits else "Untagged")

sector_categorized = gs[_ok].copy()
sector_categorized["sector_regex"] = sector_categorized["ProjectTitle"].apply(_regex_sector)
sector_categorized["people_targeted_plan"] = sector_categorized[_demo].sum(axis=1)
sector_categorized["budget_per_person"] = (sector_categorized["Budget"]
                                            / sector_categorized["people_targeted_plan"]).round(2)

_out_cols = ["ChfProjectCode", "PooledFundName", "AllocationYear", "AllocationSourceName",
             "AllocationType", "OrganizationName", "OrganizationType", "ProjectTitle",
             "Budget", "people_targeted_plan", "budget_per_person", "sector_regex"]
sector_categorized = sector_categorized[_out_cols].copy()

_out_path = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/drc_cbpf_sector_categories.csv"
sector_categorized.to_csv(_out_path, index=False)

# Verify the written file round-trips and matches the cohort category distribution
_chk = pd.read_csv(_out_path)
assert len(_chk) == len(sector_categorized), "row count mismatch after write"
assert (_chk["sector_regex"] == sector_categorized["sector_regex"].values).all(), "category mismatch after write"
print(f"written: {_out_path}")
print(f"rows: {len(_chk)} | columns: {list(_chk.columns)}")
print("category counts:", _chk["sector_regex"].value_counts().to_dict())
print("by year:", _chk["AllocationYear"].value_counts().to_dict())
display(_chk.head(8))

# COMMAND ----------

# DBTITLE 1,AI grouping method
# MAGIC %md
# MAGIC ## AI sector grouping — `ai_classify` (AI-decided group matching)
# MAGIC
# MAGIC **Method:** Databricks AI function `ai_classify` (v2.1) reads each `ProjectTitle` (French or English) and assigns one of the **same 10 labels** as the regex method (8 sectors + Multisector + Untagged), with per-label descriptions, global instructions (“prefer the dominant sector; Multisector only when several sectors are equally central”), confidence scores, and a rationale per project.
# MAGIC
# MAGIC **Guardrails:** one call per project, results stored once and reused (AI output is sampled, not deterministic); labels remain **inferred, not verified** — rationales are included so any label can be spot-checked. Agreement with `sector_regex` is reported, and disagreements are listed for manual review.

# COMMAND ----------

# DBTITLE 1,AI sector grouping via ai_classify
import pandas as pd, json

# 1) Load the categorized cohort (145 projects) and register for SQL
sc = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/drc_cbpf_sector_categories.csv")
spark.createDataFrame(sc[["ChfProjectCode", "ProjectTitle", "sector_regex"]]).createOrReplaceTempView("sc_titles")

_labels = json.dumps({
    "Santé": "Health care, medical assistance, epidemic response such as Ebola, measles, cholera, vaccination",
    "Nutrition": "Nutrition, treatment or prevention of acute malnutrition",
    "Sécurité alimentaire": "Food security, agriculture, livelihoods, food assistance, cash for food",
    "WASH": "Water supply, hygiene promotion, sanitation",
    "Protection": "Protection, gender-based violence, child protection, PSEA, housing land property, mine action",
    "Éducation": "Education, schooling, learning",
    "Abri-AME": "Shelter, non-food items, household kits",
    "CCCM": "Camp coordination and camp management, displacement site management",
    "Multisector": "Truly integrated multi-sector response where no single sector dominates",
    "Untagged": "No humanitarian sector identifiable from the title"
}, ensure_ascii=False)
_instr = ("Inputs are humanitarian project titles in French or English from the DRC pooled fund. "
          "Classify each project by its single primary intervention sector. "
          "Prefer the dominant sector when one clearly leads. Use Multisector only when several sectors are equally central. "
          "Use Untagged only when no sector can be identified.")

# 2) One ai_classify call per project, stored once; fields extracted server-side
sql = f"""
WITH classified AS (
  SELECT ChfProjectCode, ProjectTitle, sector_regex,
         ai_classify(
           ProjectTitle,
           '{_labels}',
           MAP('version','2.1','instructions','{_instr}',
               'enableConfidenceScores','true','enableRationales','true')
         ) AS ai_result
  FROM sc_titles
)
SELECT ChfProjectCode, ProjectTitle, sector_regex,
       variant_get(ai_result, '$.response[0].value', 'STRING') AS sector_ai,
       variant_get(ai_result, '$.response[0].confidence_score', 'DOUBLE') AS confidence,
       variant_get(ai_result, '$.response[0].rationale', 'STRING') AS rationale,
       variant_get(ai_result, '$.error_message', 'STRING') AS error_message
FROM classified
"""
sector_ai_table = spark.sql(sql).toPandas()

# 3) Validation + agreement with the regex labels
_valid = set(json.loads(_labels).keys())
_bad = sector_ai_table[~sector_ai_table["sector_ai"].isin(_valid)]
print(f"classified: {len(sector_ai_table)} projects | errors: {sector_ai_table['error_message'].notna().sum()} "
      f"| invalid labels: {len(_bad)} | null labels: {sector_ai_table['sector_ai'].isna().sum()}")

sector_ai_table["agree"] = sector_ai_table["sector_ai"] == sector_ai_table["sector_regex"]
print(f"agreement with sector_regex: {sector_ai_table['agree'].sum()}/{len(sector_ai_table)} "
      f"({100 * sector_ai_table['agree'].mean():.0f}%)")

print("\nlabel counts (regex vs AI):")
_ct = pd.crosstab(sector_ai_table["sector_regex"], sector_ai_table["sector_ai"],
                  rownames=["sector_regex"], colnames=["sector_ai"])
display(_ct)

print("\nmedian confidence by AI label:")
display(sector_ai_table.groupby("sector_ai")["confidence"].agg(n="count", median="median").round(2).sort_values("n", ascending=False))

# 4) Disagreements for manual spot-checking (rationale included)
_dis = sector_ai_table[~sector_ai_table["agree"]].copy()
_dis["title"] = _dis["ProjectTitle"].str.slice(0, 80)
_dis["rationale"] = _dis["rationale"].str.slice(0, 120)
print(f"\nDISAGREEMENTS ({len(_dis)}) — review with rationales:")
display(_dis[["ChfProjectCode", "title", "sector_regex", "sector_ai", "confidence", "rationale"]]
        .sort_values("confidence").reset_index(drop=True))