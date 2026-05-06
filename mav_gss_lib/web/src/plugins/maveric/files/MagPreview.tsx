import { colors } from '@/lib/colors';
import type { FileLeaf } from './types';

interface Props { file: FileLeaf | null }

export function MagPreview({ file }: Props) {
  if (!file) {
    return (
      <div className="p-4 italic text-[11px]" style={{ color: colors.textMuted }}>
        no MAG file selected
      </div>
    );
  }
  // Filename + source + chunk count + chunk_size all already render
  // in the surrounding FocusHeader; this pane is just the "where is
  // it on disk" hint for MAG files (which can't be previewed inline).
  return (
    <div className="flex flex-col h-full p-4 gap-2">
      <div className="text-[11px]" style={{ color: colors.textMuted }}>
        Stored by the ground station under the configured log directory.
      </div>
    </div>
  );
}
