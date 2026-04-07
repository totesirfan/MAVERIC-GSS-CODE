"""
mav_gss_lib.textutil -- Shared Text Formatting Helpers

Small utilities for turning raw bytes into operator-friendly text.

Author:  Irfan Annuar - USC ISI SERC
"""

_CLEAN_TABLE = bytearray(0xB7 for _ in range(256))  # middle dot
for _b in range(32, 127):
    _CLEAN_TABLE[_b] = _b
_CLEAN_TABLE = bytes(_CLEAN_TABLE)


def clean_text(data: bytes) -> str:
    """Printable ASCII representation with non-printable bytes as middle dot."""
    return data.translate(_CLEAN_TABLE).decode("latin-1")
