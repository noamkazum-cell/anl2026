#!/usr/bin/env python3
"""Pre-submission checks: tests, import, smoke run, benchmark summary.

Usage:
  uv run python scripts/submission_preflight.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SUBMISSION_FILES = (
    "agent360_submit.py",
    "requirements.txt",
)


def _run(cmd: list[str], *, cwd: Path = ROOT) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=cwd)


def _summarize_csv(path: Path, label: str) -> None:
    if not path.is_file():
        print(f"  {label}: [missing] {path}")
        return
    try:
        import pandas as pd
    except ImportError:
        print(f"  {label}: {path} (install pandas to summarize)")
        return
    df = pd.read_csv(path)
    ex = df[~df["opponent"].str.contains("Mirror", na=False)]
    print(f"  {label}: all score={df['score'].mean():.3f}  excl_mirror={ex['score'].mean():.3f}  n={len(df)}")


def main() -> int:
    print("=" * 60)
    print("ANL 2026 submission preflight — Agent360")
    print("=" * 60)

    missing = [f for f in SUBMISSION_FILES if not (ROOT / f).is_file()]
    if missing:
        print(f"[FAIL] Missing files: {missing}")
        return 1
    print("[OK] Submission files present:", ", ".join(SUBMISSION_FILES))

    try:
        sys.path.insert(0, str(ROOT))
        from agent360_submit import Agent360  # noqa: F401

        print("[OK] import agent360_submit.Agent360 (packaged as agent360.py in zip)")
    except Exception as exc:
        print(f"[FAIL] import Agent360: {exc}")
        return 1

    code = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_agent360.py",
            "tests/test_agent360_v2.py",
            "tests/test_agent360_v3.py",
            "tests/test_sparring_deception.py",
            "tests/test_cli.py",
            "-q",
            "--tb=no",
        ]
    )
    if code != 0:
        print("[FAIL] pytest")
        return code
    print("[OK] pytest")

    code = _run(
        [
            sys.executable,
            "-m",
            "main",
            "run",
            "--scenario",
            "Camera",
            "--no-plot",
            "--negotiator",
            "agent360_submit.Agent360",
            "--opponent",
            "negmas.sao.BoulwareTBNegotiator",
            "--negotiator-first",
        ]
    )
    if code != 0:
        print("[FAIL] smoke run (Boulware)")
        return code
    print("[OK] smoke run")

    print("\nBenchmark snapshots:")
    _summarize_csv(ROOT / "results/sparring_competition.csv", "competition panel")
    _summarize_csv(ROOT / "results/stress_v3.csv", "stress panel")

    print("\n" + "=" * 60)
    print("Submission form (ANL 2026):")
    print("  Agent Module: agent360")
    print("  Agent Class:  Agent360")
    print("\nCreate zip (Windows):")
    print("  make_submitted_zip.bat")
    print("\nOr full zip:")
    print("  make_submission.bat")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
