import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from tinytest import Outcome, Runner
from tinytest.discovery import TestFile, collect_tests, find_test_files, load_module
from tinytest.reporter import ConsoleReporter, format_counts
from tinytest.runner import RunSummary, TestResult

SAMPLE = """
import tinytest

def helper():
    return 1

def test_passes():
    tinytest.assert_equal(helper(), 1)

def test_fails():
    tinytest.assert_equal([1, 2], [1, 3])

def test_errors():
    raise KeyError("boom")

@tinytest.skip("not ready")
def test_skipped():
    raise RuntimeError("should not run")

def test_runtime_skip():
    tinytest.skip_test("no database")

@tinytest.xfail("known bug")
def test_expected_failure():
    assert 1 == 2

@tinytest.xfail()
def test_unexpected_pass():
    pass
"""


class TempTests(unittest.TestCase):
    """Helpers for writing test files into a temporary folder."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, source: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return path

    def run_tests(self, **kwargs) -> RunSummary:
        return Runner(**kwargs).run_paths([self.root])

    @staticmethod
    def outcomes(summary: RunSummary) -> dict[str, Outcome]:
        return {r.test_id.split("::")[-1]: r.outcome for r in summary.results}


class DiscoveryTests(TempTests):
    def test_finds_test_files_recursively(self) -> None:
        self.write("test_a.py", "")
        self.write("pkg/test_b.py", "")
        self.write("helpers.py", "")
        self.write("a_test.py", "")
        self.write(".hidden/test_c.py", "")
        self.write("__pycache__/test_d.py", "")
        names = [p.name for p in find_test_files(self.root)]
        self.assertEqual(names, ["test_b.py", "test_a.py"])

    def test_single_file_is_used_directly(self) -> None:
        path = self.write("checks.py", "")
        self.assertEqual(find_test_files(path), [path])

    def test_collects_test_functions_in_source_order(self) -> None:
        path = self.write(
            "test_order.py",
            """
            from os.path import join as test_imported

            def test_b(): pass
            def test_a(): pass
            def not_a_test(): pass
            test_value = 5

            class TestThing:
                def test_method(self): pass
            """,
        )
        module = load_module(path)
        names = [t.name for t in collect_tests(module, path)]
        self.assertEqual(names, ["test_b", "test_a"])

    def test_can_import_neighbour_modules(self) -> None:
        self.write("util_for_tests.py", "VALUE = 7\n")
        self.write(
            "test_neighbour.py",
            """
            import util_for_tests

            def test_value():
                assert util_for_tests.VALUE == 7
            """,
        )
        summary = self.run_tests()
        self.assertEqual(self.outcomes(summary), {"test_value": Outcome.PASSED})


class RunnerTests(TempTests):
    def test_outcomes_for_each_kind_of_test(self) -> None:
        self.write("test_sample.py", SAMPLE)
        summary = self.run_tests()
        self.assertEqual(
            self.outcomes(summary),
            {
                "test_passes": Outcome.PASSED,
                "test_fails": Outcome.FAILED,
                "test_errors": Outcome.ERROR,
                "test_skipped": Outcome.SKIPPED,
                "test_runtime_skip": Outcome.SKIPPED,
                "test_expected_failure": Outcome.XFAILED,
                "test_unexpected_pass": Outcome.XPASSED,
            },
        )
        self.assertFalse(summary.ok)
        self.assertEqual(len(summary.problems), 3)

    def test_all_passing_run_is_ok(self) -> None:
        self.write("test_ok.py", "def test_one():\n    assert True\n")
        summary = self.run_tests()
        self.assertTrue(summary.ok)
        self.assertEqual(summary.counts[Outcome.PASSED], 1)

    def test_failure_details_hide_tinytest_frames(self) -> None:
        self.write("test_sample.py", SAMPLE)
        summary = self.run_tests()
        failed = next(r for r in summary.results if r.outcome is Outcome.FAILED)
        self.assertIn("test_sample.py", failed.details)
        self.assertNotIn("runner.py", failed.details)
        self.assertNotIn("assertions.py", failed.details)
        self.assertIn("+    2,", failed.details)
        self.assertTrue(failed.message.startswith("AssertionError: [1, 2] != [1, 3]"))

    def test_xfail_with_raises_only_accepts_that_exception(self) -> None:
        self.write(
            "test_xfail.py",
            """
            import tinytest

            @tinytest.xfail(raises=ValueError)
            def test_right_error():
                raise ValueError

            @tinytest.xfail(raises=ValueError)
            def test_wrong_error():
                raise KeyError
            """,
        )
        outcomes = self.outcomes(self.run_tests())
        self.assertEqual(outcomes["test_right_error"], Outcome.XFAILED)
        self.assertEqual(outcomes["test_wrong_error"], Outcome.ERROR)

    def test_skip_if(self) -> None:
        self.write(
            "test_skip_if.py",
            """
            import tinytest

            @tinytest.skip_if(True, "always")
            def test_skipped(): pass

            @tinytest.skip_if(False, "never")
            def test_runs(): pass

            @tinytest.skip
            def test_bare_skip(): pass
            """,
        )
        outcomes = self.outcomes(self.run_tests())
        self.assertEqual(outcomes["test_skipped"], Outcome.SKIPPED)
        self.assertEqual(outcomes["test_runs"], Outcome.PASSED)
        self.assertEqual(outcomes["test_bare_skip"], Outcome.SKIPPED)

    def test_import_error_is_reported(self) -> None:
        self.write("test_broken.py", "import does_not_exist_anywhere\n")
        summary = self.run_tests()
        self.assertEqual(len(summary.results), 1)
        result = summary.results[0]
        self.assertEqual(result.outcome, Outcome.ERROR)
        self.assertIn("could not import", result.message)
        self.assertIn("ModuleNotFoundError", result.message)

    def test_keyword_filter(self) -> None:
        self.write("test_sample.py", SAMPLE)
        summary = self.run_tests(keyword="pass")
        self.assertEqual(
            set(self.outcomes(summary)), {"test_passes", "test_unexpected_pass"}
        )

    def test_fail_fast_stops_after_first_problem(self) -> None:
        self.write("test_sample.py", SAMPLE)
        self.write("test_z_later.py", "def test_never():\n    pass\n")
        summary = self.run_tests(fail_fast=True)
        self.assertEqual(list(self.outcomes(summary)), ["test_passes", "test_fails"])


class HookTests(TempTests):
    HOOKS = """
    calls = []

    def setup_module():
        calls.append("setup_module")

    def teardown_module():
        calls.append("teardown_module")

    def setup_function():
        calls.append("setup")

    def teardown_function():
        calls.append("teardown")

    def test_one():
        calls.append("one")

    def test_two():
        calls.append("two")
        assert False
    """

    def test_hooks_run_in_order(self) -> None:
        path = self.write("test_hooks.py", self.HOOKS)
        module = load_module(path)
        test_file = TestFile(path, module, collect_tests(module, path))
        Runner().run_files([test_file])
        self.assertEqual(
            module.calls,
            [
                "setup_module",
                "setup",
                "one",
                "teardown",
                "setup",
                "two",
                "teardown",
                "teardown_module",
            ],
        )

    def test_setup_module_failure_errors_every_test(self) -> None:
        self.write(
            "test_bad_setup.py",
            """
            def setup_module():
                raise RuntimeError("no fixture")

            def test_a(): pass
            def test_b(): pass
            """,
        )
        summary = self.run_tests()
        self.assertEqual(
            [r.outcome for r in summary.results], [Outcome.ERROR, Outcome.ERROR]
        )
        self.assertIn("setup_module failed", summary.results[0].message)

    def test_teardown_failure_turns_pass_into_error(self) -> None:
        self.write(
            "test_bad_teardown.py",
            """
            def teardown_function():
                raise RuntimeError("cleanup broke")

            def test_a(): pass
            """,
        )
        result = self.run_tests().results[0]
        self.assertEqual(result.outcome, Outcome.ERROR)
        self.assertIn("teardown_function failed", result.message)


class ReporterTests(unittest.TestCase):
    def test_dots_and_summary(self) -> None:
        stream = io.StringIO()
        reporter = ConsoleReporter(stream)
        results = [
            TestResult("t.py::test_a", Outcome.PASSED),
            TestResult("t.py::test_b", Outcome.FAILED, message="boom", details="trace"),
            TestResult("t.py::test_c", Outcome.SKIPPED),
        ]
        for result in results:
            reporter.test_finished(result)
        summary = RunSummary(results, duration=0.5)
        reporter.run_finished(summary)
        output = stream.getvalue()
        self.assertTrue(output.startswith(".Fs\n"))
        self.assertIn("t.py::test_b", output)
        self.assertIn("trace", output)
        self.assertTrue(output.endswith("1 failed, 1 passed, 1 skipped in 0.50s\n"))

    def test_verbose_lines(self) -> None:
        stream = io.StringIO()
        reporter = ConsoleReporter(stream, verbose=True)
        reporter.test_finished(TestResult("t.py::test_a", Outcome.PASSED))
        reporter.test_finished(
            TestResult("t.py::test_b", Outcome.SKIPPED, message="later")
        )
        lines = stream.getvalue().splitlines()
        self.assertEqual(lines[0], "PASSED   t.py::test_a")
        self.assertEqual(lines[1], "SKIPPED  t.py::test_b (later)")

    def test_empty_run(self) -> None:
        self.assertEqual(format_counts(RunSummary()), "no tests ran in 0.00s")


if __name__ == "__main__":
    unittest.main()
