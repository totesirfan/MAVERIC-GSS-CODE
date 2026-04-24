"""Mission HTTP capability — mission-owned FastAPI routers mounted by the server.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter


@dataclass(frozen=True, slots=True)
class HttpOps:
    routers: list[APIRouter] = field(default_factory=list)
