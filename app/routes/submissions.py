from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.problem import Problem
from app.models.submission import Submission, SubmissionStatus, Verdict
from app.models.user import User
from app.schemas.submission import SubmissionCreate, SubmissionOut
from app.services.judge_service import run_judge

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post(
    "",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for judging",
)
async def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionOut:
    """
    Protected endpoint.

    Flow:
    1. Validate that the problem exists.
    2. Persist submission with status=queued.
    3. Update status=running and call the judge engine.
    4. Store verdict, timings, stdout/stderr.
    5. Mark status=completed and return the full submission record.

    NOTE: Judging is synchronous in this prototype. For production scalability,
    push to a Celery/Redis task queue and poll for results.
    """
    # 1. Validate problem
    problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    # 2. Persist with status=queued
    submission = Submission(
        user_id=current_user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        source_code=payload.source_code,
        status=SubmissionStatus.queued,
        verdict=Verdict.PENDING,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # 3. Mark running
    submission.status = SubmissionStatus.running
    db.commit()

    # 4. Run judge (async, wraps blocking subprocess in thread pool)
    judge_result = await run_judge(db, submission)

    # 5. Store results and mark completed
    submission.verdict = judge_result.verdict
    submission.execution_time_ms = judge_result.execution_time_ms
    submission.stdout = judge_result.stdout
    submission.stderr = judge_result.stderr
    submission.status = SubmissionStatus.completed
    db.commit()
    db.refresh(submission)

    return submission


@router.get(
    "/me",
    response_model=list[SubmissionOut],
    summary="List all submissions by the current user",
)
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SubmissionOut]:
    """Protected endpoint. Returns all submissions made by the logged-in user."""
    submissions = (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    return submissions


@router.get(
    "/{submission_id}",
    response_model=SubmissionOut,
    summary="Get a specific submission",
)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionOut:
    """
    Protected endpoint.
    Regular users can only view their own submissions.
    Admin users can view any submission.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    if not current_user.is_admin and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to view this submission.",
        )

    return submission
