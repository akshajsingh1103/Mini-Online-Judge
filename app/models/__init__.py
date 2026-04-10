# app/models/__init__.py
# Import all models here so Alembic can detect them during autogenerate.
from app.models.user import User
from app.models.problem import Problem
from app.models.testcase import TestCase
from app.models.submission import Submission

__all__ = ["User", "Problem", "TestCase", "Submission"]
