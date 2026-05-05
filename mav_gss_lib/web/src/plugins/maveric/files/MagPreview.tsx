import { colors } from '@/lib/colors';
import { filesEndpoint } from './helpers';
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
      <div className="flex items-center">
        <span className="flex-1 text-[11px]" style={{ color: colors.textPrimary }}>{file.filename}</span>
        <a
          href={filesEndpoint('preview', file.kind, file.filename, file.source)}
          download={file.filename}
          className="text-[10px] hover:underline"
          style={{
            color: file.complete ? colors.active : colors.textMuted,
            pointerEvents: file.complete ? 'auto' : 'none',
            opacity: file.complete ? 1 : 0.5,
          }}
          title={file.complete ? 'Download MAG (.npz)' : 'Download enabled when complete'}
        >
          DOWNLOAD
        </a>
      </div>
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
