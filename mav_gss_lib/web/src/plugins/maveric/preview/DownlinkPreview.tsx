/**
 * Downlink Preview v2 — three-column "console + canvas" mock.
 *
 *   ┌──────────────────────────────────────────────────────────────────┐
 *   │ topbar                                                           │
 *   ├────────────┬─────────────────────────────────────┬───────────────┤
 *   │ sidebar    │ canvas (hero, kind-distinctive)     │ rail          │
 *   │  files     │  image | aii | mag — adaptive       │  tx           │
 *   │  list      │                                     │  queue        │
 *   │            │                                     │  activity     │
 *   └────────────┴─────────────────────────────────────┴───────────────┘
 *
 * No live wiring; pure mock. The shape of this page is what matters.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, Camera, ChevronRight, Download, Eraser, FileBox, FileJson,
  Image as ImageIcon, Lock, Monitor, Plus, Power, RefreshCcw, Search, Send,
  Sparkles, Trash2, X,
} from 'lucide-react';
import { colors } from '@/lib/colors';

// Compatibility shim: `lucide-react@^1.7.0` may not ship every icon name; the
// imports above are the ones actually rendered in this file. If any of the
// above is unused, TS will warn — keep the list pruned.

// ─── MOCK DATA ───────────────────────────────────────────────────────

type Kind = 'image' | 'aii' | 'mag';
type Source = 'HLNV' | 'ASTR';

interface Leaf { received: number; total: number; chunkSize: number }
interface ImageFile { id: string; kind: 'image'; source: Source; stem: string; full: Leaf; thumb: Leaf | null; ageS: number; }
interface FlatFile  { id: string; kind: 'aii' | 'mag'; source: Source; filename: string; received: number; total: number; chunkSize: number; ageS: number; }
type File = ImageFile | FlatFile;

const FILES: File[] = [
  { id: 'mag/ASTR/probe.npz',           kind: 'mag',   source: 'ASTR', filename: 'probe.npz',         received: 64,  total: 200, chunkSize: 150, ageS: 2 },
  { id: 'img/HLNV/out.jpg',             kind: 'image', source: 'HLNV', stem: 'out.jpg',
    full:  { received: 12,  total: 434, chunkSize: 150 },
    thumb: { received: 7,   total: 7,   chunkSize: 150 }, ageS: 4 },
  { id: 'aii/HLNV/transmit_dir.json',   kind: 'aii',   source: 'HLNV', filename: 'transmit_dir.json', received: 10,  total: 10,  chunkSize: 150, ageS: 12 },
  { id: 'img/ASTR/moon.jpg',            kind: 'image', source: 'ASTR', stem: 'moon.jpg',
    full:  { received: 200, total: 200, chunkSize: 150 },
    thumb: { received: 7,   total: 7,   chunkSize: 150 }, ageS: 38 },
  { id: 'mag/HLNV/capture_001.npz',     kind: 'mag',   source: 'HLNV', filename: 'capture_001.npz',   received: 200, total: 200, chunkSize: 150, ageS: 92 },
];

// Raw AII payload sample — what the operator actually sees in the
// preview today: pretty-printed JSON, no parsing.
const AII_RAW = JSON.stringify({
  generated_at: '2026-05-04T20:46:55Z',
  source: 'HLNV',
  ranked: [
    { rank: 1, score: 0.94, filename: 'IMG_0042.jpg' },
    { rank: 2, score: 0.91, filename: 'IMG_0017.jpg' },
    { rank: 3, score: 0.88, filename: 'IMG_0103.jpg' },
    { rank: 4, score: 0.82, filename: 'IMG_0061.jpg' },
    { rank: 5, score: 0.79, filename: 'IMG_0028.jpg' },
  ],
  count_total: 36,
}, null, 2);

const QUEUE = [
  { num: 1, cmdId: 'img_get_chunks', dest: 'HLNV', sub: 'out.jpg · start=12 · count=422', sending: true },
  { num: 2, cmdId: 'img_get_chunks', dest: 'HLNV', sub: 'tn_out.jpg · start=0 · count=7', sending: false },
  { num: 3, cmdId: 'mag_get_chunks', dest: 'ASTR', sub: 'probe.npz · start=64 · count=136', sending: false },
];

const ACTIVITY = [
  { tMs: 0,    dir: 'TX' as const, cmd: 'img_get_chunks', meta: 'HLNV · out.jpg start=12 count=422' },
  { tMs: 1100, dir: 'RX' as const, cmd: 'mag_get_chunks · CHUNK 64', meta: 'ASTR · probe.npz' },
  { tMs: 4200, dir: 'RX' as const, cmd: 'aii_get_chunks · RES', meta: 'HLNV · transmit_dir.json' },
  { tMs: 4300, dir: 'TX' as const, cmd: 'aii_get_chunks', meta: 'HLNV · transmit_dir.json start=0 count=10' },
  { tMs: 5800, dir: 'RX' as const, cmd: 'aii_cnt_chunks · RES', meta: 'HLNV · transmit_dir.json total=10' },
  { tMs: 6000, dir: 'TX' as const, cmd: 'aii_cnt_chunks', meta: 'HLNV · transmit_dir.json' },
  { tMs: 8100, dir: 'RX' as const, cmd: 'cam_capture · RES', meta: 'HLNV · captured to file out.jpg' },
];

type FilterKind = 'all' | 'image' | 'aii' | 'mag';
const FILTERS: ReadonlyArray<{ id: FilterKind; label: string }> = [
  { id: 'all',   label: 'ALL'   },
  { id: 'image', label: 'IMAGE' },
  { id: 'aii',   label: 'AII'   },
  { id: 'mag',   label: 'MAG'   },
];

function pct(received: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((received / total) * 100);
}
function fileTotals(f: File): { received: number; total: number; complete: boolean; pct: number } {
  if (f.kind === 'image') {
    const r = (f.full?.received ?? 0) + (f.thumb?.received ?? 0);
    const t = (f.full?.total ?? 0) + (f.thumb?.total ?? 0);
    const p = pct(r, t);
    return { received: r, total: t, complete: t > 0 && r === t, pct: p };
  }
  return { received: f.received, total: f.total, complete: f.received === f.total, pct: pct(f.received, f.total) };
}
function fileName(f: File): string { return f.kind === 'image' ? f.stem : f.filename; }
function ageLabel(s: number): string {
  if (s < 5) return 'now';
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

// ─── PAGE ────────────────────────────────────────────────────────────

export default function DownlinkPreview() {
  const [filter, setFilter] = useState<FilterKind>('all');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string>('aii/HLNV/transmit_dir.json');
  const [captureOpen, setCaptureOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(true);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return FILES.filter(f => {
      if (filter !== 'all' && f.kind !== filter) return false;
      if (q && !fileName(f).toLowerCase().includes(q)) return false;
      return true;
    });
  }, [filter, search]);

  const selected = useMemo(() => FILES.find(f => f.id === selectedId) ?? null, [selectedId]);

  return (
    <div
      className="flex-1 flex flex-col overflow-hidden"
      style={{
        background: 'radial-gradient(circle at 22% 18%, rgba(48,200,224,0.04) 0%, transparent 38%), ' + colors.bgApp,
        color: colors.textPrimary,
      }}
    >
      <Topbar
        filter={filter} onFilter={setFilter}
        search={search} onSearch={setSearch}
        onCapture={() => setCaptureOpen(true)}
        activityOpen={activityOpen}
        onToggleActivity={() => setActivityOpen(v => !v)}
      />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <Sidebar files={filtered} selectedId={selectedId} onSelect={setSelectedId} />
        <Canvas file={selected} />
        <Rail file={selected} activityOpen={activityOpen} />
      </div>

      {captureOpen && <CaptureSheet onClose={() => setCaptureOpen(false)} />}
    </div>
  );
}

// ─── TOPBAR ──────────────────────────────────────────────────────────

function Topbar({
  filter, onFilter, search, onSearch, onCapture, activityOpen, onToggleActivity,
}: {
  filter: FilterKind; onFilter: (f: FilterKind) => void;
  search: string; onSearch: (s: string) => void;
  onCapture: () => void;
  activityOpen: boolean; onToggleActivity: () => void;
}) {
  return (
    <div
      className="flex items-center gap-3 px-4 border-b shrink-0"
      style={{
        borderColor: colors.borderSubtle,
        backgroundColor: colors.bgPanel,
        height: 44,
      }}
    >
      <div className="flex items-baseline gap-2">
        <span
          className="font-bold uppercase"
          style={{ color: colors.value, fontSize: 14, letterSpacing: '0.08em' }}
        >
          Downlink
        </span>
        <span className="text-[11px] font-mono" style={{ color: colors.dim, letterSpacing: '0.08em' }}>
          IMG · AII · MAG
        </span>
      </div>

      <div
        className="ml-3 flex items-center gap-px rounded-sm overflow-hidden"
        style={{ border: `1px solid ${colors.borderSubtle}` }}
      >
        {FILTERS.map(({ id, label }) => {
          const active = filter === id;
          return (
            <button
              key={id}
              onClick={() => onFilter(id)}
              className="px-2.5 font-mono text-[11px] btn-feedback"
              style={{
                height: 22,
                color: active ? colors.bgApp : colors.dim,
                backgroundColor: active ? colors.label : 'transparent',
                letterSpacing: '0.04em',
                fontWeight: active ? 600 : 400,
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="relative flex items-center" style={{ width: 240 }}>
        <Search className="absolute left-2 size-3.5" style={{ color: colors.dim }} />
        <input
          className="w-full pl-7 pr-2 font-mono text-[11px] rounded-sm border outline-none"
          style={{
            height: 22,
            backgroundColor: colors.bgApp,
            borderColor: colors.borderSubtle,
            color: colors.textPrimary,
          }}
          placeholder="search filename..."
          value={search}
          onChange={e => onSearch(e.target.value)}
        />
      </div>

      <div className="flex-1" />

      <DeviceMenu icon={Camera} label="CAM" />
      <DeviceMenu icon={Monitor} label="LCD" />

      <button
        onClick={onCapture}
        className="inline-flex items-center gap-1.5 px-3 rounded-sm font-mono text-[11px] btn-feedback"
        style={{
          height: 26,
          color: colors.bgApp,
          backgroundColor: colors.success,
          fontWeight: 600,
          letterSpacing: '0.04em',
        }}
      >
        <Plus className="size-3.5" />
        CAPTURE
      </button>

      <button
        onClick={onToggleActivity}
        className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px] btn-feedback"
        style={{
          height: 26,
          color: activityOpen ? colors.label : colors.dim,
          borderColor: activityOpen ? colors.label : colors.borderSubtle,
          backgroundColor: activityOpen ? `${colors.label}18` : 'transparent',
        }}
        title="Toggle activity feed (right rail)"
      >
        <Activity className="size-3.5" />
      </button>
    </div>
  );
}

function DeviceMenu({ icon: Icon, label }: { icon: typeof Camera; label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px] btn-feedback"
        style={{
          height: 26,
          color: colors.dim,
          borderColor: colors.borderSubtle,
          backgroundColor: 'transparent',
        }}
        title={`${label} device controls`}
      >
        <Icon className="size-3.5" />
        {label}
        <ChevronRight className={`size-3 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <div
          className="absolute right-0 top-full mt-1 z-10 flex flex-col rounded-sm border shadow-panel overflow-hidden"
          style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel, minWidth: 120 }}
        >
          <DeviceItem icon={Power}    label={`${label} ON`}    tone={colors.success}  onClose={() => setOpen(false)} />
          <DeviceItem icon={Power}    label={`${label} OFF`}   tone={colors.dim}      onClose={() => setOpen(false)} />
          {label === 'LCD' && (
            <DeviceItem icon={Eraser} label={`${label} CLEAR`} tone={colors.warning} onClose={() => setOpen(false)} />
          )}
        </div>
      )}
    </div>
  );
}
function DeviceItem({ icon: Icon, label, tone, onClose }: { icon: typeof Power; label: string; tone: string; onClose: () => void }) {
  return (
    <button
      onClick={onClose}
      className="flex items-center gap-2 px-2.5 py-1.5 text-[11px] font-mono hover:bg-white/[0.04]"
      style={{ color: colors.textPrimary }}
    >
      <Icon className="size-3" style={{ color: tone }} />
      {label}
    </button>
  );
}

// ─── SIDEBAR ─────────────────────────────────────────────────────────

function Sidebar({
  files, selectedId, onSelect,
}: { files: File[]; selectedId: string; onSelect: (id: string) => void }) {
  return (
    <div
      className="shrink-0 flex flex-col border-r overflow-hidden"
      style={{ width: 280, borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b shrink-0"
        style={{ borderColor: colors.borderSubtle, height: 32 }}
      >
        <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>
          Files
        </span>
        <span className="text-[11px] font-mono ml-auto" style={{ color: colors.sep }}>
          {files.length}
        </span>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {files.map(f => (
          <FileRow key={f.id} file={f} selected={f.id === selectedId} onSelect={() => onSelect(f.id)} />
        ))}
        {files.length === 0 && (
          <div className="px-3 py-6 text-center italic text-[11px]" style={{ color: colors.textMuted }}>
            no files match
          </div>
        )}
      </div>
    </div>
  );
}

function KindGlyph({ kind }: { kind: Kind }) {
  if (kind === 'image') return <ImageIcon className="size-3.5" style={{ color: colors.active }} />;
  if (kind === 'aii')   return <FileJson  className="size-3.5" style={{ color: colors.success }} />;
  return <FileBox className="size-3.5" style={{ color: colors.warning }} />;
}

function FileRow({ file, selected, onSelect }: { file: File; selected: boolean; onSelect: () => void }) {
  const tot = fileTotals(file);
  const fresh = file.ageS < 5;
  return (
    <button
      onClick={onSelect}
      className="w-full text-left flex items-stretch gap-2 px-2 py-1.5 hover:bg-white/[0.025] transition-colors outline-none"
      style={{
        backgroundColor: selected ? `${colors.label}10` : 'transparent',
        borderLeft: `3px solid ${selected ? colors.label : 'transparent'}`,
        paddingLeft: selected ? 5 : 8,
      }}
    >
      <div className="pt-0.5"><KindGlyph kind={file.kind} /></div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <SourceTag source={file.source} />
          <span
            className="font-mono text-[11px] truncate"
            style={{ color: tot.complete ? colors.value : colors.textPrimary, fontWeight: selected ? 600 : 400 }}
            title={fileName(file)}
          >
            {fileName(file)}
          </span>
          {fresh && (
            <span
              className="rounded-full shrink-0 animate-pulse-text"
              style={{ width: 6, height: 6, backgroundColor: colors.success }}
              title="recent activity"
            />
          )}
        </div>
        <div className="mt-1 flex items-center gap-2">
          <ProgressBar pct={tot.pct} complete={tot.complete} fresh={!tot.complete && fresh} />
          <span
            className="text-[11px] tabular-nums shrink-0"
            style={{ color: tot.complete ? colors.success : colors.dim, minWidth: 30, textAlign: 'right' }}
          >
            {tot.complete ? 'done' : `${tot.pct}%`}
          </span>
          <span className="text-[11px] tabular-nums shrink-0" style={{ color: colors.sep, minWidth: 22 }}>
            {ageLabel(file.ageS)}
          </span>
        </div>
      </div>
    </button>
  );
}

function SourceTag({ source }: { source: Source }) {
  return (
    <span
      className="inline-flex items-center font-mono text-[11px] font-bold tracking-wider"
      style={{
        color: colors.label,
        height: 13,
        padding: '0 4px',
        borderRadius: 2,
        border: `1px solid ${colors.label}55`,
        backgroundColor: `${colors.label}10`,
      }}
    >
      {source}
    </span>
  );
}

function ProgressBar({ pct, complete, fresh }: { pct: number; complete: boolean; fresh?: boolean }) {
  const tone = complete ? colors.success : pct === 0 ? colors.danger : colors.warning;
  return (
    <div
      className="rounded-full overflow-hidden flex-1 relative"
      style={{ height: 5, backgroundColor: `${tone}1F` }}
    >
      <div
        style={{
          width: `${Math.max(2, pct)}%`,
          height: '100%',
          backgroundColor: tone,
          transition: 'width 240ms ease',
          boxShadow: fresh ? `0 0 6px ${tone}88` : undefined,
        }}
      />
    </div>
  );
}

// ─── CANVAS (hero, kind-distinctive) ─────────────────────────────────

function Canvas({ file }: { file: File | null }) {
  return (
    <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
      {!file ? (
        <EmptyCanvas />
      ) : file.kind === 'image' ? (
        <ImageCanvas file={file} />
      ) : file.kind === 'aii' ? (
        <AiiCanvas file={file} />
      ) : (
        <MagCanvas file={file} />
      )}
    </div>
  );
}

function CanvasHeader({
  kind, source, name, sub, action,
}: { kind: Kind; source: Source; name: string; sub?: React.ReactNode; action?: React.ReactNode }) {
  const tone = kind === 'image' ? colors.active : kind === 'aii' ? colors.success : colors.warning;
  return (
    <div
      className="flex items-center gap-3 px-5 py-3 border-b shrink-0"
      style={{
        borderColor: colors.borderSubtle,
        backgroundColor: colors.bgPanel,
        boxShadow: `inset 4px 0 0 ${tone}`,
      }}
    >
      <KindGlyph kind={kind} />
      <SourceTag source={source} />
      <div className="min-w-0">
        <div className="font-mono text-[14px] truncate" style={{ color: colors.value, letterSpacing: '0.02em' }}>
          {name}
        </div>
        {sub && <div className="text-[11px] mt-0.5" style={{ color: colors.dim }}>{sub}</div>}
      </div>
      <div className="flex-1" />
      {action}
    </div>
  );
}

function EmptyCanvas() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center" style={{ color: colors.dim }}>
      <Sparkles className="size-10 mb-3" style={{ color: `${colors.label}66` }} />
      <div className="text-[12px] font-mono" style={{ letterSpacing: '0.04em' }}>
        select a file to begin
      </div>
      <div className="text-[11px] mt-1" style={{ color: colors.sep }}>
        or stage a capture to bring one down
      </div>
    </div>
  );
}

// — IMAGE CANVAS ------------------------------------------------------

function ImageCanvas({ file }: { file: ImageFile }) {
  const fullPct = pct(file.full.received, file.full.total);
  const thumbPct = file.thumb ? pct(file.thumb.received, file.thumb.total) : 0;
  const fullComplete = file.full.received === file.full.total;
  return (
    <>
      <CanvasHeader
        kind="image"
        source={file.source}
        name={file.stem}
        sub={
          <>
            full <span className="font-mono tabular-nums" style={{ color: colors.value }}>{file.full.received}/{file.full.total}</span>
            {file.thumb && <> · thumb <span className="font-mono tabular-nums" style={{ color: colors.value }}>{file.thumb.received}/{file.thumb.total}</span></>}
            {' · '}
            <span style={{ color: colors.sep }}>{file.full.chunkSize} B/chunk</span>
          </>
        }
        action={
          fullComplete && (
            <button
              className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px]"
              style={{ height: 24, color: colors.active, borderColor: `${colors.active}66`, backgroundColor: `${colors.active}0A` }}
            >
              <Download className="size-3" />Download
            </button>
          )
        }
      />
      <div className="flex-1 grid grid-cols-[1fr_280px] gap-5 p-5 min-h-0">
        {/* Hero preview */}
        <div className="flex flex-col gap-3 min-h-0">
          <div
            className="flex-1 rounded-md border overflow-hidden flex items-center justify-center min-h-0 relative"
            style={{
              borderColor: fullComplete ? `${colors.active}55` : colors.borderSubtle,
              backgroundColor: '#0a0a0a',
              boxShadow: fullComplete ? `0 0 32px ${colors.active}1A` : undefined,
            }}
          >
            {fullComplete ? (
              <FakeImagePreview />
            ) : (
              <div className="text-center" style={{ color: colors.dim }}>
                <ImageIcon className="size-10 mx-auto mb-2 opacity-40" />
                <div className="text-[11px] font-mono">{fullPct}% downloaded · waiting for {file.full.total - file.full.received} chunks</div>
              </div>
            )}
            {!fullComplete && (
              <div
                className="absolute bottom-0 left-0 right-0 h-1"
                style={{ backgroundColor: `${colors.warning}22` }}
              >
                <div style={{ height: '100%', width: `${fullPct}%`, backgroundColor: colors.warning, transition: 'width 240ms ease' }} />
              </div>
            )}
          </div>
          <ChunkHeatmap label="FULL" leaf={file.full} tone={colors.warning} />
          {file.thumb && (
            <ChunkHeatmap label="THUMB" leaf={file.thumb} tone={colors.success} />
          )}
        </div>
        {/* Side: thumb + stats */}
        <div className="flex flex-col gap-3 min-h-0">
          <div className="rounded-md border overflow-hidden p-3 flex flex-col gap-2"
               style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>Thumb</span>
              {file.thumb && file.thumb.received === file.thumb.total ? (
                <span className="text-[11px]" style={{ color: colors.success }}>Complete</span>
              ) : (
                <span className="text-[11px]" style={{ color: colors.warning }}>{thumbPct}%</span>
              )}
              <div className="flex-1" />
              {file.thumb?.total ? (
                <span className="text-[11px] tabular-nums font-mono" style={{ color: colors.value }}>
                  {file.thumb.received}/{file.thumb.total}
                </span>
              ) : (
                <span className="text-[11px]" style={{ color: colors.dim }}>—</span>
              )}
            </div>
            <div
              className="aspect-[4/3] rounded-sm flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, #1f2937, #111827)',
                color: colors.dim,
              }}
            >
              {file.thumb && file.thumb.received === file.thumb.total ? (
                <FakeThumbPreview />
              ) : (
                <ImageIcon className="size-6 opacity-40" />
              )}
            </div>
          </div>
          <StatsCard
            rows={[
              ['Source',     file.source],
              ['Chunk size', `${file.full.chunkSize} B`],
              ['Total',      `${file.full.total + (file.thumb?.total ?? 0)} chunks`],
              ['Received',   `${file.full.received + (file.thumb?.received ?? 0)} chunks`],
              ['Age',        ageLabel(file.ageS)],
            ]}
          />
        </div>
      </div>
    </>
  );
}

