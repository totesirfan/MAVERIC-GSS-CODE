import type { CommandSchemaItem } from '@/lib/types'

// MAVERIC routing extension on top of the platform CommandSchemaItem.
// Mirrors the Python TypedDict at
// `mav_gss_lib/missions/maveric/schema_types.py::MavericCommandSchemaItem`.
//
// dest/echo/ptype come from CSP-style routing; `nodes` is the
// allowed-dest list used by the destination chooser. None/absent
// means operator-routable (no fixed constraint).
export interface MavericCommandSchemaItem extends CommandSchemaItem {
  dest?: string | null
  echo?: string | null
  ptype?: string | null
  nodes?: string[]
}

export type MavericCommandSchema = Record<string, MavericCommandSchemaItem>
