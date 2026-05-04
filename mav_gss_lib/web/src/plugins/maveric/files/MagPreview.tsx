/**
 * Magnetometer NVG file: no in-browser preview. .nvg is binary sensor
 * data; operator processes it offline from the ground-station storage
 * location.
 */

import { colors } from '@/lib/colors';
import type { FileLeaf } from './types';

interface Props { file: FileLeaf | null }

export function MagPreview({ file }: Props) {
  if (!file) {
    return (
      <div className="p-4 italic text-[11px]" style={{ color: colors.textMuted }}>
        select a file to download
      </div>
    );
  }
  return (
    <div className="flex flex-col h-full p-4 gap-2">
      <div className="text-[11px]" style={{ color: colors.textPrimary }}>{file.filename}</div>
      <div className="text-[10px]" style={{ color: colors.textMuted }}>
        {file.source ?? '—'} · {file.complete ? 'complete' : `${file.received}/${file.total ?? '—'}`}
        {file.chunk_size != null && ` · chunk ${file.chunk_size} B`}
      </div>
      <div className="text-[10px] mt-4" style={{ color: colors.textMuted }}>
        Stored by the ground station under the configured log directory.
      </div>
    </div>
  );
}
