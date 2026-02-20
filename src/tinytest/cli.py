"""Command line entry point: python -m tinytest [path ...]."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .reporter import ConsoleReporter
from .runner import Runner

__all__ = ["main"]

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tinytest", description="Find and run test_* functions."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="files or folders to search (default: current folder)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print one line per test"
    )
    parser.add_argument(
        "-k", dest="keyword", help="only run tests whose name contains KEYWORD"
    )
    parser.add_argument(
        "-x", "--exitfirst", action="store_true", help="stop after the first failure"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    args = build_parser().parse_args(argv)
    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for path in missing:
            print(f"tinytest: no such file or folder: {path}", file=sys.stderr)
        return EXIT_USAGE

    reporter = ConsoleReporter(verbose=args.verbose)
    runner = Runner(reporter, keyword=args.keyword, fail_fast=args.exitfirst)
    summary = runner.run_paths(paths)
    return EXIT_OK if summary.ok else EXIT_FAILED
