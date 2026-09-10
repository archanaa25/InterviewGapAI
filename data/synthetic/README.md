# Synthetic candidate resumes

Ten fictional resumes for the resume-analysis and interview-planning phase. Names, employers, institutions, work histories, and outcomes are invented. Contact addresses use example.com. Experience is stated as of September 2026.

Use `resumes/candidate_01.md` through `resumes/candidate_10.md` as plain-text resume inputs. The common structure is summary, skills, work experience, projects, and education. Candidate 10 intentionally supplies little detail; candidate 09 provides beginner evidence only.

`resume_manifest.json` contains scenario labels and expected areas to explore. Keep it separate from analyzer inputs to avoid revealing the intended classification. Its evidence labels describe what the resume claims, not verified skill scores. Unlisted competencies remain unknown.

The set covers a broad practitioner, document-focused specialist, action-focused specialist, backend transition, data science transition, quality specialist, security specialist, platform specialist, graduate, and experienced candidate with sparse evidence. These are ten controlled scenarios, not an exhaustive representation of candidates.

Resume wording describes work in ordinary language instead of copying corpus labels or question text. Common technology names remain where natural. The fixtures do not claim complete vocabulary disjointness from the corpus.

Markdown inputs support the first text-analysis milestone; PDF/DOCX parsing and upload behavior are not exercised by these fixtures.
