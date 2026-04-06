/**
 * Shared column widths for packet/command lists.
 * Sized to fit longest expected content (e.g., "ASTROBOARD" = 10 chars in mono).
 * All values are Tailwind width classes.
 */

export const col = {
  chevron: 'w-5',       // expand indicator
  num:     'w-10',      // packet/command number
  time:    'w-[72px]',  // HH:MM:SS
  frame:   'w-[76px]',  // ASM+Golay / AX.25
  node:    'w-[84px]',  // ASTROBOARD (10ch mono)
  ptype:   'w-[52px]',  // badge: icon + "CMD"
  flags:   'w-[76px]',  // CRC + UL + DUP badges
  size:    'w-12',      // "1234B"
  grip:    'w-[22px]',  // drag handle
  actions: 'w-[60px]',  // buttons
} as const
