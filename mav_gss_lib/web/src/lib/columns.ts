/**
 * Shared column widths for TX queue items.
 * RX and TX schemas are provided by the active MissionSpec.
 * All values are Tailwind width classes.
 */

export const col = {
  chevron: 'w-5',       // expand indicator
  num:     'w-9',       // packet/command number
  time:    'w-[68px]',  // HH:MM:SS
  frame:   'w-[72px]',  // ASM+Golay / AX.25
  node:    'w-[52px]',  // compact mission label
  ptype:   'w-[52px]',  // compact mission badge
  flags:   'w-[72px]',  // CRC + UL + DUP badges
  size:    'w-10',      // "1234B"
  grip:    'w-[22px]',  // drag handle
  actions: 'w-[60px]',  // buttons
} as const
