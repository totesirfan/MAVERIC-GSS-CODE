/**
 * Regression: when a file_progress message arrives for a previously-
 * unknown image pair, the provider must refetch /status and
 * auto-select the matching pair. Equivalent to the legacy
 * ImagingProvider behavior (ImagingProvider.tsx ~line 135 in v1).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { FileChunkProvider } from '../FileChunkProvider';
import { useImageFiles, useFlatFiles } from '../FileChunkContext';

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

describe('FileChunkProvider — aii/mag selection', () => {
  it('auto-selects a brand-new aii file when no current selection (single immediate refetch)', async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse({ files: [] }))    // image (initial)
      .mockReturnValueOnce(jsonResponse({ files: [] }))    // aii (initial)
      .mockReturnValueOnce(jsonResponse({ files: [] }));   // mag (initial)

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <FileChunkProvider>{children}</FileChunkProvider>
    );
    const { result } = renderHook(() => useFlatFiles('aii'), { wrapper });

    await act(async () => { await Promise.resolve(); });
    expect(result.current.selectedId).toBe('');
    fetchMock.mockClear();

    // First arrival: file is unknown → provider should refetch
    // immediately AND auto-select. No debounce involved.
    fetchMock.mockReturnValueOnce(jsonResponse({
      files: [{
        id: 'aii/HLNV/foo.json', kind: 'aii', source: 'HLNV',
        filename: 'foo.json', received: 1, total: 4, complete: false, chunk_size: 50,
        last_activity_ms: 1, valid: null,
      }],
    }));

    await act(async () => {
      for (const fn of listeners) {
        fn({
          type: 'file_progress', kind: 'aii', source: 'HLNV',
          id: 'aii/HLNV/foo.json', filename: 'foo.json',
          received: 1, total: 4, complete: false,
        });
      }
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.selectedId).toBe('aii/HLNV/foo.json');
    // Exactly one status fetch — not double-fetched via scheduleRefetch.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('selects a known aii file on first progress when current selection is empty', async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse({ files: [] }))    // image (initial)
      .mockReturnValueOnce(jsonResponse({                  // aii (initial — file already present)
        files: [{
          id: 'aii/HLNV/known.json', kind: 'aii', source: 'HLNV',
          filename: 'known.json', received: 1, total: 4, complete: false, chunk_size: 50,
          last_activity_ms: 1, valid: null,
        }],
      }))
      .mockReturnValueOnce(jsonResponse({ files: [] }));   // mag (initial)

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <FileChunkProvider>{children}</FileChunkProvider>
    );
    const { result } = renderHook(() => useFlatFiles('aii'), { wrapper });
    await act(async () => { await Promise.resolve(); });
    // Selection starts empty even though one aii file is in the list.
    expect(result.current.selectedId).toBe('');

    // Progress arrives for the known file. shouldAutoSelect(empty, list)
    // returns true → known branch must call setAiiSelectedId.
    await act(async () => {
      for (const fn of listeners) {
        fn({
          type: 'file_progress', kind: 'aii', source: 'HLNV',
          id: 'aii/HLNV/known.json', filename: 'known.json',
          received: 2, total: 4, complete: false,
        });
      }
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.selectedId).toBe('aii/HLNV/known.json');
  });

  it('debounces routine progress on a known aii file (no immediate refetch)', async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse({ files: [] }))
      .mockReturnValueOnce(jsonResponse({
        files: [{
          id: 'aii/HLNV/foo.json', kind: 'aii', source: 'HLNV',
          filename: 'foo.json', received: 1, total: 4, complete: false, chunk_size: 50,
          last_activity_ms: 1, valid: null,
        }],
      }))
      .mockReturnValueOnce(jsonResponse({ files: [] }));

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <FileChunkProvider>{children}</FileChunkProvider>
    );
    renderHook(() => useFlatFiles('aii'), { wrapper });
    await act(async () => { await Promise.resolve(); });
    fetchMock.mockClear();

    // Progress on the known file. Should NOT trigger an immediate fetch;
    // only the debounced refetch should fire after ~200 ms.
    await act(async () => {
      for (const fn of listeners) {
        fn({
          type: 'file_progress', kind: 'aii', source: 'HLNV',
          id: 'aii/HLNV/foo.json', filename: 'foo.json',
          received: 2, total: 4, complete: false,
        });
      }
      await Promise.resolve();
    });
    expect(fetchMock).toHaveBeenCalledTimes(0);

    // After debounce window, exactly one fetch.
    fetchMock.mockReturnValueOnce(jsonResponse({ files: [] }));
    await act(async () => { await new Promise(r => setTimeout(r, 250)); });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does NOT yank selection when current aii selection is incomplete', async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse({ files: [] }))
      .mockReturnValueOnce(jsonResponse({
        files: [{
          id: 'aii/HLNV/reading.json', kind: 'aii', source: 'HLNV',
          filename: 'reading.json', received: 2, total: 8, complete: false, chunk_size: 50,
          last_activity_ms: 1, valid: null,
        }],
      }))
      .mockReturnValueOnce(jsonResponse({ files: [] }));

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <FileChunkProvider>{children}</FileChunkProvider>
    );
    const { result } = renderHook(() => useFlatFiles('aii'), { wrapper });

    await act(async () => { await Promise.resolve(); });
    // Operator clicked into reading.json:
    act(() => result.current.setSelectedId('aii/HLNV/reading.json'));
    expect(result.current.selectedId).toBe('aii/HLNV/reading.json');

    // A new aii file arrives. Current selection is incomplete → keep it.
    fetchMock.mockReturnValueOnce(jsonResponse({
      files: [
        {
          id: 'aii/HLNV/reading.json', kind: 'aii', source: 'HLNV',
          filename: 'reading.json', received: 2, total: 8, complete: false, chunk_size: 50,
          last_activity_ms: 1, valid: null,
        },
        {
          id: 'aii/HLNV/new.json', kind: 'aii', source: 'HLNV',
          filename: 'new.json', received: 1, total: 4, complete: false, chunk_size: 50,
          last_activity_ms: 2, valid: null,
        },
      ],
    }));

    await act(async () => {
      for (const fn of listeners) {
        fn({
          type: 'file_progress', kind: 'aii', source: 'HLNV',
          id: 'aii/HLNV/new.json', filename: 'new.json',
          received: 1, total: 4, complete: false,
        });
      }
      await Promise.resolve();
      await Promise.resolve();
    });

    // Selection stays where the operator parked it.
    expect(result.current.selectedId).toBe('aii/HLNV/reading.json');
  });
});
