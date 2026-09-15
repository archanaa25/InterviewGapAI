"""
LLM-as-judge over concept judgements the Evaluation Agent already made on a
real candidate's interview.

src.evaluation.coverage_judge checks whether the knowledge base *could*
support judging a concept, against the golden corpus. This checks the
judgement the Evaluation Agent actually produced for a live candidate:
given the answer excerpt it cited and the status it assigned, would an
independent reviewer reach the same status for the same reason. It runs over
data/runs/ records from real interviews, not a golden set - the online half
of eval, where the offline dashboard panels only ever score against fixed
queries and fixture candidates.
"""

import os

from dotenv import load_dotenv

from src.llm_client import build_client
from src.llm_retry import call_with_retry
from src.schemas.online_judge import OnlineJudgeVerdict


load_dotenv()

# A judge scoring the Evaluation Agent's own reasoning must not share its
# vendor: the same model grading itself tends to rubber-stamp its own
# reasoning style rather than catch it, which defeats the point of an
# independent check. ONLINE_JUDGE_PROVIDER can still force a specific
# provider (e.g. for a case where both vendors are genuinely wanted), but
# the default always flips away from whatever the agent stage is using.
_AGENT_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
_DEFAULT_JUDGE_PROVIDER = "openai" if _AGENT_PROVIDER == "deepseek" else "deepseek"
JUDGE_PROVIDER = os.getenv("ONLINE_JUDGE_PROVIDER") or _DEFAULT_JUDGE_PROVIDER

client, _default_model = build_client("gpt-5.6", provider=JUDGE_PROVIDER)
MODEL = os.getenv("ONLINE_JUDGE_MODEL") or _default_model


SYSTEM_PROMPT = """
You are auditing a judgement an AI interview evaluator already made about a
candidate's answer. You are NOT evaluating the candidate yourself.

You are given:
- the interview question
- an expected concept the candidate was meant to demonstrate
- the status the evaluator assigned to that concept (DEMONSTRATED, PARTIAL,
  or MISSING)
- the rationale the evaluator wrote
- the excerpt of the candidate's answer the evaluator cited as evidence

Decide whether the cited excerpt actually supports the assigned status and
rationale.

AGREE: the excerpt plausibly supports the assigned status and the rationale
follows from it, even if you might have phrased it differently.

DISAGREE: the excerpt does not support the assigned status, or the rationale
does not follow from the excerpt (for example the excerpt is unrelated,
contradicts the status, or is too thin to justify it).

Also give a faithfulness_score from 1 (rationale is unconnected to or
contradicts the excerpt) to 5 (rationale follows directly and clearly from
the excerpt), independent of whether you agree with the status - a judgement
you disagree with can still be faithfully reasoned from the wrong evidence,
and one you agree with can still be a stretch from the excerpt given.

Judge only the reasoning shown to you. Do not use outside knowledge about
what a "better" answer would have been.
"""


def judge_production_verdict(
    *,
    question_id: str,
    question: str,
    concept: str,
    original_status: str,
    rationale: str,
    answer_excerpt: str,
) -> OnlineJudgeVerdict:

    response = call_with_retry(
        lambda: client.responses.parse(
            model=MODEL,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"""
INTERVIEW QUESTION
------------------
{question}

EXPECTED CONCEPT
----------------
{concept}

EVALUATOR'S ASSIGNED STATUS
----------------------------
{original_status}

EVALUATOR'S RATIONALE
----------------------
{rationale}

CITED ANSWER EXCERPT
---------------------
{answer_excerpt or "(no excerpt cited)"}

Audit this judgement.
""",
                },
            ],
            text_format=OnlineJudgeVerdict,
        )
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(f"Online judging failed: {question_id} / {concept}")

    result.question_id = question_id
    result.concept = concept

    return result


__all__ = ["judge_production_verdict", "MODEL"]
