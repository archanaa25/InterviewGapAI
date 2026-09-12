"""Tests for the evaluation-report loaders behind the interviewer dashboard."""

import json

import pytest

from ui import eval_reports as reports


def test_corpus_composition_matches_the_corpus_on_disk() -> None:
    data = reports.corpus_composition()

    assert data is not None
    # Totals must equal the sum of the breakdown, or a chart would disagree
    # with the headline beside it.
    assert data["question_total"] == sum(
        item["count"] for item in data["by_competency"]
    )
    assert data["question_total"] == sum(
        item["count"] for item in data["by_difficulty"]
    )
    assert data["sub_competencies"] >= len(data["by_competency"])
    assert data["by_competency"][0]["count"] >= data["by_competency"][-1]["count"]


def test_golden_query_set_splits_negatives_from_retrieval_queries() -> None:
    data = reports.golden_query_set()

    assert data is not None
    assert data["retrieval_total"] + data["negative_total"] == data["total"]
    assert data["negative_total"] > 0, "the set is meant to include negatives"
    # Negatives are scored differently, so they have to be identifiable.
    assert any(item["negative"] for item in data["by_type"])


def test_question_rag_strategies_are_ranked_by_mrr() -> None:
    data = reports.question_rag_strategies()

    assert data is not None
    scores = [row["mrr"] for row in data["strategies"]]
    assert scores == sorted(scores, reverse=True)
    assert data["winner"] == data["strategies"][0]["strategy"]
    # Every arm needs the three plotted metrics present, or the grouped bars
    # would silently render a zero.
    for row in data["strategies"]:
        for field in ("recall_at_1", "mrr", "ndcg_at_5"):
            assert isinstance(row[field], float), f"{row['strategy']} missing {field}"


def test_question_rag_breakdowns_cover_every_strategy() -> None:
    data = reports.question_rag_strategies()

    assert data is not None
    for row in data["strategies"]:
        assert data["breakdowns"].get(row["strategy"]), row["strategy"]


def test_evaluation_rag_metrics_are_averaged_and_in_range() -> None:
    data = reports.evaluation_rag_strategies()

    assert data is not None
    assert data["derived"] is True, "these arms carry no summary block"
    for row in data["strategies"]:
        assert row["queries"] > 0
        for field in ("recall_at_1", "recall_at_5", "mrr", "ndcg_at_5"):
            assert 0.0 <= row[field] <= 1.0, f"{row['strategy']} {field}={row[field]}"


def test_concept_coverage_totals_reconcile() -> None:
    data = reports.concept_coverage()

    assert data is not None
    assert data["total"] == sum(item["count"] for item in data["levels"])
    for row in data["by_competency"]:
        assert row["total"] == row["Covered"] + row["Partial"] + row["Not Covered"]


def test_resume_scorecard_exposes_the_error_asymmetry() -> None:
    data = reports.resume_scorecard()

    assert data is not None
    assert 0.0 <= data["accuracy"] <= 1.0
    # Over- and under-credit are not equally bad, so both are surfaced rather
    # than collapsed into one accuracy figure.
    assert data["over_credit"] is not None
    assert data["under_credit"] is not None


def test_latency_report_carries_stages_and_observations() -> None:
    data = reports.latency_report()

    assert data is not None
    assert data["stages"], "the dashboard renders one row per stage"
    for entry in data["stages"]:
        assert "after" in entry and "seconds" in entry["after"]
    for observation in data.get("observations", []):
        assert observation["title"] and observation["detail"]


def test_a_missing_file_returns_none_rather_than_raising(monkeypatch, tmp_path) -> None:
    """A panel with no data must degrade, not take the dashboard down."""

    monkeypatch.setattr(reports, "EVAL_DIR", tmp_path / "absent")
    monkeypatch.setattr(reports, "RESULTS_DIR", tmp_path / "absent" / "results")
    monkeypatch.setattr(reports, "PREPARED_DIR", tmp_path / "absent")

    assert reports.corpus_composition() is None
    assert reports.golden_query_set() is None
    assert reports.question_rag_strategies() is None
    assert reports.evaluation_rag_strategies() is None
    assert reports.concept_coverage() is None
    assert reports.resume_scorecard() is None
    assert reports.latency_report() is None


def test_a_malformed_line_does_not_discard_the_experiment(monkeypatch, tmp_path) -> None:
    rows = [
        {"competency": "rag", "difficulty": "basic", "question_type": "conceptual",
         "sub_competency": "rag_fundamentals"},
        {"competency": "rag", "difficulty": "basic", "question_type": "conceptual",
         "sub_competency": "rag_retrieval"},
    ]
    body = "\n".join(json.dumps(row) for row in rows) + "\n{ not json\n"
    (tmp_path / "interview_questions.jsonl").write_text(body, encoding="utf-8")

    monkeypatch.setattr(reports, "PREPARED_DIR", tmp_path)

    data = reports.corpus_composition()
    assert data is not None
    assert data["question_total"] == 2


@pytest.mark.parametrize(
    "raw, expected",
    [("rag", "RAG"), ("ai_security", "AI Security"), ("brand_new", "Brand New")],
)
def test_competency_labels_fall_back_to_a_readable_name(raw, expected) -> None:
    assert reports.label_competency(raw) == expected


def test_model_quality_ranks_arms_and_keeps_over_credit_visible() -> None:
    data = reports.model_quality()

    assert data is not None
    accuracies = [row["accuracy"] for row in data["arms"]]
    assert accuracies == sorted(accuracies, reverse=True)

    for row in data["arms"]:
        assert 0.0 <= row["accuracy"] <= 1.0
        # Accuracy alone cannot decide this comparison, so the error split
        # has to survive into the dashboard.
        assert row["over_credit"] is not None
        assert row["under_credit"] is not None
        assert row["scored"] <= row["attempted"]

    assert data["best_accuracy"] == data["arms"][0]["arm"]
    assert data["fewest_over_credit"] == min(
        data["arms"], key=lambda row: row["over_credit"]
    )["arm"]


def test_model_quality_returns_none_when_unrun(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(reports, "EVAL_DIR", tmp_path / "absent")
    assert reports.model_quality() is None
