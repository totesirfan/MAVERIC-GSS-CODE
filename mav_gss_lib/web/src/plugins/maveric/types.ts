import type { CommandSchemaItem } from '@/lib/types'

// Mirror of the Python `HeaderValue = str | int | bool` union from
// `mav_gss_lib/platform/spec/types.py`. Routing fields preserve
// whatever the operator wrote in the YAML command header — symbolic
// names like "LPPM" today, numeric bytes if a future header switches
// to wire-encoded form. The wire mapping happens in the packet codec,
// not in /api/schema, so the TS view must accept the same polymorphism.
export type HeaderValue = string | number | boolean

// MAVERIC routing extension on top of the platform CommandSchemaItem.
// Mirrors the Python TypedDict at
// `mav_gss_lib/missions/maveric/schema_types.py::MavericCommandSchemaItem`.
//
// dest/echo/ptype come from CSP-style routing; `nodes` is the
// allowed-dest list used by the destination chooser. None/absent
// means operator-routable (no fixed constraint).
export interface MavericCommandSchemaItem extends CommandSchemaItem {
  dest?: HeaderValue | null
  echo?: HeaderValue | null
  ptype?: HeaderValue | null
  nodes?: HeaderValue[]
}

export type MavericCommandSchema = Record<string, MavericCommandSchemaItem>