function FakeImagePreview() {
  // Hardcoded gradient as a stand-in image preview.
  return (
    <div
      className="w-full h-full flex items-end p-3"
      style={{
        background: 'radial-gradient(circle at 70% 30%, #fde68a 0%, #f59e0b 22%, #1e3a8a 60%, #0a0a0a 100%)',
      }}
    >
      <div
        className="px-2 py-0.5 rounded-sm font-mono text-[11px]"
        style={{ backgroundColor: 'rgba(0,0,0,0.55)', color: '#fde68a' }}
      >
        480 × 320  ·  preview
      </div>
    </div>
  );
}
function FakeThumbPreview() {
  return (
    <div
      className="w-full h-full"
      style={{
        background: 'radial-gradient(circle at 70% 30%, #fde68a 0%, #f59e0b 22%, #1e3a8a 60%, #0a0a0a 100%)',
      }}
    />
  );
}

function ChunkHeatmap({ label, leaf, tone }: { label: string; leaf: Leaf; tone: string }) {
  const cells = Math.min(leaf.total, 96);
  const stride = Math.max(1, Math.ceil(leaf.total / cells));
  return (
    <div className="rounded-md border p-3"
         style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>
          {label} · chunks
        </span>
        <span className="text-[11px] tabular-nums font-mono" style={{ color: colors.value }}>
          {leaf.received}/{leaf.total}
        </span>
        <div className="flex-1" />
        {leaf.received < leaf.total && (
          <button
            className="inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[11px]"
            style={{ height: 20, color: tone, borderColor: `${tone}66`, backgroundColor: `${tone}10` }}
          >
            <RefreshCcw className="size-2.5" />pull missing
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-px">
        {Array.from({ length: cells }, (_, i) => {
          const cellEnd = Math.min((i + 1) * stride, leaf.total);
          const cellStart = i * stride;
          const cellHas = Math.max(0, Math.min(leaf.received, cellEnd) - cellStart);
          const fill = cellHas / Math.max(1, cellEnd - cellStart);
          const bg =
            fill === 1 ? colors.success
            : fill > 0 ? `${colors.warning}88`
            : 'transparent';
          return (
            <span
              key={i}
              style={{
                width: 10, height: 10, borderRadius: 2,
                backgroundColor: bg,
                border: fill === 0 ? `1px solid ${colors.danger}55` : 'none',
              }}
              title={`chunks ${cellStart}-${cellEnd - 1}: ${cellHas}/${cellEnd - cellStart}`}
            />
          );
        })}
      </div>
    </div>
  );
}

// — AII CANVAS --------------------------------------------------------

function AiiCanvas({ file }: { file: FlatFile }) {
  const complete = file.received === file.total;
  return (
    <>
      <CanvasHeader
        kind="aii"
        source={file.source}
        name={file.filename}
        sub={
          <>
            <span className="font-mono tabular-nums" style={{ color: colors.value }}>{file.received}/{file.total}</span>
            {' chunks · '}
            <span style={{ color: colors.sep }}>{file.chunkSize} B/chunk</span>
            {complete && <> · <span style={{ color: colors.success }}>complete</span></>}
          </>
        }
        action={
          complete && (
            <button
              className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px]"
              style={{ height: 24, color: colors.success, borderColor: `${colors.success}66`, backgroundColor: `${colors.success}0A` }}
            >
              <Download className="size-3" />.json
            </button>
          )
        }
      />
      <div className="flex-1 overflow-auto p-5 min-h-0 space-y-3">
        <ChunkHeatmap
          label={file.filename}
          leaf={{ received: file.received, total: file.total, chunkSize: file.chunkSize }}
          tone={complete ? colors.success : colors.warning}
        />
        {complete ? (
          <pre
            className="rounded-md border p-3 font-mono text-[11px] leading-relaxed overflow-auto"
            style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgApp, color: colors.textPrimary }}
          >
            {AII_RAW}
          </pre>
        ) : (
          <div
            className="rounded-md border p-6 text-center font-mono text-[11px]"
            style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel, color: colors.dim }}
          >
            JSON preview available when transfer completes
            <div className="mt-1 text-[11px]" style={{ color: colors.sep }}>
              {file.received}/{file.total} chunks received
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// — MAG CANVAS --------------------------------------------------------

function MagCanvas({ file }: { file: FlatFile }) {
  const complete = file.received === file.total;
  const bytesApprox = file.total * file.chunkSize;
  return (
    <>
      <CanvasHeader
        kind="mag"
        source={file.source}
        name={file.filename}
        sub={
          <>
            <span className="font-mono tabular-nums" style={{ color: colors.value }}>{file.received}/{file.total}</span>
            {' chunks · '}
            <span style={{ color: colors.sep }}>{file.chunkSize} B/chunk</span>
            {complete && <> · <span style={{ color: colors.success }}>complete</span></>}
          </>
        }
        action={
          complete && (
            <button
              className="inline-flex items-center gap-1 px-2 rounded-sm border font-mono text-[11px]"
              style={{ height: 24, color: colors.warning, borderColor: `${colors.warning}66`, backgroundColor: `${colors.warning}0A` }}
            >
              <Download className="size-3" />.npz
            </button>
          )
        }
      />
      <div className="flex-1 overflow-auto p-5 min-h-0 space-y-3">
        <ChunkHeatmap
          label={file.filename}
          leaf={{ received: file.received, total: file.total, chunkSize: file.chunkSize }}
          tone={complete ? colors.success : colors.warning}
        />
        <div
          className="rounded-md border p-6 flex flex-col items-center justify-center text-center gap-3"
          style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel, minHeight: 200 }}
        >
          <FileBox className="size-10" style={{ color: colors.warning, opacity: 0.5 }} />
          <div className="font-mono text-[12px]" style={{ color: colors.textPrimary }}>
            {file.filename}
          </div>
          <div className="text-[11px] font-mono" style={{ color: colors.dim }}>
            NumPy zipped archive · ~{bytesApprox.toLocaleString()} B
          </div>
          <div className="text-[11px] font-mono max-w-[420px]" style={{ color: colors.sep }}>
            {complete
              ? '.npz is a binary container — download to inspect with numpy.load()'
              : `${file.received}/${file.total} chunks received`}
          </div>
        </div>
      </div>
    </>
  );
}

