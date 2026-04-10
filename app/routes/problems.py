from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.problem import Problem
from app.models.testcase import TestCase
from app.models.user import User
from app.schemas.problem import ProblemCreate, ProblemDetail, ProblemOut
from app.schemas.testcase import TestCaseCreate, TestCaseOut

router = APIRouter(prefix="/problems", tags=["Problems"])


@router.get(
    "",
    response_model=list[ProblemOut],
    summary="List all problems",
)
def list_problems(db: Session = Depends(get_db)) -> list[ProblemOut]:
    """Public endpoint. Returns all problems without testcases."""
    problems = db.query(Problem).order_by(Problem.created_at.desc()).all()
    return problems


@router.get(
    "/{problem_id}",
    response_model=ProblemDetail,
    summary="Get a problem with its sample testcases",
)
def get_problem(problem_id: int, db: Session = Depends(get_db)) -> ProblemDetail:
    """
    Public endpoint.  Returns a single problem including sample testcases only.
    Hidden testcases (is_sample=False) are never included.
    """
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    sample_tcs = [tc for tc in problem.testcases if tc.is_sample]

    return ProblemDetail(
        id=problem.id,
        title=problem.title,
        statement=problem.statement,
        difficulty=problem.difficulty,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        created_at=problem.created_at,
        sample_testcases=sample_tcs,
    )


@router.post(
    "",
    response_model=ProblemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new problem (authenticated)",
)
def create_problem(
    payload: ProblemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProblemOut:
    """
    Protected endpoint. Any authenticated user may create a problem.
    NOTE: In production this should be restricted to admin users.
    """
    problem = Problem(
        title=payload.title,
        statement=payload.statement,
        difficulty=payload.difficulty,
        time_limit_ms=payload.time_limit_ms,
        memory_limit_mb=payload.memory_limit_mb,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


@router.post(
    "/{problem_id}/testcases",
    response_model=TestCaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a testcase to a problem (authenticated)",
)
def add_testcase(
    problem_id: int,
    payload: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestCaseOut:
    """
    Protected endpoint.  Adds a testcase (sample or hidden) to the given problem.
    Hidden testcases (is_sample=False) will never appear in public API responses.
    """
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    tc = TestCase(
        problem_id=problem_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        is_sample=payload.is_sample,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc
