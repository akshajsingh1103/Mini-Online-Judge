import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Language(str, enum.Enum):
    python = "python"
    cpp = "cpp"


class SubmissionStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"


class Verdict(str, enum.Enum):
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    RE = "RE"
    CE = "CE"
    PENDING = "PENDING"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(
        Enum(Language, name="language_enum"), nullable=False
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status_enum"),
        default=SubmissionStatus.queued,
        nullable=False,
    )
    verdict: Mapped[Verdict | None] = mapped_column(
        Enum(Verdict, name="verdict_enum"), nullable=True
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="submissions")  # noqa: F821
    problem: Mapped["Problem"] = relationship("Problem", back_populates="submissions")  # noqa: F821
