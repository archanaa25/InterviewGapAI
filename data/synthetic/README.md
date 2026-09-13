# Synthetic candidate resumes

Thirteen fictional resumes for the resume-analysis and interview-planning phase. Names, employers, institutions, work histories, and outcomes are invented. Contact addresses use example.com. Experience is stated as of September 2026.

Use `resumes/candidate_01.md` through `resumes/candidate_13.md` as plain-text resume inputs. The common structure is summary, skills, work experience, projects, and education. Candidate 10 intentionally supplies little detail; candidate 09 provides beginner evidence only.

`resume_manifest.json` contains scenario labels and expected areas to explore. Keep it separate from analyzer inputs to avoid revealing the intended classification. Its evidence labels describe what the resume claims, not verified skill scores. Unlisted competencies remain unknown.

Candidates 01-10 cover a broad practitioner, document-focused specialist, action-focused specialist, backend transition, data science transition, quality specialist, security specialist, platform specialist, graduate, and experienced candidate with sparse evidence.

Candidates 11-13 are Python data-analytics professionals with no language-model experience at all: an analytics engineer, a product analyst, and a data platform analyst. They exist to exercise the case the first ten do not - a competent engineer for whom almost every assessed competency is genuinely unknown rather than weak. Two deliberate near-misses sit in candidate_13: a keyword search index over support tickets, which is not RAG, and distributed batch tuning, which is not AI system design. Crediting either is a false positive worth catching.

These are thirteen controlled scenarios, not an exhaustive representation of candidates.

Resume wording describes work in ordinary language instead of copying corpus labels or question text. Common technology names remain where natural. The fixtures do not claim complete vocabulary disjointness from the corpus.

Markdown inputs support the first text-analysis milestone; PDF/DOCX parsing and upload behavior are not exercised by these fixtures.
