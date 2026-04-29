// MAVERIC imaging-panel shared helpers, constants, and types.

import type { PairedFile, FileLeaf, MissingRange } from './types';

export type { PairedFile, FileLeaf, MissingRange };

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

export function imagingFileEndpoint(
  kind: 'chunks' | 'file' | 'preview',
  leaf: Pick<FileLeaf, 'filename' | 'source'>,
): string {
  const params = new URLSearchParams();
  if (leaf.source) params.set('source', leaf.source);
  const query = params.toString();
  return `/api/plugins/imaging/${kind}/${encodeURIComponent(leaf.filename)}${query ? `?${query}` : ''}`;
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
