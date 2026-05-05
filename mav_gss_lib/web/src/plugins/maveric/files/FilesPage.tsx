/**
 * Files page — combined AII + MAG dashboard. Built on the same
 * primitives as Imaging (ChunkGrid, MissingRangePill, StageRow,
 * RxLogPanel) plus the FILE_KIND_CAPS registry. AII and MAG do not
 * have thumb/full pairing or a destination arg; image files live on
 * the dedicated Imaging page.
 */
import { useEffect, useMemo, useState } from 'react';
import { ConfirmDialog } from '@/components/shared/dialogs/ConfirmDialog';
import { showToast } from '@/components/shared/overlays/StatusToast';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
import { GssInput } from '@/components/ui/gss-input';
import { colors } from '@/lib/colors';
import { useColumnDefs } from '@/state/sessionHooks';
import { composeRxColumns } from '@/lib/columns';
import { usePluginServices } from '@/hooks/usePluginServices';
import { useFlatFiles, useFileChunks } from './FileChunkContext';
import { FilesTable } from './FilesTable';
import { FilesProgressGrid } from './FilesProgressGrid';
import { FilesTxControls } from './FilesTxControls';
import { FilesRxLogPanel } from './FilesRxLogPanel';
import { JsonPreview } from './JsonPreview';
import { MagPreview } from './MagPreview';
import { filesEndpoint } from './helpers';
import { fileCaps, type FileKindId } from '../shared/fileKinds';
import type { MissingRange } from '../shared/missingRanges';
import type { FileLeaf } from './types';

type FilterKind = 'all' | 'aii' | 'mag';

const FILTER_OPTIONS: ReadonlyArray<{ id: FilterKind; label: string }> = [
  { id: 'all', label: 'ALL' },
  { id: 'aii', label: 'AII' },
  { id: 'mag', label: 'MAG' },
];

