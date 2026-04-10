"""
Code execution service.

Executes user-submitted source code inside a temporary directory using
subprocess (shell=False) and returns a structured result.  Blocking calls
are wrapped in run_in_executor so FastAPI's async event loop is never blocked.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from functools import partial


@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: int = 0
    timed_out: bool = False
    compile_error: bool = False
    compile_stderr: str = ""  # only populated for C++


def execute_code(
    source_code: str,
    language: str,
    stdin_input: str,
    time_limit_ms: int,
) -> ExecutionResult:
    """
    Synchronous core of the execution engine.

    Creates a temp directory, writes the source file, optionally compiles
    (C++), runs the binary/interpreter with the given stdin, and cleans up.
    Never uses shell=True.
    """
    result = ExecutionResult()
    tmpdir = tempfile.mkdtemp(prefix="moj_")

    try:
        if language == "python":
            src_path = os.path.join(tmpdir, "solution.py")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(source_code)
            cmd = ["python", src_path]

        elif language == "cpp":
            src_path = os.path.join(tmpdir, "solution.cpp")
            exe_path = os.path.join(tmpdir, "solution")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(source_code)

            # --- Compile ---
            compile_proc = subprocess.run(
                ["g++", "-O2", "-o", exe_path, src_path],
                capture_output=True,
                text=True,
                timeout=30,  # hard cap for compilation
                shell=False,
            )
            if compile_proc.returncode != 0:
                result.compile_error = True
                result.compile_stderr = compile_proc.stderr
                return result

            cmd = [exe_path]

        else:
            result.compile_error = True
            result.compile_stderr = f"Unsupported language: {language}"
            return result

        # --- Execute ---
        timeout_sec = time_limit_ms / 1000.0
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                shell=False,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.exit_code = proc.returncode
            result.execution_time_ms = elapsed_ms

        except subprocess.TimeoutExpired:
            result.timed_out = True
            result.execution_time_ms = time_limit_ms

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return result


async def execute_code_async(
    source_code: str,
    language: str,
    stdin_input: str,
    time_limit_ms: int,
) -> ExecutionResult:
    """
    Async wrapper around execute_code().

    Runs the blocking subprocess work in the default ThreadPoolExecutor so
    FastAPI's event loop is never blocked.
    """
    loop = asyncio.get_event_loop()
    fn = partial(execute_code, source_code, language, stdin_input, time_limit_ms)
    return await loop.run_in_executor(None, fn)
