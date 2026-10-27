from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import compliance as C
from ..deps import current_user
from ..models import User

router = APIRouter(prefix="/api/compliance")


class LotCheckIn(BaseModel):
    item: str
    condition: str = "fresh"
    expiry: Optional[date] = None


class AskIn(BaseModel):
    question: str


class TestCaseIn(BaseModel):
    prompt: str
    category: str = "Custom Probe"
    expected_clause_ids: Optional[List[str]] = None
    forbidden_hallucinated_phrases: Optional[List[str]] = None
    required_grounded_phrases: Optional[List[str]] = None


@router.post("/check")
def check_compliance(b: LotCheckIn, u: User = Depends(current_user)):
    """Audits a proposed surplus/waste batch against statutory FSSAI and CPCB rules."""
    return C.check_lot_compliance(
        item=b.item,
        condition=b.condition,
        expiry_date=b.expiry,
    )


@router.post("/ask")
def ask_copilot(b: AskIn, u: User = Depends(current_user)):
    """Interactive RAG Copilot: answers compliance queries with statutory citations."""
    q = b.question.strip()
    if not q:
        raise HTTPException(422, "Please provide a question.")
    return C.ask_compliance_copilot(q)


@router.get("/regulations")
def list_regulations(u: User = Depends(current_user)):
    """Returns the indexed repository of FSSAI, DAHD, and CPCB regulations."""
    return {"regulations": C.get_all_regulations()}


@router.get("/eval/benchmark")
def get_benchmark(u: User = Depends(current_user)):
    """Retrieves stored RAG hallucination and faithfulness benchmark metrics."""
    from ..hallucination_eval import get_cached_benchmark
    return get_cached_benchmark()


@router.post("/eval/run")
def trigger_benchmark(u: User = Depends(current_user)):
    """Re-runs the adversarial hallucination test cases and updates benchmark scores."""
    from ..hallucination_eval import run_hallucination_benchmark
    return run_hallucination_benchmark()


@router.post("/eval/testcases")
def add_and_test_case(b: TestCaseIn, u: User = Depends(current_user)):
    """Appends a new test case and evaluates it against the Compliance Copilot."""
    if not b.prompt.strip():
        raise HTTPException(422, "Please provide a non-empty test prompt.")
    from ..hallucination_eval import add_custom_test_case
    return add_custom_test_case(
        prompt=b.prompt,
        category=b.category,
        expected_clause_ids=b.expected_clause_ids,
        forbidden_hallucinated_phrases=b.forbidden_hallucinated_phrases,
        required_grounded_phrases=b.required_grounded_phrases,
    )


