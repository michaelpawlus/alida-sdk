"""Output helpers for JSON/error output following agent-friendly conventions."""

import json
import sys


def emit_json(data: object) -> None:
    """Write JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def emit_error(message: str, code: int = 1) -> None:
    """Write a JSON error to stdout and exit with the given code."""
    print(json.dumps({"error": message, "code": code}))
    raise SystemExit(code)
