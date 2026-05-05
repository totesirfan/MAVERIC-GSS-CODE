import { describe, it, expect } from 'vitest';
import { computeMissingRanges } from '../missingRanges';

describe('computeMissingRanges', () => {
  it('returns [] when total is null or zero', () => {
    expect(computeMissingRanges(null, new Set())).toEqual([]);
    expect(computeMissingRanges(0, new Set())).toEqual([]);
  });

  it('returns [] when nothing is missing', () => {
    expect(computeMissingRanges(3, new Set([0, 1, 2]))).toEqual([]);
  });

  it('collapses contiguous gaps into ranges', () => {
    expect(computeMissingRanges(8, new Set([0, 4, 7]))).toEqual([
      { start: 1, end: 3, count: 3 },
      { start: 5, end: 6, count: 2 },
    ]);
  });

  it('handles every-chunk-missing', () => {
    expect(computeMissingRanges(3, new Set())).toEqual([
      { start: 0, end: 2, count: 3 },
    ]);
  });

  it('handles single-chunk gaps', () => {
    expect(computeMissingRanges(5, new Set([0, 1, 3, 4]))).toEqual([
      { start: 2, end: 2, count: 1 },
    ]);
  });
});
