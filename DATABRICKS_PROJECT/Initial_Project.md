# Humanitarian project funding, targets, and reach

**Status** · Data layer built and validated in Unity Catalog (`workspace.default`) - see Built data layer below  
**Timebox** · Five hours  
**Tools** · Databricks for data exploration, SQL, and the dashboard.

## The question

For each humanitarian project, **how much funding was assigned, how many people did it plan to reach, and how many people did it report reaching?**

Challenge 1, **Smart Beneficiary Targeting Validation**, is the priority. Build a project-level view of funding, planned targets, and reported reach. Use budget per person targeted to flag unusual plans and show the comparable projects behind each flag. Where reach is available, show how the reported result compares with the target. Challenge 2, **Geo-Insight**, is a stretch goal.

## Pilot country · Democratic Republic of the Congo

Cover **DRC in 2025 and 2026**. Teammates already have the 2025 work underway. Prepare the 2026 inputs and align field names and calculation definitions with the 2025 team before combining the results. DRC has the largest sum of 2026 CBPF project budgets in the supplied snapshot. The pilot asks which projects plan to reach unusually many or few people for their budget and what comparable projects can tell a reviewer about those differences.

| Allocation year | DRC CBPF project budgets | Rank in CBPF file | DRC CERF approved allocations | Rank in CERF file |
| --- | ---: | ---: | ---: | ---: |
| 2025 | 47.05 million | 8th | 51.04 million | 1st |
| 2026 | 384.02 million | 1st | 48.75 million | 2nd |

The totals above sum `Budget` by `PooledFundName` in CBPF and `totalAmountApproved` by `countryCode` in CERF, separately by year. Amounts are shown in the units recorded in each file. Confirm the currency before labeling the figures and check the snapshot’s coverage before treating the 2026 figures as full-year totals.

| Allocation year | DRC CBPF project rows | Rows with usable budget and demographic inputs | DRC CERF allocation rows |
| --- | ---: | ---: | ---: |
| 2025 | 79 | 69 | 24 |
| 2026 | 80 | 76 | 16 |

The input check requires an approval date, a positive budget, four complete nonnegative demographic counts that sum to more than zero, and excludes rows labeled `HFU Management Cost`. All 80 DRC CBPF rows in 2026 are Reserve allocations. The 2025 candidates include 44 Reserve and 25 Standard allocations. Show both allocation types in the 2025 profile and use Reserve projects from each year for the closest year-over-year comparison. Verify service type before assigning peer groups.

DRC is `DRC` in CBPF and `COD` in CERF. The Republic of the Congo uses `COG` in CERF and is outside the pilot.

## Sources under exploration

Use the three team-provided HDX entry points and their listed dataset resources for this exploration. The two shared funding CSVs and the revised DRC 2026 JIAF workbook have been inspected locally. For the other resources, the notes below reflect the catalog descriptions.

### CBPF allocations and contributions

