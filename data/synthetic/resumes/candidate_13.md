# Rhea Dsouza

**Senior Data Platform Analyst**  
rhea.dsouza@example.com

## Professional Summary
Seven years across data engineering and analysis for a logistics business. Builds and maintains the batch pipelines that other analysts query, and is the person called when a nightly job fails or a number looks wrong.

## Technical Skills
Python, pandas, PySpark, SQL, Airflow, Kafka, Postgres, Redshift, Docker, Git, Terraform, pytest, Grafana.

## Work Experience
**Senior Data Platform Analyst — Halverton Freight | Feb 2022–Present**
- Maintains around 60 scheduled pipelines moving shipment, telematics, and billing data into the warehouse.
- Reduced a daily aggregation job from 95 minutes to 22 by repartitioning on the join key and removing a shuffle caused by an unnecessary sort.
- Added dead-letter handling and alerting for malformed vendor files, which had previously stalled the whole batch until someone noticed the next morning.
- Set up a staging environment mirroring production schemas so pipeline changes are validated before release.
- Built a keyword search index over historical support tickets so the operations team could find similar past incidents by matching terms.

**Data Engineer — Halverton Freight | Sep 2019–Jan 2022**
- Migrated reporting from nightly CSV exports to an incremental warehouse load.
- Wrote the reconciliation checks comparing warehouse totals against source system counts.
- Supported analysts with query tuning and schema questions.

## Selected Project
**Late-delivery investigation:** Assembled a dataset joining GPS traces, depot scan events, and customer complaints to test whether late deliveries clustered by route, driver, or depot. Found the pattern was a depot cut-off time, not driver behaviour, and presented the evidence against the prevailing assumption.

## Education
BEng, Information Systems — Fictional Northbrook University, 2019.