function StatsCard({ rows }: { rows: ReadonlyArray<readonly [string, string]> }) {
  return (
    <div className="rounded-md border overflow-hidden"
         style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}>
      {rows.map(([k, v], i) => (
        <div
          key={k}
          className="flex items-center justify-between px-3 py-1.5 text-[11px]"
          style={{
            borderTop: i === 0 ? 'none' : `1px solid ${colors.borderSubtle}`,
          }}
        >
          <span className="text-[11px] uppercase tracking-wider" style={{ color: colors.dim }}>{k}</span>
          <span className="font-mono tabular-nums" style={{ color: colors.value }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

// ─── RIGHT RAIL — TX, QUEUE, ACTIVITY ────────────────────────────────

function Rail({ file, activityOpen }: { file: File | null; activityOpen: boolean }) {
  return (
    <div
      className="shrink-0 flex flex-col border-l overflow-hidden"
      style={{ width: 320, borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel }}
    >
      <TxCard file={file} />
      <QueueCard />
      {activityOpen && <ActivityCard />}
    </div>
  );
}

// — TX CARD -----------------------------------------------------------

function TxCard({ file }: { file: File | null }) {
  const kind: Kind = file?.kind ?? 'image';
  const ext = kind === 'image' ? '.jpg' : kind === 'aii' ? '.json' : '.npz';
  const labels: Record<Kind, string> = { image: 'IMG', aii: 'AII', mag: 'MAG' };
  const tone = kind === 'image' ? colors.active : kind === 'aii' ? colors.success : colors.warning;
  return (
    <div className="border-b shrink-0" style={{ borderColor: colors.borderSubtle }}>
      <div
        className="flex items-center gap-2 px-3 border-b"
        style={{ borderColor: colors.borderSubtle, height: 32 }}
      >
        <Send className="size-3.5" style={{ color: tone }} />
        <span className="font-bold uppercase font-mono text-[12px]" style={{ color: colors.value, letterSpacing: '0.04em' }}>
          {labels[kind]} TX
        </span>
        <span className="text-[11px] font-mono" style={{ color: colors.sep }}>
          {file ? 'pinned to selection' : 'no selection'}
        </span>
        <div className="flex-1" />
        <RoutePill on label="HLNV" />
        <RoutePill label="ASTR" />
      </div>
      <div className="p-3 space-y-2.5">
        <ChunkRow ext={ext} />
        {kind === 'image' && (
          <>
            <Action label="cnt" cmd={`img_cnt_chunks`} ext={ext} dest />
            <Action label="get" cmd={`img_get_chunks`} ext={ext} dest range />
            <Action label="del" cmd={`img_delete`}     ext={ext} destructive />
          </>
        )}
        {kind === 'aii' && (
          <>
            <Action label="cnt" cmd="aii_cnt_chunks" ext={ext} locked />
            <Action label="get" cmd="aii_get_chunks" ext={ext} locked range />
            <Action label="del" cmd="aii_delete"     ext={ext} locked destructive />
            <DividerLabel>AI ranking</DividerLabel>
            <Action label="dir" cmd="aii_dir" ext="" extras={<><Mini placeholder="dest" /><Mini placeholder="max_tx" /></>} />
            <Action label="img" cmd="aii_img" ext={ext} extras={<Mini placeholder="dest" />} />
          </>
        )}
        {kind === 'mag' && (
          <>
            <Action label="cnt" cmd="mag_cnt_chunks" ext={ext} />
            <Action label="get" cmd="mag_get_chunks" ext={ext} range />
            <Action label="del" cmd="mag_delete"     ext={ext} destructive />
            <DividerLabel>MAG</DividerLabel>
            <Action label="cap"  cmd="mag_capture" ext={ext} extras={<><Mini placeholder="t" /><Mini placeholder="mode" /></>} />
            <Action label="kill" cmd="mag_kill"    ext="" noFilename />
            <Action label="tlm"  cmd="mag_tlm"     ext="" noFilename />
          </>
        )}
      </div>
    </div>
  );
}

function RoutePill({ on, label }: { on?: boolean; label: string }) {
  return (
    <button
      className="px-1.5 rounded-sm border font-mono text-[11px]"
      style={{
        height: 20,
        color: on ? colors.label : colors.dim,
        borderColor: on ? colors.label : colors.borderSubtle,
        backgroundColor: on ? `${colors.label}18` : 'transparent',
      }}
    >
      {label}
    </button>
  );
}

function ChunkRow({ ext }: { ext: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: colors.dim, width: 28 }}>chk</span>
      <input
        className="font-mono px-2 rounded-sm border outline-none text-[11px] tabular-nums"
        style={{ width: 64, height: 22, backgroundColor: colors.bgApp, borderColor: colors.borderSubtle, color: colors.textPrimary }}
        defaultValue="150"
      />
      <span className="inline-flex items-center gap-1 text-[11px] font-mono" style={{ color: colors.warning }}>
        <Lock className="size-3" />150
      </span>
      <span className="text-[11px] font-mono ml-auto" style={{ color: colors.sep }}>{ext} kind</span>
    </div>
  );
}

function Action({
  label, cmd, ext,
  dest, range, destructive, locked, noFilename, extras,
}: {
  label: string; cmd: string; ext: string;
  dest?: boolean; range?: boolean; destructive?: boolean; locked?: boolean; noFilename?: boolean;
  extras?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <div className="pt-1" style={{ width: 28 }}>
        <span
          className="inline-flex items-center justify-center font-mono text-[11px] rounded-sm"
          style={{
            width: 28, height: 18,
            color: destructive ? colors.danger : colors.dim,
            backgroundColor: destructive ? `${colors.danger}10` : `${colors.dim}14`,
            border: `1px solid ${destructive ? colors.danger + '44' : colors.borderSubtle}`,
            letterSpacing: '0.04em',
            fontWeight: 600,
          }}
          title={cmd}
        >
          {label}
        </span>
      </div>
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div className="flex items-center gap-1 flex-wrap">
          {!noFilename && (
            <div className="relative flex-1 min-w-[100px]">
              <input
                disabled={locked}
                defaultValue={locked ? 'transmit_dir' : ''}
                placeholder="filename"
                className="w-full pr-9 px-2 font-mono rounded-sm border outline-none text-[11px]"
                style={{ height: 22, backgroundColor: colors.bgApp, borderColor: colors.borderSubtle, color: colors.textPrimary, opacity: locked ? 0.7 : 1 }}
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] font-mono pointer-events-none" style={{ color: colors.dim }}>
                {ext}
              </span>
            </div>
          )}
          {range && <><Mini placeholder="start" w={48} /><Mini placeholder="cnt" w={48} /></>}
          {extras}
          <button
            className="px-2 rounded-sm font-mono text-[11px] btn-feedback"
            style={{
              height: 22,
              color: colors.bgApp,
              backgroundColor: destructive ? colors.danger : colors.active,
              fontWeight: 600,
            }}
            title={`Stage ${cmd}`}
          >
            stage
          </button>
        </div>
        {dest && (
          <div className="flex items-center gap-px self-start" title="0=prestored 1=full 2=thumb">
            {[
              { id: 0, label: 'STR',  active: false },
              { id: 1, label: 'FULL', active: true  },
              { id: 2, label: 'THMB', active: false },
            ].map(p => (
              <button
                key={p.id}
                className="px-1.5 border font-mono text-[11px]"
                style={{
                  height: 18,
                  color: p.active ? colors.label : colors.dim,
                  borderColor: p.active ? colors.label : colors.borderSubtle,
                  backgroundColor: p.active ? `${colors.label}18` : 'transparent',
                  letterSpacing: '0.04em',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Mini({ placeholder, w = 64 }: { placeholder: string; w?: number }) {
  return (
    <input
      className="font-mono px-1.5 rounded-sm border outline-none text-[11px] tabular-nums"
      style={{ width: w, height: 22, backgroundColor: colors.bgApp, borderColor: colors.borderSubtle, color: colors.textPrimary }}
      placeholder={placeholder}
    />
  );
}

function DividerLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <div className="flex-1" style={{ height: 1, backgroundColor: colors.borderSubtle }} />
      <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: colors.sep }}>{children}</span>
      <div className="flex-1" style={{ height: 1, backgroundColor: colors.borderSubtle }} />
    </div>
  );
}

// — QUEUE CARD --------------------------------------------------------

function QueueCard() {
  return (
    <div className="border-b shrink-0" style={{ borderColor: colors.borderSubtle }}>
      <div
        className="flex items-center gap-2 px-3 border-b"
        style={{ borderColor: colors.borderSubtle, height: 32 }}
      >
        <Send className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase font-mono text-[12px]" style={{ color: colors.value, letterSpacing: '0.04em' }}>
          Queue
        </span>
        <span className="text-[11px] font-mono ml-auto tabular-nums" style={{ color: colors.dim }}>
          {QUEUE.length}
        </span>
      </div>
      <div className="px-2 py-2 space-y-1">
        {QUEUE.map(q => (
          <div
            key={q.num}
            className="flex items-center gap-2 rounded-sm border px-2 py-1.5"
            style={{
              borderColor: q.sending ? `${colors.info}55` : colors.borderSubtle,
              backgroundColor: q.sending ? `${colors.info}0F` : colors.bgApp,
            }}
            title={q.sub}
          >
            <span className="font-mono text-[11px] tabular-nums" style={{ color: colors.sep, width: 14 }}>{q.num}</span>
            <SourceTag source={q.dest as Source} />
            <span className="font-mono text-[11px] truncate" style={{ color: colors.textPrimary }}>{q.cmdId}</span>
            {q.sending && (
              <span
                className="rounded-full ml-auto shrink-0 animate-pulse-text"
                style={{ width: 6, height: 6, backgroundColor: colors.info }}
              />
            )}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 px-2 py-2 border-t" style={{ borderColor: colors.borderSubtle }}>
        <button
          className="inline-flex items-center gap-1 px-2 rounded-sm font-mono text-[11px]"
          style={{ height: 24, color: colors.dim }}
        >
          <Trash2 className="size-3" />Clear
        </button>
        <div className="flex-1" />
        <button
          className="inline-flex items-center gap-1.5 px-3 rounded-sm font-mono text-[11px] btn-feedback"
          style={{ height: 26, color: colors.bgApp, backgroundColor: colors.success, fontWeight: 600 }}
        >
          <Send className="size-3.5" />Send all
        </button>
      </div>
    </div>
  );
}

// — ACTIVITY CARD -----------------------------------------------------

function ActivityCard() {
  // Animate a fake new entry every few seconds.
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 4500);
    return () => clearInterval(id);
  }, []);
  const tickRef = useRef(0);
  tickRef.current = tick;
  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div
        className="flex items-center gap-2 px-3 border-b"
        style={{ borderColor: colors.borderSubtle, height: 32 }}
      >
        <Activity className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase font-mono text-[12px]" style={{ color: colors.value, letterSpacing: '0.04em' }}>
          Activity
        </span>
        <span className="text-[11px] font-mono ml-auto" style={{ color: colors.sep }}>
          live
        </span>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {ACTIVITY.map((row, i) => {
          const isFresh = i === 0;
          return (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-1 text-[11px] font-mono"
              style={{
                color: colors.textPrimary,
                borderLeft: `2px solid ${row.dir === 'TX' ? colors.active : colors.success}`,
                animation: isFresh && tick > 0 ? 'preview-flash 800ms ease-out' : undefined,
              }}
            >
              <span style={{ color: colors.sep, fontSize: 11, width: 32 }}>+{(row.tMs / 1000).toFixed(1)}s</span>
              <span style={{ color: row.dir === 'TX' ? colors.active : colors.success, width: 18, fontWeight: 600 }}>{row.dir}</span>
              <span className="flex-1 truncate">{row.cmd}</span>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes preview-flash {
          0%   { background-color: ${colors.success}30; }
          100% { background-color: transparent; }
        }
      `}</style>
    </div>
  );
}

// ─── CAPTURE SHEET ───────────────────────────────────────────────────

function CaptureSheet({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="absolute inset-0 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(2px)' }}
      onClick={onClose}
    >
      <div
        className="w-[640px] rounded-md border shadow-panel"
        style={{ borderColor: `${colors.success}55`, backgroundColor: colors.bgPanel, boxShadow: `0 0 60px ${colors.success}20` }}
        onClick={e => e.stopPropagation()}
      >
        <div
          className="flex items-center gap-2 px-4 border-b"
          style={{ borderColor: colors.borderSubtle, height: 38 }}
        >
          <Camera className="size-4" style={{ color: colors.success }} />
          <span className="font-bold uppercase font-mono text-[13px]" style={{ color: colors.value, letterSpacing: '0.04em' }}>
            Capture
          </span>
          <span className="text-[11px] font-mono" style={{ color: colors.sep }}>cam_capture</span>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="inline-flex items-center justify-center"
            style={{ width: 22, height: 22, color: colors.dim }}
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3 p-4">
          {[
            ['Filename',     'capture_001'],
            ['Quantity',     '1'],
            ['Delay (s)',    '0'],
            ['Focus',        'auto'],
            ['Exposure µs',  '20000'],
            ['K cap',        '1.0'],
            ['K thumb',      '0.25'],
            ['Quality',      '80'],
          ].map(([label, ph]) => (
            <CapField key={label} label={label} ph={ph} />
          ))}
        </div>
        <div className="flex items-center gap-2 px-4 py-3 border-t" style={{ borderColor: colors.borderSubtle }}>
          <span className="text-[11px] font-mono" style={{ color: colors.dim }}>
            HLNV · cam_capture
          </span>
          <div className="flex-1" />
          <button
            className="px-3 rounded-sm font-mono text-[11px]"
            style={{ height: 26, color: colors.dim }}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="inline-flex items-center gap-1.5 px-3 rounded-sm font-mono text-[11px] btn-feedback"
            style={{ height: 26, color: colors.bgApp, backgroundColor: colors.success, fontWeight: 600 }}
          >
            <Send className="size-3" />Stage capture
          </button>
        </div>
      </div>
    </div>
  );
}

function CapField({ label, ph }: { label: string; ph: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider mb-1 font-semibold" style={{ color: colors.dim }}>{label}</div>
      <input
        className="w-full px-2 rounded-sm border outline-none font-mono text-[11px]"
        style={{ height: 24, backgroundColor: colors.bgApp, borderColor: colors.borderSubtle, color: colors.textPrimary }}
        placeholder={ph}
      />
    </div>
  );
}
