"""Shared paths and helpers for the offline tests."""

from pathlib import Path
from typing import Iterable

from agenttrace.cli import analyse_stream
from agenttrace.report import Analysis

TESTS = Path(__file__).resolve().parent
REPO_ROOT = TESTS.parent
FIXTURES = TESTS / "fixtures"


def fixture(name: str) -> Path:
    return FIXTURES / name


def analyse_fixtures(
    names: Iterable[str],
    forced_format: str | None = None,
    declarations: tuple[str, ...] = (),
) -> Analysis:
    """Run the real reader over fixture files, the way the command line does."""

    analysis = Analysis(declarations)
    for name in names:
        path = fixture(name)
        with open(path, "r", encoding="utf-8", errors="replace") as stream:
            analyse_stream(str(path), stream, forced_format, analysis, declarations)
    return analysis
