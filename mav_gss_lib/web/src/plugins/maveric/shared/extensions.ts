import { fileCaps, type FileKindId } from './fileKinds';

/** Append `caps.extension` if `s` doesn't already end in it (case-insensitive).
 *  Image kind also accepts `.jpeg` as already-suffixed. */
export function withExtension(s: string, kind: FileKindId): string {
  const trimmed = s;
  if (kind === 'image') {
    return /\.jpe?g$/i.test(trimmed) ? trimmed : `${trimmed}.jpg`;
  }
  const ext = fileCaps(kind).extension;
  const re = new RegExp(`\\${ext}$`, 'i');
  return re.test(trimmed) ? trimmed : `${trimmed}${ext}`;
}

/** Legacy alias preserved for imaging callsites. */
export const withJpg = (s: string): string => withExtension(s, 'image');
