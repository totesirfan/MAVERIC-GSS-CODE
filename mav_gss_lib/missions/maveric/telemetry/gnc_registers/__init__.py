"""GNC register schema, handlers, and snapshot store.

Public API lives at this package level; internals may be reorganized.

Author: Irfan
"""

from .schema import (
    REGISTERS,
    RegisterDef,
    DecodedRegister,
    MODE_NAMES,
    parse_type,
    decode_register,
)
from .handlers import (
    COMMAND_HANDLERS,
    decode_from_cmd,
    GNC_PLANNER_MODE_NAMES,
    # Private-looking symbols exposed because tests/test_maveric_gnc_handlers.py imports them.
    _handle_mtq_get_1,
    _handle_mtq_get_fast,
    _handle_gnc_get_mode,
    _handle_gnc_get_cnts,
    _walk_fast_frame,
)
from .store import GncRegisterStore

__all__ = [
    "REGISTERS", "RegisterDef", "DecodedRegister", "MODE_NAMES", "parse_type",
    "decode_register",
    "COMMAND_HANDLERS", "decode_from_cmd", "GNC_PLANNER_MODE_NAMES",
    "_handle_mtq_get_1", "_handle_mtq_get_fast", "_handle_gnc_get_mode",
    "_handle_gnc_get_cnts", "_walk_fast_frame",
    "GncRegisterStore",
]
