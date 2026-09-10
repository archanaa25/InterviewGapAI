# Priya Nambiar

**AI Engineer**  
priya.nambiar@example.com

## Professional Summary
Engineer working on assistants that take real actions inside finance and media systems, with attention to what those assistants are allowed to do. Five years in Python, the last two on assistant features that touch customer records.

## Technical Skills
Python, FastAPI, PostgreSQL, OAuth, Docker, Kubernetes, Git, pytest, audit logging, message queues.

## Work Experience
**AI Engineer — Ivory Sparrow Systems | Jan 2024–Present**
- Built an assistant that raises refunds and updates subscriptions, holding anything irreversible until a supervisor approves it.
- Gave the assistant a narrow set of operations rather than direct database access, and kept read and write operations on separate credentials.
- Enforced which accounts a request may touch in the surrounding service, so the check does not depend on the assistant behaving correctly.
- Treated anything the assistant produced as untrusted before it reached another system, after a pasted customer note caused an unintended lookup.
- Removed names and account numbers from stored conversation records, and kept an audit entry for every action taken.
- Added a marker on each request so a retried action could not be applied twice.

**Backend Engineer — Tallow Bay Media | Sep 2021–Dec 2023**
- Owned Python services for subscription billing, including retries and reconciliation jobs.
- Added contract tests between the billing service and two internal consumers.

## Selected Project
**Access review helper:** Assistant that drafts quarterly access reviews for managers to sign off. Restricted it to reading group membership and refused any request that named a system outside the reviewed set.

## Education
BTech, Computer Science — Fictional Netherby Institute, 2021.
