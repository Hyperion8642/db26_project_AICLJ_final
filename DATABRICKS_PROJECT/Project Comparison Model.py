# Databricks notebook source
# DBTITLE 1,Notebook header
# MAGIC %md
# MAGIC # Project Comparison Model
# MAGIC
# MAGIC Peer-group outlier flags (Tukey/MAD) and a KNN **comparable-project ML model** for the beneficiary-to-budget ratio of the 145-project DRC 2025–26 CBPF cohort.

# COMMAND ----------

# DBTITLE 1,Peer-group outlier method
# MAGIC %md
# MAGIC ## Peer-group outlier flags — median, IQR (Tukey fences) and MAD
# MAGIC
# MAGIC **Data:** `drc_cbpf_sector_categories.csv` — the 145-project DRC 2025–2026 CBPF eligible cohort (source: `global_cbpf_project_summary.csv`; `sector_regex` is inferred from project titles, single keyword-match).
# MAGIC
# MAGIC **Peer groups:** the `sector_regex` categories. For each group we compute the median, quartiles, **IQR**, **Tukey fences** ($Q_1 - 1.5\times\text{IQR}$ and $Q_3 + 1.5\times\text{IQR}$), and the **Median Absolute Deviation (MAD)** of `budget_per_person`.
# MAGIC
# MAGIC **Flag rules per project:**
# MAGIC * **Tukey:** below the lower fence or above the upper fence of its group
# MAGIC * **MAD (more resistant):** modified z-score $0.6745\times(x-\text{median})/\text{MAD}$ beyond ±3.5
# MAGIC
# MAGIC Groups with fewer than 10 projects (Project.md's peer minimum) are labeled *insufficient peers* — no flags computed. Fences use the full group (median/IQR/MAD are resistant statistics, so a single project barely moves them — leave-one-out is unnecessary here).

# COMMAND ----------

import pandas as pd
import numpy as np

cm = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/drc_cbpf_sector_categories.csv")
MIN_PEERS = 10  # Project.md peer minimum

# 1) Peer-group summary: median, IQR, Tukey fences, MAD
_stats = []
for _sec, _g in cm.groupby("sector_regex"):
    _v = _g["budget_per_person"].to_numpy(dtype=float)
    _q1, _med, _q3 = np.percentile(_v, [25, 50, 75])
    _iqr = _q3 - _q1
    _mad = float(np.median(np.abs(_v - _med)))
    _stats.append({
        "sector_regex": _sec, "n": len(_v),
        "median": round(_med, 2), "Q1": round(_q1, 2), "Q3": round(_q3, 2),
        "IQR": round(_iqr, 2),
        "lower_fence": round(_q1 - 1.5 * _iqr, 2),
        "upper_fence": round(_q3 + 1.5 * _iqr, 2),
        "MAD": round(_mad, 2),
    })
group_stats = pd.DataFrame(_stats).sort_values("n", ascending=False).reset_index(drop=True)
print(f"PEER-GROUP STATS (metric: budget_per_person, n={len(cm)} projects)")
display(group_stats)

# 2) Per-project flags (Tukey fences + MAD modified z-score)
_rows = []
for _sec, _g in cm.groupby("sector_regex"):
    _v = _g["budget_per_person"].to_numpy(dtype=float)
    if len(_v) < MIN_PEERS:
        for _, _r in _g.iterrows():
            _rows.append({"ChfProjectCode": _r["ChfProjectCode"], "AllocationYear": _r["AllocationYear"],
                          "sector_regex": _sec, "budget_per_person": _r["budget_per_person"],
                          "group_median": np.nan, "lower_fence": np.nan, "upper_fence": np.nan,
                          "flag_tukey": f"insufficient peers ({len(_v) - 1})",
                          "mod_z": np.nan, "flag_mad": "n/a (group too small)"})
        continue
    _q1, _med, _q3 = np.percentile(_v, [25, 50, 75])
    _iqr = _q3 - _q1
    _lo, _hi = _q1 - 1.5 * _iqr, _q3 + 1.5 * _iqr
    _mad = float(np.median(np.abs(_v - _med)))
    for _, _r in _g.iterrows():
        _x = float(_r["budget_per_person"])
        _ft = ("below lower fence" if _x < _lo else
               "above upper fence" if _x > _hi else "within fences")
        if _mad > 0:
            _mz = 0.6745 * (_x - _med) / _mad
            _fm = "outlier (|mod z| > 3.5)" if abs(_mz) > 3.5 else "within MAD rule"
        else:
            _mz, _fm = np.nan, "MAD = 0 (undefined)"
        _rows.append({"ChfProjectCode": _r["ChfProjectCode"], "AllocationYear": _r["AllocationYear"],
                      "sector_regex": _sec, "budget_per_person": _r["budget_per_person"],
                      "group_median": round(_med, 2), "lower_fence": round(_lo, 2),
                      "upper_fence": round(_hi, 2), "flag_tukey": _ft,
                      "mod_z": round(_mz, 2) if _mz == _mz else np.nan, "flag_mad": _fm})

peer_flags_iqr = pd.DataFrame(_rows)
print("\nTukey flag counts:", peer_flags_iqr["flag_tukey"].value_counts().to_dict())
print("MAD flag counts:", peer_flags_iqr["flag_mad"].value_counts().to_dict())

# 3) Flagged projects (either rule) with both rules side by side
_flagged = peer_flags_iqr[peer_flags_iqr["flag_tukey"].str.startswith(("below", "above"))
                          | peer_flags_iqr["flag_mad"].str.startswith("outlier")].copy()
_flagged["pilot_2026R"] = _flagged["ChfProjectCode"].str.contains("-26-R-")
print(f"\nFLAGGED PROJECTS: {len(_flagged)} of {len(peer_flags_iqr)} "
      f"({_flagged['pilot_2026R'].sum()} from the 2026 Reserve pilot)")
display(_flagged.sort_values("budget_per_person")
        .style.format({"budget_per_person": "${:,.2f}", "group_median": "${:,.2f}",
                       "lower_fence": "${:,.2f}", "upper_fence": "${:,.2f}"}))

# 4) Agreement between the two rules
_both = peer_flags_iqr[peer_flags_iqr["flag_tukey"].str.startswith(("below", "above"))
                       & peer_flags_iqr["flag_mad"].str.startswith("outlier")]
_tukey_only = peer_flags_iqr[peer_flags_iqr["flag_tukey"].str.startswith(("below", "above"))
                            & ~peer_flags_iqr["flag_mad"].str.startswith("outlier")]
_mad_only = peer_flags_iqr[~peer_flags_iqr["flag_tukey"].str.startswith(("below", "above"))
                           & peer_flags_iqr["flag_mad"].str.startswith("outlier")]
print(f"\nBoth rules flag: {len(_both)} | Tukey only: {len(_tukey_only)} | MAD only: {len(_mad_only)}")

# COMMAND ----------

# DBTITLE 1,ML model method
# MAGIC %md
# MAGIC ## Comparable-project ML model — beneficiary-to-budget ratio
# MAGIC
# MAGIC **Idea:** a K-nearest-neighbors model learns what beneficiary-to-budget ratio (`people_targeted_plan / Budget` — beneficiaries reached per US$) **similar projects** achieve. For every project we:
# MAGIC
# MAGIC 1. find its **K = 10 most comparable projects** (Project.md's peer minimum), matched on sector, organization type, allocation source/year and budget size — **never on the ratio itself**, so comparables are matched on scope, not outcome;
# MAGIC 2. compare its actual ratio to the median of those comparables;
# MAGIC 3. flag it **HIGH** (reaches ≥ 1.5× more beneficiaries per $ than its comparables) or **LOW** (≤ 0.67×), else *in line*.
# MAGIC
# MAGIC The logged model takes raw columns (`sector_regex`, `OrganizationType`, `AllocationSourceName`, `AllocationYear`, `Budget`); the log transform of budget and the target live inside the pipeline.

