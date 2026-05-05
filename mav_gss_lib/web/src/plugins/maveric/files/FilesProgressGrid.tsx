import { Grid3x3 } from 'lucide-react';
import { ChunkGrid } from '../shared/ChunkGrid';
import { MissingRangePill } from '../shared/MissingRangePill';
import { useFileChunkSet } from '../shared/useFileChunkSet';
import { computeMissingRanges, type MissingRange } from '../shared/missingRanges';
import { SourcePill } from '../shared/SourcePill';
import { colors } from '@/lib/colors';
import type { FileLeaf } from './types';

interface FilesProgressGridProps {
  selected: FileLeaf | null;
  onRestageRange: (file: FileLeaf, range: MissingRange) => void;
}

export function FilesProgressGrid({ selected, onRestageRange }: FilesProgressGridProps) {
  const chunkSet = useFileChunkSet(
    selected && selected.total !== null
      ? { kind: selected.kind, filename: selected.filename, source: selected.source, total: selected.total, received: selected.received }
      : null,
  );
  const total = selected?.total ?? 0;
  const ranges = computeMissingRanges(selected?.total ?? null, chunkSet);
  const pct = total > 0 && selected ? Math.round((selected.received / total) * 100) : 0;

  return (
    <div
      className="rounded-md border overflow-hidden shrink-0"
      style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel, boxShadow: '0 1px 3px rgba(0,0,0,0.4)' }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <Grid3x3 className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
          Progress
        </span>
        {selected && (
          <>
            <SourcePill source={selected.source} />
            <span className="text-[11px] font-mono truncate max-w-[260px]" style={{ color: colors.textPrimary }}>
              {selected.filename}
            </span>
          </>
        )}
      </div>
      {selected ? (
        selected.total === null ? (
          <div className="px-4 py-3 text-[11px]" style={{ color: colors.dim }}>Not counted</div>
        ) : (
          <div className="px-4 py-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold font-mono" style={{ color: colors.value }}>
                {selected.received} / {total}
              </span>
              <span className="text-[11px]" style={{ color: colors.dim }}>({pct}%)</span>
              <div className="flex-1" />
              <MissingRangePill
                received={selected.received}
                total={total}
                ranges={ranges}
                onClick={() => ranges.forEach(r => onRestageRange(selected, r))}
              />
            </div>
            <ChunkGrid total={total} chunkSet={chunkSet} onRestageRange={(r) => onRestageRange(selected, r)} />
          </div>
        )
      ) : (
        <div className="px-3 py-3 text-[11px]" style={{ color: colors.dim }}>Select a file to view progress</div>
      )}
    </div>
  );
}
