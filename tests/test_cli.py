import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tinytest.cli import main

PASSING = "def test_ok():\n    assert 1 + 1 == 2\n"
FAILING = "def test_bad():\n    assert 1 + 1 == 3\n"


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_exit_zero_when_all_pass(self) -> None:
        (self.root / "test_ok.py").write_text(PASSING, encoding="utf-8")
        code, out, _ = self.run_main(str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("1 passed", out)

    def test_exit_one_on_failure(self) -> None:
        (self.root / "test_ok.py").write_text(PASSING, encoding="utf-8")
        (self.root / "test_bad.py").write_text(FAILING, encoding="utf-8")
        code, out, _ = self.run_main(str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("1 failed, 1 passed", out)
        self.assertIn("test_bad.py::test_bad", out)

    def test_exit_two_for_missing_path(self) -> None:
        code, _, err = self.run_main(str(self.root / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_verbose_and_keyword(self) -> None:
        (self.root / "test_ok.py").write_text(PASSING, encoding="utf-8")
        (self.root / "test_bad.py").write_text(FAILING, encoding="utf-8")
        code, out, _ = self.run_main("-v", "-k", "ok", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("PASSED", out)
        self.assertNotIn("test_bad", out)

    def test_python_dash_m(self) -> None:
        (self.root / "test_bad.py").write_text(FAILING, encoding="utf-8")
        src = Path(__file__).resolve().parents[1] / "src"
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in [str(src), env.get("PYTHONPATH", "")] if p
        )
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "tinytest", str(self.root)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("1 failed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