# COMMAND ----------

# DBTITLE 1,EDA: features and target distribution
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# reload so this section is self-contained
cm = pd.read_csv("/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/drc_cbpf_sector_categories.csv")
cm["beneficiaries_per_usd"] = cm["people_targeted_plan"] / cm["Budget"]

display(pd.DataFrame({
    "feature": ["sector_regex", "OrganizationType", "AllocationSourceName", "AllocationYear", "Budget",
                 "beneficiaries_per_usd (target)"],
    "type": ["categorical / nominal", "categorical / nominal", "categorical / nominal",
              "numeric integer (year)", "numeric float, skewed → log inside pipeline",
              "numeric float, skewed → log-transformed target"],
}))

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
for s, g in cm[cm["sector_regex"].isin(cm["sector_regex"].value_counts().head(4).index)].groupby("sector_regex"):
    axes[0].scatter(np.log10(g["Budget"]), g["beneficiaries_per_usd"], s=14, alpha=0.7, label=s)
axes[0].set_xlabel("log10 Budget ($)"); axes[0].set_ylabel("beneficiaries per $"); axes[0].legend(fontsize=8)
axes[0].set_title("Target vs budget size, by sector")
cm.boxplot(column="beneficiaries_per_usd", by="sector_regex", ax=axes[1])
axes[1].set_yscale("log"); axes[1].set_title(""); axes[1].tick_params(axis="x", rotation=45)
plt.suptitle(""); plt.tight_layout(); plt.show()
print(cm[["Budget", "people_targeted_plan", "beneficiaries_per_usd"]].describe().round(4))

# COMMAND ----------

# DBTITLE 1,Train + evaluate + log KNN comparable model
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import mlflow
from mlflow.models import infer_signature

CAT = ["sector_regex", "OrganizationType", "AllocationSourceName"]
K = 10  # Project.md peer minimum
X = cm[CAT + ["AllocationYear", "Budget"]]   # raw inputs; log(Budget) happens inside the pipeline
y = cm["beneficiaries_per_usd"]

preprocess = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
    ("year", StandardScaler(), ["AllocationYear"]),
    ("budget", Pipeline([("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                          ("scale", StandardScaler())]), ["Budget"]),
])
knn_model = TransformedTargetRegressor(
    regressor=Pipeline([("pre", preprocess),
                        ("knn", KNeighborsRegressor(n_neighbors=K, weights="distance"))]),
    func=np.log, inverse_func=np.exp)

# held-out evaluation on a random split (rows are cross-sectional, not a time series)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
knn_model.fit(Xtr, ytr)
pred_te = knn_model.predict(Xte)
r2 = r2_score(yte, pred_te)
r2_log = r2_score(np.log(yte), np.log(pred_te))
mae = mean_absolute_error(yte, pred_te)
print(f"Holdout (n={len(yte)}): R2={r2:.3f} (log scale: {r2_log:.3f}) | MAE={mae:.4f} beneficiaries/$")
print("A modest fit is expected — the model's purpose is comparable-matching, not precise prediction.")

# refit on the full cohort and log with MLflow
knn_model.fit(X, y)
signature = infer_signature(X.head(100), knn_model.predict(X.head(100)))
with mlflow.start_run(run_name="knn10_comparables_beneficiaries_per_usd"):
    mlflow.log_params({"k": K, "features": CAT + ["AllocationYear", "Budget"],
                       "target": "beneficiaries_per_usd",
                       "n_train": len(Xtr), "n_test": len(Xte), "n_final_fit": len(X)})
    mlflow.log_metrics({"holdout_r2": r2, "holdout_r2_log": r2_log, "holdout_mae": mae})
    model_info = mlflow.sklearn.log_model(knn_model, name="model",
                                          signature=signature, input_example=X.head(3))
print("MLflow model logged:", model_info.model_uri)

# COMMAND ----------

# DBTITLE 1,Comparable projects and HIGH/LOW flags
from sklearn.neighbors import NearestNeighbors

# HOW THIS CELL WORKS
# 1. Reuse the fitted KNN model's feature space Z (one-hot sector/org-type/source
#    + scaled AllocationYear + scaled log Budget) and ask it for each project's
#    K=10 nearest neighbours, excluding the project itself.
# 2. comparable_peer_ratio = median beneficiaries_per_usd of those 10 comparables
#    — what "projects like this one" typically achieve per US$.
# 3. actual_vs_peers = the project's own ratio / comparable_peer_ratio:
#       >= 1.5   -> HIGH efficiency flag (reaches >= 50% more people per $ than comparables)
#       <= 1/1.5  -> LOW  efficiency flag (reaches <= 67% as many)
#       otherwise -> in line with comparables.
# 4. describe_project(code) prints one project's ratio next to its comparables,
#    each tagged as reaching more/fewer beneficiaries/$ than the project asked about.

# comparable lookup in the same feature space the KNN model uses
Z = knn_model.regressor_.named_steps["pre"].transform(X)
nn = NearestNeighbors(n_neighbors=K + 1).fit(Z)
_, idx = nn.kneighbors(Z)

rows = []
for i in range(len(cm)):
    peers = [j for j in idx[i] if j != i][:K]          # drop self, keep K comparables
    peer_ratio = float(np.median(cm["beneficiaries_per_usd"].iloc[peers]))
    actual = float(cm["beneficiaries_per_usd"].iloc[i])
    rel = actual / peer_ratio
    flag = "HIGH efficiency vs comparables" if rel >= 1.5 else (
           "LOW efficiency vs comparables" if rel <= 1 / 1.5 else "in line with comparables")
    rows.append({"ChfProjectCode": cm["ChfProjectCode"].iloc[i],
                 "ProjectTitle": str(cm["ProjectTitle"].iloc[i])[:70],
                 "OrganizationName": cm["OrganizationName"].iloc[i],
                 "AllocationYear": cm["AllocationYear"].iloc[i],
                 "sector_regex": cm["sector_regex"].iloc[i],
                 "Budget": cm["Budget"].iloc[i],
                 "beneficiaries_per_usd": round(actual, 4),
                 "comparable_peer_ratio": round(peer_ratio, 4),
                 "actual_vs_peers": round(rel, 6),  # 6 dp: log() of this must stay finite
                 "flag": flag,
                 "comparables": " | ".join(f"{cm['ChfProjectCode'].iloc[j][-10:]}: {str(cm['ProjectTitle'].iloc[j])[:45]}"
                                           for j in peers[:5])})
comparable_results = pd.DataFrame(rows)
comparable_results["pilot_2026R"] = comparable_results["ChfProjectCode"].str.contains("-26-R-")

print(f"Flags: {comparable_results['flag'].value_counts().to_dict()}")
print(f"Flagged projects from the 2026 Reserve pilot: "
      f"{comparable_results.loc[comparable_results['flag'] != 'in line with comparables', 'pilot_2026R'].sum()}")

display(comparable_results[comparable_results["flag"] == "HIGH efficiency vs comparables"]
        .sort_values("actual_vs_peers", ascending=False).head(10))
display(comparable_results[comparable_results["flag"] == "LOW efficiency vs comparables"]
        .sort_values("actual_vs_peers").head(10))

def describe_project(code):
    """Show a project's ratio next to its K comparable projects, each tagged HIGH/LOW."""
    i = cm.index[cm["ChfProjectCode"] == code][0]
    peers = [j for j in idx[i] if j != i][:K]
    out = cm.loc[peers, ["ChfProjectCode", "ProjectTitle", "OrganizationName", "AllocationYear",
                         "sector_regex", "Budget", "beneficiaries_per_usd"]].copy()
    out["ProjectTitle"] = out["ProjectTitle"].str.slice(0, 60)
    out["vs_this_project"] = np.where(
        out["beneficiaries_per_usd"] > cm["beneficiaries_per_usd"].iloc[i], "reaches more beneficiaries/$",
        "reaches fewer beneficiaries/$")
    print(f"{code} — {cm['ProjectTitle'].iloc[i]}\n"
          f"  {cm['beneficiaries_per_usd'].iloc[i]:.4f} beneficiaries/$ "
          f"({cm['sector_regex'].iloc[i]}, {cm['OrganizationType'].iloc[i]}, ${cm['Budget'].iloc[i]:,.0f})")
    display(out.round(4))

# example: the most HIGH-flagged project and its comparables
describe_project(comparable_results.sort_values("actual_vs_peers", ascending=False)
                 .iloc[0]["ChfProjectCode"])

# COMMAND ----------

# DBTITLE 1,Efficiency score & sector tiers — method
# MAGIC %md
# MAGIC ## Approach 1 — efficiency score + sector tiers (1-D k-means)
# MAGIC
# MAGIC **Efficiency score:** `efficiency_score = log(actual_vs_peers)` from the comparable-project model above.
# MAGIC * **0** — reaches exactly what its 10 comparables reach per US$;
# MAGIC * **+1** — ≈ 2.7× more beneficiaries/$ than its comparables; **−1** — ≈ 2.7× fewer.
# MAGIC
# MAGIC Because the comparables already match on sector, org type, allocation source/year and budget size, this is an **adjusted** efficiency score, not a raw ratio.
# MAGIC
# MAGIC **Tiers:** within each sector with ≥ 10 projects (Project.md's peer minimum), 1-D k-means (k=3) on the efficiency score; centroids ordered low→high give **Low / Average / High** efficiency tiers. Sectors with < 10 projects are labeled *insufficient peers* (no tier).
# MAGIC
# MAGIC *Why not one 2-D KMeans on sector dummies + score?* One-hot columns dominate Euclidean distance, so the clusters would just reproduce sector boundaries — tiering within sector gives the same result, deterministically.

# COMMAND ----------

# DBTITLE 1,Efficiency score + sector tiers (approach 1)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

PEER_MIN = 10  # Project.md peer minimum

eff = comparable_results.copy()
eff["efficiency_score"] = np.log(eff["actual_vs_peers"])  # 0 = in line with comparables
assert np.isfinite(eff["efficiency_score"]).all(), "non-positive actual_vs_peers found — check cell above"

tier_rows = []
_tier_meta = []  # per-sector k-means centroids, for MLflow
for _sec, _g in eff.groupby("sector_regex"):
    _base = _g[["ChfProjectCode", "ProjectTitle", "OrganizationName", "AllocationYear", "sector_regex",
                "Budget", "beneficiaries_per_usd", "actual_vs_peers", "efficiency_score", "pilot_2026R"]].copy()
    if len(_g) < PEER_MIN:
        _base["tier"] = "insufficient peers"
        tier_rows.append(_base)
        continue
    _s = _g[["efficiency_score"]].to_numpy()
    _km = KMeans(n_clusters=3, n_init=10, random_state=42).fit(_s)
    _order = np.argsort(_km.cluster_centers_.ravel())          # ascending centroid
    _names = np.array(["Low", "Average", "High"])
    _base["tier"] = _names[_order][_km.labels_]
    _centers = _km.cluster_centers_.ravel()[_order]           # Low, Average, High centroids
    _tier_meta.append({"sector_regex": _sec, "centroid_low": _centers[0],
                       "centroid_average": _centers[1], "centroid_high": _centers[2]})
    tier_rows.append(_base)

tiered = pd.concat(tier_rows).sort_values(["sector_regex", "efficiency_score"],
                                          ascending=[True, False]).reset_index(drop=True)

_counts = (tiered.pivot_table(index="sector_regex", columns="tier", values="ChfProjectCode",
                              aggfunc="count", fill_value=0)
            .reindex(columns=["Low", "Average", "High", "insufficient peers"], fill_value=0))
print("Sector × efficiency tier (project counts):")
display(_counts)

print("\nAll tiered projects (insufficient-peer sectors excluded from chart, listed in table):")
display(tiered.loc[tiered["tier"] != "insufficient peers",
                   ["ChfProjectCode", "ProjectTitle", "OrganizationName", "sector_regex",
                    "efficiency_score", "actual_vs_peers", "beneficiaries_per_usd", "tier", "pilot_2026R"]]
        .round(3))

_plot = tiered[tiered["tier"] != "insufficient peers"]
_sectors = _plot["sector_regex"].unique().tolist()
_colors = {"Low": "#d9534f", "Average": "#5bc0de", "High": "#5cb85c"}
fig, ax = plt.subplots(figsize=(11, 3.5))
for _i, _sec in enumerate(_sectors):
    _g = _plot[_plot["sector_regex"] == _sec]
    ax.scatter(_g["efficiency_score"], [_i] * len(_g), c=_g["tier"].map(_colors), s=40, alpha=0.8)
ax.set_yticks(range(len(_sectors)), _sectors)
ax.axvline(0, color="gray", ls=":", lw=1)
ax.set_xlabel("efficiency score = log(actual ratio / comparable-peer median ratio)")
ax.set_title("Efficiency tiers within sector (1-D k-means, k=3)")
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=c, label=t) for t, c in _colors.items()])
plt.tight_layout(); plt.show()

