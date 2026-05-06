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
// (e.g. ChunkTimeline + PrimaryActionBlock for the same focused file)
// land on the same `(target, received)` cache key on the same render
// pass, they share one in-flight Promise instead of double-firing the
// /chunks endpoint. Entries are removed when the fetch settles, so the
// cache cannot grow unbounded — it's effectively a per-tick coalesce.
const inFlight = new Map<string, Promise<Set<number>>>();

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
    // Cache key includes `received` so a chunk arrival invalidates
    // the previous in-flight result for that file — same trigger that
    // already drives the effect.
    const cacheKey = `${id}|r=${received}`;
    let promise = inFlight.get(cacheKey);
    if (!promise) {
      const ctrl = new AbortController();
      promise = fetch(
        filesEndpoint('chunks', target.kind, target.filename, target.source),
        { signal: ctrl.signal },
      )
        .then(r => r.json() as Promise<{ chunks?: number[] }>)
        .then(data => new Set<number>(data.chunks ?? []))
        .finally(() => {
          // Drop the cache entry on settle so the next hook tick can
          // re-fetch when `received` advances or the operator forces
          // a refresh.
          if (inFlight.get(cacheKey) === promise) inFlight.delete(cacheKey);
        });
      inFlight.set(cacheKey, promise);
    }
    promise
      .then(set => { if (alive) setChunks(set); })
      .catch(() => {
        // Don't downgrade a previously-fetched non-empty set to empty
        // on a transient network blip. Two callers share one promise;
        // if one resolves first and updates state, the second's `.catch`
        // (which fires when the same shared promise rejects on a later
        // tick after the parse step) would wipe the chunks the first
        // caller already set. Only clear when we have nothing to keep.
        if (alive) setChunks(prev => prev.size > 0 ? prev : new Set());
      });
    return () => { alive = false; };
  }, [id, totalKnown, received]); // eslint-disable-line react-hooks/exhaustive-deps

  return chunks as Set<number>;
}

export { EMPTY_SET };
