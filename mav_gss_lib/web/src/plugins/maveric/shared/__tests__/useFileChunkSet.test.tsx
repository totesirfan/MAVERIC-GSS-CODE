import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useFileChunkSet } from '../useFileChunkSet';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body: unknown) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(body) } as unknown as Response);
}

describe('useFileChunkSet', () => {
  it('returns empty set when file is null', () => {
    const { result } = renderHook(() => useFileChunkSet(null));
    expect(result.current.size).toBe(0);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('fetches chunks for the file and exposes them as a Set', async () => {
    fetchMock.mockReturnValueOnce(jsonResponse({ chunks: [0, 2, 5] }));
    const { result } = renderHook(() =>
      useFileChunkSet({ kind: 'aii', filename: 'foo.json', source: 'HLNV', total: 6, received: 3 }),
    );
    await waitFor(() => expect(result.current.size).toBe(3));
    expect(result.current.has(0)).toBe(true);
    expect(result.current.has(2)).toBe(true);
    expect(result.current.has(5)).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/plugins/files/chunks/foo.json?kind=aii&source=HLNV'),
      expect.objectContaining({ signal: expect.anything() }),
    );
  });

  it('returns empty set when fetch fails', async () => {
    fetchMock.mockReturnValueOnce(Promise.reject(new Error('boom')));
    const { result } = renderHook(() =>
      useFileChunkSet({ kind: 'mag', filename: 'm.npz', source: 'ASTR', total: 4, received: 0 }),
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(result.current.size).toBe(0);
  });

  it('skips fetch when total is null', () => {
    const { result } = renderHook(() =>
      useFileChunkSet({ kind: 'aii', filename: 'x.json', source: 'HLNV', total: null, received: 0 }),
    );
    expect(result.current.size).toBe(0);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('refetches when received advances during an active transfer', async () => {
    fetchMock.mockReturnValueOnce(jsonResponse({ chunks: [0] }));
    const target1 = { kind: 'aii' as const, filename: 'foo.json', source: 'HLNV', total: 4, received: 1 };
    const { result, rerender } = renderHook(
      (t: typeof target1) => useFileChunkSet(t),
      { initialProps: target1 },
    );
    await waitFor(() => expect(result.current.size).toBe(1));

    fetchMock.mockReturnValueOnce(jsonResponse({ chunks: [0, 1, 2] }));
    rerender({ ...target1, received: 3 });
    await waitFor(() => expect(result.current.size).toBe(3));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('does not clobber state with an empty set when an in-flight fetch is aborted', async () => {
    // Arrange a slow first fetch that we will abort by re-rendering, and
    // a fast second fetch that succeeds. The aborted fetch's rejection
    // must NOT overwrite the second fetch's chunks.
    let resolveFirst!: (value: unknown) => void;
    fetchMock.mockReturnValueOnce(new Promise(r => { resolveFirst = r; }));
    fetchMock.mockReturnValueOnce(jsonResponse({ chunks: [0, 1, 2, 3] }));

    const target1 = { kind: 'aii' as const, filename: 'foo.json', source: 'HLNV', total: 4, received: 1 };
    const { result, rerender } = renderHook(
      (t: typeof target1) => useFileChunkSet(t),
      { initialProps: target1 },
    );

    // Before first fetch resolves, rerender with new received → aborts first.
    rerender({ ...target1, received: 4 });
    // Second fetch resolves with the full set.
    await waitFor(() => expect(result.current.size).toBe(4));
    // Now resolve the first (aborted) fetch with what would be stale data.
    resolveFirst({ ok: true, json: () => Promise.resolve({ chunks: [0] }) });
    await new Promise(r => setTimeout(r, 0));
    // State must still reflect the second fetch.
    expect(result.current.size).toBe(4);
  });
});
