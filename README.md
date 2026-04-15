# Mini Online Judge

A backend system modelled after platforms like LeetCode and HackerRank — built entirely with **FastAPI + PostgreSQL + SQLAlchemy + Alembic + JWT**.

---

## Project Overview

Mini Online Judge lets users register, browse coding problems, submit solutions in **Python** or **C++**, and receive automated verdicts (`AC`, `WA`, `TLE`, `RE`, `CE`) within the same HTTP response.

The project demonstrates:

- Clean layered architecture (routes → services → models)
- Real subprocess-based code execution with timeout enforcement
- JWT authentication with bcrypt password hashing
- Database-first migrations via Alembic
- Async-safe blocking calls via `asyncio.run_in_executor`

---

## Tech Stack

| Technology | Reason |
|---|---|
| **FastAPI** | Async-first, auto-generates OpenAPI docs, excellent DI system |
| **PostgreSQL** | ACID compliance, robust enum/JSON support |
| **SQLAlchemy ORM** | Type-safe mapped columns, relationship management |
| **Alembic** | Schema versioning; never relies on `create_all()` in production |
| **Pydantic v2 + pydantic-settings** | Strict validation + environment config in one place |
| **python-jose** | JWT signing and verification |
| **passlib / bcrypt** | Industry-standard password hashing |
| **subprocess** | Real code execution (no mocking) with shell=False for safety |
| **asyncio run_in_executor** | Runs blocking subprocess calls off the event loop |

---

## Features

- User registration and JWT-based login
- Browse all problems or view a problem with its public sample testcases
- Create problems and add hidden or sample testcases (authenticated)
- Submit Python and C++ solutions via REST API
- Full judge pipeline: compile → execute → compare output → verdict
- Submission history per user (`GET /submissions/me`)
- Admin users can view any submission; regular users see only their own
- Hidden testcases never exposed in any API response

---

## Project Structure

```
mini-online-judge/
├── app/
│   ├── main.py              ← FastAPI app, router registration, lifespan, health check
│   ├── config.py            ← Pydantic BaseSettings (single source for all env vars)
│   ├── database.py          ← SQLAlchemy engine, SessionLocal, DeclarativeBase
│   ├── dependencies.py      ← get_db() and get_current_user() for FastAPI DI
│   ├── models/
│   │   ├── __init__.py      ← Re-exports all models (required by Alembic autogenerate)
│   │   ├── user.py          ← User ORM model
│   │   ├── problem.py       ← Problem ORM model + Difficulty enum
│   │   ├── testcase.py      ← TestCase ORM model (cascade delete from Problem)
│   │   └── submission.py    ← Submission ORM model + Language/Status/Verdict enums
│   ├── schemas/
│   │   ├── __init__.py      ← Re-exports all Pydantic schemas
│   │   ├── user.py          ← UserCreate, UserOut, Token, LoginRequest
│   │   ├── problem.py       ← ProblemCreate, ProblemOut, ProblemDetail
│   │   ├── testcase.py      ← TestCaseCreate, TestCaseOut
│   │   └── submission.py    ← SubmissionCreate, SubmissionOut
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          ← POST /auth/register, POST /auth/login
│   │   ├── problems.py      ← GET/POST /problems, POST /problems/{id}/testcases
│   │   └── submissions.py   ← POST /submissions, GET /submissions/me, GET /submissions/{id}
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py      ← register_user(), authenticate_user()
│   │   ├── execution_service.py ← execute_code() + execute_code_async()
│   │   └── judge_service.py     ← run_judge() orchestration
│   └── utils/
│       ├── __init__.py
│       ├── security.py          ← hash_password(), verify_password(), JWT helpers
│       └── output_compare.py    ← outputs_match() with whitespace normalization
├── alembic/
│   ├── env.py               ← Alembic config; reads DATABASE_URL from pydantic-settings
│   ├── script.py.mako       ← Migration file template
│   └── versions/            ← Auto-generated migration files
├── alembic.ini              ← Alembic tool config (url overridden at runtime)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourname/mini-online-judge.git
cd mini-online-judge
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials and a strong JWT secret
```

### 5. Create the PostgreSQL database

```sql
CREATE DATABASE mini_judge;
```

Or via CLI:

```bash
createdb mini_judge
```

### 6. Run Alembic migrations

```bash
# Generate the initial migration (detects all models automatically)
alembic revision --autogenerate -m "initial_schema"

# Apply migrations to the database
alembic upgrade head
```

### 7. Start the development server

```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Full PostgreSQL connection string | `postgresql://user:pass@localhost:5432/mini_judge` |
| `JWT_SECRET_KEY` | Secret key for signing JWTs (keep long and random) | `supersecretkey123` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `30` |

---

## Database Setup

This project uses **Alembic** for all schema management.

- `alembic/env.py` reads `DATABASE_URL` from `app.config.settings` so the migration tool and the application always use the same connection string.
- All models are imported in `app/models/__init__.py`, which ensures Alembic's `autogenerate` feature detects every table.
- **Never** use `Base.metadata.create_all()` for production schema management — use `alembic upgrade head`.

To create new migrations after model changes:

