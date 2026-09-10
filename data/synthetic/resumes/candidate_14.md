# Emeka Obi

**AI Platform Engineer**  
emeka.obi@example.com

## Professional Summary
Engineer responsible for the services that assistant features run on, and for the checks that decide whether a change is safe to release. Seven years in backend engineering, the last three supporting language-model features owned by other teams.

## Technical Skills
Python, FastAPI, PostgreSQL, Redis, RabbitMQ, Docker, Kubernetes, Terraform, Prometheus, Grafana, pytest.

## Work Experience
**AI Platform Engineer — Clay Harbour Retail | Oct 2023–Present**
- Ran the shared service that product teams call for assistant features, including request queueing, retries, and per-team limits.
- Separated the request-handling path from the hosted model integrations so either could be replaced without touching the other.
- Added caching for repeated requests and traced a slow path to serialised calls that could run at the same time.
- Set spending and response-time budgets per team and reported when a feature exceeded them.
- Built the release check that runs each proposed change against a held-out set of two hundred customer requests written by support staff.
- Blocked releases where answers got worse on that set, and reviewed disagreements with the support lead before allowing an exception.
- Recorded which requests were answered, refused, or failed, so the three were not reported as one number.

**Backend Engineer — Pine Ledger Works | Jun 2019–Sep 2023**
- Owned order-processing services and their on-call rotation.
- Led a migration that split a shared database by service boundary.

## Selected Project
**Release comparison board:** Internal page showing how each candidate release scored against the held-out request set, broken down by request type, so a single average could not hide a regression in one area.

## Education
BSc, Software Engineering — Fictional Westmere College, 2019.
