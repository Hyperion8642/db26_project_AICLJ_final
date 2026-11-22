# Databricks notebook source
# DBTITLE 1,Load global CBPF contributions
# Load global CBPF contributions data
PATH = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/global_cbpf_contributions.csv"
df = spark.read.csv(f"file:{PATH}", header=True, inferSchema=True)
print(f"Loaded {df.count():,} rows")
display(df)

# COMMAND ----------

# DBTITLE 1,Load CERF allocations
# Load CERF allocations and clean malformed rows (unquoted embedded newlines shift columns)
from pyspark.sql import functions as F

CERF_PATH = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/CERF_donor_cont_allocations.csv"
cerf_df = (
    spark.read.csv(f"file:{CERF_PATH}", header=True, inferSchema=True, multiLine=True)
    .filter(F.col("totalAmountApproved").rlike("^[0-9.]+$") & F.col("year").between(2000, 2026))
    .withColumn("totalAmountApproved", F.col("totalAmountApproved").cast("double"))
    .withColumn("year", F.col("year").cast("int"))
)
print(f"Loaded {cerf_df.count():,} CERF allocation rows")
display(cerf_df)

# COMMAND ----------

# DBTITLE 1,Join CBPF and CERF by country-year
# Join CBPF contributions with CERF allocations by country and year
# Normalize CBPF fund names to match CERF country names
FUND_COUNTRY_MAP = {
    "CAR": "Central African Republic",
    "DRC": "Democratic Republic of the Congo",
    "oPt": "occupied Palestinian territory",
    "Syria": "Syrian Arab Republic",
    "Syria Cross border": "Syrian Arab Republic",
    "Sudan": "Republic of the Sudan",
}
fund_country = F.coalesce(
    F.create_map(*[F.lit(x) for kv in FUND_COUNTRY_MAP.items() for x in kv])[F.col("PooledFundName")],
    F.trim(F.regexp_replace("PooledFundName", r"\s*\([^)]*\)$", "")),  # strip fund suffixes like " (RhPF-WCA)"
)

cbpf_country_year = (
    df.withColumn("country", fund_country)
    .filter(~F.col("country").rlike("Envelope"))  # regional envelopes are not countries
    .groupBy("country", F.col("FiscalYear").alias("year"))
    .agg(
        F.sum("PledgeAmt").alias("cbpf_pledged_amt"),
        F.sum("PaidAmt").alias("cbpf_paid_amt"),
        F.countDistinct("ContributionCode").alias("cbpf_contributions"),
    )
)

cerf_country_year = (
    cerf_df.groupBy(F.col("countryName").alias("country"), "year")
    .agg(
        F.sum("totalAmountApproved").alias("cerf_approved_amt"),
        F.countDistinct("projectID").alias("cerf_projects"),
    )
)

joined = (
    cbpf_country_year
    .join(cerf_country_year, ["country", "year"], "full_outer")
    .orderBy("country", "year")
)
print(f"Joined rows: {joined.count():,}")
display(joined)

# COMMAND ----------

# DBTITLE 1,Rank 2026 funding gaps by country
# Rank countries by CBPF vs CERF funding difference in 2026
# (2026 chosen: data current through Nov 20, 2026, and more funds active than 2025)
funding_2026 = (
    joined.filter(F.col("year") == 2026)
    .select(
        "country",
        F.coalesce("cbpf_paid_amt", F.lit(0.0)).alias("cbpf_paid"),
        F.coalesce("cerf_approved_amt", F.lit(0.0)).alias("cerf_approved"),
        "cbpf_contributions",
        "cerf_projects",
    )
    .withColumn("funding_gap", F.round(F.col("cbpf_paid") - F.col("cerf_approved"), 0))
    .orderBy(F.desc(F.abs("funding_gap")))
)
print(f"Countries with funding in 2026: {funding_2026.count()}")
display(funding_2026)

# COMMAND ----------

# DBTITLE 1,Rank 2025 funding gaps by country
# Same ranking for 2025 (full year) for cross-check
funding_2025 = (
    joined.filter(F.col("year") == 2025)
    .select(
        "country",
        F.coalesce("cbpf_paid_amt", F.lit(0.0)).alias("cbpf_paid"),
        F.coalesce("cerf_approved_amt", F.lit(0.0)).alias("cerf_approved"),
        "cbpf_contributions",
        "cerf_projects",
    )
    .withColumn("funding_gap", F.round(F.col("cbpf_paid") - F.col("cerf_approved"), 0))
    .orderBy(F.desc(F.abs("funding_gap")))
)
print(f"Countries with funding in 2025: {funding_2025.count()}")
display(funding_2025)

# COMMAND ----------

# DBTITLE 1,Load JIAF DRC 2025 CSVs
# Load the three JIAF DRC 2025 CSVs
JIAF_DIR = "/Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT"

jiaf_pin = spark.read.csv(f"file:{JIAF_DIR}/jiaf_drc_2025_pin.csv", header=True, inferSchema=True)
jiaf_severity = spark.read.csv(f"file:{JIAF_DIR}/jiaf_drc_2025_severity.csv", header=True, inferSchema=True)
jiaf_trend = spark.read.csv(f"file:{JIAF_DIR}/jiaf_drc_2025_pin_trend.csv", header=True, inferSchema=True)

for name, d in [("jiaf_pin", jiaf_pin), ("jiaf_severity", jiaf_severity), ("jiaf_trend", jiaf_trend)]:
    print(f"{name}: {d.count():,} rows x {len(d.columns)} cols")

# COMMAND ----------

# DBTITLE 1,Explore jiaf_severity
# Explore jiaf_severity: contents and severity score distributions
GEO_COLS = ("Admin 1", "Admin 1 P-Code", "Admin 2", "Admin 2 P-Code",
            "Admin 3", "Admin 3 P-Code", "Population")
sev_cols = [c for c in jiaf_severity.columns if c not in GEO_COLS]
print(f"Severity columns ({len(sev_cols)}):\n  {sev_cols}")
print(f"Health zones: {jiaf_severity.count():,} across "
      f"{jiaf_severity.select('Admin 1').distinct().count()} provinces")

for c in ["Severité chocs", "CCCM", "Éducation", "Nutrition", "Sécurité alimentaire", "Santé"]:
    print(f"\n-- {c} --")
    jiaf_severity.groupBy(c).count().orderBy(c).show(10)

display(jiaf_severity)

# COMMAND ----------

jiaf_trend.head()

# COMMAND ----------

