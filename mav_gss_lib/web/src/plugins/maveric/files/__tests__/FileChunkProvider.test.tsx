/**
 * Regression: when a file_progress message arrives for a previously-
 * unknown image pair, the provider must refetch /status and
 * auto-select the matching pair. Equivalent to the legacy
 * ImagingProvider behavior (ImagingProvider.tsx ~line 135 in v1).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { FileChunkProvider } from '../FileChunkProvider';
import { useImageFiles } from '../FileChunkContext';

type Listener = (msg: Record<string, unknown>) => void;

const listeners = new Set<Listener>();

vi.mock('@/state/rxHooks', () => ({
  useRxStatus: () => ({
    subscribeCustom: (fn: Listener) => {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  }),
}));

const fetchMock = vi.fn();
beforeEach(() => {
  listeners.clear();
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

describe('FileChunkProvider — image auto-select on new pair', () => {
  it('selects the fresh pair when a file_progress arrives for an unknown filename', async () => {
    // First fetch (initial mount): empty image status, empty aii, empty mag.
    fetchMock
      .mockReturnValueOnce(jsonResponse({ files: [] }))    // image
      .mockReturnValueOnce(jsonResponse({ files: [] }))    // aii
      .mockReturnValueOnce(jsonResponse({ files: [] }));   // mag

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <FileChunkProvider>{children}</FileChunkProvider>
    );
    const { result } = renderHook(() => useImageFiles(), { wrapper });

    // Wait for initial fetches to flush.
    await act(async () => { await Promise.resolve(); });
    expect(result.current.selectedId).toBe('');

    // Second fetch (reaction to file_progress): returns the new pair.
    fetchMock.mockReturnValueOnce(jsonResponse({
      files: [{
        id: 'image/HLNV/capture.jpg',
        kind: 'image',
        source: 'HLNV',
        stem: 'capture.jpg',
        full: {
          id: 'image/HLNV/capture.jpg', kind: 'image', source: 'HLNV',
          filename: 'capture.jpg', received: 1, total: 10,
          complete: false, chunk_size: 200,
        },
        thumb: null,
        last_activity_ms: 123,
      }],
    }));

    // Fire the WS message that references the brand-new pair.
    await act(async () => {
      for (const fn of listeners) {
        fn({
          type: 'file_progress', kind: 'image', source: 'HLNV',
          id: 'image/HLNV/capture.jpg', filename: 'capture.jpg',
          received: 1, total: 10, complete: false,
        });
      }
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.selectedId).toBe('image/HLNV/capture.jpg');
    expect(result.current.previewTab).toBe('full');
  });
});
