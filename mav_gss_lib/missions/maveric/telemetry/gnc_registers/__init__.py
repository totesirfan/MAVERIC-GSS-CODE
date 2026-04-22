"""Legacy package — only `GncRegisterStore` remains and is deleted in Task 16.

Schema and handlers moved to ../semantics/gnc_{schema,handlers}.py.
"""
from .store import GncRegisterStore

__all__ = ["GncRegisterStore"]
