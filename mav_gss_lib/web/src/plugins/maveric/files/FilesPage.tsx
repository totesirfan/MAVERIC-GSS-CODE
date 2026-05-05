/**
 * Files page — combined AII + MAG dashboard. Built on the same
 * primitives as Imaging (ChunkGrid, MissingRangePill, StageRow,
 * RxLogPanel, QueuePanel) plus the FILE_KIND_CAPS registry. AII and
 * MAG do not have thumb/full pairing or a destination arg; image files
 * live on the dedicated Imaging page.
 */
import { useEffect, useMemo, useState } from 'react';
import { Eye, FileText } from 'lucide-react';
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
import { QueuePanel } from '../shared/QueuePanel';
import { fileCaps, type FileKindId } from '../shared/fileKinds';
import type { MissingRange } from '../shared/missingRanges';
import type { FileLeaf } from './types';

type FilterKind = 'all' | 'aii' | 'mag';

const FILTER_OPTIONS: ReadonlyArray<{ id: FilterKind; label: string }> = [
  { id: 'all', label: 'ALL' },
  { id: 'aii', label: 'AII' },
  { id: 'mag', label: 'MAG' },
];

const FILES_QUEUE_REGEX = /^(aii|mag)_/;

export default function FilesPage() {
  const aii = useFlatFiles('aii');
  const mag = useFlatFiles('mag');
  const { lastTouchedFlatKind, setLastTouchedFlatKind } = useFileChunks();
  const {
    packets,
    queueCommand,
    txConnected,
    fetchSchema,
    pendingQueue,
    sendAll,
    abortSend,
    sendProgress,
    removeQueueItem,
  } = usePluginServices();

  const [filter, setFilter] = useState<FilterKind>('all');
  const [search, setSearch] = useState('');
  const [deleteOne, setDeleteOne] = useState<FileLeaf | null>(null);
  const [aiiDestNode, setAiiDestNode] = useState('');
  const [magDestNode, setMagDestNode] = useState('');
  const [schema, setSchema] = useState<Record<string, Record<string, unknown>> | null>(null);

  useEffect(() => { fetchSchema().then(setSchema).catch(() => {}); }, [fetchSchema]);

  const { defs: ctxDefs } = useColumnDefs();
  const rxColumns = ctxDefs?.rx ?? composeRxColumns([]);
  const txColumns = ctxDefs?.tx ?? [];

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
    const aHit = aii.files.find(f => f.id === aii.selectedId) ?? null;
    const mHit = mag.files.find(f => f.id === mag.selectedId) ?? null;
    if (lastTouchedFlatKind === 'aii') return aHit ?? mHit;
    if (lastTouchedFlatKind === 'mag') return mHit ?? aHit;
    return aHit ?? mHit;
  }, [filter, aii, mag, lastTouchedFlatKind]);

  // Right-pane only renders a selection currently visible in the table —
  // a search that hides the row also blanks the preview rather than
  // leaving a "ghost" selection.
  const activeSelection = useMemo<FileLeaf | null>(() => {
    if (!candidateSelection) return null;
    return filtered.some(f => f.id === candidateSelection.id) ? candidateSelection : null;
  }, [candidateSelection, filtered]);

  // TX controls bind to one kind:
  //   1. selection's kind (operator clicked a row)
  //   2. filter, when constrained to a single kind
  //   3. the last kind the operator interacted with (sticky, so the
  //      panel doesn't silently default to AII when the operator was
  //      last working with MAG)
  //   4. AII as the final fallback for a fresh session
  // When filter='all' AND no selection, the TX panel header also surfaces
  // an explicit AII|MAG toggle so the operator can flip without picking
  // a row first.
  const txKind: FileKindId =
    activeSelection?.kind === 'aii' || activeSelection?.kind === 'mag'
      ? activeSelection.kind
      : filter === 'aii' || filter === 'mag'
      ? filter
      : (lastTouchedFlatKind ?? 'aii');
  const showTxKindSwitcher = filter === 'all' && !activeSelection;

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

  const performDelete = async (file: FileLeaf) => {
    try {
      const r = await fetch(filesEndpoint('file', file.kind, file.filename, file.source), { method: 'DELETE' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await Promise.all([aii.refetch(), mag.refetch()]);
      showToast(`Deleted ${file.filename}`, 'success', 'tx');
    } catch (err) {
      showToast(`Failed to delete: ${(err as Error).message}`, 'error', 'tx');
    } finally {
      setDeleteOne(null);
    }
  };

  const handleRestageRange = (file: FileLeaf, range: MissingRange) => {
    const caps = fileCaps(file.kind as FileKindId);
    if (!file.source) {
      showToast('No source on file — cannot route', 'error', 'tx');
      return;
    }
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

  const hiddenCount = allFiles.length - filtered.length;
  const emptyMessage = filtered.length > 0
    ? null
    : (filter === 'all' && allFiles.length === 0)
      ? 'no files yet'
      : (hiddenCount > 0)
        ? `no ${filter === 'all' ? 'matching' : filter.toUpperCase()} files — ${hiddenCount} hidden by filter${search ? '/search' : ''}`
        : 'no files yet';

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Filter toolbar */}
      <div
        className="flex items-center gap-2 px-3 border-b shrink-0"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>
          Filter
        </span>
        <div className="flex items-center gap-1">
          {FILTER_OPTIONS.map(({ id, label }) => {
            const active = filter === id;
            return (
              <button
                key={id}
                onClick={() => setFilter(id)}
                className="px-2 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
                style={{
                  height: 20,
                  color: active ? colors.label : colors.dim,
                  borderColor: active ? colors.label : colors.borderSubtle,
                  backgroundColor: active ? `${colors.label}18` : 'transparent',
                }}
                title={`Filter · ${label}`}
              >
                {label}
              </button>
            );
          })}
        </div>
        <GssInput
          className="ml-2 w-[260px] font-mono"
          placeholder="search filename..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <span className="text-[11px] ml-auto" style={{ color: colors.dim }}>
          {filtered.length} file{filtered.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="flex-1 flex overflow-hidden p-3">
        <ResizablePanelGroup className="flex-1 h-full">
          {/* Left column mirrors ImagingPage: RxLog (fixed), TX (flex), Queue. */}
          <ResizablePanel defaultSize={42} minSize={25}>
            <div className="flex flex-col gap-3 h-full min-w-0">
              <div className="h-[200px] shrink-0 flex flex-col">
                <FilesRxLogPanel filter={filter} packets={packets} columns={rxColumns} />
              </div>

              <FilesTxControls
                kind={txKind}
                selected={activeSelection?.kind === txKind ? activeSelection : null}
                knownFiles={txKind === 'aii' ? aii.files : mag.files}
                destNode={txKind === 'aii' ? aiiDestNode : magDestNode}
                onDestNodeChange={txKind === 'aii' ? setAiiDestNode : setMagDestNode}
                schema={schema}
                txConnected={txConnected}
                queueCommand={queueCommand}
                availableKinds={showTxKindSwitcher ? ['aii', 'mag'] : undefined}
                onKindChange={showTxKindSwitcher
                  ? (k) => { if (k === 'aii' || k === 'mag') setLastTouchedFlatKind(k); }
                  : undefined}
              />

              <QueuePanel
                title="Files Queue"
                kindRegex={FILES_QUEUE_REGEX}
                idPrefix="files"
                pendingQueue={pendingQueue}
                txColumns={txColumns}
                sendProgress={sendProgress}
                sendAll={sendAll}
                abortSend={abortSend}
                removeQueueItem={removeQueueItem}
              />
            </div>
          </ResizablePanel>

          <ResizableHandle
            withHandle
            className="mx-1 w-1 rounded-full bg-transparent hover:bg-[#222222] data-[resize-handle-active]:bg-[#30C8E0] transition-colors"
          />

          {/* Right column = data view: Files table (top), Progress, Preview. */}
          <ResizablePanel defaultSize={58} minSize={25}>
            <div className="flex flex-col gap-3 h-full min-w-0">
              <div
                className="flex-1 min-h-0 flex flex-col rounded-md border overflow-hidden shadow-panel"
                style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
              >
                <div
                  className="flex items-center gap-2 px-3 border-b shrink-0"
                  style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
                >
                  <FileText className="size-3.5" style={{ color: colors.dim }} />
                  <span
                    className="font-bold uppercase"
                    style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}
                  >
                    Files
                  </span>
                  <span className="text-[11px]" style={{ color: colors.dim }}>
                    {filtered.length} of {allFiles.length} · {aii.files.length} AII · {mag.files.length} MAG
                  </span>
                </div>
                <div className="flex-1 min-h-0 overflow-auto">
                  {filtered.length > 0 ? (
                    <FilesTable
                      files={filtered}
                      selectedId={activeSelection?.id ?? null}
                      onSelect={handleSelectRow}
                      onDelete={(f) => setDeleteOne(f)}
                    />
                  ) : (
                    <div className="px-3 py-4 italic text-[11px]" style={{ color: colors.textMuted }}>
                      {emptyMessage}
                    </div>
                  )}
                </div>
              </div>

              <FilesProgressGrid selected={activeSelection} onRestageRange={handleRestageRange} />

              <div
                className="h-[240px] shrink-0 flex flex-col rounded-md border overflow-hidden shadow-panel"
                style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
              >
                <div
                  className="flex items-center gap-2 px-3 border-b shrink-0"
                  style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
                >
                  <Eye className="size-3.5" style={{ color: colors.dim }} />
                  <span
                    className="font-bold uppercase"
                    style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}
                  >
                    Preview
                  </span>
                  {activeSelection && (
                    <span className="text-[11px] font-mono truncate" style={{ color: colors.dim }}>
                      {activeSelection.kind.toUpperCase()} · {activeSelection.filename}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-h-0 overflow-hidden">
                  {activeSelection?.kind === 'aii'
                    ? <JsonPreview file={activeSelection} />
                    : <MagPreview file={activeSelection?.kind === 'mag' ? activeSelection : null} />}
                </div>
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {deleteOne && (
        <ConfirmDialog
          open
          title="Delete file?"
          detail={`Remove ${deleteOne.filename}? This cannot be undone.`}
          variant="destructive"
          onConfirm={() => performDelete(deleteOne)}
          onCancel={() => setDeleteOne(null)}
        />
      )}
    </div>
  );
}
