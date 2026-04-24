"""Mission-neutral rendering contracts .

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Cell:
    value: str | int | float | bool | None
    tone: str | None = None
    badge: bool = False
    tooltip: str | None = None
    monospace: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "tone": self.tone,
            "badge": self.badge,
            "tooltip": self.tooltip,
            "monospace": self.monospace,
        }


@dataclass(frozen=True, slots=True)
class ColumnDef:
    id: str
    label: str
    width: str | None = None
    flex: bool = False
    align: str | None = None
    hide_if_all: list[Any] = field(default_factory=list)
    # `toggle` names a shared-frontend view-toggle id (e.g. "showFrame",
    # "showEcho"). The platform passes the opaque string through; the
    # frontend renderer decides what it means.
    toggle: str | None = None

    @classmethod
    def from_dict(cls, col: dict[str, Any]) -> "ColumnDef":
        return cls(
            id=str(col.get("id", "")),
            label=str(col.get("label", "")),
            width=col.get("width"),
            flex=bool(col.get("flex", False)),
            align=col.get("align"),
            hide_if_all=list(col.get("hide_if_all", [])),
            toggle=col.get("toggle"),
        )

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "label": self.label}
        if self.width is not None:
            out["width"] = self.width
        if self.flex:
            out["flex"] = True
        if self.align is not None:
            out["align"] = self.align
        if self.hide_if_all:
            out["hide_if_all"] = list(self.hide_if_all)
        if self.toggle is not None:
            out["toggle"] = self.toggle
        return out


@dataclass(frozen=True, slots=True)
class DetailBlock:
    kind: str
    label: str
    fields: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "label": self.label, "fields": list(self.fields)}


@dataclass(frozen=True, slots=True)
class IntegrityBlock:
    kind: str
    label: str
    scope: str
    ok: bool | None
    received: str | None = None
    computed: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "scope": self.scope,
            "ok": self.ok,
            "received": self.received,
            "computed": self.computed,
        }


@dataclass(frozen=True, slots=True)
class PacketRendering:
    columns: list[ColumnDef]
    row: dict[str, Cell]
    detail_blocks: list[DetailBlock] = field(default_factory=list)
    protocol_blocks: list[DetailBlock] = field(default_factory=list)
    integrity_blocks: list[IntegrityBlock] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "columns": [c.to_json() for c in self.columns],
            "row": {k: v.to_json() for k, v in self.row.items()},
            "detail_blocks": [b.to_json() for b in self.detail_blocks],
            "protocol_blocks": [b.to_json() for b in self.protocol_blocks],
            "integrity_blocks": [b.to_json() for b in self.integrity_blocks],
        }
