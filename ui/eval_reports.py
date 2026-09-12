"""
Read the evaluation artifacts under data/ for the interviewer dashboard.

Loading only. No Streamlit import, so this is testable without a browser and
the dashboard stays a rendering layer over it.

Every loader returns None when its file is absent rather than raising: a
dashboard that shows five of six panels is more useful than one that refuses
to open because an experiment has not been run yet.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPARED_DIR = PROJECT_ROOT / "data" / "prepared" / "master"
EVAL_DIR = PROJECT_ROOT / "data" / "eval"
RESULTS_DIR = EVAL_DIR / "results"

# Friendlier names than the raw identifiers for chart axes.
COMPETENCY_LABELS = {
    "rag": "RAG",
    "agentic_ai": "Agentic AI",
    "ai_evaluation": "AI Evaluation",
    "ai_ml_llm_fundamentals": "LLM Fundamentals",
    "ai_system_design": "AI System Design",
    "python_software_engineering": "Python / SWE",
    "ai_security": "AI Security",
}

STRATEGY_LABELS = {
    "dense_metadata": "dense + metadata",
    "dense_competency_difficulty": "dense + comp + difficulty",
    "dense_competency": "dense + competency",
    "hybrid": "hybrid (BM25+dense)",
    "dense": "dense (plain)",
    "bm25": "BM25 (plain)",
}

QUERY_TYPE_LABELS = {
    "semantic": "Semantic",
    "scenario": "Scenario",
    "keyword": "Keyword",
    "hard_semantic": "Hard Semantic",
    "ambiguous": "Ambiguous",
    "near_neighbor": "Near Neighbor",
    "negative": "Negative",
    "cross_concept": "Cross Concept",
}

# Query types that are supposed to retrieve nothing. Scoring them with the
# same recall metrics as the rest would be misleading, so the dashboard marks
# them instead of ranking them.
NEGATIVE_QUERY_TYPES = frozenset({"negative"})


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_jsonl(path: Path) -> list[dict] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # One malformed line should not discard the rest of an experiment.
            continue
    return rows or None


def label_competency(value: str) -> str:
    return COMPETENCY_LABELS.get(value, value.replace("_", " ").title())


def last_run(filename: str, *, directory: Path | None = None) -> str | None:
    """
    When an artifact was last written, for the panel's run stamp.

    File mtime, not a field inside the file: most of these artifacts do not
    record their own generation time, and a stamp that silently meant
    something different per panel would be worse than none.
    """

    path = (directory or EVAL_DIR) / filename
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None

    from datetime import datetime

    return datetime.fromtimestamp(stamp).strftime("%b %d, %Y  %H:%M")


def _counts(rows: list[dict], field: str, labeller=None) -> list[dict]:
    counter = Counter(row.get(field) for row in rows if row.get(field))
    return [
        {
            "name": labeller(name) if labeller else str(name).title(),
            "count": count,
        }
        for name, count in counter.most_common()
    ]


def corpus_composition() -> dict | None:
    """Question and knowledge corpus shape, by competency, difficulty and type."""

    questions = _read_jsonl(PREPARED_DIR / "interview_questions.jsonl")
    if questions is None:
        return None

    knowledge = _read_jsonl(PREPARED_DIR / "evaluation_knowledge.jsonl") or []

    return {
        "question_total": len(questions),
        "knowledge_total": len(knowledge),
        "sub_competencies": len(
            {row.get("sub_competency") for row in questions if row.get("sub_competency")}
        ),
        "by_competency": _counts(questions, "competency", label_competency),
        "by_difficulty": _counts(questions, "difficulty"),
        "by_question_type": _counts(questions, "question_type"),
        "knowledge_by_competency": _counts(knowledge, "competency", label_competency),
    }


def golden_query_set() -> dict | None:
    """The question-retrieval golden set: size, query mix, expected behaviour."""

    queries = _read_json(EVAL_DIR / "question_retrieval_golden.json")
    if not isinstance(queries, list):
        return None

    manifest = _read_json(EVAL_DIR / "question_retrieval_golden_manifest.json") or {}
    distribution = manifest.get("distribution", {})

    by_type = [
        {
            "name": QUERY_TYPE_LABELS.get(name, str(name).title()),
            "count": count,
            # Negative queries answer a different question - whether the
            # retriever declines - so they are flagged, not ranked alongside.
            "negative": name in NEGATIVE_QUERY_TYPES,
        }
        for name, count in Counter(
            row.get("query_type") for row in queries if row.get("query_type")
        ).most_common()
    ]

    negatives = sum(item["count"] for item in by_type if item["negative"])

    return {
        "dataset": manifest.get("dataset", "Question retrieval golden set"),
        "total": len(queries),
        "negative_total": negatives,
        "retrieval_total": len(queries) - negatives,
        "by_type": by_type,
        "expected_behavior": distribution.get("expected_behavior", {}),
        "negative_metric": (
            manifest.get("recommended_metrics", {}).get("negative_retrieval", [])
        ),
    }


def _strategy_row(name: str, summary: dict) -> dict:
    return {
        "strategy": STRATEGY_LABELS.get(name, name),
        "raw": name,
        "recall_at_1": summary.get("recall_at_1"),
        "recall_at_3": summary.get("recall_at_3"),
        "recall_at_5": summary.get("recall_at_5"),
        "mrr": summary.get("mrr"),
        "ndcg_at_5": summary.get("ndcg_at_5"),
        "latency_ms": summary.get("average_latency_ms"),
        "queries": summary.get("total_queries"),
    }


def question_rag_strategies() -> dict | None:
    """
    Question-RAG retrieval arms, ranked by MRR.

    These files carry their own summary block, so the numbers here are the
    ones the experiment recorded rather than a re-derivation.
    """

    if not RESULTS_DIR.is_dir():
        return None

    rows: list[dict] = []
    breakdowns: dict[str, list[dict]] = {}

    for path in sorted(RESULTS_DIR.glob("*_v2.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict) or "summary" not in payload:
            continue

        name = payload.get("retriever", path.stem)
        rows.append(_strategy_row(name, payload["summary"]))

        breakdowns[STRATEGY_LABELS.get(name, name)] = [
            {
                "query_type": QUERY_TYPE_LABELS.get(kind, str(kind).title()),
                "queries": stats.get("total_queries"),
                "recall_at_1": stats.get("recall_at_1"),
                "recall_at_5": stats.get("recall_at_5"),
                "mrr": stats.get("mrr"),
                "ndcg_at_5": stats.get("ndcg_at_5"),
                "latency_ms": stats.get("average_latency_ms"),
            }
            for kind, stats in (payload.get("query_type_breakdown") or {}).items()
        ]

    if not rows:
        return None

    rows.sort(key=lambda row: row["mrr"] or 0, reverse=True)

    corpus_size = None
    for path in sorted(RESULTS_DIR.glob("*_v2.json")):
        payload = _read_json(path)
        if isinstance(payload, dict) and payload.get("corpus_size"):
            corpus_size = payload["corpus_size"]
            break

    return {
        "strategies": rows,
        "breakdowns": breakdowns,
        "corpus_size": corpus_size,
        "winner": rows[0]["strategy"],
    }


# The evaluation-RAG arms, unlike the question-RAG ones, are per-query rows
# with no summary block, so their headline numbers are averaged here.
EVALUATION_RAG_ARMS = {
    "bm25": "BM25",
    "dense": "dense (plain)",
    "dense_competency": "dense + competency",
}


def evaluation_rag_strategies() -> dict | None:
    """Evaluation-RAG retrieval arms, averaged from their per-query rows."""

    rows: list[dict] = []

    for name, label in EVALUATION_RAG_ARMS.items():
        data = _read_jsonl(EVAL_DIR / f"evaluation_rag_{name}_results.jsonl")
        if not data:
            continue

        def average(field: str) -> float | None:
            values = [row[field] for row in data if isinstance(row.get(field), (int, float))]
            return mean(values) if values else None

        rows.append(
            {
                "strategy": label,
                "raw": name,
                "queries": len(data),
                "recall_at_1": average("recall_at_1"),
                "recall_at_3": average("recall_at_3"),
                "recall_at_5": average("recall_at_5"),
                "mrr": average("reciprocal_rank"),
                "ndcg_at_5": average("ndcg_at_5"),
                "latency_ms": average("latency_ms"),
            }
        )

    if not rows:
        return None

    rows.sort(key=lambda row: row["mrr"] or 0, reverse=True)

    golden = _read_jsonl(EVAL_DIR / "evaluation_rag_golden.jsonl") or []

    return {
        "strategies": rows,
        "golden_total": len(golden),
        "winner": rows[0]["strategy"],
        "derived": True,
    }


def concept_coverage() -> dict | None:
    """Whether the knowledge base can grade each expected concept."""

    rows = _read_jsonl(EVAL_DIR / "evaluation_concept_coverage.jsonl")
    if rows is None:
        return None

    levels = Counter(row.get("coverage") for row in rows if row.get("coverage"))

    per_competency: dict[str, Counter] = {}
    for row in rows:
        competency = row.get("competency")
        if not competency:
            continue
        per_competency.setdefault(competency, Counter())[row.get("coverage")] += 1

    order = ("COVERED", "PARTIAL", "NOT_COVERED")

    # str.title() keeps the underscore ("NOT_COVERED" -> "Not_Covered"), which
    # would reach a chart axis and a column header as written.
    def level_label(level: str) -> str:
        return level.replace("_", " ").title()

    return {
        "total": len(rows),
        "levels": [
            {"level": level_label(level), "count": levels.get(level, 0)}
            for level in order
            if levels.get(level)
        ],
        "by_competency": [
            {
                "name": label_competency(competency),
                **{
                    level_label(level): counts.get(level, 0)
                    for level in order
                },
                "total": sum(counts.values()),
            }
            for competency, counts in sorted(
                per_competency.items(), key=lambda item: -sum(item[1].values())
            )
        ],
    }


def resume_scorecard() -> dict | None:
    """Resume-analyzer accuracy against the synthetic manifest labels."""

    payload = _read_json(EVAL_DIR / "resume_analysis_scorecard.json")
    if not isinstance(payload, dict) or "summary" not in payload:
        return None

    summary = payload["summary"]
    counts = summary.get("counts", {})

    return {
        "judgements": summary.get("judgements"),
        "accuracy": summary.get("accuracy"),
        "precision": summary.get("precision"),
        "recall": summary.get("recall"),
        "outcomes": [
            {"outcome": key.replace("_", " ").title(), "count": value}
            for key, value in counts.items()
        ],
        # The asymmetry is the finding: over-crediting means the interview
        # skips probing an area it should have.
        "over_credit": counts.get("over_credit"),
        "under_credit": counts.get("under_credit"),
    }


def latency_report() -> dict | None:
    """The intake latency before/after report, as written by its harness."""

    payload = _read_json(EVAL_DIR / "intake_latency_report.json")
    return payload if isinstance(payload, dict) else None


__all__ = [
    "concept_coverage",
    "last_run",
    "corpus_composition",
    "evaluation_rag_strategies",
    "golden_query_set",
    "label_competency",
    "latency_report",
    "question_rag_strategies",
    "resume_scorecard",
]
