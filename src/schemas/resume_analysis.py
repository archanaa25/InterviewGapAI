"""
Resume Analysis Schema for InterviewGapAI.

This module defines the structured output produced by the Resume Analyzer.

IMPORTANT DESIGN PRINCIPLE
--------------------------
Resume analysis evaluates the amount and quality of EVIDENCE present
in a resume.

It does NOT determine whether a candidate actually possesses or lacks
a competency.

Absence of resume evidence means UNKNOWN_NEEDS_PROBING, not weakness.

Actual demonstrated skill gaps are determined later from interview
answers.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Competency(str, Enum):
    """
    Competencies supported by the InterviewGapAI question corpus.

    These values should remain aligned with the competency metadata
    used by Question RAG.
    """

    RAG = "rag"
    AGENTIC_AI = "agentic_ai"
    AI_ML_LLM_FUNDAMENTALS = "ai_ml_llm_fundamentals"
    AI_EVALUATION = "ai_evaluation"
    PYTHON_SOFTWARE_ENGINEERING = "python_software_engineering"
    AI_SYSTEM_DESIGN = "ai_system_design"
    AI_SECURITY = "ai_security"


class EvidenceLevel(str, Enum):
    """
    Strength of evidence found in the candidate's resume.

    This is NOT a skill-level classification.
    """

    DEMONSTRATED = "DEMONSTRATED"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
    UNKNOWN_NEEDS_PROBING = "UNKNOWN_NEEDS_PROBING"


class ProbePriority(str, Enum):
    """
    How important it is to investigate this competency
    during the interview.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceItem(BaseModel):
    """
    A specific piece of resume evidence supporting a competency.

    Evidence should be traceable to information contained in the
    candidate resume.
    """

    evidence: str = Field(
        ...,
        min_length=1,
        description=(
            "Concise factual evidence from the resume supporting "
            "the competency assessment."
        ),
    )

    source: str = Field(
        ...,
        min_length=1,
        description=(
            "Where the evidence came from, for example "
            "'Work Experience - Quiet Birch Solutions' or "
            "'Selected Project - Employee information helper'."
        ),
    )


class CompetencyEvidence(BaseModel):
    """
    Resume evidence assessment for one InterviewGapAI competency.
    """

    competency: Competency = Field(
        ...,
        description="Competency being assessed.",
    )

    evidence_level: EvidenceLevel = Field(
        ...,
        description=(
            "Level of evidence present in the resume. "
            "This must not be interpreted as actual candidate skill level."
        ),
    )

    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Resume evidence supporting this classification.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confidence that the evidence-level classification is "
            "supported by the resume."
        ),
    )

    probe_priority: ProbePriority = Field(
        ...,
        description=(
            "Priority for probing this competency during the interview."
        ),
    )

    reason: str = Field(
        ...,
        min_length=1,
        description=(
            "Short explanation for the evidence level and probe priority."
        ),
    )


class ResumeAnalysis(BaseModel):
    """
    Structured output of the InterviewGapAI Resume Analyzer.

    Every supported competency should appear exactly once in
    competency_evidence.
    """

    candidate_id: str = Field(
        ...,
        min_length=1,
        description="Candidate identifier inherited from CandidateResume.",
    )

    overall_summary: str = Field(
        ...,
        min_length=1,
        description=(
            "Evidence-focused summary of the candidate's background. "
            "Must not make unsupported claims about missing skills."
        ),
    )

    competency_evidence: List[CompetencyEvidence] = Field(
        ...,
        description=(
            "Evidence assessment for every competency supported by "
            "InterviewGapAI."
        ),
    )