```bash
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

To roll back one revision:

```bash
alembic downgrade -1
```

---

## How Submission Judging Works

1. **POST /submissions** receives `problem_id`, `language`, and `source_code`.
2. A `Submission` row is created with `status=queued`, `verdict=PENDING`.
3. Status is immediately updated to `running`.
4. The judge engine loads all **hidden** testcases (`is_sample=False`) for the problem. If none exist, it falls back to sample testcases with a warning log.
5. For each testcase the execution service:
   - Creates a unique temp directory.
   - Writes the source file (`solution.py` or `solution.cpp`).
   - For C++: compiles with `g++ -O2`. A non-zero return code → **CE**, stops immediately.
   - Runs the binary/interpreter with the testcase's `input_data` piped to stdin.
   - Enforces `time_limit_ms`. A `TimeoutExpired` → **TLE**, stops immediately.
   - A non-zero exit code → **RE**, stops immediately.
   - Compares normalized stdout to `expected_output` using `outputs_match()`. Mismatch → **WA**, stops immediately.
   - Cleans up the temp directory in `finally` regardless of outcome.
6. If all testcases pass → **AC**.
7. The submission is updated with verdict, `execution_time_ms` (max across all testcases), stdout, stderr, and `status=completed`.
8. The complete submission object is returned in the response.

> **Async Safety**: `execute_code()` is a blocking function. It is always called through `execute_code_async()`, which wraps it in `asyncio.get_event_loop().run_in_executor(None, ...)`, offloading the work to a thread pool and keeping FastAPI's event loop unblocked.

---

## Supported Verdicts

| Code | Full Name | When It Occurs |
|---|---|---|
| `AC` | Accepted | All testcases produce correct output within time limit |
| `WA` | Wrong Answer | Output doesn't match expected on at least one testcase |
| `TLE` | Time Limit Exceeded | Process didn't finish within `time_limit_ms` |
| `RE` | Runtime Error | Process exited with non-zero code (crash, exception, etc.) |
| `CE` | Compile Error | C++ compilation failed (`g++` returned non-zero) |
| `PENDING` | Pending | Initial state before judging begins |

---

## API Endpoint Summary

| Method | Path | Auth Required | Description |
|---|---|---|---|
| `GET` | `/` | No | Health check |
| `POST` | `/auth/register` | No | Register a new user |
| `POST` | `/auth/login` | No | Login and receive JWT |
| `GET` | `/problems` | No | List all problems |
| `GET` | `/problems/{id}` | No | Get problem + sample testcases |
| `POST` | `/problems` | Yes | Create a new problem |
| `POST` | `/problems/{id}/testcases` | Yes | Add a testcase (hidden or sample) |
| `POST` | `/submissions` | Yes | Submit code for judging |
| `GET` | `/submissions/me` | Yes | List current user's submissions |
| `GET` | `/submissions/{id}` | Yes | Get a specific submission (own or admin) |

---

## Testing a Sample Flow

### 1. Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "secret123"}'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
```

Copy the `access_token` from the response. Set it as an environment variable:

```bash
TOKEN="eyJhbGc..."
```

### 3. Create a problem

```bash
curl -X POST http://localhost:8000/problems \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sum of Two Numbers",
    "statement": "Given two integers A and B on a single line, print their sum.",
    "difficulty": "easy",
    "time_limit_ms": 2000,
    "memory_limit_mb": 256
  }'
```

Note the returned `id` (e.g., `1`). Set `PROBLEM_ID=1`.

### 4. Add a hidden testcase

```bash
curl -X POST http://localhost:8000/problems/1/testcases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_data": "3 5", "expected_output": "8", "is_sample": false}'
```

### 5. Add a sample testcase (visible to users)

```bash
curl -X POST http://localhost:8000/problems/1/testcases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_data": "1 2", "expected_output": "3", "is_sample": true}'
```

### 6. Submit a Python solution (AC)

```bash
curl -X POST http://localhost:8000/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "language": "python",
    "source_code": "a, b = map(int, input().split())\nprint(a + b)"
  }'
```

### 7. Submit a wrong Python solution (WA)

```bash
curl -X POST http://localhost:8000/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "language": "python",
    "source_code": "a, b = map(int, input().split())\nprint(a - b)"
  }'
```

### 8. Submit a C++ solution (AC)

```bash
curl -X POST http://localhost:8000/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "language": "cpp",
    "source_code": "#include<iostream>\nusing namespace std;\nint main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}"
  }'
```

### 9. View your submission history

```bash
curl http://localhost:8000/submissions/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Limitations & Security Notes

> **Code execution runs in Python subprocess without container-based sandboxing. Production systems should use isolated containers (e.g., Docker with seccomp profiles or nsjail) to prevent arbitrary code execution exploits. This prototype is intended for local development and portfolio use only.**

Additional notes:

- `shell=False` is enforced throughout the execution engine to prevent shell injection.
- Temp directories are always cleaned up in a `finally` block.
- Hidden testcases are filtered server-side and never appear in any API response.
- Problem creation is open to any authenticated user for simplicity; a production system would gate this on `is_admin=True`.

---

## Future Improvements

- **Async task queue**: Move judging to Celery + Redis. POST /submissions returns immediately; clients poll for verdict.
- **Container sandboxing**: Run user code in Docker containers with seccomp profiles or `nsjail` for true isolation.
- **Leaderboard**: Track per-problem accept rates and user rankings.
- **Problem tags**: Tag problems by topic (dynamic programming, graphs, etc.) with filtering.
- **Contest mode**: Time-bounded contests with live scoreboards.
- **Rate limiting**: Prevent submission spam per user.
- **Memory limit enforcement**: Use `resource.setrlimit` or cgroup-based limits.
- **Admin panel**: A protected admin router for user management and bulk testcase upload.