# --- MLflow: log the tiering run (sizes, centroids, full tier table) ---
import os, re, tempfile
import mlflow

_slug = lambda s: re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")
with mlflow.start_run(run_name="sector_efficiency_tiers_1d_kmeans"):
    mlflow.log_params({"method": "1-D k-means on efficiency_score = log(actual_vs_peers)",
                       "k": 3, "peer_min": PEER_MIN, "n_projects": len(tiered),
                       "n_tiered": int((tiered["tier"] != "insufficient peers").sum())})
    for _sec, _row in _counts.iterrows():
        for _tier, _n in _row.items():
            if _n > 0:
                mlflow.log_metric(f"{_slug(_sec)}_{_slug(_tier)}_n", int(_n))
    for _m in _tier_meta:
        for _tn, _cv in (("low", _m["centroid_low"]), ("average", _m["centroid_average"]),
                         ("high", _m["centroid_high"])):
            mlflow.log_metric(f"{_slug(_m['sector_regex'])}_centroid_{_tn}", round(float(_cv), 4))
    _tmp = tempfile.mkdtemp()
    _csv = os.path.join(_tmp, "sector_efficiency_tiers.csv")
    tiered.to_csv(_csv, index=False)
    mlflow.log_artifact(_csv)
print("Logged to MLflow: tier sizes, per-sector tier centroids, and the full tiered table as a CSV artifact.")

# COMMAND ----------

# DBTITLE 1,All-country model — method
# MAGIC %md
# MAGIC ## All-country comparable model — 2025–26 CBPF
# MAGIC
# MAGIC **Data:** `cbpf_projects_2025_2026.csv` — **2,448 eligible projects across 33 country funds** (2025–26; already filtered for approved, Budget > 0, valid beneficiary totals, no Management Cost). DRC's 145 projects are exactly the cohort used above, so results are directly comparable.
# MAGIC
# MAGIC **Sector tagging:** `sector_tag` from an English/French keyword regex on `ProjectTitle` (accents stripped). Titles matching **≥ 2 sectors → Multisector**, exactly 1 → that sector, 0 → *Untagged*. Inferred from titles, not a verified sector column.
# MAGIC
# MAGIC **Model:** same KNN recipe as the DRC section, with two additions:
# MAGIC * **country (`PooledFundName`) is a matching feature** — cost structures differ across funds;
# MAGIC * comparables are searched **within country only**, matched on `sector_tag`, org type, allocation source/year and log budget — never on the ratio itself.
# MAGIC
# MAGIC **Tiers:** efficiency score = log(actual ratio / in-country comparable median) — already country-adjusted — then 1-D k-means (k=3) **within `sector_tag` across the whole cohort** (≥ 10 projects per sector).

