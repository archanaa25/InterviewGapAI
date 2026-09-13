# Priya Raghavan

**Analytics Engineer**  
priya.raghavan@example.com

## Professional Summary
Analytics engineer with five years turning raw operational tables into reporting other teams can rely on. Works mainly in SQL and Python, and owns the nightly jobs behind a company-wide revenue dashboard.

## Technical Skills
Python, pandas, NumPy, SQL, PostgreSQL, Snowflake, dbt, Airflow, Git, pytest, Tableau, Excel.

## Work Experience
**Analytics Engineer — Bramblewick Retail Group | Mar 2023–Present**
- Owns the nightly transformation jobs feeding the finance and operations dashboards, covering roughly 40 source tables.
- Rewrote a 900-line reporting query as a set of tested, documented models after three consecutive month-end corrections traced back to it.
- Added row-count and null-rate checks between transformation steps so a bad upstream load fails the job instead of quietly publishing wrong totals.
- Cut the nightly batch from just over four hours to about 50 minutes by replacing repeated full-table scans with incremental loads keyed on an updated-at column.
- Runs a weekly session walking analysts through the table definitions, which reduced repeat questions about which revenue column to use.

**Data Analyst — Bramblewick Retail Group | Jan 2021–Feb 2023**
- Produced weekly trading reports and ad-hoc analyses for category managers.
- Automated a recurring stock-cover report in pandas that had previously been rebuilt by hand each Monday.
- Investigated discrepancies between the warehouse system and the finance ledger and documented the reconciliation rules.

## Selected Project
**Margin restatement:** Traced a persistent gap between reported and actual product margin to a currency conversion applied twice in a legacy view. Rebuilt the affected models, backfilled 18 months of history, and wrote regression checks comparing recomputed figures against the finance team's own records.

## Education
BSc, Economics and Statistics — Fictional Ashfield University, 2020.
