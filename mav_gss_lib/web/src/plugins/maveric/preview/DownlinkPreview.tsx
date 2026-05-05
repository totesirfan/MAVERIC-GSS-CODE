/**
 * Downlink Preview — static mock of the proposed unified Imaging+Files
 * page. No real data, no commands actually staged. Pure layout + mock
 * sample state to evaluate the redesign without committing to it.
 */
import { useMemo, useState } from 'react';
import {
  FileDown,
  Send,
  Camera,
  Power,
  PowerOff,
  Monitor,
  Eraser,
  Lock,
  Activity,
  ChevronUp,
  Trash2,
  Plus,
  Search,
  Image as ImageIcon,
  FileJson,
  FileBox,
  Download,
  RefreshCcw,
  Eye,
} from 'lucide-react';
import { colors } from '@/lib/colors';

type MockKind = 'image' | 'aii' | 'mag';
type Source = 'HLNV' | 'ASTR';

interface MockLeaf {
  received: number;
  total: number;
  chunkSize: number;
}
interface MockImage {
  id: string;
  kind: 'image';
  source: Source;
  stem: string;
  full: MockLeaf;
  thumb: MockLeaf | null;
  ageS: number;
}
interface MockFlat {
  id: string;
  kind: 'aii' | 'mag';
  source: Source;
  filename: string;
  received: number;
  total: number;
  chunkSize: number;
  ageS: number;
}
type MockFile = MockImage | MockFlat;

const MOCK_FILES: MockFile[] = [
  {
    id: 'img/HLNV/out.jpg',
    kind: 'image',
    source: 'HLNV',
    stem: 'out.jpg',
    full:  { received: 12,  total: 434, chunkSize: 150 },
    thumb: { received: 7,   total: 7,   chunkSize: 150 },
    ageS: 4,
  },
  {
    id: 'img/ASTR/moon.jpg',
    kind: 'image',
    source: 'ASTR',
    stem: 'moon.jpg',
    full:  { received: 200, total: 200, chunkSize: 150 },
    thumb: { received: 7,   total: 7,   chunkSize: 150 },
    ageS: 38,
  },
  {
    id: 'aii/HLNV/transmit_dir.json',
    kind: 'aii',
    source: 'HLNV',
    filename: 'transmit_dir.json',
    received: 10, total: 10, chunkSize: 150,
    ageS: 12,
  },
  {
    id: 'mag/HLNV/capture_001.npz',
    kind: 'mag',
    source: 'HLNV',
    filename: 'capture_001.npz',
    received: 200, total: 200, chunkSize: 150,
    ageS: 92,
  },
  {
    id: 'mag/ASTR/probe.npz',
    kind: 'mag',
    source: 'ASTR',
    filename: 'probe.npz',
    received: 64, total: 200, chunkSize: 150,
    ageS: 2,
  },
];

const AII_CANDIDATES = [
  { rank: 1, score: 0.94, filename: 'IMG_0042.jpg', source: 'HLNV' as Source, downloaded: false },
  { rank: 2, score: 0.91, filename: 'IMG_0017.jpg', source: 'HLNV' as Source, downloaded: true  },
  { rank: 3, score: 0.88, filename: 'IMG_0103.jpg', source: 'HLNV' as Source, downloaded: false },
  { rank: 4, score: 0.82, filename: 'IMG_0061.jpg', source: 'HLNV' as Source, downloaded: false },
  { rank: 5, score: 0.79, filename: 'IMG_0028.jpg', source: 'HLNV' as Source, downloaded: false },
];

// Mock B-field magnitude time-series for MAG sparkline.
const MAG_SAMPLES = Array.from({ length: 80 }, (_, i) => {
  const t = i / 80;
  return 38 + 12 * Math.sin(2 * Math.PI * 1.5 * t) + 4 * Math.sin(2 * Math.PI * 4 * t);
});

const MOCK_QUEUE = [
  { num: 1, cmdId: 'img_get_chunks', dest: 'HLNV', sub: 'out.jpg · start=12 · count=422' },
  { num: 2, cmdId: 'img_get_chunks', dest: 'HLNV', sub: 'tn_out.jpg · start=0 · count=7' },
];

type FilterKind = 'all' | 'image' | 'aii' | 'mag';
const FILTER_OPTIONS: ReadonlyArray<{ id: FilterKind; label: string }> = [
  { id: 'all',   label: 'ALL'   },
  { id: 'image', label: 'IMAGE' },
  { id: 'aii',   label: 'AII'   },
  { id: 'mag',   label: 'MAG'   },
];

