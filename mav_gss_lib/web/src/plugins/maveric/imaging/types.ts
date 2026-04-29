/**
 * MAVERIC imaging — paired-file model types.
 *
 * The GSS treats every captured image as a logical pair of a full-size
 * JPEG and a thumbnail. The pair is derived from a configurable prefix
 * convention (`imaging.thumb_prefix` in mission config). When the prefix
 * is empty, every file appears as an unpaired single-file entry with
 * `thumb: null`. When the prefix is set, every pair always has BOTH
 * sides populated (real or placeholder) — the backend's
 * `paired_status` method handles the speculation.
 *
 * TX queue items and other shared types live in @/lib/types — import
 * directly from there; do not re-declare them here.
 */

/** Matches the wire DTO shape from /api/plugins/imaging/status. */
export interface FileLeaf {
  /** Stable id for this physical image, including source when known. */
  id: string;
  /** Source node that produced this file, e.g. "HLNV" or "ASTR". */
  source: string | null;
  /** Actual filename on disk, e.g. "limb_003.jpg" or "thumb_limb_003.jpg" */
  filename: string;
  /** Total chunk count (null until img_cnt_chunks or cam_capture returns) */
  total: number | null;
  /** COUNT of chunks received so far — not the indices. Chunk indices are
   *  fetched separately via /api/plugins/imaging/chunks/<filename>. */
  received: number;
  /** True if fully reassembled */
  complete: boolean;
  /** Bytes per chunk as reported by the OBC; null until a chunk arrives. */
  chunk_size: number | null;
}

export interface PairedFile {
  /** Stable source-qualified identity for the logical image pair. */
  id: string;
  /** Source node for the pair, e.g. "HLNV" or "ASTR". */
  source: string | null;
  /** Shared filename identity within one source — the full filename. */
  stem: string;
  /** Full-size image leaf. Null only when prefix is unset AND this entry is thumb-only. */
  full: FileLeaf | null;
  /** Thumbnail leaf. Null only when prefix is unset; otherwise always populated
   *  (real leaf or placeholder with total=null). */
  thumb: FileLeaf | null;
  /** Wall-clock millis of the most recent state change (set_total or
   *  chunk arrival) across either side. Null if neither side has ever
   *  been touched. Backend sorts `/api/plugins/imaging/status` newest
   *  first using this field; frontend treats it as read-only metadata. */
  last_activity_ms: number | null;
}

/** Which side of a paired file the UI is currently focused on */
export type ImagingTab = 'thumb' | 'full';

/** Contiguous range of missing chunks, used by click-to-request and the
 *  `computeMissingRanges` helper. */
export interface MissingRange {
  start: number;
  end: number;
  count: number;
}