The [HDX CBPF dataset](https://data.humdata.org/dataset/cbpf-allocations-and-contributions#data-and-resources) lists four resources.

| Resource | What it contributes |
| --- | --- |
| [Project summary CSV](https://data.humdata.org/dataset/cbpf-allocations-and-contributions/resource/4f8eee3c-cea7-453d-8f46-7525f3e289d1) | The strongest starting point for Challenge 1. The local snapshot has 17,581 rows and unique `ChfProjectCode` values. It includes `Budget`, `Men`, `Women`, `Boys`, `Girls`, fund, year, and approval date. The CSV has no explicit project reach or service cluster field. |
| [ProjectSummary JSON](https://data.humdata.org/dataset/cbpf-allocations-and-contributions/resource/4fbaeb0f-789c-483e-b560-d9e5e2998daf) | HDX describes this as an approved-project summary. Its payload still needs a schema comparison with the CSV to determine whether it adds any target, reach, or cluster fields. |
| [Contributions CSV](https://data.humdata.org/dataset/cbpf-allocations-and-contributions/resource/16c04ace-6236-482c-af15-6a14007f5c87) and [Contributions JSON](https://data.humdata.org/dataset/cbpf-allocations-and-contributions/resource/ec247f8c-103f-4bf4-aea3-b424bab4f014) | Listed as contributions to pooled funds. Use them for fund-level donor context. Assigned project budgets come from the project summary or allocation records. |

The local CBPF summary has **17,084 candidate rows** with a populated approval date, a positive budget, and four complete nonnegative demographic counts that sum to more than zero. This count precedes exclusions for management costs and peer eligibility. Confirm the budget currency and whether the demographic counts represent planned direct targets.

### CERF organization catalog

The [HDX CERF organization page](https://data.humdata.org/organization/cerf) showed 116 active listings. The visible listings include global and country allocation entries, climate-related allocations, donor contributions, and topline figures. The review covered listing titles and selected resource descriptions. Individual country files have yet to be profiled.

| Resource family | What it contributes |
| --- | --- |
| [Global CERF Allocations](https://data.humdata.org/dataset/cerf-allocations) | The global listing offers CSV, HXL-tagged CSV, and JSON. The supplied CERF allocations CSV has 8,668 rows from 2006–2026, with approved amount (`totalAmountApproved`), country, year, sectors, and clusters. `projectCode` is unique in that snapshot and `projectID` repeats. The local file has no explicit target or reach count. Confirm exact download provenance before treating it as the same snapshot as the global listing. |
| DRC country allocations listed in the CERF catalog | Use `countryCode = 'COD'` in the global file to check DRC coverage. If the team uses the country export as well, compare project codes before combining the files because records may overlap. |
| [CERF Climate Related Allocations](https://data.humdata.org/dataset/cerf-climate-related-allocations) | A thematic listing. Check its fields and overlap with global allocations before using it. |
| [Global CERF Donor Contributions](https://data.humdata.org/dataset/cerf-donor-contributions) | Donor funding context at the fund level. |
| [CERF Topline Figures](https://data.humdata.org/dataset/cerf-topline-figures) | HDX lists a single CSV for organization-page summary figures. Its file contents and granularity remain unverified. |

### JIAF humanitarian needs

The [team’s HDX JIAF search](https://data.humdata.org/search?q=JIAF+Humanitarian+Needs+People+in+Need+and+Severity&ext_search_source=main-nav) is the entry point for **People in Need (PiN)** and **severity** workbooks. PiN measures assessed humanitarian need. Project targets measure intended service coverage, and reported reach measures results. Use JIAF for Geo-Insight and, if useful, geographic context for Challenge 1. Keep all three measures as distinct fields.

The attached `jiaf_drc_2026_revised.xlsx` was converted to [`jiaf_drc_2026_needs_and_severity.csv`](jiaf_drc_2026_needs_and_severity.csv). It contains **519 unique Admin 3 areas**. The export joins `WS - 3.1 Overall PiN` (`PiN définitif`, column AN) to `WS - 3.2 Intersectoral Severity` (`Sévérité définitive revisée`, column AJ) by `Admin 3 P-Code`. It retains Admin 1–3 names and codes, population, and the reference year. All 519 codes matched one-to-one, and every output row has a final PiN value and a revised severity value.

The [workbook CSV archive](jiaf_drc_2026_workbook_csvs.zip) contains all 11 worksheets as separate CSVs, using the values saved in the workbook. It includes the `PiN Historical Trend` tab, which provides prior-year context. Compare that tab with the team's separate 2025 work before treating the values as comparable. The original resource is the [revised DRC 2026 JIAF workbook on HDX](https://data.humdata.org/dataset/78260bb2-322c-4888-992c-9cb558e5fb66/resource/ac88babf-cff0-44ec-ac91-24b60b1f2dc9).

**Current data gap.** Project-level reported reach remains unverified in the reviewed HDX resources. Keep `people_reached_reported` blank and display `Reach unavailable` until a matching result is verified. A closed project status or a positive planned target provides no reach count.

## Built data layer · Unity Catalog (`workspace.default`)

All objects below were created and validated on Nov 21, 2026. The schema was empty before the build; existing notebooks and files were not modified, and no tables were overwritten. Post-write SQL checks confirmed every count, unique-code count, and budget sum.

| Object | Contents and validation |
| --- | --- |
| `drc_cbpf_projects_2026` | All 80 DRC 2026 CBPF projects from `drc_cbpf_projects_2026.csv` (derived from the global project summary with `PooledFundName = 'DRC'`, `AllocationYear = 2026`). 80 unique `project_code`; 76 `benchmark_input_eligible` (4 ineligible: 3 `HFU Management Cost`, 1 invalid demographics); budget sum 384,019,108.69 in source units. |
| `drc_cbpf_projects_2025` | 79 DRC 2025 projects derived from `global_cbpf_project_summary.csv`, schema aligned with 2026. 69 eligible (10 `HFU Management Cost` rows excluded): 44 Reserve and 25 Standard; budget sum 47,050,029.19. |
| `drc_cbpf_projects` (view) | Union of both years: 159 projects, one row per project, with `budget_per_person_targeted` populated for the 145 eligible rows. |
| `drc_cerf_allocations` | CERF approved allocations with `countryCode = 'COD'`, malformed rows cleaned: 399 rows; 2025: 24 rows / 51,042,097.04; 2026: 16 rows / 48,750,006.17. |
| `drc_cbpf_contributions` | Donor context only: 250 contributions into the DRC pooled fund (pledged 1,547,674,976.91; paid 1,526,757,389.10). The `funding_gap` subtraction from aaron-eda is intentionally excluded from this layer. |
| `jiaf_drc_2026_needs_and_severity` | 519 unique Admin 3 P-Codes with final PiN and revised severity; no nulls. |
| `jiaf_drc_2025_needs_and_severity` | 2025 PiN and severity files joined on Admin 3 P-Code with unmatched areas preserved: 373 codes, 332 matched, 41 PiN-file codes with NULL severity (these 41 also lack a final PiN value in the raw source). All 373 codes appear in the 2026 file. |
| `jiaf_drc_2025_pin_trend` | Historical PiN context, 519 areas. Column names sanitized (e.g. `securite_alimentaire_ancien`) because Delta rejects spaces and accents. |

Rules applied: `people_targeted` = Men + Women + Boys + Girls, labeled a candidate planned target until the field definition is verified; `people_reached` stays NULL and `reach_status` shows `Unavailable`; benchmark eligibility requires an approval date, a positive budget, four complete nonnegative demographic counts, and excludes `HFU Management Cost`. Funding measures are kept separate by source, and JIAF needs and severity remain distinct from project targets and reported reach.

Still open: a verified project-level reported-reach dataset, a verified service-cluster field for peer groups (until then, compare within allocation year and type), and currency confirmation for budget figures.

## First 45 minutes in Databricks

1. Load both funding CSVs as raw tables. Preserve the original strings, then cast budgets, dates, and beneficiary counts into typed columns in a separate query or table. Enable multiline CSV parsing if a text field contains embedded line breaks. Load the 2026 JIAF CSV as a separate needs table and keep the p-codes as strings.
2. Profile row counts, unique project codes, blank values, status values, and allocation-year coverage. Check several CBPF records directly against the raw CSV. Record the file name, source URL, retrieval date if known, and row count for each input.
3. Filter CBPF to `PooledFundName = 'DRC'` and `AllocationYear IN (2025, 2026)`. While teammates work on 2025, validate the 2026 Reserve cohort. Expect 80 project rows before the input checks and 76 candidates after them. Verify five project budgets and four-group target calculations against the CSV. Retain the source labels and record any field definitions that still need confirmation.
4. Check the remaining listed project-related resources for explicit reach, cluster, and project identifier columns. If a reach resource is found, verify its join key against `ChfProjectCode` and check project scope and reporting period before joining. Build and verify CBPF and CERF project tables independently.
5. Record any reach match rate and the reasons for unmatched rows. Continue with the budget and target view while reach is unavailable.

## Project table and calculations

Keep one row per CBPF project code. Preserve source fields and use explicit names for derived values.

| Field | Definition |
| --- | --- |
| `project_code`, `project_title` | CBPF project code and title from the project summary. |
| `pooled_fund`, `allocation_year`, `cluster` | Project context for filtering and matching peers. Cluster requires a verified additional source. |
| `budget_assigned`, `budget_currency` | Project budget and confirmed currency. Record whether the source defines it as approved or allocated funding. |
| `people_targeted_plan` | Sum of the four demographic counts after confirming their meaning and checking that each value is present and nonnegative. |
| `people_targeted_report` | Target in the selected results report, when available. Keep it alongside the plan to show revisions. |
| `people_reached_reported` | Reported project total from a verified report. Prefer an approved final report and retain its approval date. |
| `reach_status` | Indicate whether reach is reported, unavailable, or awaiting validation. Leave unavailable counts blank. |
| `budget_per_person_targeted` | Assigned budget divided by the planned target when the target is positive and the budget is valid. |
| `pct_of_plan_reached` | Reported reach divided by the planned target, multiplied by 100, when both have comparable scope and the target is positive. Show a separate percentage if the team also compares reach with a revised target. |

Use a project-wide reach total where available. If the report has multiple rows per project, check for repeated reports, totals alongside breakdowns, and overlap across categories, sectors, or locations. Aggregate only verified mutually exclusive rows before joining. Retain reported values above 100% and check them against the source. Assigned budget and spending measure different things, so label ratios using the assigned budget explicitly.

### Challenge 1 benchmarking

- Exclude `HFU Management Cost` from direct-service peer comparisons.
- Start with projects in the same allocation year and verified service cluster. Show the peer group definition, peer count, median, and example projects. Exclude the project being evaluated from its own peer group. Use matched Reserve groups for year-over-year summaries.
- For the prototype, start with at least 10 eligible peers. One provisional flag rule is below the peer group's 10th percentile or above its 90th percentile. Record the threshold in the notebook and mark sparse groups as having insufficient peers.
- If cluster data is unavailable, show a clearly labeled pooled-fund and year comparison for exploration. Use verified service peers for the main validation demo when possible.
- A flag gives reviewers a project to investigate. Show the actual ratio and comparable rows so they can judge what explains the difference.

## Five-hour schedule

| Time | Deliverable |
| --- | --- |
| 0:00–0:45 | Profile the shared files, record provenance, and check the listed project resources for reach and cluster fields. |
| 0:45–2:00 | Build the 2026 DRC project table and align its schema with the teammates building 2025. Test any verified reach join and preserve a missing-reach status. |
| 2:00–3:15 | Compute budget per person targeted, target attainment where verified, and the peer comparison. Audit five sample projects and check that the joined table still has one row per project. |
| 3:15–4:30 | Bring together the validated 2025 and 2026 project tables. Build a model that suggests an amount of spend, and a ratio of expected spend / actual spend for each project.  Build a dashboard that flags projects on both ends of the expected/actual spend spectrum, to highlight both potentialliy overfunded and underfunded projects. |
| 4:30–5:00 | Commit the notebooks and SQL to GitHub. Rehearse a short walkthrough of one real project with a verified target and reach, plus one benchmark flag. If the reach join is still unresolved, demo the funding and targeting view with its reach status visible. |

## GitHub handoff

Store this brief as `PROJECT.md` and add runnable Databricks notebooks under `notebooks/` and dashboard queries under `sql/` as they are built. Document the external file URLs, input locations in Databricks, notebook run order, and known data gaps. Keep workspace credentials out of the repo. A teammate should be able to reload the pilot cohort and trace a displayed result back to its source row.

## Stretch goal · Geo-Insight

After Challenge 1 is demo-ready, pair each year's DRC funding with that year's verified needs data. Start with the 2026 JIAF CSV. Add the team's 2025 needs data when its definitions and geographic coverage are verified. Use a published overall intersectoral PiN at the chosen level where available. Check for overlapping groups and nested geographic totals before any aggregation.

Summarize DRC funding by fund and year. Confirm common currency and compatible allocation definitions before calculating `pooled allocations / people in need`. Where funding is available only nationally, show the Admin 3 severity map alongside the national funding measure. Label missing coverage explicitly so gaps in the dataset stay distinct from confirmed zero allocations.
