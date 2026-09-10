import os

from dotenv import load_dotenv
from openai import OpenAI

from src.schemas.concept_coverage import ConceptCoverageResult


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You evaluate whether an evaluation-knowledge document contains enough
information to assess a specific expected concept in an interview answer.

You are evaluating KNOWLEDGE COVERAGE.

You are NOT evaluating the candidate.

Classify coverage as:

COVERED
The referenced evaluation knowledge clearly contains the meaning needed
to determine whether the candidate demonstrated the expected concept.
Exact wording is not required. Semantic equivalence is sufficient.

PARTIAL
The evaluation knowledge contains related information, but important
parts of the expected concept are missing or only indirectly supported.

NOT_COVERED
The evaluation knowledge does not contain enough information to assess
the expected concept reliably.

Rules:

1. Judge semantic meaning, not word overlap.

2. Do not require exact wording.

3. Use only the supplied evaluation knowledge.

4. Do not add outside knowledge.

5. Do not judge whether the interview question itself is good.

6. Do not judge a candidate answer.

7. A concept is COVERED when the evaluation knowledge gives an evaluator
   enough technical information to recognize a correct answer expressing
   that concept.

8. If only part of a compound concept is supported, use PARTIAL.

9. If the relevant idea must be supplied from your own knowledge rather
   than the supplied evaluation knowledge, use NOT_COVERED.
"""


def judge_concept_coverage(
    question_id: str,
    question: str,
    concept: str,
    evaluation_knowledge: str,
) -> ConceptCoverageResult:

    response = client.responses.parse(
        model="gpt-5.6",
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
QUESTION ID
-----------
{question_id}

INTERVIEW QUESTION
------------------
{question}

EXPECTED MUST-HAVE CONCEPT
--------------------------
{concept}

REFERENCED EVALUATION KNOWLEDGE
-------------------------------
{evaluation_knowledge}

Determine whether the referenced evaluation knowledge contains enough
information to assess this expected concept.
""",
            },
        ],
        text_format=ConceptCoverageResult,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(
            f"Coverage judging failed: "
            f"{question_id} / {concept}"
        )

    result.question_id = question_id
    result.concept = concept

    return result
