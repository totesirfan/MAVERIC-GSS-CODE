"""File-based session logging for the ground station.

Two thin subclasses of `_BaseLog`, one per direction:

    session.py — SessionLog (RX) — downlink packets
    tx.py      — TXLog (TX)      — uplink commands
    _base.py   — shared I/O, background writer thread, rotation, rename

Each produces a JSONL file (machine-readable) and a text file
(human-readable) under `<log_dir>/json/` and `<log_dir>/text/` sharing the
same session banner and entry-separator style.

Author:  Irfan Annuar - USC ISI SERC
"""

from .session import SessionLog
from .tx import TXLog

__all__ = ["SessionLog", "TXLog"]
