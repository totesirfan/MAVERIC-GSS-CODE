import { createContext, useContext } from 'react';
import type { FileLeaf, ImagePair, ImagingTab } from './types';

export interface ImageFilesApi {
  files: ImagePair[];
  selectedId: string;
  previewTab: ImagingTab;
  previewVersion: string;
  destNode: string;
  setSelectedId: (id: string) => void;
  setPreviewTab: (tab: ImagingTab) => void;
  setDestNode: (node: string) => void;
  refetch: () => Promise<ImagePair[]>;
}

export interface FlatFilesApi {
  /** Flat list for one kind (aii or mag). */
  files: FileLeaf[];
  /** Provider-held selection so auto-select-on-progress works without
   *  the page being mounted. */
  selectedId: string;
  setSelectedId: (id: string) => void;
  refetch: () => Promise<FileLeaf[]>;
}

export type FlatKind = 'aii' | 'mag';

export interface FileChunkApi {
  aii: FlatFilesApi;
  mag: FlatFilesApi;
  /** Which flat kind was last interacted with — set on auto-select
   *  arrival in the provider AND on row-click in the page. Drives the
   *  Files page selection display when the user filter is 'all'. */
  lastTouchedFlatKind: FlatKind | null;
  setLastTouchedFlatKind: (k: FlatKind) => void;
}

export interface FileChunkState extends ImageFilesApi {
  aii: FlatFilesApi;
  mag: FlatFilesApi;
  lastTouchedFlatKind: FlatKind | null;
  setLastTouchedFlatKind: (k: FlatKind) => void;
}

export const FileChunkCtx = createContext<FileChunkState | null>(null);

export function useImageFiles(): ImageFilesApi {
  const v = useContext(FileChunkCtx);
  if (!v) throw new Error('useImageFiles must be used inside FileChunkProvider');
  return {
    files: v.files,
    selectedId: v.selectedId,
    previewTab: v.previewTab,
    previewVersion: v.previewVersion,
    destNode: v.destNode,
    setSelectedId: v.setSelectedId,
    setPreviewTab: v.setPreviewTab,
    setDestNode: v.setDestNode,
    refetch: v.refetch,
  };
}

export function useFileChunks(): FileChunkApi {
  const v = useContext(FileChunkCtx);
  if (!v) throw new Error('useFileChunks must be used inside FileChunkProvider');
  return {
    aii: v.aii,
    mag: v.mag,
    lastTouchedFlatKind: v.lastTouchedFlatKind,
    setLastTouchedFlatKind: v.setLastTouchedFlatKind,
  };
}

export function useFlatFiles(kind: FlatKind): FlatFilesApi {
  const all = useFileChunks();
  return all[kind];
}
