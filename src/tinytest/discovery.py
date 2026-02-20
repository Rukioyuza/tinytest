"""Finding test files and collecting test functions from them."""

from __future__ import annotations

import importlib.util
import inspect
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

__all__ = ["TestFile", "TestItem", "collect_tests", "find_test_files", "load_module"]

IGNORED_DIRS = {"__pycache__", "build", "dist", "node_modules", "venv"}


@dataclass(frozen=True)
class TestItem:
    """A single test function."""

    name: str
    func: Callable[[], object]
    path: Path

    @property
    def test_id(self) -> str:
        return f"{self.path.as_posix()}::{self.name}"


@dataclass
class TestFile:
    """A loaded test file and the tests found in it."""

    path: Path
    module: ModuleType | None = None
    tests: list[TestItem] = field(default_factory=list)
    error: BaseException | None = None


def _ignored(path: Path) -> bool:
    return any(part.startswith(".") or part in IGNORED_DIRS for part in path.parts)


def find_test_files(root: Path) -> list[Path]:
    """Return test files under root, sorted by path.

    A file passed directly is always used, whatever its name.
    """
    if root.is_file():
        return [root]
    found = []
    for path in root.rglob("test_*.py"):
        if not _ignored(path.relative_to(root).parent):
            found.append(path)
    return sorted(found)


def _module_name(path: Path) -> str:
    cleaned = re.sub(r"\W", "_", str(path.resolve().with_suffix("")))
    return f"tinytest_{cleaned}"


def load_module(path: Path) -> ModuleType:
    """Import a test file by path.

    The file's folder is added to sys.path so tests can import helper
    modules that sit next to them.
    """
    folder = str(path.resolve().parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    name = _module_name(path)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def collect_tests(module: ModuleType, path: Path) -> list[TestItem]:
    """Return the test_* functions defined in module, in source order."""
    funcs = [
        obj
        for name, obj in vars(module).items()
        if name.startswith("test_")
        and inspect.isfunction(obj)
        and obj.__module__ == module.__name__
    ]
    funcs.sort(key=lambda f: f.__code__.co_firstlineno)
    return [TestItem(f.__name__, f, path) for f in funcs]


def load_test_file(path: Path) -> TestFile:
    """Load a test file, recording an import error instead of raising."""
    test_file = TestFile(path)
    try:
        test_file.module = load_module(path)
    except Exception as exc:  # noqa: BLE001 - reported to the user
        test_file.error = exc
        return test_file
    test_file.tests = collect_tests(test_file.module, path)
    return test_file
