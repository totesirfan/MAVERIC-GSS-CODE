"""Per-format repair and validation primitives.

Adapters call ``partial_repair(path)`` after every chunk write and
``on_complete(path)`` once on completion. Each primitive is a pure
function on a path; adding a new primitive means adding a function
here and referencing it from a ``FileTransportConfig`` row.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import json
from typing import Any


def jpeg_eoi_repair(path: str) -> None:
    """Append the JPEG EOI marker (``\\xff\\xd9``) if the file starts with
    SOI (``\\xff\\xd8``) and doesn't already end with EOI.

    Lets partial JPEG transfers be viewable mid-downlink. No-op if the
    file isn't recognisably a JPEG or already ends with EOI.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(2)
            if head != b"\xff\xd8":
                return
            f.seek(0, 2)
            size = f.tell()
            if size < 2:
                return
            f.seek(size - 2)
            tail = f.read(2)
            if tail == b"\xff\xd9":
                return
        with open(path, "ab") as f:
            f.write(b"\xff\xd9")
    except OSError:
        pass


def no_repair(path: str) -> None:
    """Identity hook for kinds with no partial-repair semantics."""
    return None


def json_validate(path: str) -> dict[str, Any]:
    """Return ``{'valid': bool}`` based on whether the file parses as JSON."""
    try:
        with open(path, "rb") as f:
            json.loads(f.read())
        return {"valid": True}
    except (OSError, json.JSONDecodeError, ValueError):
        return {"valid": False}


def no_validate(path: str) -> dict[str, Any]:
    """Identity hook for kinds with no on-complete validation."""
    return {}
