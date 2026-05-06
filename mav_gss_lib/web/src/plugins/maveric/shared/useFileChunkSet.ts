import { useEffect, useState } from 'react';
import { filesEndpoint } from '../files/helpers';
import type { FileKindId } from './fileKinds';

export interface ChunkSetTarget {
  kind: FileKindId;
  filename: string;
  source: string | null;
  total: number | null;
  /** Parent's view of how many chunks have arrived. Used as a refetch
   *  trigger so the dot grid stays live during an active transfer.
   *  Without this, the hook would only fetch once per (kind, source,
   *  filename) and miss every newly-received chunk. */
  received: number;
}

const EMPTY_SET: ReadonlySet<number> = new Set<number>();

// Module-level dedup of concurrent fetches. When two hook instances
// land on the same `(target, received)` cache key (e.g. ChunkTimeline
// + a missing-ranges hook for the same focused file), they share one
// in-flight Promise + AbortController instead of double-firing
// /chunks. The entry is reference-counted: when the last consumer
// detaches before the fetch settles, the controller is aborted and
// the underlying request is cancelled — otherwise long transfers
// (which fire this effect on every chunk-arrival tick) would leak a
// tail of orphaned in-flight requests.
interface InFlightEntry {
  promise: Promise<Set<number>>;
  ctrl: AbortController;
  consumers: number;
}
const inFlight = new Map<string, InFlightEntry>();

/** Fetches the received-chunk index set for a file via
 *  /api/plugins/files/chunks. Refetches when target identity changes
 *  OR when `received` advances (matching the original imaging
 *  ProgressPanel behavior of refetching on every chunk arrival).
 *  Returns an empty set when the target is null or has no known total.
 *
 *  Guards against the abort-race: with `received` as a dep, active
 *  transfers spawn a fresh fetch on every chunk arrival and abort the
 *  prior one. Without the `alive` flag below, an aborted fetch's
 *  `.catch` could fire AFTER a newer fetch's `.then` and clobber the
 *  newer state with an empty set. */
export function useFileChunkSet(target: ChunkSetTarget | null): Set<number> {
  const [chunks, setChunks] = useState<Set<number>>(() => new Set());
  const id = target ? `${target.kind}|${target.source ?? ''}|${target.filename}` : '';
  const totalKnown = target?.total !== null && target?.total !== undefined;
  const received = target?.received ?? 0;

  useEffect(() => {
    if (!target || !totalKnown) {
      setChunks(new Set());
      return;
    }
    let alive = true;
    const cacheKey = `${id}|r=${received}`;
    let entry = inFlight.get(cacheKey);
    if (!entry) {
      const ctrl = new AbortController();
      const promise = fetch(
        filesEndpoint('chunks', target.kind, target.filename, target.source),
        { signal: ctrl.signal },
      )
        .then(r => r.json() as Promise<{ chunks?: number[] }>)
        .then(data => new Set<number>(data.chunks ?? []))
        .finally(() => {
          // Drop the cache entry on settle so the next tick can re-fetch.
          if (inFlight.get(cacheKey)?.promise === promise) inFlight.delete(cacheKey);
        });
      entry = { promise, ctrl, consumers: 0 };
      inFlight.set(cacheKey, entry);
    }
    entry.consumers += 1;
    const sharedEntry = entry;
    sharedEntry.promise
      .then(set => { if (alive) setChunks(set); })
      .catch(() => {
        // Don't downgrade a previously-fetched non-empty set to empty
        // on a transient network blip or on abort. Two callers share
        // one promise; if one resolves first and updates state, the
        // second's `.catch` (e.g. on abort after the first .then ran)
        // would wipe the chunks the first caller already set. Only
        // clear when we have nothing to keep.
        if (alive) setChunks(prev => prev.size > 0 ? prev : new Set());
      });
    return () => {
      alive = false;
      sharedEntry.consumers -= 1;
      if (sharedEntry.consumers <= 0 && inFlight.get(cacheKey) === sharedEntry) {
        // Last consumer detached before settle — cancel the request
        // so file-switching during an active transfer doesn't accumulate
        // orphan fetches. abort() is a no-op if the fetch already
        // settled, so racing this against the .finally above is safe.
        sharedEntry.ctrl.abort();
        inFlight.delete(cacheKey);
      }
    };
  }, [id, totalKnown, received]); // eslint-disable-line react-hooks/exhaustive-deps

  return chunks as Set<number>;
}

export { EMPTY_SET };