# COMMAND ----------

# DBTITLE 1,All-country: load + sector tagging
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
    hits = {sec for sec, kws in SECTOR_KW.items() if any(kw in t for kw in kws)}
    if len(hits) >= 2:
        return "Multisector"
    if len(hits) == 1:
        return next(iter(hits))
    if re.search(r"multisector|multi sector|integrated|integre", t):
        return "Multisector"
    return "Untagged"

ac["sector_tag"] = ac["ProjectTitle"].map(tag_sector)
print(f"eligible projects: {len(ac)} | funds: {ac['PooledFundName'].nunique()}")
display(ac["sector_tag"].value_counts().rename("projects").to_frame())
display(ac["PooledFundName"].value_counts().head(10).rename("eligible projects").to_frame())

# COMMAND ----------

pd.set_option('display.max_columns', None)
d_all.head()

# COMMAND ----------

# DBTITLE 1,All-country: train + evaluate + log KNN
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import mlflow
from mlflow.models import infer_signature

CAT_ALL = ["PooledFundName", "sector_tag", "OrganizationType", "AllocationSourceName"]
Ka = 10  # same peer minimum as the DRC model
Xa = ac[CAT_ALL + ["AllocationYear", "Budget"]]   # raw inputs; log(Budget) inside the pipeline
ya = ac["ben_per_usd"]

pre_all = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_ALL),
    ("year", StandardScaler(), ["AllocationYear"]),
    ("budget", Pipeline([("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                          ("scale", StandardScaler())]), ["Budget"]),
])
knn_model_all = TransformedTargetRegressor(
    regressor=Pipeline([("pre", pre_all),
                        ("knn", KNeighborsRegressor(n_neighbors=Ka, weights="distance"))]),
    func=np.log, inverse_func=np.exp)

Xa_tr, Xa_te, ya_tr, ya_te = train_test_split(Xa, ya, test_size=0.2, random_state=42)
knn_model_all.fit(Xa_tr, ya_tr)
pa = knn_model_all.predict(Xa_te)
r2a, r2a_log, maea = (r2_score(ya_te, pa), r2_score(np.log(ya_te), np.log(pa)),
                      mean_absolute_error(ya_te, pa))
print(f"Holdout (n={len(ya_te)}): R2={r2a:.3f} (log scale: {r2a_log:.3f}) | MAE={maea:.4f} beneficiaries/$")

# refit on the full cohort and log to MLflow
knn_model_all.fit(Xa, ya)
sig_all = infer_signature(Xa.head(100), knn_model_all.predict(Xa.head(100)))
with mlflow.start_run(run_name="knn10_comparables_all_countries"):
    mlflow.log_params({"k": Ka, "features": CAT_ALL + ["AllocationYear", "Budget"],
                       "target": "ben_per_usd", "n_train": len(Xa_tr), "n_test": len(Xa_te),
                       "n_final_fit": len(Xa), "n_funds": ac["PooledFundName"].nunique()})
    mlflow.log_metrics({"holdout_r2": r2a, "holdout_r2_log": r2a_log, "holdout_mae": maea})
    model_info_all = mlflow.sklearn.log_model(knn_model_all, name="model",
                                              signature=sig_all, input_example=Xa.head(3))
print("MLflow model logged:", model_info_all.model_uri)

# COMMAND ----------

# DBTITLE 1,All-country: in-country comparables + flags
from sklearn.neighbors import NearestNeighbors

# comparables are searched WITHIN each country fund (cost structures differ across funds)
Za = knn_model_all.regressor_.named_steps["pre"].transform(Xa)
peer_ratio_a = np.full(len(ac), np.nan)
peer_idx_a = [None] * len(ac)
for _cty, _grp in ac.groupby("PooledFundName").groups.items():
    _idx = np.array(list(_grp))
    _k = min(Ka, len(_idx) - 1)                 # small funds: use every other project
    if _k < 1:
        continue                                 # single-project fund: no in-country peers
    _nn = NearestNeighbors(n_neighbors=_k + 1).fit(Za[_idx])
    _, _nb = _nn.kneighbors(Za[_idx])
    for _r, _i in enumerate(_idx):
        _peers = _idx[_nb[_r][_nb[_r] != _r][:_k]]
        peer_ratio_a[_i] = float(np.median(ac["ben_per_usd"].iloc[_peers]))
        peer_idx_a[_i] = _peers

rows_all = []
for _i in range(len(ac)):
    _actual = float(ac["ben_per_usd"].iloc[_i])
    _out = {"ChfProjectCode": ac["ChfProjectCode"].iloc[_i],
            "PooledFundName": ac["PooledFundName"].iloc[_i],
            "ProjectTitle": str(ac["ProjectTitle"].iloc[_i])[:70],
            "OrganizationName": ac["OrganizationName"].iloc[_i],
            "sector_tag": ac["sector_tag"].iloc[_i],
            "Budget": ac["Budget"].iloc[_i],
            "ben_per_usd": round(_actual, 4),
            "comparable_peer_ratio": round(peer_ratio_a[_i], 4) if peer_ratio_a[_i] == peer_ratio_a[_i] else np.nan,
            "actual_vs_peers": np.nan, "flag": "no in-country peers", "comparables": ""}
    if peer_ratio_a[_i] == peer_ratio_a[_i]:
        _rel = _actual / peer_ratio_a[_i]
        _out["actual_vs_peers"] = round(_rel, 6)
        _out["flag"] = ("HIGH efficiency vs comparables" if _rel >= 1.5 else
                         "LOW efficiency vs comparables" if _rel <= 1 / 1.5 else "in line with comparables")
        _out["comparables"] = " | ".join(f"{ac['ChfProjectCode'].iloc[j][-10:]}: {str(ac['ProjectTitle'].iloc[j])[:40]}"
                                     for j in peer_idx_a[_i][:3])
    rows_all.append(_out)
comparables_all = pd.DataFrame(rows_all)

print(f"Flags: {comparables_all['flag'].value_counts().to_dict()}")
print("\nTop HIGH (reaches most beneficiaries/$ vs its in-country comparables):")
display(comparables_all[comparables_all["flag"] == "HIGH efficiency vs comparables"]
        .sort_values("actual_vs_peers", ascending=False).head(10)
        [["ChfProjectCode", "PooledFundName", "ProjectTitle", "sector_tag", "ben_per_usd",
          "comparable_peer_ratio", "actual_vs_peers"]])
print("\nTop LOW (reaches fewest beneficiaries/$ vs its in-country comparables):")
display(comparables_all[comparables_all["flag"] == "LOW efficiency vs comparables"]
        .sort_values("actual_vs_peers").head(10)
        [["ChfProjectCode", "PooledFundName", "ProjectTitle", "sector_tag", "ben_per_usd",
          "comparable_peer_ratio", "actual_vs_peers"]])

def describe_project_all(code):
    """Show one project's ratio next to its in-country comparables (all-country model)."""
    _i = ac.index[ac["ChfProjectCode"] == code][0]
    _peers = peer_idx_a[_i]
    if _peers is None:
        print(f"{code}: no in-country comparables (single-project fund).")
        return
    _out = ac.loc[_peers, ["ChfProjectCode", "ProjectTitle", "OrganizationName", "PooledFundName",
                           "sector_tag", "Budget", "ben_per_usd"]].copy()
    _out["ProjectTitle"] = _out["ProjectTitle"].str.slice(0, 60)
    _out["vs_this_project"] = np.where(_out["ben_per_usd"] > ac["ben_per_usd"].iloc[_i],
                                        "reaches more beneficiaries/$", "reaches fewer beneficiaries/$")
    print(f"{code} — {ac['ProjectTitle'].iloc[_i]}\n"
          f"  {ac['ben_per_usd'].iloc[_i]:.4f} beneficiaries/$ ({ac['PooledFundName'].iloc[_i]}, "
          f"{ac['sector_tag'].iloc[_i]}, ${ac['Budget'].iloc[_i]:,.0f})")
    display(_out.round(4))

# COMMAND ----------

# DBTITLE 1,All-country: efficiency score + sector tiers + MLflow
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

# efficiency score = log(actual / in-country comparable median); already country-adjusted,
# so tiers are fit within sector_tag across the WHOLE cohort (not per country)
PEER_MIN_ALL = 10
eff_all = comparables_all[comparables_all["flag"] != "no in-country peers"].copy()
eff_all["efficiency_score"] = np.log(eff_all["actual_vs_peers"])
assert np.isfinite(eff_all["efficiency_score"]).all()

tier_rows_all, tier_meta_all = [], []
for _sec, _g in eff_all.groupby("sector_tag"):
    _base = _g[["ChfProjectCode", "PooledFundName", "ProjectTitle", "sector_tag",
                "ben_per_usd", "actual_vs_peers", "efficiency_score"]].copy()
    if len(_g) < PEER_MIN_ALL:
        _base["tier"] = "insufficient peers"
        tier_rows_all.append(_base)
        continue
    _s = _g[["efficiency_score"]].to_numpy()
    _km = KMeans(n_clusters=3, n_init=10, random_state=42).fit(_s)
    _order = np.argsort(_km.cluster_centers_.ravel())
    _names = np.array(["Low", "Average", "High"])
    _base["tier"] = _names[_order][_km.labels_]
    _c = _km.cluster_centers_.ravel()[_order]
    tier_meta_all.append({"sector_tag": _sec, "centroid_low": _c[0],
                          "centroid_average": _c[1], "centroid_high": _c[2]})
    tier_rows_all.append(_base)
tiers_all = pd.concat(tier_rows_all).sort_values(["sector_tag", "efficiency_score"],
                                                 ascending=[True, False]).reset_index(drop=True)

_counts_all = (tiers_all.pivot_table(index="sector_tag", columns="tier", values="ChfProjectCode",
                                     aggfunc="count", fill_value=0)
               .reindex(columns=["Low", "Average", "High", "insufficient peers"], fill_value=0))
print("Sector × efficiency tier (project counts, all countries):")
display(_counts_all)

# --- MLflow ---
import os, re, tempfile
_slug = lambda s: re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")
with mlflow.start_run(run_name="sector_efficiency_tiers_all_countries"):
    mlflow.log_params({"method": "1-D k-means on log(actual_vs_peers), in-country comparables",
                       "k": 3, "peer_min": PEER_MIN_ALL, "n_projects": len(eff_all),
                       "n_tiered": int((tiers_all["tier"] != "insufficient peers").sum())})
    for _sec, _row in _counts_all.iterrows():
        for _t, _n in _row.items():
            if _n > 0:
                mlflow.log_metric(f"{_slug(_sec)}_{_slug(_t)}_n", int(_n))
    for _m in tier_meta_all:
        for _tn, _cv in (("low", _m["centroid_low"]), ("average", _m["centroid_average"]),
                         ("high", _m["centroid_high"])):
            mlflow.log_metric(f"{_slug(_m['sector_tag'])}_centroid_{_tn}", round(float(_cv), 4))
    _tmp = tempfile.mkdtemp()
    tiers_all.to_csv(os.path.join(_tmp, "sector_efficiency_tiers_all_countries.csv"), index=False)
    mlflow.log_artifact(os.path.join(_tmp, "sector_efficiency_tiers_all_countries.csv"))
print("Logged tiers to MLflow (tier sizes, centroids, full CSV artifact).")

_plot = tiers_all[tiers_all["tier"] != "insufficient peers"]
_sectors = _plot["sector_tag"].unique().tolist()
_colors = {"Low": "#d9534f", "Average": "#5bc0de", "High": "#5cb85c"}
fig, ax = plt.subplots(figsize=(11, 4))
for _i, _sec in enumerate(_sectors):
    _g = _plot[_plot["sector_tag"] == _sec]
    ax.scatter(_g["efficiency_score"], [_i] * len(_g), c=_g["tier"].map(_colors), s=25, alpha=0.7)
ax.set_yticks(range(len(_sectors)), _sectors)
ax.axvline(0, color="gray", ls=":", lw=1)
ax.set_xlabel("efficiency score = log(actual ratio / in-country comparable median)")
ax.set_title("Efficiency tiers within sector — all countries (1-D k-means, k=3)")
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=c, label=t) for t, c in _colors.items()])
plt.tight_layout(); plt.show()

