/**
 * Frontend mirror of the backend FILE_KINDS registry
 * (mav_gss_lib/missions/maveric/files/registry.py).
 *
 * Source of truth for "what does this file kind support" — referenced by
 * the predicates, TX control rendering, restage routing, preview
 * download, and filename extension auto-append.
 *
 * Cross-checked against mission.yml at test time
 * (tests/test_frontend_file_kinds.py).
 */

export type FileKindId = 'image' | 'aii' | 'mag';

export interface FileKindCaps {
  id: FileKindId;
  label: string;            // operator-facing badge text
  cntCmd: string;
  getCmd: string;
  deleteCmd: string;
  captureCmd: string | null;
  /** Mission cmd_ids related to this kind that aren't the standard
   *  cnt/get/delete/capture quartet (e.g. aii_dir, lcd_display). */
  extraCmds: readonly string[];
  /** True only for image — img_get_chunks takes a `destination` arg
   *  (1=full, 2=thumb). AII/MAG do not. */
  hasDestinationArg: boolean;
  /** True only for image — pairs full + thumb leaves under one stem. */
  hasPairing: boolean;
  /** RX-log filter: which cmd_ids belong to this kind family. */
  rxFilter: RegExp;
  /** Extension auto-appended when the operator types a bare filename. */
  extension: string;
  /** MIME used by /api/plugins/files/preview/<filename>?kind=... */
  mediaType: string;
  /** Subsystem nodes that own this kind today. Used as a fallback when
   *  /api/schema doesn't return per-cmd node restrictions. */
  fallbackNodes: readonly string[];
  /** Nodes whose ERR/NACK/FAIL/TIMEOUT packets should be included in this
   *  kind's RX log even when the cmd_id family doesn't match. Empty
   *  means "no error fallback" (predicate matches cmd_id family only).
   *  Image opts in to preserve the legacy isImagingRxPacket behavior;
   *  AII/MAG opt out because errors-from-HLNV/ASTR are ambiguous between
   *  the two file kinds. */
  errorNodes: readonly string[];
  /** Per-cmd override for which file kind's extension to apply to a
   *  filename arg. Default (cmd not present) = use the row's current
   *  kind. Override is needed when an extra command's filename argument
   *  refers to a file of a *different* kind — the canonical case is
   *  AII's `aii_img.filename` which names a JPEG image input, not the
   *  AII output. Without the override, ExtraCmdRow would auto-append
   *  the wrong extension. */
  extraCmdFilenameKind: { readonly [cmdId: string]: FileKindId };
  /** Pre-fill value for the cnt/get/delete filename inputs. Set when
   *  this kind has a canonical singleton filename (AII = `transmit_dir`,
   *  the top-N AI-ranked candidate list). Operator can still type over
   *  it. Image / MAG don't have a canonical default — operator names
   *  every file. */
  defaultFilename?: string;
  /** Operator-facing subtitle rendered next to the section label. Use
   *  to clarify the kind's purpose when "AII" or "MAG" alone isn't
   *  self-explanatory. */
  subtitle?: string;
}

export const FILE_KIND_CAPS: { readonly [K in FileKindId]: FileKindCaps } = {
  image: {
    id: 'image',
    label: 'IMG',
    cntCmd: 'img_cnt_chunks',
    getCmd: 'img_get_chunks',
    deleteCmd: 'img_delete',
    captureCmd: 'cam_capture',
    extraCmds: ['cam_on', 'cam_off', 'lcd_display', 'lcd_on', 'lcd_off', 'lcd_clear'],
    hasDestinationArg: true,
    hasPairing: true,
    rxFilter: /^(img|cam|lcd)_/,
    extension: '.jpg',
    mediaType: 'image/jpeg',
    fallbackNodes: ['HLNV', 'ASTR'],
    errorNodes: ['HLNV', 'ASTR'],
    extraCmdFilenameKind: {},
  },
  aii: {
    id: 'aii',
    label: 'AII',
    // AII = the spacecraft's top-N AI-ranked candidate list, persisted
    // as `transmit_dir.json` per source (HLNV/ASTR). On-board AI
    // (HoloNav / Astroboard) scores recent images for downlink-
    // worthiness; the operator downloads transmit_dir.json to see
    // which images the AI thinks are worth pulling, then stages
    // img_get_chunks for the winners. NOT a directory listing of
    // everything on the spacecraft — just the top candidates.
    cntCmd: 'aii_cnt_chunks',
    getCmd: 'aii_get_chunks',
    deleteCmd: 'aii_delete',
    captureCmd: null,
    // aii_dir → trigger spacecraft to recompute the ranking.
    // aii_img → request AII metadata for one specific image (e.g. why
    //          the AI scored it where it did).
    extraCmds: ['aii_dir', 'aii_img'],
    hasDestinationArg: false,
    hasPairing: false,
    rxFilter: /^aii_/,
    extension: '.json',
    mediaType: 'application/json',
    fallbackNodes: ['HLNV', 'ASTR'],
    errorNodes: [],
    // aii_img.filename names the JPEG that the spacecraft will derive
    // an AII record from — NOT the .json output. Use image extension.
    extraCmdFilenameKind: { aii_img: 'image' },
    // Singleton: AII downlinks are always `transmit_dir.json` per
    // source. Pre-fill so operator never has to retype it.
    defaultFilename: 'transmit_dir',
    subtitle: 'AI candidate list (transmit_dir)',
  },
  mag: {
    id: 'mag',
    label: 'MAG',
    cntCmd: 'mag_cnt_chunks',
    getCmd: 'mag_get_chunks',
    deleteCmd: 'mag_delete',
    // Backend FILE_TRANSPORTS.mag has capture_cmd=None — mag_capture exists
    // as a stage-able command but isn't an "auto-seed-on-capture" hook.
    // Surface it as an extraCmd so the command deck renders a row for it.
    captureCmd: null,
    extraCmds: ['mag_capture', 'mag_kill', 'mag_tlm'],
    hasDestinationArg: false,
    hasPairing: false,
    rxFilter: /^mag_/,
    extension: '.npz',
    mediaType: 'application/octet-stream',
    fallbackNodes: ['HLNV', 'ASTR'],
    errorNodes: [],
    extraCmdFilenameKind: {},
  },
};

export function fileCaps(kind: FileKindId): FileKindCaps {
  return FILE_KIND_CAPS[kind];
}

export function allKinds(): FileKindId[] {
  return ['image', 'aii', 'mag'];
}

/** Every cmd_id the registry references, flat. Used by the backend
 *  guardrail test and by the merged "ALL" filter on the Files page. */
export function allCapsCmdIds(): string[] {
  const out = new Set<string>();
  for (const c of Object.values(FILE_KIND_CAPS)) {
    out.add(c.cntCmd);
    out.add(c.getCmd);
    out.add(c.deleteCmd);
    if (c.captureCmd) out.add(c.captureCmd);
    for (const id of c.extraCmds) out.add(id);
  }
  return [...out].sort();
}
