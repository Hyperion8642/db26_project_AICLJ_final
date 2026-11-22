# Databricks notebook source
import pandas as pd

# COMMAND ----------

df_sector_budgets = pd.read_csv('Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/cbpf_cost_per_person_2025_2026.csv')
df_budget_person_starts = pd.read_csv('Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/drc_cbpf_budget_person_starts.csv')
df_budget_person_severity = pd.read_csv('')

# COMMAND ----------

# df_new
# df_new['eff_score'] = 

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

pd.read_csv('Workspace/Users/jcao2653@uw.edu/DATABRICKS_PROJECT/cbpf_cost_per_person_2025_2026.csv')

# COMMAND ----------

