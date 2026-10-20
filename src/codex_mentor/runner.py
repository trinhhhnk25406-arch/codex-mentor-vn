"""Thực thi mã nguồn trong môi trường con độc lập để bắt Traceback thực tế."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def error_text(self) -> str:
        if self.timed_out:
            return "TimeoutError: Chương trình chạy quá thời gian cho phép (nghi ngờ vòng lặp vô hạn hoặc đang đợi stdin)."
        err = self.stderr.strip()
        return err if err else self.stdout.strip()


def run_python_file(path: Path, timeout: int = 10, display_name: Optional[str] = None) -> RunResult:
    """Chạy tệp Python trong subprocess. stdin bị đóng để tránh treo khi code có hàm input()."""
    target = path.resolve()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    try:
        proc = subprocess.run(
            [sys.executable, str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(target.parent),
            stdin=subprocess.DEVNULL,
            env=env,
        )
        stderr = proc.stderr.replace(str(target), display_name or target.name)
        return RunResult(
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=stderr.strip(),
            duration_ms=0.0,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return RunResult(
            returncode=-1,
            stdout=out.strip(),
            stderr=err.strip(),
            duration_ms=float(timeout * 1000),
            timed_out=True,
        )


def run_candidate_source(source: str, original_file: Path, timeout: int = 10) -> RunResult:
    """Tạo tệp sandbox tạm thời để chạy thử bản sửa lỗi mà không làm biến đổi tệp gốc."""
    orig = original_file.resolve()
    temp_file = orig.with_name(f".{orig.stem}.codex_tmp.py")
    try:
        temp_file.write_text(source, encoding="utf-8")
        return run_python_file(temp_file, timeout=timeout, display_name=orig.name)
    finally:
        temp_file.unlink(missing_ok=True)