# COMMAND ----------

# DBTITLE 1,All-country: focused-sector tier chart
import matplotlib.pyplot as plt

# Focused-sector view of the tiers above: excludes Untagged, Multisector and Mine Action.
# (CCCM also drops out naturally — all 7 of its projects are "insufficient peers".)
_focus = tiers_all[(tiers_all["tier"] != "insufficient peers")
                   & ~tiers_all["sector_tag"].isin(["Untagged", "Multisector", "Mine Action"])]
_sectors_f = _focus["sector_tag"].unique().tolist()
_colors_f = {"Low": "#d9534f", "Average": "#5bc0de", "High": "#5cb85c"}
fig, ax = plt.subplots(figsize=(11, 4))
for _i, _sec in enumerate(_sectors_f):
    _g = _focus[_focus["sector_tag"] == _sec]
    ax.scatter(_g["efficiency_score"], [_i] * len(_g), c=_g["tier"].map(_colors_f), s=25, alpha=0.7)
ax.set_yticks(range(len(_sectors_f)), _sectors_f)
ax.axvline(0, color="gray", ls=":", lw=1)
ax.set_xlabel("efficiency score = log(actual ratio / in-country comparable median)")
ax.set_title("Efficiency tiers — focus sectors (Untagged / Multisector / Mine Action excluded)")
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=c, label=t) for t, c in _colors_f.items()])
plt.tight_layout(); plt.show()

# COMMAND ----------

# DBTITLE 1,Dashboard exports: sector stats + project tags (CSV)
import os

# Dashboard exports from the all-country model: (1) project-level tags/tiers, (2) sector-level stats.
OUT_DIR = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT"

# --- (1) project-level: tags + tier + score + core project facts ---
_tags = tiers_all[["ChfProjectCode", "sector_tag", "tier", "actual_vs_peers",
                   "efficiency_score", "ben_per_usd"]].copy()
_tags = _tags.merge(
    ac[["ChfProjectCode", "PooledFundName", "ProjectTitle", "OrganizationName", "OrganizationType",
        "AllocationSourceName", "AllocationYear", "Budget", "people_targeted"]],
    on="ChfProjectCode", how="left", validate="one_to_one")
_tags = _tags.merge(
    comparables_all[["ChfProjectCode", "flag", "comparable_peer_ratio"]],
    on="ChfProjectCode", how="left", validate="one_to_one")
_tags = _tags.rename(columns={
    "PooledFundName": "country", "sector_tag": "sector", "tier": "efficiency_tier",
    "ben_per_usd": "beneficiaries_per_usd", "actual_vs_peers": "ratio_vs_comparables",
    "comparable_peer_ratio": "comparables_median_ratio", "people_targeted": "people_served_targeted",
    "efficiency_score": "efficiency_score"})
