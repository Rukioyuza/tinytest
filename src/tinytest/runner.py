"""Running tests and collecting their results."""

from __future__ import annotations

import time
import traceback
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Protocol

from .discovery import TestFile, TestItem, find_test_files, load_test_file
from .markers import SKIP_ATTR, XFAIL_ATTR, SkipTest, XFail

__all__ = ["Outcome", "Reporter", "RunSummary", "Runner", "TestResult"]

_PACKAGE_DIR = Path(__file__).resolve().parent


class Outcome(str, Enum):
    """What happened when a test ran."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    XFAILED = "xfailed"
    XPASSED = "xpassed"


BAD_OUTCOMES = {Outcome.FAILED, Outcome.ERROR, Outcome.XPASSED}


@dataclass
class TestResult:
    """The result of one test (or of a file that failed to import)."""

    test_id: str
    outcome: Outcome
    duration: float = 0.0
    message: str = ""
    details: str = ""


@dataclass
class RunSummary:
    """All results from a run."""

    results: list[TestResult] = field(default_factory=list)
    duration: float = 0.0

    @property
    def counts(self) -> Counter[Outcome]:
        return Counter(result.outcome for result in self.results)

    @property
    def ok(self) -> bool:
        """True when nothing failed, errored or unexpectedly passed."""
        return not any(r.outcome in BAD_OUTCOMES for r in self.results)

    @property
    def problems(self) -> list[TestResult]:
        return [r for r in self.results if r.outcome in BAD_OUTCOMES]


class Reporter(Protocol):
    """Receives progress from the runner."""

    def test_finished(self, result: TestResult) -> None: ...

    def run_finished(self, summary: RunSummary) -> None: ...


def _is_internal(filename: str) -> bool:
    try:
        return Path(filename).resolve().parent == _PACKAGE_DIR
    except OSError:
        return False


def format_exception(exc: BaseException) -> str:
    """Format a traceback without the frames from tinytest itself."""
    frames = [
        frame
        for frame in traceback.extract_tb(exc.__traceback__)
        if not _is_internal(frame.filename)
    ]
    lines = ["Traceback (most recent call last):\n"]
    lines += traceback.StackSummary.from_list(frames).format()
    lines += traceback.format_exception_only(type(exc), exc)
    return "".join(lines).rstrip()


def _first_line(exc: BaseException) -> str:
    text = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {text.splitlines()[0]}" if text else name


def _call_hook(module: ModuleType | None, name: str) -> None:
    hook = getattr(module, name, None)
    if callable(hook):
        hook()


class Runner:
    """Runs test files and reports each result as it finishes."""

    def __init__(
        self,
        reporter: Reporter | None = None,
        keyword: str | None = None,
        fail_fast: bool = False,
    ) -> None:
        self.reporter = reporter
        self.keyword = keyword
        self.fail_fast = fail_fast
        self._stop = False

    def run_paths(self, paths: Iterable[Path]) -> RunSummary:
        """Discover and run all tests under the given paths."""
        files: list[Path] = []
        for path in paths:
            files.extend(find_test_files(path))
        return self.run_files([load_test_file(f) for f in files])

    def run_files(self, files: Iterable[TestFile]) -> RunSummary:
        """Run tests from already loaded files."""
        summary = RunSummary()
        start = time.perf_counter()
        self._stop = False
        for test_file in files:
            if self._stop:
                break
            self._run_file(test_file, summary)
        summary.duration = time.perf_counter() - start
        if self.reporter is not None:
            self.reporter.run_finished(summary)
        return summary

    def _record(self, summary: RunSummary, result: TestResult) -> None:
        summary.results.append(result)
        if self.reporter is not None:
            self.reporter.test_finished(result)
        if self.fail_fast and result.outcome in BAD_OUTCOMES:
            self._stop = True

    def _selected(self, test: TestItem) -> bool:
        return self.keyword is None or self.keyword in test.name

    def _run_file(self, test_file: TestFile, summary: RunSummary) -> None:
        file_id = test_file.path.as_posix()
        if test_file.error is not None:
            result = TestResult(
                file_id,
                Outcome.ERROR,
                message=f"could not import: {_first_line(test_file.error)}",
                details=format_exception(test_file.error),
            )
            self._record(summary, result)
            return

        tests = [t for t in test_file.tests if self._selected(t)]
        if not tests:
            return

        try:
            _call_hook(test_file.module, "setup_module")
        except Exception as exc:  # noqa: BLE001
            for test in tests:
                self._record(
                    summary,
                    TestResult(
                        test.test_id,
                        Outcome.ERROR,
                        message=f"setup_module failed: {_first_line(exc)}",
                        details=format_exception(exc),
                    ),
                )
            return

        for test in tests:
            if self._stop:
                break
            self._record(summary, self.run_test(test, test_file.module))

        try:
            _call_hook(test_file.module, "teardown_module")
        except Exception as exc:  # noqa: BLE001
            self._record(
                summary,
                TestResult(
                    f"{file_id}::teardown_module",
                    Outcome.ERROR,
                    message=f"teardown_module failed: {_first_line(exc)}",
                    details=format_exception(exc),
                ),
            )

    def run_test(self, test: TestItem, module: ModuleType | None = None) -> TestResult:
        """Run one test with its setup_function/teardown_function hooks."""
        skip_reason = getattr(test.func, SKIP_ATTR, None)
        if skip_reason is not None:
            return TestResult(test.test_id, Outcome.SKIPPED, message=skip_reason)

        start = time.perf_counter()
        try:
            _call_hook(module, "setup_function")
        except Exception as exc:  # noqa: BLE001
            return TestResult(
                test.test_id,
                Outcome.ERROR,
                time.perf_counter() - start,
                f"setup_function failed: {_first_line(exc)}",
                format_exception(exc),
            )

        result = self._call(test)

        try:
            _call_hook(module, "teardown_function")
        except Exception as exc:  # noqa: BLE001
            if result.outcome not in BAD_OUTCOMES:
                result = TestResult(
                    test.test_id,
                    Outcome.ERROR,
                    message=f"teardown_function failed: {_first_line(exc)}",
                    details=format_exception(exc),
                )
        result.duration = time.perf_counter() - start
        return result

    def _call(self, test: TestItem) -> TestResult:
        expected: XFail | None = getattr(test.func, XFAIL_ATTR, None)
        try:
            test.func()
        except SkipTest as exc:
            return TestResult(test.test_id, Outcome.SKIPPED, message=str(exc))
        except Exception as exc:  # noqa: BLE001
            if expected is not None and (
                expected.raises is None or isinstance(exc, expected.raises)
            ):
                return TestResult(
                    test.test_id, Outcome.XFAILED, message=expected.reason
                )
            failed = isinstance(exc, AssertionError)
            outcome = Outcome.FAILED if failed else Outcome.ERROR
            return TestResult(
                test.test_id,
                outcome,
                message=_first_line(exc),
                details=format_exception(exc),
            )
        if expected is not None:
            message = "expected to fail but passed"
            if expected.reason:
                message += f" ({expected.reason})"
            return TestResult(test.test_id, Outcome.XPASSED, message=message)
        return TestResult(test.test_id, Outcome.PASSED)


def run(
    paths: Iterable[Path | str],
    reporter: Reporter | None = None,
    keyword: str | None = None,
    fail_fast: bool = False,
) -> RunSummary:
    """Convenience wrapper: discover and run tests under paths."""
    runner = Runner(reporter, keyword=keyword, fail_fast=fail_fast)
    return runner.run_paths(Path(p) for p in paths)
