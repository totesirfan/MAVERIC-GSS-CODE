/**
 * Root-mounted provider that owns file-chunk state for all kinds.
 *
 * - Subscribes once to /ws/rx via useRxStatus().subscribeCustom (no
 *   parallel WebSocket — would break the shutdown bookkeeping).
 * - Holds image-page selection state inside the provider so the legacy
 *   auto-select-on-incoming-chunk UX is preserved.
 * - Holds aii/mag flat lists; FilesPage owns its own selection.
 * - Debounces per-kind status refetches to 200ms trailing-edge so
 *   high-cadence chunk arrivals don't spam the status endpoint.
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
import { FileChunkCtx, type FileChunkState } from './FileChunkContext';
import { filesEndpoint } from './helpers';
import type {
  FileLeaf,
  FileProgressMessage,
  FlatStatusResponse,
  ImagePair,
  ImageStatusResponse,
  ImagingTab,
} from './types';

function leafMatches(
  leaf: FileLeaf | null | undefined,
  filename: string,
  source: string | null | undefined,
): leaf is FileLeaf {
  if (!leaf || leaf.filename !== filename) return false;
  return source ? leaf.source === source : true;
}

function matchingSide(
  pair: ImagePair,
  filename: string,
  source: string | null | undefined,
): ImagingTab | null {
  if (leafMatches(pair.thumb, filename, source)) return 'thumb';
  if (leafMatches(pair.full, filename, source)) return 'full';
  return null;
}

const REFETCH_DEBOUNCE_MS = 200;

export function FileChunkProvider({ children }: PropsWithChildren) {
  const { subscribeCustom: subscribeRxCustom } = useRxStatus();

  // Image slice (preserves legacy ImagingProvider state shape)
  const [imagePairs, setImagePairs] = useState<ImagePair[]>([]);
  const [imageSelectedId, setImageSelectedId] = useState('');
  const [imagePreviewTab, setImagePreviewTab] = useState<ImagingTab>('thumb');
  const [imageDestNode, setImageDestNode] = useState('');

  // Files slice
  const [aiiFiles, setAiiFiles] = useState<FileLeaf[]>([]);
  const [magFiles, setMagFiles] = useState<FileLeaf[]>([]);

  // Ref mirror so the broadcast handler reads current pairs without
  // becoming a dependency and resubscribing on every change.
  const imagePairsRef = useRef<ImagePair[]>([]);
  useEffect(() => { imagePairsRef.current = imagePairs; }, [imagePairs]);

  // Per-kind debounce timers — 200ms trailing edge.
  const debounceRef = useRef<{ image?: number; aii?: number; mag?: number }>({});

  const refetchImage = useCallback(async (): Promise<ImagePair[]> => {
    const r = await fetch(filesEndpoint('status', 'image'));
    if (!r.ok) return imagePairsRef.current;
    const fresh = ((await r.json()) as ImageStatusResponse).files;
    setImagePairs(fresh);
    return fresh;
  }, []);
  const refetchAii = useCallback(async (): Promise<FileLeaf[]> => {
    const r = await fetch(filesEndpoint('status', 'aii'));
    if (!r.ok) return [];
    const fresh = ((await r.json()) as FlatStatusResponse).files;
    setAiiFiles(fresh);
    return fresh;
  }, []);
  const refetchMag = useCallback(async (): Promise<FileLeaf[]> => {
    const r = await fetch(filesEndpoint('status', 'mag'));
    if (!r.ok) return [];
    const fresh = ((await r.json()) as FlatStatusResponse).files;
    setMagFiles(fresh);
    return fresh;
  }, []);

  const scheduleRefetch = useCallback(
    (kind: 'image' | 'aii' | 'mag') => {
      const fn = kind === 'image' ? refetchImage : kind === 'aii' ? refetchAii : refetchMag;
      const slot = debounceRef.current;
      if (slot[kind]) window.clearTimeout(slot[kind]);
      slot[kind] = window.setTimeout(() => {
        slot[kind] = undefined;
        void fn();
      }, REFETCH_DEBOUNCE_MS);
    },
    [refetchImage, refetchAii, refetchMag],
  );

  // Initial fetch — paired image view requires REST so the broadcast
  // alone (per-leaf) doesn't have enough info to reconstruct pairs.
  useEffect(() => {
    void refetchImage();
    void refetchAii();
    void refetchMag();
    return () => {
      const slot = debounceRef.current;
      for (const k of ['image', 'aii', 'mag'] as const) {
        if (slot[k]) {
          window.clearTimeout(slot[k]);
          slot[k] = undefined;
        }
      }
    };
  }, [refetchImage, refetchAii, refetchMag]);

  // WS subscription — share the existing /ws/rx connection.
  useEffect(() => {
    return subscribeRxCustom((msg) => {
      if (msg.type !== 'file_progress') return;
      const progress = msg as unknown as FileProgressMessage;
      const fn = progress.filename;
      if (!fn) return;
      const source = progress.source ?? null;

      if (progress.kind === 'image') {
        const snapshot = imagePairsRef.current;
        const targetPair = snapshot.find(
          (p) => leafMatches(p.full, fn, source) || leafMatches(p.thumb, fn, source),
        );
        const targetSide = targetPair ? matchingSide(targetPair, fn, source) : null;
        if (targetPair) {
          setImagePairs((prev) => {
            const idx = prev.findIndex((p) => p.id === targetPair.id);
            if (idx < 0) return prev;
            const pair = prev[idx];
            const nextPair: ImagePair = { ...pair };
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
          setImageSelectedId(targetPair.id);
          if (targetSide) setImagePreviewTab(targetSide);
        } else {
          // New pair — refetch to get the paired grouping, then select
          // the matching fresh pair. Skip the debouncer: legacy auto-
          // select fires immediately so the operator sees the active
          // file selected.
          void refetchImage().then((fresh) => {
            const match = fresh.find(
              (p) => leafMatches(p.full, fn, source) || leafMatches(p.thumb, fn, source),
            );
            if (match) {
              setImageSelectedId(match.id);
              const side = matchingSide(match, fn, source);
              if (side) setImagePreviewTab(side);
            }
          });
        }
      } else if (progress.kind === 'aii') {
        scheduleRefetch('aii');
      } else if (progress.kind === 'mag') {
        scheduleRefetch('mag');
      }
    });
  }, [subscribeRxCustom, scheduleRefetch, refetchImage]);

  const selectedImagePair = useMemo(
    () => imagePairs.find((p) => p.id === imageSelectedId) ?? null,
    [imagePairs, imageSelectedId],
  );
  const imagePreviewVersion = [
    imageSelectedId,
    selectedImagePair?.full?.received ?? '',
    selectedImagePair?.thumb?.received ?? '',
  ].join(':');

  const state = useMemo<FileChunkState>(
    () => ({
      files: imagePairs,
      selectedId: imageSelectedId,
      previewTab: imagePreviewTab,
      previewVersion: imagePreviewVersion,
      destNode: imageDestNode,
      setSelectedId: setImageSelectedId,
      setPreviewTab: setImagePreviewTab,
      setDestNode: setImageDestNode,
      refetch: refetchImage,
      aiiFiles,
      magFiles,
      refetchAii,
      refetchMag,
    }),
    [
      imagePairs, imageSelectedId, imagePreviewTab, imagePreviewVersion, imageDestNode,
      refetchImage, aiiFiles, magFiles, refetchAii, refetchMag,
    ],
  );

  return <FileChunkCtx.Provider value={state}>{children}</FileChunkCtx.Provider>;
}
