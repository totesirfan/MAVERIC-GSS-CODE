"""File-based JSONL event logging for the ground station.

One writer owns the session stream:

    session.py — SessionLog, the shared RX/TX/audit JSONL event stream
    _base.py   — shared I/O, background writer thread, rotation, rename,
                 ``session_id`` (file stem) stamped onto every record

JSONL records use the unified envelope (`event_id`, `event_kind`,
`session_id`, `ts_ms`, `ts_iso`, `seq`, `v`, `mission_id`, `operator`,
`station`) so SQL ingest sees one schema across RX and TX. The platform
builds records in ``mav_gss_lib.platform.log_records``; the writers here are
format-agnostic — they just persist whatever envelope the platform hands
them.

Session files live under ``<log_dir>/json/`` as
``session_<ts>_<station>_<op>.jsonl``.

Author:  Irfan Annuar - USC ISI SERC
"""

from .session import SessionLog

__all__ = ["SessionLog"]