_tags["efficiency_score"] = _tags["efficiency_score"].round(4)
_tags["ratio_vs_comparables"] = _tags["ratio_vs_comparables"].round(4)
_tags["beneficiaries_per_usd"] = _tags["beneficiaries_per_usd"].round(4)
_tags = _tags[["ChfProjectCode", "country", "ProjectTitle", "OrganizationName", "OrganizationType",
               "AllocationSourceName", "AllocationYear", "sector", "efficiency_tier", "flag",
               "Budget", "people_served_targeted", "beneficiaries_per_usd",
               "comparables_median_ratio", "ratio_vs_comparables", "efficiency_score"]]
_tags.to_csv(f"{OUT_DIR}/cbpf_dashboard_project_tags.csv", index=False)

# --- (2) sector-level summary stats (one row per sector + ALL SECTORS total) ---
def _sector_row(_sec, _g):
    _n_tiered = int((_g["efficiency_tier"] != "insufficient peers").sum())
    return {"sector": _sec, "n_projects": len(_g), "n_tiered": _n_tiered,
            "low_n": int((_g["efficiency_tier"] == "Low").sum()),
            "average_n": int((_g["efficiency_tier"] == "Average").sum()),
            "high_n": int((_g["efficiency_tier"] == "High").sum()),
            "insufficient_peers_n": int((_g["efficiency_tier"] == "insufficient peers").sum()),
            "pct_low": 100 * (_g["efficiency_tier"] == "Low").sum() / _n_tiered if _n_tiered else np.nan,
            "pct_high": 100 * (_g["efficiency_tier"] == "High").sum() / _n_tiered if _n_tiered else np.nan,
            "mean_budget_usd": _g["Budget"].mean(),
            "median_budget_usd": _g["Budget"].median(),
            "mean_people_served_targeted": _g["people_served_targeted"].mean(),
            "median_people_served_targeted": _g["people_served_targeted"].median(),
            "mean_beneficiaries_per_usd": _g["beneficiaries_per_usd"].mean(),
            "median_beneficiaries_per_usd": _g["beneficiaries_per_usd"].median()}

stats_df = pd.DataFrame([_sector_row(_sec, _g) for _sec, _g in
                         [("ALL SECTORS", _tags)] + sorted(_tags.groupby("sector"))])
stats_df["mean_budget_usd"] = stats_df["mean_budget_usd"].round(0)
stats_df["median_budget_usd"] = stats_df["median_budget_usd"].round(0)
stats_df["mean_people_served_targeted"] = stats_df["mean_people_served_targeted"].round(0)
stats_df["median_people_served_targeted"] = stats_df["median_people_served_targeted"].round(0)
stats_df["mean_beneficiaries_per_usd"] = stats_df["mean_beneficiaries_per_usd"].round(4)
stats_df["median_beneficiaries_per_usd"] = stats_df["median_beneficiaries_per_usd"].round(4)
stats_df[["pct_low", "pct_high"]] = stats_df[["pct_low", "pct_high"]].round(1)
stats_df.to_csv(f"{OUT_DIR}/cbpf_dashboard_sector_stats.csv", index=False)

# --- sanity checks + preview ---
assert len(_tags) == len(tiers_all), "project tags table lost rows in the merge"
assert stats_df.loc[stats_df["sector"] != "ALL SECTORS", "n_projects"].sum() == len(_tags), \
    "sector stats do not sum to the project count"
print(f"project tags CSV: {len(_tags)} rows -> {OUT_DIR}/cbpf_dashboard_project_tags.csv")
print(f"sector stats CSV: {len(stats_df)} rows -> {OUT_DIR}/cbpf_dashboard_sector_stats.csv")
display(stats_df)

# COMMAND ----------

# DBTITLE 1,eff_score model — method
# MAGIC %md
# MAGIC ## Efficiency-score model — `eff_score` dataset (scaffold, not yet run)
# MAGIC
# MAGIC Same strategy as the all-country model above, pointed at a new dataset with an **updated efficiency-score calculation**.
# MAGIC
# MAGIC **Before running:** in the first cell below, update `EFFSCORE_PATH` (currently a placeholder path) and confirm `OUTCOME_COL` matches the column name of the updated score. The cells will refuse to run until the file exists.
# MAGIC
# MAGIC **What it does:**
# MAGIC * target = `OUTCOME_COL` if present in the file; otherwise falls back to beneficiaries/$ (people_targeted / Budget);
# MAGIC * reuses the same `sector_tag` rules from above unless the file already carries a `sector_tag` column;
# MAGIC * KNN k=10 — country + sector + org type + allocation source/year + log budget as matching features, comparables searched **within country**, flag thresholds 1.5× / 0.67×;
# MAGIC * tiers within sector (1-D k-means, k=3, ≥ 10 projects per sector) computed **directly on the dataset's `eff_score`** — no derived or recalculated score; MLflow-logged like the previous runs. The comparable flags above still compare each project's `eff_score` to its in-country peer median.
# MAGIC
# MAGIC **Note:** the target is log-transformed (`func=np.log`) because the old score is a ratio. If your updated `eff_score` is already on a log/normalized scale, drop `func`/`inverse_func` in the model cell.

# COMMAND ----------

# DBTITLE 1,eff_score: config + load (placeholder)
import os
import numpy as np
import pandas as pd

# ==== UPDATE THESE WHEN THE eff_score FILE IS READY ====
EFFSCORE_PATH = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/efficiency_final.csv"  # PLACEHOLDER PATH — replace me
OUTCOME_COL = "eff_score"   # expected name of the updated efficiency-score column in that file
K_ES = 10                   # peer minimum, same as the previous models
# ========================================================

if not os.path.exists(EFFSCORE_PATH):
    raise FileNotFoundError(
        f"{EFFSCORE_PATH} does not exist yet. Update EFFSCORE_PATH to the real location of "
        f"the eff_score dataset, then rerun this cell and the ones below in order.")

es = pd.read_csv(EFFSCORE_PATH)

# target: the updated score column if present, otherwise beneficiaries/$ as before
if OUTCOME_COL in es.columns:
    es["outcome"] = es[OUTCOME_COL]
    print(f"Using '{OUTCOME_COL}' as the efficiency outcome ({es['outcome'].notna().sum()} non-null values).")
else:
    es["outcome"] = es["people_targeted"] / es["Budget"]
    print(f"'{OUTCOME_COL}' not found — falling back to beneficiaries/$ (people_targeted / Budget).")

if "sector_tag" not in es.columns:
    es["sector_tag"] = es["ProjectTitle"].map(tag_sector)  # same tagger as defined above
    print("No 'sector_tag' column — tags inferred from ProjectTitle with the same rules as above.")

print(f"rows: {len(es)} | funds: {es['PooledFundName'].nunique()} | sectors: {es['sector_tag'].nunique()}")
display(es[["ChfProjectCode", "PooledFundName", "sector_tag", "outcome"]].head(10))

# COMMAND ----------

# DBTITLE 1,eff_score: train + evaluate + log KNN
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import mlflow
from mlflow.models import infer_signature

CAT_ES = ["PooledFundName", "sector_tag", "OrganizationType", "AllocationSourceName"]
X_es = es[CAT_ES + ["AllocationYear", "Budget"]]   # raw inputs; log(Budget) inside the pipeline
y_es = es["outcome"]

