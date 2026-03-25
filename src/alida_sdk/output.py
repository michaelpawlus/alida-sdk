"""Output helpers for JSON/CSV/error output following agent-friendly conventions."""

from __future__ import annotations

import csv
import json
import sys
from contextlib import contextmanager
from typing import IO, Iterator


def emit_json(data: object) -> None:
    """Write JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def emit_error(message: str, code: int = 1) -> None:
    """Write a JSON error to stdout and exit with the given code."""
    print(json.dumps({"error": message, "code": code}))
    raise SystemExit(code)


def emit_csv(
    headers: list[str],
    rows: list[dict[str, str]],
    dest: IO[str] | None = None,
) -> None:
    """Write CSV rows to *dest* (defaults to stdout)."""
    target = dest or sys.stdout
    writer = csv.DictWriter(target, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)


@contextmanager
def output_dest(output_file: str | None) -> Iterator[IO[str]]:
    """Yield a writable file handle: the given path, or stdout."""
    if output_file:
        f = open(output_file, "w")  # noqa: SIM115
        try:
            yield f
        finally:
            f.close()
    else:
        yield sys.stdout
