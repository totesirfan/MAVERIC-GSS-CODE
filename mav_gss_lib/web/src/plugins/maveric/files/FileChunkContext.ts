import { createContext, useContext } from 'react';
import type { FileLeaf, ImagePair, ImagingTab } from './types';

/**
 * Image-page slice — preserves legacy ImagingProvider auto-select UX.
 *
 * ``refetch`` returns the fresh pair list so existing call sites that
 * do ``const fresh = await refetch(); fresh.find(...)`` keep working
 * (see ImagingPage.tsx delete flow).
 */
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

/**
 * Files-page slice — flat lists for AII + Mag, no provider-held selection.
 */
export interface FileChunkApi {
  aiiFiles: FileLeaf[];
  magFiles: FileLeaf[];
  refetchAii: () => Promise<FileLeaf[]>;
  refetchMag: () => Promise<FileLeaf[]>;
}

export interface FileChunkState extends ImageFilesApi {
  aiiFiles: FileLeaf[];
  magFiles: FileLeaf[];
  refetchAii: () => Promise<FileLeaf[]>;
  refetchMag: () => Promise<FileLeaf[]>;
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
    aiiFiles: v.aiiFiles,
    magFiles: v.magFiles,
    refetchAii: v.refetchAii,
    refetchMag: v.refetchMag,
  };
}
