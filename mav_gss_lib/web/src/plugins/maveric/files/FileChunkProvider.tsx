/**
 * Root-mounted provider that owns file-chunk state for all kinds.
 *
 * - Subscribes once to /ws/rx via useRxStatus().subscribeCustom (no
 *   parallel WebSocket — would break the shutdown bookkeeping).
 * - Holds image-pair selection state inside the provider so the
 *   auto-select-on-incoming-chunk UX is preserved across remounts.
 * - Holds aii/mag flat lists; consumers (DownlinkPreview) own their
 *   own per-kind focus state.
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
import { FileChunkCtx, type FileChunkState, type FlatKind } from './FileChunkContext';
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

function shouldAutoSelect(currentId: string, currentList: FileLeaf[]): boolean {
  if (!currentId) return true;
  const current = currentList.find(f => f.id === currentId);
  if (!current) return true; // currently-selected file vanished
  return current.complete;   // skip-when-mid-read
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

  // Per-kind selection (AII / MAG). Lives in the provider so auto-select
  // continues to work when the Files page is unmounted.
  const [aiiSelectedId, setAiiSelectedId] = useState('');
  const [magSelectedId, setMagSelectedId] = useState('');
  const [lastTouchedFlatKind, setLastTouchedFlatKind] = useState<FlatKind | null>(null);

  // Refs for auto-select decisions inside the WS handler. Refs avoid
  // re-subscribing the WS handler every time selection or files change.
  const aiiSelectedRef = useRef('');
  const magSelectedRef = useRef('');
  const aiiFilesRef = useRef<FileLeaf[]>([]);
  const magFilesRef = useRef<FileLeaf[]>([]);
  useEffect(() => { aiiSelectedRef.current = aiiSelectedId; }, [aiiSelectedId]);
  useEffect(() => { magSelectedRef.current = magSelectedId; }, [magSelectedId]);
  useEffect(() => { aiiFilesRef.current = aiiFiles; }, [aiiFiles]);
  useEffect(() => { magFilesRef.current = magFiles; }, [magFiles]);

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
    void (async () => { await refetchImage(); })();
    void (async () => { await refetchAii(); })();
    void (async () => { await refetchMag(); })();
    const slot = debounceRef.current;
    return () => {
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
        const src = progress.source ?? null;
        const known = aiiFilesRef.current.some(f => f.filename === fn && f.source === src);
        if (known) {
          // Routine progress on a known file — debounce status refetch so
          // high-cadence chunks don't spam the endpoint. Also evaluate
          // auto-select against the current ref so an empty selection
          // (e.g. initial mount that loaded files via /status, then
          // progress arrives) gets a selection on the first packet,
          // matching imaging behavior.
          scheduleRefetch('aii');
          if (shouldAutoSelect(aiiSelectedRef.current, aiiFilesRef.current)) {
            const match = aiiFilesRef.current.find(f => f.filename === fn && f.source === src);
            if (match) {
              setAiiSelectedId(match.id);
              setLastTouchedFlatKind('aii');
            }
          }
        } else {
          // First arrival: refetch immediately so we can auto-select.
          // Pass `fresh` (post-refetch state) to shouldAutoSelect, NOT
          // aiiFilesRef.current — the ref still holds the pre-refetch
          // state inside this .then callback, which would mis-classify
          // a vanished file as still present and incorrectly skip
          // auto-select.
          void refetchAii().then((fresh) => {
            if (!shouldAutoSelect(aiiSelectedRef.current, fresh)) return;
            const match = fresh.find(f => f.filename === fn && f.source === src) ?? fresh[0];
            if (match) {
              setAiiSelectedId(match.id);
              setLastTouchedFlatKind('aii');
            }
          });
        }
      } else if (progress.kind === 'mag') {
        const src = progress.source ?? null;
        const known = magFilesRef.current.some(f => f.filename === fn && f.source === src);
        if (known) {
          scheduleRefetch('mag');
          if (shouldAutoSelect(magSelectedRef.current, magFilesRef.current)) {
            const match = magFilesRef.current.find(f => f.filename === fn && f.source === src);
            if (match) {
              setMagSelectedId(match.id);
              setLastTouchedFlatKind('mag');
            }
          }
        } else {
          void refetchMag().then((fresh) => {
            if (!shouldAutoSelect(magSelectedRef.current, fresh)) return;
            const match = fresh.find(f => f.filename === fn && f.source === src) ?? fresh[0];
            if (match) {
              setMagSelectedId(match.id);
              setLastTouchedFlatKind('mag');
            }
          });
        }
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
      aii: {
        files: aiiFiles,
        selectedId: aiiSelectedId,
        setSelectedId: setAiiSelectedId,
        refetch: refetchAii,
      },
      mag: {
        files: magFiles,
        selectedId: magSelectedId,
        setSelectedId: setMagSelectedId,
        refetch: refetchMag,
      },
      lastTouchedFlatKind,
      setLastTouchedFlatKind,
    }),
    [
      imagePairs, imageSelectedId, imagePreviewTab, imagePreviewVersion, imageDestNode, refetchImage,
      aiiFiles, aiiSelectedId, refetchAii,
      magFiles, magSelectedId, refetchMag,
      lastTouchedFlatKind,
    ],
  );

  return <FileChunkCtx.Provider value={state}>{children}</FileChunkCtx.Provider>;
}
