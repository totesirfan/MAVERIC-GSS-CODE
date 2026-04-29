/**
 * ImagingProvider — root-mounted state for the MAVERIC imaging page.
 *
 * Mission-owned (MAVERIC), mounted at the app root by the platform's
 * MissionProviders wrapper. Subscribes to the `imaging_progress`
 * websocket broadcasts and seeds initial state from
 * /api/plugins/imaging/status so the paired-file view is ready before
 * the Imaging page (or a pop-out) mounts.
 *
 * Why root-level and not inside ImagingPage: the RX socket delivers
 * `imaging_progress` and `on_client_connect` replay messages
 * immediately on connect — a page-local provider would miss anything
 * that fires while the operator is on a different tab. The platform
 * ParametersProvider plays the same root-mount role for live
 * parameter values; this provider mirrors that pattern for imaging
 * progress events.
 *
 * Single-consumer rule: only `ImagingPage.tsx` should call
 * `useImaging()`. It destructures once and passes narrow props to
 * memo'd children.
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react';
import { useRxStatus } from '@/state/rxHooks';
import { fetchImagingStatus } from './helpers';
import { ImagingContext, type ImagingApi } from './ImagingContext';
import type { PairedFile, ImagingTab, FileLeaf } from './types';

interface ImagingProgressMsg {
  type: 'imaging_progress';
  id?: string;
  source?: string | null;
  filename: string;
  received: number;
  total: number | null;
  complete: boolean;
}

function leafMatches(
  leaf: FileLeaf | null | undefined,
  filename: string,
  source: string | null | undefined,
): leaf is FileLeaf {
  if (!leaf || leaf.filename !== filename) return false;
  return source ? leaf.source === source : true;
}

function matchingSide(
  pair: PairedFile,
  filename: string,
  source: string | null | undefined,
): ImagingTab | null {
  if (leafMatches(pair.thumb, filename, source)) return 'thumb';
  if (leafMatches(pair.full, filename, source)) return 'full';
  return null;
}

export function ImagingProvider({ children }: PropsWithChildren) {
  const { subscribeCustom: subscribeRxCustom } = useRxStatus();

  const [files, setFiles] = useState<PairedFile[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [previewTab, setPreviewTab] = useState<ImagingTab>('thumb');
  const [destNode, setDestNode] = useState('');

  // Ref mirror so the broadcast handler reads current files without
  // becoming a dependency and resubscribing on every change.
  const filesRef = useRef<PairedFile[]>([]);
  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  const refetch = useCallback(async () => {
    const fresh = await fetchImagingStatus();
    setFiles(fresh);
    return fresh;
  }, []);

  // Seed initial state. The on_client_connect replay the backend
  // emits for imaging handles the live per-file progress; this
  // REST fetch gives us the paired-file grouping (thumb/full
  // pairing by prefix) that the broadcast alone can't reconstruct.
  useEffect(() => {
    fetchImagingStatus().then(setFiles).catch(() => {});
  }, []);

  useEffect(() => {
    return subscribeRxCustom((msg) => {
      if (msg.type !== 'imaging_progress') return;
      const progress = msg as unknown as ImagingProgressMsg;
      const fn = progress.filename;
      if (!fn) return;
      const source = progress.source ?? null;

      const snapshot = filesRef.current;
      const targetPair = snapshot.find(
        (p) => leafMatches(p.full, fn, source) || leafMatches(p.thumb, fn, source),
      );
      const targetSide = targetPair ? matchingSide(targetPair, fn, source) : null;

      if (targetPair) {
        setFiles((prev) => {
          const idx = prev.findIndex((p) => p.id === targetPair.id);
          if (idx < 0) return prev;
          const pair = prev[idx];
          const nextPair: PairedFile = { ...pair };
          if (leafMatches(pair.full, fn, source)) {
            nextPair.full = {
              ...pair.full,
              received: progress.received,
              total: progress.total ?? pair.full.total,
              complete: progress.complete,
            };
          } else if (leafMatches(pair.thumb, fn, source)) {
            nextPair.thumb = {
              ...pair.thumb,
              received: progress.received,
              total: progress.total ?? pair.thumb.total,
              complete: progress.complete,
            };
          }
          const next = [...prev];
          next[idx] = nextPair;
          return next;
        });
        setSelectedId(targetPair.id);
        if (targetSide) setPreviewTab(targetSide);
      } else {
        fetchImagingStatus().then((fresh) => {
          setFiles(fresh);
          const match = fresh.find(
            (p) => leafMatches(p.full, fn, source) || leafMatches(p.thumb, fn, source),
          );
          if (match) {
            setSelectedId(match.id);
            const side = matchingSide(match, fn, source);
            if (side) setPreviewTab(side);
          }
        });
      }
    });
  }, [subscribeRxCustom]);

  const selected = useMemo(
    () => files.find((f) => f.id === selectedId) ?? null,
    [files, selectedId],
  );
  const previewVersion = [
    selectedId,
    selected?.full?.received ?? '',
    selected?.thumb?.received ?? '',
  ].join(':');

  const api = useMemo<ImagingApi>(
    () => ({
      files,
      selectedId,
      previewTab,
      previewVersion,
      destNode,
      setSelectedId,
      setPreviewTab,
      setDestNode,
      refetch,
    }),
    [files, selectedId, previewTab, previewVersion, destNode, refetch],
  );

  return <ImagingContext.Provider value={api}>{children}</ImagingContext.Provider>;
}
