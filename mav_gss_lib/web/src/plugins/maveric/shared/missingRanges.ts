export interface MissingRange {
  start: number;
  end: number;
  count: number;
}

/** Collapse a set of received chunk indices into the contiguous ranges
 *  of missing indices (suitable for staging chunk re-requests). */
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