export default function FilesPage() {
  const aii = useFlatFiles('aii');
  const mag = useFlatFiles('mag');
  const { lastTouchedFlatKind, setLastTouchedFlatKind } = useFileChunks();
  const { packets, queueCommand, txConnected, fetchSchema } = usePluginServices();

  const [filter, setFilter] = useState<FilterKind>('all');
  const [search, setSearch] = useState('');
  const [bulkSelected, setBulkSelected] = useState<Set<string>>(new Set());
  const [deleteOne, setDeleteOne] = useState<FileLeaf | null>(null);
  const [deleteMany, setDeleteMany] = useState<FileLeaf[] | null>(null);
  const [aiiDestNode, setAiiDestNode] = useState('');
  const [magDestNode, setMagDestNode] = useState('');
  const [schema, setSchema] = useState<Record<string, Record<string, unknown>> | null>(null);

  useEffect(() => { fetchSchema().then(setSchema).catch(() => {}); }, [fetchSchema]);

  // Column defs for the embedded RX log
  const { defs: ctxDefs } = useColumnDefs();
  const rxColumns = ctxDefs?.rx ?? composeRxColumns([]);

  // Merged + filtered + searched view of all flat files
  const allFiles = useMemo<FileLeaf[]>(() => {
    const merged = [...aii.files, ...mag.files];
    merged.sort((a, b) => (b.last_activity_ms ?? 0) - (a.last_activity_ms ?? 0));
    return merged;
  }, [aii.files, mag.files]);

  const filtered = useMemo(() => {
    let rows = filter === 'all' ? allFiles : allFiles.filter(f => f.kind === filter);
    const q = search.trim().toLowerCase();
    if (q) rows = rows.filter(f => f.filename.toLowerCase().includes(q));
    return rows;
  }, [allFiles, filter, search]);

  // Prune bulk selection to currently-visible rows whenever the visible
  // set changes. Without this, the "DELETE N" button can over-count
  // (selections from a prior filter linger in state but won't be
  // deleted because the action is scoped to `filtered`).
  useEffect(() => {
    setBulkSelected(prev => {
      if (prev.size === 0) return prev;
      const visible = new Set(filtered.map(f => f.id));
      const next = new Set<string>();
      for (const id of prev) if (visible.has(id)) next.add(id);
      return next.size === prev.size ? prev : next;
    });
  }, [filtered]);

  // Selection: provider holds per-kind selection AND lastTouchedFlatKind.
  // For filter='all' we prefer the kind that was most recently touched
  // (by click in this page or by auto-select on arrival in the provider)
  // — but if its selection no longer resolves (e.g. the file was just
  // deleted), fall back to the other kind so the right-pane doesn't
  // suddenly blank out while the operator still has a valid selection
  // on the other side.
  const candidateSelection = useMemo<FileLeaf | null>(() => {
    if (filter === 'aii') return aii.files.find(f => f.id === aii.selectedId) ?? null;
    if (filter === 'mag') return mag.files.find(f => f.id === mag.selectedId) ?? null;
    // 'all'
    const aHit = aii.files.find(f => f.id === aii.selectedId) ?? null;
    const mHit = mag.files.find(f => f.id === mag.selectedId) ?? null;
    if (lastTouchedFlatKind === 'aii') return aHit ?? mHit;
    if (lastTouchedFlatKind === 'mag') return mHit ?? aHit;
    return aHit ?? mHit;
  }, [filter, aii, mag, lastTouchedFlatKind]);

  // Right-pane only renders a selection that is currently visible in the
  // table. Matches the original FilesPage behavior (selected derived from
  // filtered) so a search that hides the selected row also blanks the
  // preview rather than leaving a "ghost" selection visible.
  const activeSelection = useMemo<FileLeaf | null>(() => {
    if (!candidateSelection) return null;
    return filtered.some(f => f.id === candidateSelection.id) ? candidateSelection : null;
  }, [candidateSelection, filtered]);

  const handleSelectRow = (id: string) => {
    const row = filtered.find(f => f.id === id);
    if (!row) return;
    if (row.kind === 'aii') {
      aii.setSelectedId(id);
      setLastTouchedFlatKind('aii');
    } else if (row.kind === 'mag') {
      mag.setSelectedId(id);
      setLastTouchedFlatKind('mag');
    }
  };

  const toggleBulk = (id: string) => {
    setBulkSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };
  const toggleBulkAll = () => {
    if (bulkSelected.size === filtered.length && filtered.length > 0) setBulkSelected(new Set());
    else setBulkSelected(new Set(filtered.map(f => f.id)));
  };

  const performDelete = async (rows: FileLeaf[]) => {
    const results = await Promise.allSettled(
      rows.map(async f => {
        const r = await fetch(filesEndpoint('file', f.kind, f.filename, f.source), { method: 'DELETE' });
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${f.filename}`);
        return f;
      }),
    );
    // Always refetch — partial successes need the table to reflect what was actually deleted.
    await Promise.all([aii.refetch(), mag.refetch()]);
    setBulkSelected(new Set());
    setDeleteOne(null);
    setDeleteMany(null);
    const okCount = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected') as PromiseRejectedResult[];
    if (failed.length === 0) {
      showToast(`Deleted ${okCount} file${okCount === 1 ? '' : 's'}`, 'success', 'tx');
    } else if (okCount === 0) {
      showToast(`Failed to delete ${failed.length} file${failed.length === 1 ? '' : 's'}: ${(failed[0].reason as Error).message}`, 'error', 'tx');
    } else {
      showToast(`Deleted ${okCount}, failed ${failed.length}: ${(failed[0].reason as Error).message}`, 'error', 'tx');
    }
  };

  const handleRestageRange = (file: FileLeaf, range: MissingRange) => {
    const caps = fileCaps(file.kind as FileKindId);
    if (!file.source) {
      showToast('No source on file — cannot route', 'error', 'tx');
      return;
    }
    // mission.yml requires chunk_size on *_get_chunks. Use the file's
    // own chunk_size so restage matches the original transfer; fall back
    // to '150' (matches imaging default) if the store didn't record one.
    const chunkSizeArg = file.chunk_size != null ? String(file.chunk_size) : '150';
    queueCommand({
      cmd_id: caps.getCmd,
      args: {
        filename: file.filename,
        start_chunk: String(range.start),
        num_chunks: String(range.count),
        chunk_size: chunkSizeArg,
      },
      packet: { dest: file.source },
    });
    showToast(`Staged ${range.count} chunk${range.count === 1 ? '' : 's'}`, 'success', 'tx');
  };

  const visibleKinds: FileKindId[] = filter === 'all' ? ['aii', 'mag']
                                    : [filter as FileKindId];

  // Empty-state copy
  const hiddenCount = allFiles.length - filtered.length;
  const emptyMessage = filtered.length > 0
    ? null
    : (filter === 'all' && allFiles.length === 0)
      ? 'no files yet'
      : (hiddenCount > 0)
        ? `no ${filter === 'all' ? 'matching' : filter.toUpperCase()} files — ${hiddenCount} hidden by filter${search ? '/search' : ''}`
        : 'no files yet';

  return (
    <div className="flex flex-col h-full" style={{ background: colors.bgApp, color: colors.textPrimary }}>
      <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: colors.borderSubtle }}>
        <span className="text-[10px]" style={{ color: colors.textMuted }}>FILTER:</span>
        {FILTER_OPTIONS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setFilter(id)}
            className="text-[10px] px-2 py-[2px] border"
            style={{
              borderColor: filter === id ? colors.active : colors.borderStrong,
              color: filter === id ? colors.active : colors.textMuted,
            }}
          >
            {label}
          </button>
        ))}
        <GssInput
          className="ml-2 w-[220px] text-[11px] font-mono"
          placeholder="search filename..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {bulkSelected.size > 0 && (
          <button
            className="ml-2 text-[10px] px-2 py-[2px] border"
            style={{ borderColor: colors.danger, color: colors.danger }}
            onClick={() => setDeleteMany(filtered.filter(f => bulkSelected.has(f.id)))}
          >
            DELETE {bulkSelected.size}
          </button>
        )}
        <span className="text-[10px] ml-auto" style={{ color: colors.textMuted }}>
          {filtered.length} file(s)
        </span>
      </div>

      <ResizablePanelGroup orientation="horizontal" className="flex-1">
        <ResizablePanel defaultSize={42} minSize={25}>
          <div className="flex flex-col gap-3 h-full min-w-0 p-3">
            <div className="flex-1 min-h-0 overflow-auto">
              {filtered.length > 0 ? (
                <FilesTable
                  files={filtered}
                  selectedId={activeSelection?.id ?? null}
                  onSelect={handleSelectRow}
                  onDelete={(f) => setDeleteOne(f)}
                  selectedIds={bulkSelected}
                  onToggleSelected={toggleBulk}
                  onToggleSelectAll={toggleBulkAll}
                />
              ) : (
                <div className="px-2 py-4 italic text-[11px]" style={{ color: colors.textMuted }}>
                  {emptyMessage}
                </div>
              )}
            </div>
            <div className="h-[180px] shrink-0">
              <FilesRxLogPanel filter={filter} packets={packets} columns={rxColumns} />
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle
          withHandle
          className="mx-1 w-1 rounded-full bg-transparent hover:bg-[#222222] data-[resize-handle-active]:bg-[#30C8E0] transition-colors"
        />
        <ResizablePanel defaultSize={58} minSize={25}>
          <div className="flex flex-col gap-3 h-full min-w-0 p-3">
            <FilesProgressGrid selected={activeSelection} onRestageRange={handleRestageRange} />
            <div className="flex-1 min-h-0 flex gap-3">
              <div className="flex-1 min-w-0 flex flex-col gap-3">
                {visibleKinds.map(k => (
                  <FilesTxControls
                    key={k}
                    kind={k}
                    selected={activeSelection?.kind === k ? activeSelection : null}
                    knownFiles={k === 'aii' ? aii.files : mag.files}
                    destNode={k === 'aii' ? aiiDestNode : magDestNode}
                    onDestNodeChange={k === 'aii' ? setAiiDestNode : setMagDestNode}
                    schema={schema}
                    txConnected={txConnected}
                    queueCommand={queueCommand}
                  />
                ))}
              </div>
              <div className="flex-1 min-w-0 border rounded-md overflow-hidden" style={{ borderColor: colors.borderSubtle }}>
                {activeSelection?.kind === 'aii'
                  ? <JsonPreview file={activeSelection} />
                  : <MagPreview file={activeSelection} />}
              </div>
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>

      {deleteOne && (
        <ConfirmDialog
          open
          title="Delete file?"
          detail={`Remove ${deleteOne.filename}? This cannot be undone.`}
          variant="destructive"
          onConfirm={() => performDelete([deleteOne])}
          onCancel={() => setDeleteOne(null)}
        />
      )}
      {deleteMany && (
        <ConfirmDialog
          open
          title={`Delete ${deleteMany.length} files?`}
          detail={`${deleteMany.map(f => f.filename).join(', ')} will be removed from disk. This cannot be undone.`}
          variant="destructive"
          onConfirm={() => performDelete(deleteMany)}
          onCancel={() => setDeleteMany(null)}
        />
      )}
    </div>
  );
}
