// SVG constants for EPS flow diagram drops + bus-bat link.
//
// Copy to mav_gss_lib/web/src/plugins/maveric/eps/live/svg.ts as-is. The
// preview's flow drops rely on exact geometry (cell y-extent = 40, arrowhead
// at y=32→40) and the dash/offset ratio is locked:
//   stroke-dasharray: "5 3"       (pattern sum = 8)
//   stroke-dashoffset: -16        (2 × pattern sum for a seamless loop)
// Do not tweak one without recomputing the other.

export const DROP_VIEWBOX = "0 0 22 40";

// Two-path pattern: "flow" (animated dashed line, 0..34) + "head" (arrowhead
// at 32..40). Used by FlowSourceDrops (down) and FlowLoadDrops (up).
export const DROP_ACTIVE = {
  flow: "M11,0 L11,34",
  head: "M4,32 L11,40 L18,32",
} as const;

// Single-path muted line, no arrowhead, full cell height.
export const DROP_IDLE = {
  flow: "M11,0 L11,40",
} as const;

// Bus↔battery horizontal link geometry inside .bus-core. Width comes from
// the .bat-link container; the SVG itself just draws a centerline.
export const BAT_LINK_VIEWBOX = "0 0 40 12";
export const BAT_LINK_PATH = "M0,6 L40,6";

// Animation tokens — consume as stroke-dasharray / stroke-dashoffset only
// when the parent element has state class "on" / "active" / "charge" /
// "discharge". Rails are always animated (class "rail").
export const FLOW_DASH_ARRAY = "5 3";
export const FLOW_DASH_OFFSET_END = -16;    // keyframe terminal offset
export const FLOW_DASH_DURATION_MS = 900;

// Stroke widths by role.
export const STROKE = {
  flowActive: 1.5,
  flowIdle:   1.0,
  head:       1.5,
  link:       1.5,
} as const;
