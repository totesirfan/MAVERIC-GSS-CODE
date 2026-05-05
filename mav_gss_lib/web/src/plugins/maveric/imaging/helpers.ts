// MAVERIC imaging-panel shared helpers, constants, and types.
//
// Routes through the new /api/plugins/files surface under the hood (kind=image).
//
// `PairedFile` is the legacy name for `ImagePair` and lives in
// `./types`. Everything else lives in `../files/types`.

import { filesEndpoint } from '../files/helpers';
import type { ImageStatusResponse } from '../files/types';
import type { FileLeaf, PairedFile } from './types';

export type { PairedFile, FileLeaf };
export { computeMissingRanges, type MissingRange } from '../shared/missingRanges';
export { withJpg } from '../shared/extensions';

export async function fetchImagingStatus(): Promise<PairedFile[]> {
  try {
    const r = await fetch(filesEndpoint('status', 'image'));
    if (!r.ok) return [];
    const data = (await r.json()) as ImageStatusResponse;
    return data.files ?? [];
  } catch {
    return [];
  }
}

export function imagingFileEndpoint(
  action: 'chunks' | 'file' | 'preview',
  leaf: Pick<FileLeaf, 'filename' | 'source'>,
): string {
  return filesEndpoint(action, 'image', leaf.filename, leaf.source);
}