function ageLabel(s: number): string {
  if (s < 5) return 'now';
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

function fileTotalProgress(f: MockFile): { received: number; total: number; complete: boolean } {
  if (f.kind === 'image') {
    const t = (f.full?.total ?? 0) + (f.thumb?.total ?? 0);
    const r = (f.full?.received ?? 0) + (f.thumb?.received ?? 0);
    return { received: r, total: t, complete: t > 0 && r === t };
  }
  return { received: f.received, total: f.total, complete: f.received === f.total };
}

export default function DownlinkPreview() {
  const [filter, setFilter] = useState<FilterKind>('all');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string>('aii/HLNV/transmit_dir.json');
  const [activityOpen, setActivityOpen] = useState(false);
  const [captureSheet, setCaptureSheet] = useState(false);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return MOCK_FILES.filter(f => {
      if (filter !== 'all' && f.kind !== filter) return false;
      const fn = 'stem' in f ? f.stem : f.filename;
      if (q && !fn.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [filter, search]);

  const selected = MOCK_FILES.find(f => f.id === selectedId) ?? null;

  return (
    <div
      className="flex-1 flex flex-col overflow-hidden"
      style={{ background: colors.bgApp, color: colors.textPrimary }}
    >
      <ToolbarRow
        filter={filter}
        onFilter={setFilter}
        search={search}
        onSearch={setSearch}
        onCapture={() => setCaptureSheet(true)}
        activityOpen={activityOpen}
        onToggleActivity={() => setActivityOpen(v => !v)}
      />

      <div className="flex-1 flex overflow-hidden p-3 gap-3 min-h-0">
        {/* Main column — list + selected detail */}
        <div className="flex-1 flex flex-col gap-3 min-w-0">
          <FileListPanel
            files={filtered}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <SelectedDetailRow file={selected} />
        </div>

        {activityOpen && <ActivityDrawer onClose={() => setActivityOpen(false)} />}
      </div>

      <QueueStrip />

      {captureSheet && <CaptureSheet onClose={() => setCaptureSheet(false)} />}
    </div>
  );
}

// ─── Toolbar ─────────────────────────────────────────────────────────

function ToolbarRow({
  filter, onFilter,
  search, onSearch,
  onCapture,
  activityOpen, onToggleActivity,
}: {
  filter: FilterKind; onFilter: (f: FilterKind) => void;
  search: string; onSearch: (s: string) => void;
  onCapture: () => void;
  activityOpen: boolean; onToggleActivity: () => void;
}) {
  return (
    <div
      className="flex items-center gap-3 px-3 border-b shrink-0 flex-wrap"
      style={{ borderColor: colors.borderSubtle, minHeight: 38, paddingTop: 6, paddingBottom: 6 }}
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
              onClick={() => onFilter(id)}
              className="px-2 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
              style={{
                height: 22,
                color: active ? colors.label : colors.dim,
                borderColor: active ? colors.label : colors.borderSubtle,
                backgroundColor: active ? `${colors.label}18` : 'transparent',
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div
        className="relative flex items-center"
        style={{ width: 240 }}
      >
        <Search className="absolute left-2 size-3.5" style={{ color: colors.dim }} />
        <input
          className="w-full pl-7 pr-2 font-mono text-[11px] rounded-sm border outline-none"
          style={{
            height: 22,
            backgroundColor: colors.bgPanel,
            borderColor: colors.borderSubtle,
            color: colors.textPrimary,
          }}
          placeholder="search filename..."
          value={search}
          onChange={e => onSearch(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider mr-1" style={{ color: colors.dim }}>
          Device
        </span>
        <DeviceBtn icon={Power}     label="CAM ON"  />
        <DeviceBtn icon={PowerOff}  label="CAM OFF" />
        <DeviceBtn icon={Monitor}   label="LCD ON"  />
        <DeviceBtn icon={PowerOff}  label="LCD OFF" />
        <DeviceBtn icon={Eraser}    label="LCD CLR" />
      </div>

      <div className="flex-1" />

      <button
        onClick={onCapture}
        className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
        style={{
          height: 22,
          color: colors.bgApp,
          borderColor: colors.success,
          backgroundColor: colors.success,
        }}
        title="Open camera capture sheet"
      >
        <Plus className="size-3" />
        Capture
      </button>

      <button
        onClick={onToggleActivity}
        className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
        style={{
          height: 22,
          color: activityOpen ? colors.label : colors.dim,
          borderColor: activityOpen ? colors.label : colors.borderSubtle,
          backgroundColor: activityOpen ? `${colors.label}18` : 'transparent',
        }}
        title="Toggle activity drawer (RX log + sent history)"
      >
        <Activity className="size-3" />
        Activity
      </button>
    </div>
  );
}

function DeviceBtn({ icon: Icon, label }: { icon: typeof Power; label: string }) {
  return (
    <button
      className="inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[10px] color-transition btn-feedback"
      style={{
        height: 22,
        color: colors.dim,
        borderColor: colors.borderSubtle,
        backgroundColor: 'transparent',
      }}
      title={label}
    >
      <Icon className="size-3" />
      {label}
    </button>
  );
}

// ─── File list ───────────────────────────────────────────────────────

function FileListPanel({
  files, selectedId, onSelect,
}: { files: MockFile[]; selectedId: string; onSelect: (id: string) => void }) {
  return (
    <div
      className="flex-1 min-h-0 flex flex-col rounded-md border overflow-hidden shadow-panel"
      style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b shrink-0"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <FileDown className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
          Downlink
        </span>
        <span className="text-[11px]" style={{ color: colors.dim }}>
          {files.length} file{files.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        <table className="w-full text-[11px] font-mono">
          <thead className="sticky top-0" style={{ background: colors.bgPanelRaised, color: colors.textMuted }}>
            <tr>
              <th className="text-left px-2 py-1 w-7"></th>
              <th className="text-left px-2 py-1">SOURCE</th>
              <th className="text-left px-2 py-1">FILENAME</th>
              <th className="text-left px-2 py-1">PROGRESS</th>
              <th className="text-left px-2 py-1">AGE</th>
              <th className="text-right px-2 py-1"></th>
            </tr>
          </thead>
          <tbody>
            {files.map(f => (
              <FileListRow key={f.id} file={f} selected={f.id === selectedId} onSelect={() => onSelect(f.id)} />
            ))}
            {files.length === 0 && (
              <tr><td colSpan={6} className="px-2 py-4 italic" style={{ color: colors.textMuted }}>no files</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KindIcon({ kind }: { kind: MockKind }) {
  if (kind === 'image') return <ImageIcon className="size-3.5" style={{ color: colors.active }} />;
  if (kind === 'aii')   return <FileJson  className="size-3.5" style={{ color: colors.active }} />;
  return <FileBox className="size-3.5" style={{ color: colors.neutral }} />;
}

function SourcePill({ source }: { source: Source }) {
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full border px-1.5 py-0 font-mono text-[9px] font-bold leading-4"
      style={{ color: colors.label, borderColor: `${colors.label}66`, backgroundColor: `${colors.label}14` }}
    >
      {source}
    </span>
  );
}

function FileListRow({
  file, selected, onSelect,
}: { file: MockFile; selected: boolean; onSelect: () => void }) {
  const totals = fileTotalProgress(file);
  const pct = totals.total > 0 ? Math.round((totals.received / totals.total) * 100) : 0;

  return (
    <tr
      className="cursor-pointer border-t"
      style={{ borderColor: colors.borderSubtle, background: selected ? colors.bgPanelRaised : undefined }}
      onClick={onSelect}
    >
      <td className="px-2 py-1.5"><KindIcon kind={file.kind} /></td>
      <td className="px-2 py-1.5"><SourcePill source={file.source} /></td>
      <td className="px-2 py-1.5">
        <div style={{ color: colors.textPrimary }}>
          {'stem' in file ? file.stem : file.filename}
        </div>
        {file.kind === 'image' && (
          <div className="text-[10px] mt-0.5 flex items-center gap-2" style={{ color: colors.textMuted }}>
            <span>full {file.full.received}/{file.full.total}</span>
            {file.thumb && <span>· thumb {file.thumb.received}/{file.thumb.total}</span>}
          </div>
        )}
      </td>
      <td className="px-2 py-1.5">
        <div className="flex items-center gap-2">
          <ProgressBar pct={pct} complete={totals.complete} />
          <span className="text-[10px] tabular-nums" style={{ color: colors.dim }}>{pct}%</span>
        </div>
      </td>
      <td className="px-2 py-1.5" style={{ color: colors.textMuted }}>{ageLabel(file.ageS)}</td>
      <td className="px-2 py-1.5 text-right">
        {!totals.complete ? (
          <button
            className="inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[10px]"
            style={{ height: 20, color: colors.warning, borderColor: `${colors.warning}66`, backgroundColor: `${colors.warning}0A` }}
            title="Pull all missing chunks"
            onClick={(e) => e.stopPropagation()}
          >
            <RefreshCcw className="size-2.5" />
            pull
          </button>
        ) : (
          <button
            className="text-[10px] hover:underline"
            style={{ color: colors.danger }}
            title="Delete from chunk store"
            onClick={(e) => e.stopPropagation()}
          >
            DELETE
          </button>
        )}
      </td>
    </tr>
  );
}

function ProgressBar({ pct, complete }: { pct: number; complete: boolean }) {
  const color = complete ? colors.success : pct === 0 ? colors.danger : colors.warning;
  return (
    <div className="rounded-full overflow-hidden" style={{ width: 120, height: 4, backgroundColor: `${color}22` }}>
      <div style={{ width: `${pct}%`, height: '100%', backgroundColor: color }} />
    </div>
  );
}

// ─── Selected detail row ──────────────────────────────────────────────

function SelectedDetailRow({ file }: { file: MockFile | null }) {
  return (
    <div className="h-[420px] shrink-0 flex gap-3 min-h-0">
      <ProgressPreviewPanel file={file} />
      <TxPanel file={file} />
    </div>
  );
}

function ProgressPreviewPanel({ file }: { file: MockFile | null }) {
  return (
    <div
      className="flex-1 min-w-0 flex flex-col rounded-md border overflow-hidden shadow-panel"
      style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b shrink-0"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <Eye className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
          File detail
        </span>
        {file && (
          <>
            <KindIcon kind={file.kind} />
            <SourcePill source={file.source} />
            <span className="text-[11px] font-mono truncate" style={{ color: colors.dim }}>
              {'stem' in file ? file.stem : file.filename}
            </span>
          </>
        )}
        {file && file.kind !== 'image' && file.received === file.total && (
          <button
            className="ml-auto inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[10px]"
            style={{ height: 20, color: colors.active, borderColor: `${colors.active}66`, backgroundColor: `${colors.active}0A` }}
          >
            <Download className="size-2.5" />
            download
          </button>
        )}
      </div>
      <div className="flex-1 min-h-0 overflow-auto p-3">
        {!file ? (
          <div className="text-[11px] italic" style={{ color: colors.textMuted }}>
            select a file to see progress and preview
          </div>
        ) : file.kind === 'image' ? (
          <ImageDetail file={file} />
        ) : file.kind === 'aii' ? (
          <AiiDetail file={file} />
        ) : (
          <MagDetail file={file} />
        )}
      </div>
    </div>
  );
}

function ImageDetail({ file }: { file: MockImage }) {
  return (
    <div className="space-y-3">
      <SideProgress label="THUMB" leaf={file.thumb} />
      <SideProgress label="FULL"  leaf={file.full} />
      {file.full.received === file.full.total && (
        <div
          className="rounded-md border overflow-hidden flex items-center justify-center"
          style={{ borderColor: colors.borderSubtle, height: 180, backgroundColor: colors.bgApp }}
        >
          <div className="text-center" style={{ color: colors.dim }}>
            <ImageIcon className="size-8 mx-auto mb-2" />
            <div className="text-[11px] font-mono">image preview · 480x320</div>
          </div>
        </div>
      )}
    </div>
  );
}

function SideProgress({ label, leaf }: { label: string; leaf: MockLeaf | null }) {
  if (!leaf) {
    return (
      <div>
        <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: colors.dim }}>{label}</div>
        <div className="text-[11px] mt-1" style={{ color: colors.dim }}>not present</div>
      </div>
    );
  }
  const pct = leaf.total > 0 ? Math.round((leaf.received / leaf.total) * 100) : 0;
  const complete = leaf.received === leaf.total;
  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] uppercase tracking-wider font-bold" style={{ color: colors.dim }}>{label}</span>
        <span className="text-[11px] font-semibold font-mono" style={{ color: colors.value }}>{leaf.received} / {leaf.total}</span>
        <span className="text-[11px]" style={{ color: colors.dim }}>({pct}%)</span>
        <span className="text-[10px] font-mono" style={{ color: colors.dim }}>· {leaf.chunkSize} B/chunk</span>
        <div className="flex-1" />
        {complete ? (
          <span className="text-[11px]" style={{ color: colors.success }}>Complete</span>
        ) : (
          <button
            className="inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[11px]"
            style={{ height: 20, color: colors.warning, borderColor: `${colors.warning}66`, backgroundColor: `${colors.warning}0A` }}
          >
            <RefreshCcw className="size-2.5" />
            {leaf.total - leaf.received} missing
          </button>
        )}
      </div>
      <ChunkDots total={leaf.total} received={leaf.received} />
    </div>
  );
}

function ChunkDots({ total, received }: { total: number; received: number }) {
  // For very large totals, render a heatmap bar instead of dots.
  if (total > 200) {
    const cells = 80;
    const stride = Math.ceil(total / cells);
    return (
      <div className="flex flex-wrap gap-px">
        {Array.from({ length: cells }, (_, i) => {
          const cellEnd = Math.min((i + 1) * stride, total);
          const cellStart = i * stride;
          const cellHas = Math.max(0, Math.min(received, cellEnd) - cellStart);
          const cellWidth = cellEnd - cellStart;
          const fill = cellWidth === 0 ? 0 : cellHas / cellWidth;
          const opacity = 0.15 + 0.85 * fill;
          return (
            <span
              key={i}
              style={{
                width: 8,
                height: 8,
                borderRadius: 2,
                backgroundColor: fill === 1 ? colors.success : fill > 0 ? colors.warning : 'transparent',
                border: fill === 0 ? `1px solid ${colors.danger}` : 'none',
                opacity: fill === 0 ? 1 : opacity,
              }}
            />
          );
        })}
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-[3px]">
      {Array.from({ length: total }, (_, i) => {
        const got = i < received;
        return (
          <span
            key={i}
            style={{
              width: 8, height: 8, borderRadius: '50%',
              backgroundColor: got ? colors.success : 'transparent',
              border: got ? 'none' : `1px solid ${colors.danger}`,
            }}
          />
        );
      })}
    </div>
  );
}

function AiiDetail({ file }: { file: MockFlat }) {
  const complete = file.received === file.total;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold font-mono" style={{ color: colors.value }}>{file.received} / {file.total}</span>
        <span className="text-[11px]" style={{ color: colors.dim }}>· {file.chunkSize} B/chunk</span>
        {complete ? (
          <span className="text-[11px] ml-2" style={{ color: colors.success }}>Complete</span>
        ) : (
          <button className="ml-2 inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[11px]"
            style={{ height: 20, color: colors.warning, borderColor: `${colors.warning}66`, backgroundColor: `${colors.warning}0A` }}>
            <RefreshCcw className="size-2.5" />pull
          </button>
        )}
      </div>
      <div className="text-[10px] uppercase tracking-wider font-bold mt-2" style={{ color: colors.dim }}>
        AI-ranked candidates
      </div>
      <table className="w-full text-[11px] font-mono">
        <thead style={{ color: colors.textMuted }}>
          <tr className="border-b" style={{ borderColor: colors.borderSubtle }}>
            <th className="text-left py-1 w-7">#</th>
            <th className="text-left py-1">SCORE</th>
            <th className="text-left py-1">FILENAME</th>
            <th className="text-right py-1"></th>
          </tr>
        </thead>
        <tbody>
          {AII_CANDIDATES.map(c => (
            <tr key={c.rank} className="border-b" style={{ borderColor: colors.borderSubtle }}>
              <td className="py-1 tabular-nums" style={{ color: colors.dim }}>{c.rank}</td>
              <td className="py-1 tabular-nums" style={{ color: colors.value }}>{c.score.toFixed(2)}</td>
              <td className="py-1" style={{ color: colors.textPrimary }}>{c.filename}</td>
              <td className="py-1 text-right">
                {c.downloaded ? (
                  <span className="text-[10px]" style={{ color: colors.success }}>✓ pulled</span>
                ) : (
                  <button
                    className="inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[10px]"
                    style={{ height: 20, color: colors.active, borderColor: `${colors.active}66`, backgroundColor: `${colors.active}0A` }}
                  >
                    <Download className="size-2.5" />pull
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MagDetail({ file }: { file: MockFlat }) {
  const complete = file.received === file.total;
  // Sparkline path
  const w = 320, h = 70;
  const min = Math.min(...MAG_SAMPLES), max = Math.max(...MAG_SAMPLES);
  const path = MAG_SAMPLES.map((v, i) => {
    const x = (i / (MAG_SAMPLES.length - 1)) * w;
    const y = h - ((v - min) / (max - min)) * h;
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold font-mono" style={{ color: colors.value }}>{file.received} / {file.total}</span>
        <span className="text-[11px]" style={{ color: colors.dim }}>· {file.chunkSize} B/chunk</span>
        {complete ? (
          <span className="text-[11px] ml-2" style={{ color: colors.success }}>Complete</span>
        ) : (
          <button className="ml-2 inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[11px]"
            style={{ height: 20, color: colors.warning, borderColor: `${colors.warning}66`, backgroundColor: `${colors.warning}0A` }}>
            <RefreshCcw className="size-2.5" />pull
          </button>
        )}
      </div>
      <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: colors.dim }}>
        |B| (μT) · 200 samples · 1.0 s window
      </div>
      <div
        className="rounded-md border p-2"
        style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgApp }}
      >
        <svg width={w} height={h} style={{ display: 'block' }}>
          <path d={path} fill="none" stroke={colors.active} strokeWidth={1.4} />
        </svg>
      </div>
      <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
        <Stat label="MIN" value={`${min.toFixed(2)} μT`} />
        <Stat label="MAX" value={`${max.toFixed(2)} μT`} />
        <Stat label="TEMP" value="22.5 °C" />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border px-2 py-1" style={{ borderColor: colors.borderSubtle }}>
      <div className="text-[9px] uppercase tracking-wider" style={{ color: colors.textMuted }}>{label}</div>
      <div style={{ color: colors.textPrimary }}>{value}</div>
    </div>
  );
}

// ─── TX panel ────────────────────────────────────────────────────────

function TxPanel({ file }: { file: MockFile | null }) {
  const kind: MockKind = file?.kind ?? 'image';
  const ext = kind === 'image' ? '.jpg' : kind === 'aii' ? '.json' : '.npz';
  const labels: Record<MockKind, string> = { image: 'IMG', aii: 'AII', mag: 'MAG' };
  return (
    <div
      className="flex-1 min-w-0 flex flex-col rounded-md border overflow-hidden shadow-panel"
      style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b shrink-0"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <Send className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
          {labels[kind]} TX
        </span>
        <span className="text-[11px] font-mono" style={{ color: colors.dim }}>
          context-pinned to {file ? `selected ${labels[kind]}` : 'last-touched'}
        </span>
        <div className="flex-1" />
        <PillToggle on label="HLNV" />
        <PillToggle label="ASTR" />
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-3">
        <ChunkRow ext={ext} />
        {kind === 'image' && (
          <>
            <StageRow cmd={`img_cnt_chunks`} ext={ext} dest />
            <StageRow cmd={`img_get_chunks`} ext={ext} dest range />
            <StageRow cmd={`img_delete`} ext={ext} destructive />
          </>
        )}
        {kind === 'aii' && (
          <>
            <StageRow cmd={`aii_cnt_chunks`} ext={ext} locked />
            <StageRow cmd={`aii_get_chunks`} ext={ext} locked range />
            <StageRow cmd={`aii_delete`} ext={ext} destructive locked />
            <DividerNote text="AI ranking" />
            <StageRow cmd="aii_dir" ext="" customExtras={<><MiniInput placeholder="destination" /><MiniInput placeholder="max_tx" /></>} />
            <StageRow cmd="aii_img" ext={ext} customExtras={<MiniInput placeholder="destination" />} />
          </>
        )}
        {kind === 'mag' && (
          <>
            <StageRow cmd={`mag_cnt_chunks`} ext={ext} />
            <StageRow cmd={`mag_get_chunks`} ext={ext} range />
            <StageRow cmd={`mag_delete`} ext={ext} destructive />
            <DividerNote text="MAG" />
            <StageRow cmd="mag_capture" ext={ext} customExtras={<><MiniInput placeholder="time" /><MiniInput placeholder="mode" /></>} />
            <StageRow cmd="mag_kill" ext="" noFilename />
            <StageRow cmd="mag_tlm" ext="" noFilename />
          </>
        )}
      </div>
    </div>
  );
}

function ChunkRow({ ext }: { ext: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>Chunk</span>
      <input
        className="font-mono px-2 rounded-sm border outline-none"
        style={{ width: 72, height: 22, backgroundColor: colors.bgPanel, borderColor: colors.borderSubtle, color: colors.textPrimary }}
        defaultValue="150"
      />
      <span className="inline-flex items-center gap-1 text-[10px] font-mono" style={{ color: colors.warning }}>
        <Lock className="size-3" />locked to 150
      </span>
      <span className="text-[10px] font-mono ml-1" style={{ color: colors.sep }}>{ext} kind · bytes per chunk</span>
    </div>
  );
}

function StageRow({
  cmd, ext, dest, range, destructive, locked, noFilename, customExtras,
}: {
  cmd: string; ext: string;
  dest?: boolean; range?: boolean; destructive?: boolean; locked?: boolean;
  noFilename?: boolean; customExtras?: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1 flex items-center gap-1" style={{ color: destructive ? colors.danger : colors.dim }}>
        {destructive && <Trash2 className="size-3" />}
        {cmd}
      </div>
      <div className="flex items-end gap-2 flex-wrap">
        {!noFilename && (
          <div className="relative flex-1 min-w-[120px]">
            <input
              disabled={locked}
              defaultValue={locked ? 'transmit_dir' : ''}
              placeholder="filename"
              className="w-full pr-9 px-2 font-mono rounded-sm border outline-none"
              style={{ height: 22, backgroundColor: colors.bgPanel, borderColor: colors.borderSubtle, color: colors.textPrimary, opacity: locked ? 0.7 : 1 }}
            />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] font-mono pointer-events-none" style={{ color: colors.dim }}>
              {ext}
            </span>
          </div>
        )}
        {range && (
          <>
            <MiniInput placeholder="start" />
            <MiniInput placeholder="count" />
          </>
        )}
        {dest && <DestSelector />}
        {customExtras}
        <button
          className="px-2 rounded-sm font-mono text-[11px] btn-feedback"
          style={{
            height: 22,
            color: colors.bgApp,
            backgroundColor: destructive ? colors.danger : colors.active,
          }}
        >
          Stage
        </button>
      </div>
    </div>
  );
}

function DestSelector() {
  return (
    <div className="flex items-center gap-px" title="Imaging folder · 0=prestored 1=full 2=thumb">
      {[
        { id: 0, label: 'STR', active: false },
        { id: 1, label: 'FULL', active: true  },
        { id: 2, label: 'THMB', active: false },
      ].map(p => (
        <button
          key={p.id}
          className="px-1.5 border font-mono text-[10px]"
          style={{
            height: 22,
            color: p.active ? colors.label : colors.dim,
            borderColor: p.active ? colors.label : colors.borderSubtle,
            backgroundColor: p.active ? `${colors.label}18` : 'transparent',
          }}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

function MiniInput({ placeholder }: { placeholder: string }) {
  return (
    <input
      className="font-mono px-2 rounded-sm border outline-none"
      style={{ width: 72, height: 22, backgroundColor: colors.bgPanel, borderColor: colors.borderSubtle, color: colors.textPrimary }}
      placeholder={placeholder}
    />
  );
}

function PillToggle({ on, label }: { on?: boolean; label: string }) {
  return (
    <button
      className="px-2 rounded-sm border font-mono text-[11px]"
      style={{
        height: 22,
        color: on ? colors.label : colors.dim,
        borderColor: on ? colors.label : colors.borderSubtle,
        backgroundColor: on ? `${colors.label}18` : 'transparent',
      }}
    >
      {label}
    </button>
  );
}

function DividerNote({ text }: { text: string }) {
  return (
    <div className="border-t pt-2 -mx-3 px-3 text-[10px] font-semibold uppercase tracking-wider" style={{ borderColor: colors.borderSubtle, color: colors.dim }}>
      {text}
    </div>
  );
}

// ─── Activity drawer + queue strip + capture sheet ───────────────────

function ActivityDrawer({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="w-[340px] shrink-0 flex flex-col rounded-md border overflow-hidden shadow-panel"
      style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b shrink-0"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <Activity className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
          Activity
        </span>
        <div className="flex-1" />
        <button className="text-[11px]" style={{ color: colors.dim }} onClick={onClose}>
          ×
        </button>
      </div>
      <div className="flex-1 overflow-auto px-2 py-1">
        {[
          { t: '20:47:12', dir: 'TX', cmd: 'img_get_chunks', tone: colors.active },
          { t: '20:47:11', dir: 'RX', cmd: 'aii_get_chunks · ACK', tone: colors.success },
          { t: '20:47:10', dir: 'RX', cmd: 'aii_get_chunks · RES', tone: colors.success },
          { t: '20:46:58', dir: 'TX', cmd: 'aii_get_chunks', tone: colors.active },
          { t: '20:46:57', dir: 'TX', cmd: 'aii_cnt_chunks', tone: colors.active },
          { t: '20:46:55', dir: 'RX', cmd: 'cam_capture · RES', tone: colors.success },
          { t: '20:46:50', dir: 'TX', cmd: 'cam_capture', tone: colors.active },
        ].map((row, i) => (
          <div key={i} className="flex items-center gap-2 py-0.5 text-[11px] font-mono" style={{ color: colors.textPrimary }}>
            <span style={{ color: colors.dim, width: 60 }}>{row.t}</span>
            <span style={{ color: row.tone, width: 20 }}>{row.dir}</span>
            <span className="flex-1 truncate">{row.cmd}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QueueStrip() {
  return (
    <div
      className="flex items-center gap-2 px-3 border-t shrink-0"
      style={{ borderColor: colors.borderSubtle, minHeight: 38, paddingTop: 6, paddingBottom: 6, backgroundColor: colors.bgPanelRaised }}
    >
      <ChevronUp className="size-3.5" style={{ color: colors.dim }} />
      <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>
        Queue
      </span>
      <span className="text-[11px]" style={{ color: colors.dim }}>{MOCK_QUEUE.length} cmds</span>
      <div className="flex items-center gap-1.5 overflow-auto">
        {MOCK_QUEUE.map(q => (
          <span
            key={q.num}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm border font-mono text-[10px] shrink-0"
            style={{ borderColor: colors.borderSubtle, color: colors.textPrimary, backgroundColor: colors.bgPanel }}
            title={q.sub}
          >
            <span style={{ color: colors.dim }}>{q.num}</span>
            <span style={{ color: colors.label }}>{q.dest}</span>
            <span>{q.cmdId}</span>
          </span>
        ))}
      </div>
      <div className="flex-1" />
      <button
        className="inline-flex items-center gap-1 px-2 rounded-sm font-mono text-[11px]"
        style={{ height: 24, color: colors.dim }}
      >
        <Trash2 className="size-3" /> Clear
      </button>
      <button
        className="inline-flex items-center gap-1 px-2 rounded-sm font-mono text-[11px]"
        style={{ height: 24, color: colors.bgApp, backgroundColor: colors.success }}
      >
        <Send className="size-3" /> Send All
      </button>
    </div>
  );
}

function CaptureSheet({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="absolute inset-0 flex items-start justify-center pt-16"
      style={{ backgroundColor: 'rgba(0,0,0,0.45)' }}
      onClick={onClose}
    >
      <div
        className="w-[640px] rounded-md border shadow-panel"
        style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
        onClick={e => e.stopPropagation()}
      >
        <div
          className="flex items-center gap-2 px-3 border-b"
          style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
        >
          <Camera className="size-3.5" style={{ color: colors.dim }} />
          <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
            Capture
          </span>
          <span className="text-[11px] font-mono" style={{ color: colors.dim }}>cam_capture</span>
          <div className="flex-1" />
          <button className="text-[14px]" style={{ color: colors.dim }} onClick={onClose}>×</button>
        </div>
        <div className="grid grid-cols-3 gap-2 p-3">
          <Field label="Filename"><MiniInput placeholder="capture_001" /></Field>
          <Field label="Quantity"><MiniInput placeholder="1" /></Field>
          <Field label="Delay (s)"><MiniInput placeholder="0" /></Field>
          <Field label="Focus"><MiniInput placeholder="auto" /></Field>
          <Field label="Exposure µs"><MiniInput placeholder="20000" /></Field>
          <Field label="K cap"><MiniInput placeholder="1.0" /></Field>
          <Field label="K thumb"><MiniInput placeholder="0.25" /></Field>
          <Field label="Quality"><MiniInput placeholder="80" /></Field>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 border-t" style={{ borderColor: colors.borderSubtle }}>
          <div className="flex-1" />
          <button
            className="px-3 rounded-sm font-mono text-[11px]"
            style={{ height: 26, color: colors.dim }}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="inline-flex items-center gap-1 px-3 rounded-sm font-mono text-[11px]"
            style={{ height: 26, color: colors.bgApp, backgroundColor: colors.active }}
          >
            <Send className="size-3" /> Stage capture
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-wider mb-0.5 font-semibold" style={{ color: colors.dim }}>{label}</div>
      {children}
    </div>
  );
}
