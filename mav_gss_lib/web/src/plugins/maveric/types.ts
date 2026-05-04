import type { CommandSchemaItem } from '@/lib/types'

// MAVERIC routing extension on top of the platform CommandSchemaItem.
// Mirrors the Python TypedDict at
// `mav_gss_lib/missions/maveric/schema_types.py::MavericCommandSchemaItem`.
//
// dest/echo/ptype come from CSP-style routing; `nodes` is the
// allowed-dest list used by the destination chooser. None/absent
// means operator-routable (no fixed constraint).
//
// Schema invariant: routing values are ALWAYS symbolic node / ptype
// NAMES ("LPPM", "CMD"...), never numeric wire bytes — the MAVERIC
// schema producer normalizes via `_resolve_node_value` /
// `_resolve_ptype_value` before emitting. Numeric polymorphism stays
// inside the packet codec at encode time and does NOT reach
// /api/schema. The TxBuilder filter therefore can compare directly
// to the operator's selected node-name string.
export interface MavericCommandSchemaItem extends CommandSchemaItem {
  dest?: string | null
  echo?: string | null
  ptype?: string | null
  nodes?: string[]
}

export type MavericCommandSchema = Record<string, MavericCommandSchemaItem>