pre_es = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_ES),
    ("year", StandardScaler(), ["AllocationYear"]),
    ("budget", Pipeline([("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                          ("scale", StandardScaler())]), ["Budget"]),
])
# NOTE: if the updated eff_score is already log/normalized, drop func/inverse_func below
knn_model_es = TransformedTargetRegressor(
    regressor=Pipeline([("pre", pre_es),
                        ("knn", KNeighborsRegressor(n_neighbors=K_ES, weights="distance"))]),
    func=np.log, inverse_func=np.exp)

Xes_tr, Xes_te, yes_tr, yes_te = train_test_split(X_es, y_es, test_size=0.2, random_state=42)
knn_model_es.fit(Xes_tr, yes_tr)
p_es = knn_model_es.predict(Xes_te)
r2_es, r2_es_log, mae_es = (r2_score(yes_te, p_es), r2_score(np.log(yes_te), np.log(p_es)),
                            mean_absolute_error(yes_te, p_es))
print(f"Holdout (n={len(yes_te)}): R2={r2_es:.3f} (log scale: {r2_es_log:.3f}) | MAE={mae_es:.4f}")

# refit on the full cohort and log to MLflow
knn_model_es.fit(X_es, y_es)
sig_es = infer_signature(X_es.head(100), knn_model_es.predict(X_es.head(100)))
with mlflow.start_run(run_name="knn10_comparables_eff_score"):
    mlflow.log_params({"k": K_ES, "features": CAT_ES + ["AllocationYear", "Budget"],
                       "target": OUTCOME_COL, "source_file": os.path.basename(EFFSCORE_PATH),
                       "n_train": len(Xes_tr), "n_test": len(Xes_te), "n_final_fit": len(X_es)})
    mlflow.log_metrics({"holdout_r2": r2_es, "holdout_r2_log": r2_es_log, "holdout_mae": mae_es})
    model_info_es = mlflow.sklearn.log_model(knn_model_es, name="model",
                                             signature=sig_es, input_example=X_es.head(3))
print("MLflow model logged:", model_info_es.model_uri)

# COMMAND ----------

# DBTITLE 1,eff_score: comparables + flags + describe
from sklearn.neighbors import NearestNeighbors

# comparables searched WITHIN each country fund, on the same feature space (never on the outcome)
Z_es = knn_model_es.regressor_.named_steps["pre"].transform(X_es)
peer_outcome_es = np.full(len(es), np.nan)
peer_idx_es = [None] * len(es)
for _cty, _grp in es.groupby("PooledFundName").groups.items():
    _idx = np.array(list(_grp))
    _k = min(K_ES, len(_idx) - 1)
    if _k < 1:
        continue  # single-project fund: no in-country comparables
    _nn = NearestNeighbors(n_neighbors=_k + 1).fit(Z_es[_idx])
    _, _nb = _nn.kneighbors(Z_es[_idx])
    for _r, _i in enumerate(_idx):
        _peers = _idx[_nb[_r][_nb[_r] != _r][:_k]]
        peer_outcome_es[_i] = float(np.median(es["outcome"].iloc[_peers]))
        peer_idx_es[_i] = _peers

rows_es = []
for _i in range(len(es)):
    _actual = float(es["outcome"].iloc[_i])
    _out = {"ChfProjectCode": es["ChfProjectCode"].iloc[_i],
            "PooledFundName": es["PooledFundName"].iloc[_i],
            "ProjectTitle": str(es["ProjectTitle"].iloc[_i])[:70],
            "OrganizationName": es["OrganizationName"].iloc[_i],
            "sector_tag": es["sector_tag"].iloc[_i],
            "outcome": _actual,
            "comparable_peer_outcome": round(peer_outcome_es[_i], 4) if peer_outcome_es[_i] == peer_outcome_es[_i] else np.nan,
            "actual_vs_peers": np.nan, "flag": "no in-country peers", "comparables": ""}
    if peer_outcome_es[_i] == peer_outcome_es[_i]:
        _rel = _actual / peer_outcome_es[_i]
        _out["actual_vs_peers"] = round(_rel, 6)
        _out["flag"] = ("HIGH efficiency vs comparables" if _rel >= 1.5 else
                         "LOW efficiency vs comparables" if _rel <= 1 / 1.5 else "in line with comparables")
        _out["comparables"] = " | ".join(f"{es['ChfProjectCode'].iloc[j][-10:]}: {str(es['ProjectTitle'].iloc[j])[:40]}"
                                     for j in peer_idx_es[_i][:3])
    rows_es.append(_out)
comparables_es = pd.DataFrame(rows_es)

print(f"Flags: {comparables_es['flag'].value_counts().to_dict()}")
print("\nTop HIGH (updated score far above in-country comparables):")
display(comparables_es[comparables_es["flag"] == "HIGH efficiency vs comparables"]
        .sort_values("actual_vs_peers", ascending=False).head(10)
        [["ChfProjectCode", "PooledFundName", "ProjectTitle", "sector_tag", "outcome",
          "comparable_peer_outcome", "actual_vs_peers"]])
print("\nTop LOW (updated score far below in-country comparables):")
display(comparables_es[comparables_es["flag"] == "LOW efficiency vs comparables"]
        .sort_values("actual_vs_peers").head(10)
        [["ChfProjectCode", "PooledFundName", "ProjectTitle", "sector_tag", "outcome",
          "comparable_peer_outcome", "actual_vs_peers"]])

def describe_project_es(code):
    """Show one project's updated score next to its in-country comparables."""
    _i = es.index[es["ChfProjectCode"] == code][0]
    _peers = peer_idx_es[_i]
    if _peers is None:
        print(f"{code}: no in-country comparables (single-project fund).")
        return
    _out = es.loc[_peers, ["ChfProjectCode", "ProjectTitle", "OrganizationName", "PooledFundName",
                           "sector_tag", "Budget", "outcome"]].copy()
    _out["ProjectTitle"] = _out["ProjectTitle"].str.slice(0, 60)
    _out["vs_this_project"] = np.where(_out["outcome"] > es["outcome"].iloc[_i],
                                        "scores higher", "scores lower")
    print(f"{code} — {es['ProjectTitle'].iloc[_i]}\n"
          f"  score = {es['outcome'].iloc[_i]:.4f} ({es['PooledFundName'].iloc[_i]}, {es['sector_tag'].iloc[_i]})")
    display(_out.round(4))

# COMMAND ----------

# DBTITLE 1,eff_score: tiers + chart + MLflow
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import os, re, tempfile

# Tiers directly on the dataset's eff_score — no derived or recalculated score.
# 1-D k-means (k=3) within sector; sectors with < 10 projects get "insufficient peers".
PEER_MIN_ES = 10
eff_es = es.merge(comparables_es[["ChfProjectCode", "flag"]], on="ChfProjectCode",
                  how="left", validate="one_to_one")
assert np.isfinite(eff_es["eff_score"]).all()

tier_rows_es, tier_meta_es = [], []
for _sec, _g in eff_es.groupby("sector_tag"):
    _base = _g[["ChfProjectCode", "PooledFundName", "ProjectTitle", "sector_tag",
                "Budget", "eff_score", "flag"]].copy()
    if len(_g) < PEER_MIN_ES:
        _base["tier"] = "insufficient peers"
        tier_rows_es.append(_base)
        continue
    _s = _g[["eff_score"]].to_numpy()
    _km = KMeans(n_clusters=3, n_init=10, random_state=42).fit(_s)
    _order = np.argsort(_km.cluster_centers_.ravel())
    _names = np.array(["Low", "Average", "High"])
    _base["tier"] = _names[_order][_km.labels_]
    _c = _km.cluster_centers_.ravel()[_order]
    tier_meta_es.append({"sector_tag": _sec, "centroid_low": _c[0],
                          "centroid_average": _c[1], "centroid_high": _c[2]})
    tier_rows_es.append(_base)
tiers_es = pd.concat(tier_rows_es).sort_values(["sector_tag", "eff_score"],
                                               ascending=[True, False]).reset_index(drop=True)

_counts_es = (tiers_es.pivot_table(index="sector_tag", columns="tier", values="ChfProjectCode",
                                   aggfunc="count", fill_value=0)
              .reindex(columns=["Low", "Average", "High", "insufficient peers"], fill_value=0))
print("Sector × efficiency tier (project counts, eff_score model):")
display(_counts_es)

# --- MLflow ---
_slug = lambda s: re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")
with mlflow.start_run(run_name="sector_efficiency_tiers_eff_score"):
    mlflow.log_params({"method": "1-D k-means on eff_score as provided in the dataset (within sector)",
                       "k": 3, "peer_min": PEER_MIN_ES, "n_projects": len(eff_es),
                       "n_tiered": int((tiers_es["tier"] != "insufficient peers").sum()),
                       "source_file": os.path.basename(EFFSCORE_PATH)})
    for _sec, _row in _counts_es.iterrows():
        for _t, _n in _row.items():
            if _n > 0:
                mlflow.log_metric(f"{_slug(_sec)}_{_slug(_t)}_n", int(_n))
    for _m in tier_meta_es:
        for _tn, _cv in (("low", _m["centroid_low"]), ("average", _m["centroid_average"]),
                         ("high", _m["centroid_high"])):
            mlflow.log_metric(f"{_slug(_m['sector_tag'])}_centroid_{_tn}", round(float(_cv), 4))
    _tmp = tempfile.mkdtemp()
    tiers_es.to_csv(os.path.join(_tmp, "sector_efficiency_tiers_eff_score.csv"), index=False)
    mlflow.log_artifact(os.path.join(_tmp, "sector_efficiency_tiers_eff_score.csv"))
print("Logged eff_score tiers to MLflow (tier sizes, centroids, full CSV artifact).")

_plot_es = tiers_es[tiers_es["tier"] != "insufficient peers"]
_sectors_es = _plot_es["sector_tag"].unique().tolist()
_colors = {"Low": "#d9534f", "Average": "#5bc0de", "High": "#5cb85c"}
fig, ax = plt.subplots(figsize=(11, 4))
for _i, _sec in enumerate(_sectors_es):
    _g = _plot_es[_plot_es["sector_tag"] == _sec]
    ax.scatter(_g["eff_score"], [_i] * len(_g), c=_g["tier"].map(_colors), s=25, alpha=0.7)
ax.set_yticks(range(len(_sectors_es)), _sectors_es)
ax.axvline(0, color="gray", ls=":", lw=1)
ax.set_xlabel("eff_score (as provided in the dataset)")
ax.set_title("Efficiency tiers within sector — dataset eff_score (1-D k-means, k=3)")
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=c, label=t) for t, c in _colors.items()])
plt.tight_layout(); plt.show()

