import logging
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models.submission import Submission, Verdict
from app.models.testcase import TestCase
from app.services.execution_service import execute_code_async
from app.utils.output_compare import outputs_match

logger = logging.getLogger(__name__)


class JudgeResult(NamedTuple):
    verdict: Verdict
    execution_time_ms: int
    stdout: str
    stderr: str


async def run_judge(db: Session, submission: Submission) -> JudgeResult:
    """
    Executes submission against testcases and returns final verdict.
    """

    # --- Fetch ALL testcases (simpler + safer for now) ---
    testcases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == submission.problem_id)
        .all()
    )

    if not testcases:
        logger.error(f"No testcases found for problem {submission.problem_id}")
        return JudgeResult(
            verdict=Verdict.WA,
            execution_time_ms=0,
            stdout="",
            stderr="No testcases configured.",
        )

    logger.info(f"Running {len(testcases)} testcases")

    max_time_ms = 0
    outputs = []
    errors = []

    # --- Run each testcase ---
    for idx, tc in enumerate(testcases):
        logger.info(f"Running testcase #{idx + 1}")

        result = await execute_code_async(
            source_code=submission.source_code,
            language=submission.language.value,
            stdin_input=tc.input_data,
            time_limit_ms=submission.problem.time_limit_ms,
        )

        max_time_ms = max(max_time_ms, result.execution_time_ms)
        outputs.append(result.stdout.strip())
        errors.append(result.stderr.strip())

        # --- Compile Error ---
        if result.compile_error:
            return JudgeResult(
                verdict=Verdict.CE,
                execution_time_ms=0,
                stdout="",
                stderr=result.compile_stderr,
            )

        # --- Time Limit Exceeded ---
        if result.timed_out:
            return JudgeResult(
                verdict=Verdict.TLE,
                execution_time_ms=max_time_ms,
                stdout="\n".join(outputs),
                stderr="\n".join(errors),
            )

        # --- Runtime Error ---
        if result.exit_code != 0:
            return JudgeResult(
                verdict=Verdict.RE,
                execution_time_ms=max_time_ms,
                stdout="\n".join(outputs),
                stderr="\n".join(errors),
            )

        # --- Wrong Answer ---
        if not outputs_match(result.stdout, tc.expected_output):
            logger.warning(
                f"WA on testcase #{idx + 1} | expected={tc.expected_output} got={result.stdout}"
            )
            return JudgeResult(
                verdict=Verdict.WA,
                execution_time_ms=max_time_ms,
                stdout="\n".join(outputs),
                stderr="\n".join(errors),
            )

    # --- All passed ---
    return JudgeResult(
        verdict=Verdict.AC,
        execution_time_ms=max_time_ms,
        stdout="\n".join(outputs),
        stderr="\n".join(errors),
    )