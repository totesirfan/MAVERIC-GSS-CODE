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
    const ctrl = new AbortController();
    fetch(filesEndpoint('chunks', target.kind, target.filename, target.source), { signal: ctrl.signal })
      .then(r => r.json())
      .then((data: { chunks?: number[] }) => {
        if (!alive) return;
        setChunks(new Set<number>(data.chunks ?? []));
      })
      .catch(() => {
        // Drop both abort-after-supersede AND post-unmount catches.
        // Real network failures we treat as "no info" — but only when
        // this effect's instance is still the latest one.
        if (!alive || ctrl.signal.aborted) return;
        setChunks(new Set());
      });
    return () => {
      alive = false;
      ctrl.abort();
    };
  }, [id, totalKnown, received]); // eslint-disable-line react-hooks/exhaustive-deps

  return chunks as Set<number>;
}

export { EMPTY_SET };
