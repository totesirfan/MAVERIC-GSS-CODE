/**
 * Shared column widths for TX queue items.
 * RX column widths are defined by the mission adapter via packet_list_columns().
 * These TX widths are kept in sync with MAVERIC's RX column sizes.
 * All values are Tailwind width classes.
 */

export const col = {
  chevron: 'w-5',       // expand indicator
  num:     'w-9',       // packet/command number
  time:    'w-[68px]',  // HH:MM:SS
  frame:   'w-[72px]',  // ASM+Golay / AX.25
  node:    'w-[52px]',  // ASTR/HLNV (4ch mono)
  ptype:   'w-[52px]',  // badge: icon + "CMD"
  flags:   'w-[72px]',  // CRC + UL + DUP badges
  size:    'w-10',      // "1234B"
  grip:    'w-[22px]',  // drag handle
  actions: 'w-[60px]',  // buttons
} as const
