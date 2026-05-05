import { useState } from 'react';
import { Grid3x3, ChevronDown, Trash2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { colors } from '@/lib/colors';
import { SourcePill } from '../shared/SourcePill';
import { ChunkGrid } from '../shared/ChunkGrid';
import { MissingRangePill } from '../shared/MissingRangePill';
import { useFileChunkSet } from '../shared/useFileChunkSet';
import { computeMissingRanges, type MissingRange } from '../shared/missingRanges';
import { type PairedFile, type FileLeaf } from './helpers';

type Side = 'thumb' | 'full';

interface ProgressPanelProps {
  files: PairedFile[];
  selected: PairedFile | null;
  onSelect: (id: string) => void;
  /** Delete every real leaf in the selected pair. Placeholder leaves
   *  (total === null) are skipped — there's no file on disk to delete. */
  onDelete: (leaves: FileLeaf[]) => void;
  /** Stage contiguous re-request commands for a specific side. */
  onStageRerequest: (side: Side, leaf: FileLeaf, ranges: MissingRange[]) => void;
}

/**
 * File selector + stacked per-side progress rows with clickable missing
 * chunks. Auto-routes target per grid: thumb grid stages with thumb
 * filename, full grid stages with full filename. Route (HLNV/ASTR)
 * respects whatever the operator has set globally — not auto-overridden.
 */
export function ProgressPanel({
  files,
  selected,
  onSelect,
  onDelete,
  onStageRerequest,
}: ProgressPanelProps) {
  const [pickerOpen, setPickerOpen] = useState(false);

  return (
    <div
      className="rounded-md border overflow-hidden shrink-0"
      style={{
        borderColor: colors.borderSubtle,
        backgroundColor: colors.bgPanel,
        boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
      }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b"
        style={{
          borderColor: colors.borderSubtle,
          minHeight: 34,
          paddingTop: 6,
          paddingBottom: 6,
        }}
      >
        <Grid3x3 className="size-3.5" style={{ color: colors.dim }} />
        <span
          className="font-bold uppercase"
          style={{
            color: colors.value,
            fontSize: 14,
            letterSpacing: '0.02em',
          }}
        >
          Progress
        </span>
        <div className="flex-1" />
        {files.length > 0 && (
          <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
            <PopoverTrigger
              className="flex items-center gap-1.5 border rounded px-2 py-0.5 text-[11px] font-mono text-fg hover:bg-white/[0.04] outline-none transition-colors"
              style={{ borderColor: colors.borderSubtle }}
            >
              <SourcePill source={selected?.source} />
              <span className="max-w-[220px] truncate">
                {selected?.stem ?? 'Select file'}
              </span>
              <ChevronDown className="size-3" style={{ color: colors.dim }} />
            </PopoverTrigger>
            <PopoverContent align="end" className="p-0 w-[320px]">
              <Command>
                <CommandInput placeholder="Search filename..." className="h-8 text-[11px]" />
                <CommandList>
                  <CommandEmpty className="py-4 text-center text-[11px]" style={{ color: colors.dim }}>
                    No files
                  </CommandEmpty>
                  <CommandGroup>
                    {files.map(p => (
                      <CommandItem
                        key={p.id}
                        value={`${p.source ?? ''} ${p.stem}`}
                        onSelect={() => {
                          onSelect(p.id);
                          setPickerOpen(false);
                        }}
                        className="text-[11px] font-mono gap-2"
                      >
                        <SourcePill source={p.source} />
                        <span className="flex-1 truncate">{p.stem}</span>
                        <LeafState leaf={p.thumb} label="thumb" />
                        <LeafState leaf={p.full} label="full" />
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        )}
        {selected && (() => {
          const realLeaves: FileLeaf[] = [];
          if (selected.full && selected.full.total !== null) realLeaves.push(selected.full);
          if (selected.thumb && selected.thumb.total !== null) realLeaves.push(selected.thumb);
          if (realLeaves.length === 0) return null;
          return (
            <button
              onClick={() => onDelete(realLeaves)}
              className="p-1 rounded border hover:bg-white/[0.04]"
              style={{ borderColor: colors.borderSubtle }}
              title={`Delete ${realLeaves.map((leaf) => leaf.id).join(' + ')}`}
            >
              <Trash2 className="size-3" style={{ color: colors.danger }} />
            </button>
          );
        })()}
      </div>

      {selected ? (
        <div className="px-4 py-3 space-y-4">
          {selected.thumb && (
            <ProgressRow side="thumb" leaf={selected.thumb} onStageRerequest={onStageRerequest} />
          )}
          {selected.full && (
            <ProgressRow side="full" leaf={selected.full} onStageRerequest={onStageRerequest} />
          )}
        </div>
      ) : (
        <div className="px-3 py-3 text-[11px]" style={{ color: colors.dim }}>
          {files.length === 0 ? 'No active transfers' : 'Select a file to view progress'}
        </div>
      )}
    </div>
  );
}

function LeafState({ leaf, label }: { leaf: FileLeaf | null; label: string }) {
  if (!leaf) return null;
  const complete = leaf.total !== null && leaf.received === leaf.total;
  const stateText =
    leaf.total === null
      ? `${label}: ?`
      : complete
      ? `${label} ✓`
      : `${label} ${leaf.received}/${leaf.total}`;
  return (
    <span
      className="text-[10px] ml-2"
      style={{ color: complete ? colors.success : colors.dim }}
    >
      {stateText}
    </span>
  );
}

function ProgressRow({
  side,
  leaf,
  onStageRerequest,
}: {
  side: Side;
  leaf: FileLeaf;
  onStageRerequest: ProgressPanelProps['onStageRerequest'];
}) {
  const chunkSet = useFileChunkSet(
    leaf.total !== null
      ? { kind: 'image', filename: leaf.filename, source: leaf.source, total: leaf.total, received: leaf.received }
      : null,
  );
  const ranges = computeMissingRanges(leaf.total, chunkSet);
  const total = leaf.total ?? 0;
  const pct = total > 0 ? Math.round((leaf.received / total) * 100) : 0;

  if (leaf.total === null) {
    return (
      <div>
        <div className="text-[10px] uppercase tracking-wider font-bold mb-1" style={{ color: colors.dim }}>
          {side}
        </div>
        <div className="text-[11px]" style={{ color: colors.dim }}>
          Not counted
        </div>
      </div>
    );
  }

  const handleRestage = (range: MissingRange) => onStageRerequest(side, leaf, [range]);
  const handleStageAll = () => onStageRerequest(side, leaf, ranges);

  return (
    <div>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: colors.dim }}>
          {side}
        </span>
        <span className="text-[11px] font-semibold font-mono" style={{ color: colors.value }}>
          {leaf.received} / {total}
        </span>
        <span className="text-[11px]" style={{ color: colors.dim }}>
          ({pct}%)
        </span>
        <span className="text-[10px] font-mono" style={{ color: colors.dim }}>
          · {leaf.chunk_size ?? '?'} B/chunk
        </span>
        <div className="flex-1" />
        <MissingRangePill received={leaf.received} total={total} ranges={ranges} onClick={handleStageAll} />
      </div>
      <ChunkGrid total={total} chunkSet={chunkSet} onRestageRange={handleRestage} />
    </div>
  );
}