# COMMAND ----------

# DBTITLE 1,eff_score: similar projects for best/worst N
# Two most similar in-country projects (eff_score model's KNN feature space) for the
# top-N best and worst eff_score projects. peer_idx_es (from the comparables cell) stores
# each project's in-country neighbors sorted by distance, so the first 2 are the most similar.
TOP_N_ES = 10  # projects per group

def similar_projects_es(code, k=2):
    """Print a project and its k most similar in-country projects (eff_score model)."""
    _i = es.index[es["ChfProjectCode"] == code][0]
    print(f"{code} — {str(es['ProjectTitle'].iloc[_i])[:80]}")
    print(f"  eff_score={es['eff_score'].iloc[_i]:.2f} | {es['PooledFundName'].iloc[_i]} | {es['sector_tag'].iloc[_i]}")
    _peers = peer_idx_es[_i]
    _peers = [] if _peers is None else list(_peers)
    for _m, _j in enumerate(_peers[:k], start=1):
        print(f"  #{_m} {es['ChfProjectCode'].iloc[_j]} (eff_score {es['eff_score'].iloc[_j]:.2f}) — {str(es['ProjectTitle'].iloc[_j])[:60]}")

rank_es = eff_es.sort_values("eff_score", ascending=False)  # index kept = es row position
rows_sim = []
for _group, _sel in (("BEST", rank_es.head(TOP_N_ES)),
                     ("WORST", rank_es.tail(TOP_N_ES).iloc[::-1])):  # worst first
    for _r, (_i, _row) in enumerate(_sel.iterrows(), start=1):
        _pp = peer_idx_es[int(_i)]
        _peers = [] if _pp is None else list(_pp)[:2]
        _rec = {"group": _group, "rank": _r,
                "project_code": _row["ChfProjectCode"],
                "project_title": str(_row["ProjectTitle"])[:45],
                "country": _row["PooledFundName"], "sector": _row["sector_tag"],
                "eff_score": round(float(_row["eff_score"]), 2)}
        for _m in (1, 2):
            if _m <= len(_peers):
                _j = _peers[_m - 1]
                _rec[f"similar_{_m}"] = f"{es['ChfProjectCode'].iloc[_j]} ({es['eff_score'].iloc[_j]:.2f})"
                _rec[f"similar_{_m}_title"] = str(es["ProjectTitle"].iloc[_j])[:45]
            else:
                _rec[f"similar_{_m}"] = ""   # fund too small for 2 in-country comparables
                _rec[f"similar_{_m}_title"] = ""
        rows_sim.append(_rec)
similar_es = pd.DataFrame(rows_sim)

print(f"Top {TOP_N_ES} BEST by eff_score — with their 2 most similar in-country projects:")
display(similar_es[similar_es["group"] == "BEST"])
print(f"\nTop {TOP_N_ES} WORST by eff_score — with their 2 most similar in-country projects:")
display(similar_es[similar_es["group"] == "WORST"])
print("\n(similar_projects_es('CODE') looks up any other project; neighbors share country, sector, "
      "org type, allocation source/year and similar log budget — never the score itself.)")

# COMMAND ----------

# DBTITLE 1,eff_score: write closest_1/closest_2 into efficiency_final.csv
# Add closest_1 / closest_2 columns to efficiency_final.csv: PROJECT TITLES of the 1st and
# 2nd most similar in-country projects from the eff_score model (peer_idx_es, sorted by
# distance in the matching feature space — never the score itself).
EFFSCORE_PATH = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/efficiency_final.csv"

_closest_rows = []
for _i in range(len(es)):
    _pp = peer_idx_es[_i]
    _peers = [] if _pp is None else list(_pp)
    _closest_rows.append({
        "closest_1": es["ProjectTitle"].iloc[_peers[0]] if len(_peers) > 0 else "",
        "closest_2": es["ProjectTitle"].iloc[_peers[1]] if len(_peers) > 1 else "",
    })
_closest = pd.DataFrame(_closest_rows, index=es.index)
out_es = es.merge(_closest, left_index=True, right_index=True, validate="one_to_one")
if "outcome" in out_es.columns:
    out_es = out_es.drop(columns=["outcome"])  # notebook-added helper column — keep only the 2 new columns

# --- sanity checks before overwriting the file ---
assert len(out_es) == len(es), "row count changed"
assert not ((out_es["closest_1"] == out_es["ChfProjectCode"]) |
            (out_es["closest_2"] == out_es["ChfProjectCode"])).any(), "a project is its own comparable"
_codes = set(out_es["ProjectTitle"])
_has1 = out_es["closest_1"] != ""
assert (out_es.loc[_has1, "closest_1"].isin(_codes)).all(), "closest_1 title not found in the file"
_has2 = out_es["closest_2"] != ""
assert (out_es.loc[_has2, "closest_2"].isin(_codes)).all(), "closest_2 title not found in the file"

out_es.to_csv(EFFSCORE_PATH, index=False)
print(f"Wrote {len(out_es)} rows with closest_1/closest_2 -> {EFFSCORE_PATH}")
print(f"projects with no in-country comparable: {int((out_es['closest_1'] == '').sum())} | "
      f"with only 1: {int(((out_es['closest_1'] != '') & (out_es['closest_2'] == '')).sum())}")
display(out_es[["ChfProjectCode", "PooledFundName", "sector_tag", "eff_score",
                "closest_1", "closest_2"]].head(10))