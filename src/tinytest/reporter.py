"""Console output for test runs."""

from __future__ import annotations

import sys
from typing import TextIO

from .runner import Outcome, RunSummary, TestResult

__all__ = ["ConsoleReporter", "format_counts"]

_SYMBOLS = {
    Outcome.PASSED: ".",
    Outcome.FAILED: "F",
    Outcome.ERROR: "E",
    Outcome.SKIPPED: "s",
    Outcome.XFAILED: "x",
    Outcome.XPASSED: "X",
}

_ORDER = [
    Outcome.FAILED,
    Outcome.ERROR,
    Outcome.XPASSED,
    Outcome.PASSED,
    Outcome.SKIPPED,
    Outcome.XFAILED,
]


def format_counts(summary: RunSummary) -> str:
    """Return a line like '3 passed, 1 failed in 0.01s'."""
    counts = summary.counts
    parts = [f"{counts[o]} {o.value}" for o in _ORDER if counts[o]]
    if not parts:
        parts = ["no tests ran"]
    return f"{', '.join(parts)} in {summary.duration:.2f}s"


class ConsoleReporter:
    """Prints a dot per test (or a line per test when verbose)."""

    def __init__(self, stream: TextIO | None = None, verbose: bool = False) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self.verbose = verbose
        self._column = 0

    def _write(self, text: str) -> None:
        self.stream.write(text)
        self.stream.flush()

    def test_finished(self, result: TestResult) -> None:
        if self.verbose:
            line = f"{result.outcome.value.upper():8} {result.test_id}"
            if result.message and result.outcome in (Outcome.SKIPPED, Outcome.XFAILED):
                line += f" ({result.message})"
            self._write(line + "\n")
            return
        self._write(_SYMBOLS[result.outcome])
        self._column += 1
        if self._column == 70:
            self._write("\n")
            self._column = 0

    def run_finished(self, summary: RunSummary) -> None:
        if not self.verbose and self._column:
            self._write("\n")
            self._column = 0
        for result in summary.problems:
            self._write(f"\n{'_' * 10} {result.test_id} {'_' * 10}\n")
            self._write((result.details or result.message) + "\n")
        self._write("\n" + format_counts(summary) + "\n")
