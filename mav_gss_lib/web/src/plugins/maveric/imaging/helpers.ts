// MAVERIC imaging-panel shared helpers, constants, and types.

import type { PairedFile, FileLeaf, MissingRange } from './types';

export type { PairedFile, FileLeaf, MissingRange };

/** Default chunk size for img_cnt_chunks when the operator leaves it blank. */
export const DEFAULT_CHUNK_SIZE = '150';

/** Default target arg for thumb-first workflow — UI state initializes to this. */
export const DEFAULT_TARGET_ARG = '2';

/** Append `.jpg` if the filename doesn't already end in `.jpg` or `.jpeg`. */
export const withJpg = (s: string): string =>
  /\.jpe?g$/i.test(s) ? s : `${s}.jpg`;

/** Fetch `/api/plugins/imaging/status` and return the paired files array. */
export async function fetchImagingStatus(): Promise<PairedFile[]> {
  try {
    const r = await fetch('/api/plugins/imaging/status');
    if (!r.ok) return [];
    const data = await r.json();
    return (data.files ?? []) as PairedFile[];
  } catch {
    return [];
  }
}

/** Collapse a sorted list of missing chunk indices into contiguous ranges. */
export function computeMissingRanges(
  total: number | null,
  received: Set<number>,
): MissingRange[] {
  if (!total) return [];
  const missing: number[] = [];
  for (let i = 0; i < total; i++) {
    if (!received.has(i)) missing.push(i);
  }
  if (missing.length === 0) return [];
  const ranges: MissingRange[] = [];
  let start = missing[0];
  let end = start;
  for (let i = 1; i < missing.length; i++) {
    if (missing[i] === end + 1) {
      end = missing[i];
    } else {
      ranges.push({ start, end, count: end - start + 1 });
      start = missing[i];
      end = start;
    }
  }
  ranges.push({ start, end, count: end - start + 1 });
  return ranges;
}

/** Format a list of ranges into short labels: [{start:5,end:7},{start:10,end:10}] -> ["5–7","10"] */
export function formatMissingRanges(ranges: MissingRange[]): string[] {
  return ranges.map(r => (r.start === r.end ? `${r.start}` : `${r.start}–${r.end}`));
}
