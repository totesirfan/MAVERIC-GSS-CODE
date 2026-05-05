import { useState, useEffect, useRef, useMemo } from 'react';
import {
  Send,
  Camera,
  Download,
  Power,
  PowerOff,
  Monitor,
  Eraser,
  Trash2,
  Lock,
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { GssInput } from '@/components/ui/gss-input';
import { showToast } from '@/components/shared/overlays/StatusToast';
import { colors } from '@/lib/colors';
import { withJpg } from './helpers';
import { FilenameInput } from '../shared/FilenameInput';
import { fileCaps } from '../shared/fileKinds';
import { StageRow } from '../shared/StageRow';
import type { PairedFile, ImagingTab, FileLeaf } from './types';

interface TxControlsPanelProps {
  nodes: string[];
  destNode: string;
  onDestNodeChange: (n: string) => void;
  selected: PairedFile | null;
  /** Full paired-file list — used to look up the locked chunk_size when
   *  the operator's typed Count/Get filename matches a known leaf. */
  files: PairedFile[];
  previewTab: ImagingTab;
  thumbPrefix: string;
  queueCommand: (cmd: { cmd_id: string; args: Record<string, string>; packet: { dest: string } }) => void;
  schema: Record<string, Record<string, unknown>> | null;
  txConnected: boolean;
}

type TabName = 'download' | 'camera' | 'lcd';
type DestId = 0 | 1 | 2;
type DestOverride = DestId | null;

/** Imaging folder destinations — match mission.yml description on the
 *  destination arg ("0=prestored_images, 1=captured_images, 2=thumbnails"). */
const DEST_OPTIONS: ReadonlyArray<{ id: DestId; label: string; title: string }> = [
  { id: 0, label: 'STR', title: 'Destination 0 · prestored_images (factory-loaded)' },
  { id: 1, label: 'FULL', title: 'Destination 1 · captured_images (full)' },
  { id: 2, label: 'THMB', title: 'Destination 2 · thumbnails' },
];

/** Auto-derive destination from filename: thumb-prefix → 2, otherwise 1.
 *  Prestored (0) is never inferred from the filename; it must be set
 *  explicitly via the operator override. */
function destFromFilename(fn: string, thumbPrefix: string): string {
  if (thumbPrefix && fn.startsWith(thumbPrefix)) return '2';
  return '1';
}

/** Resolve the destination string used on the wire: explicit override
 *  wins, otherwise fall back to filename-derived. */
function resolveDest(override: DestOverride, fn: string, thumbPrefix: string): string {
  return override !== null ? String(override) : destFromFilename(fn, thumbPrefix);
}

/** Three-segment destination selector. Highlighted = current effective
 *  destination. Click to override; click the matching pill to release
 *  back to filename-auto-derive. */
function DestSelect({
  effective,
  override,
  onChange,
}: {
  effective: number;
  override: DestOverride;
  onChange: (d: DestOverride) => void;
}) {
  return (
    <div className="flex items-center gap-px">
      {DEST_OPTIONS.map(({ id, label, title }) => {
        const active = effective === id;
        const explicitlyOverridden = override === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onChange(explicitlyOverridden ? null : id)}
            className="px-1.5 border font-mono text-[10px] color-transition btn-feedback"
            style={{
              height: 22,
              color: active ? colors.label : colors.dim,
              borderColor: active ? colors.label : colors.borderSubtle,
              backgroundColor: active ? `${colors.label}18` : 'transparent',
            }}
            title={title + (explicitlyOverridden ? ' · click to clear override' : '')}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

export function TxControlsPanel({
  nodes,
  destNode,
  onDestNodeChange,
  selected,
  files,
  previewTab,
  thumbPrefix,
  queueCommand,
  txConnected,
}: TxControlsPanelProps) {
  const [activeTab, setActiveTab] = useState<TabName>('download');

  // ── Download tab form state + auto-fill ─────────────────────────
  const [cntFn, setCntFn] = useState('');
  const [getFn, setGetFn] = useState('');
  const [getStart, setGetStart] = useState('');
  const [getCount, setGetCount] = useState('');
  // Combined chunk size shared by Count Chunks + Get Chunks. Default 150 B.
  const [chunkSize, setChunkSize] = useState('150');
  // Per-row destination override (0/1/2). null = use filename auto-derive.
  // Operator clicks a pill to force a destination; clicking the matching
  // pill again clears the override and falls back to auto.
  const [cntDest, setCntDest] = useState<DestOverride>(null);
  const [getDest, setGetDest] = useState<DestOverride>(null);
  const [lcdDest, setLcdDest] = useState<DestOverride>(null);

  // Look up the locked chunk_size for a typed cnt/get filename.
  // Match key (filename, source, destination): destination is implicit
  // in the filename via the thumb prefix, but we re-check it here so a
  // typo never silently desyncs. Source preference: current route, fall
  // back to any leaf. Returns the locked size, or null if no match.
  const allLeaves = useMemo<FileLeaf[]>(
    () => files.flatMap(p => [p.full, p.thumb].filter((l): l is FileLeaf => !!l)),
    [files],
  );
  const lockedSizeForTyped = (typedFn: string): number | null => {
    const trimmed = typedFn.trim();
    if (!trimmed) return null;
    const fn = withJpg(trimmed);
    const expectedDest = destFromFilename(fn, thumbPrefix);
    const matchSource = allLeaves.find(l => l.filename === fn && l.source === destNode);
    const match = matchSource ?? allLeaves.find(l => l.filename === fn);
    if (!match) return null;
    if (destFromFilename(match.filename, thumbPrefix) !== expectedDest) return null;
    return match.chunk_size ?? null;
  };
  const lockFromCnt = lockedSizeForTyped(cntFn);
  const lockFromGet = lockedSizeForTyped(getFn);
  // Conflict = both rows lock to different sizes. Each row stages with
  // its own lock regardless; the shared input shows neither value.
  const lockConflict =
    lockFromCnt != null && lockFromGet != null && lockFromCnt !== lockFromGet;
  const sharedLock = lockConflict ? null : (lockFromCnt ?? lockFromGet);
  useEffect(() => {
    if (sharedLock != null) setChunkSize(String(sharedLock));
  }, [sharedLock]);

  const autoRef = useRef({ cntFn: '', getFn: '', start: '', count: '' });

  // Source filename = whichever leaf matches the Preview's active tab.
  // If one side is null (prefix unset, orphan pair), fall back to the
  // side that exists so auto-fill still works.
  const effectiveLeaf = selected
    ? !selected.thumb
      ? selected.full
      : !selected.full
      ? selected.thumb
      : previewTab === 'thumb'
      ? selected.thumb
      : selected.full
    : null;
  const suggestedFilename = effectiveLeaf?.filename ?? '';
  const suggestedTotal = effectiveLeaf?.total ?? null;

  useEffect(() => {
    if (!suggestedFilename) return;
    const lastCnt = autoRef.current.cntFn;
    const lastGet = autoRef.current.getFn;
    setCntFn(prev => (prev === '' || prev === lastCnt ? suggestedFilename : prev));
    setGetFn(prev => (prev === '' || prev === lastGet ? suggestedFilename : prev));
    autoRef.current.cntFn = suggestedFilename;
    autoRef.current.getFn = suggestedFilename;
  }, [suggestedFilename]);

  // Smart resume autofill — when a file has a known total and partial
  // chunks already received, default Start/Count to "download the rest"
  // instead of "download everything again". For in-order arrivals this
  // is exact; for sparse gaps, operator clicks individual red dots in
  // Progress to cherry-pick.
  const suggestedReceived = effectiveLeaf?.received ?? 0;
  useEffect(() => {
    if (!suggestedFilename || suggestedTotal == null || suggestedTotal <= 0) return;
    const remaining = suggestedTotal - suggestedReceived;
    const startNum = remaining > 0 && suggestedReceived > 0 ? suggestedReceived : 0;
    const countNum = remaining > 0 ? remaining : suggestedTotal;
    const startStr = String(startNum);
    const countStr = String(countNum);
    const lastStart = autoRef.current.start;
    const lastCount = autoRef.current.count;
    setGetStart(prev => (prev === '' || prev === lastStart ? startStr : prev));
    setGetCount(prev => (prev === '' || prev === lastCount ? countStr : prev));
    autoRef.current.start = startStr;
    autoRef.current.count = countStr;
  }, [suggestedFilename, suggestedTotal, suggestedReceived]);

  // Camera tab — all args required per commands.yml cam_capture schema
  const [capFn, setCapFn] = useState('');
  const [capQty, setCapQty] = useState('1');
  const [capDelay, setCapDelay] = useState('');
  const [capFocus, setCapFocus] = useState('');
  const [capExposure, setCapExposure] = useState('');
  const [capK, setCapK] = useState('');
  const [capThumbK, setCapThumbK] = useState('');
  const [capQuality, setCapQuality] = useState('');

  // Delete (moved into Download tab)
  const [delFn, setDelFn] = useState('');

  // LCD tab
  const [lcdFn, setLcdFn] = useState('');

  // ── Stage helpers ──────────────────────────────────────────────
  const stage = (cmdId: string, args: Record<string, string>) => {
    if (!txConnected) {
      showToast('TX not connected', 'error', 'tx');
      return;
    }
    if (!destNode) {
      showToast('No destination node selected', 'error', 'tx');
      return;
    }
    queueCommand({
      cmd_id: cmdId,
      args,
      packet: { dest: destNode },
    });
  };

  return (
    <div
      className="rounded-md border overflow-hidden flex flex-col flex-1 min-h-0"
      style={{
        borderColor: colors.borderSubtle,
        backgroundColor: colors.bgPanel,
        boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
      }}
    >
      {/* Header — title + Route + Target chips */}
      <div
        className="flex items-center gap-2 px-3 border-b flex-wrap"
        style={{
          borderColor: colors.borderSubtle,
          minHeight: 34,
          paddingTop: 6,
          paddingBottom: 6,
        }}
      >
        <Send className="size-3.5" style={{ color: colors.dim }} />
        <span
          className="font-bold uppercase"
          style={{
            color: colors.value,
            fontSize: 14,
            letterSpacing: '0.02em',
          }}
        >
          Imaging TX Controls
        </span>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {nodes.map(n => {
            const active = destNode === n;
            return (
              <button
                key={n}
                onClick={() => onDestNodeChange(n)}
                className="px-2 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
                style={{
                  height: 20,
                  color: active ? colors.label : colors.dim,
                  borderColor: active ? colors.label : colors.borderSubtle,
                  backgroundColor: active ? `${colors.label}18` : 'transparent',
                }}
                title={`Route · ${n}`}
              >
                {n}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabName)} className="flex-1 flex flex-col min-h-0">
        <TabsList className="h-auto w-full grid grid-cols-3 gap-0 border-b rounded-none p-0" style={{ borderColor: colors.borderSubtle }}>
          <TabsTrigger value="download" className="gap-1.5 text-[10px] py-2 uppercase tracking-wider rounded-none">
            <Download className="size-3" />Download
          </TabsTrigger>
          <TabsTrigger value="camera" className="gap-1.5 text-[10px] py-2 uppercase tracking-wider rounded-none">
            <Camera className="size-3" />Cam
          </TabsTrigger>
          <TabsTrigger value="lcd" className="gap-1.5 text-[10px] py-2 uppercase tracking-wider rounded-none">
            <Monitor className="size-3" />LCD
          </TabsTrigger>
        </TabsList>

        {/* Download */}
        <TabsContent value="download" className="flex-1 overflow-y-auto p-3 space-y-4 mt-0">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: colors.dim }}>
              Chunk Size <span className="font-mono normal-case ml-1" style={{ color: colors.sep }}>shared · bytes per chunk</span>
            </div>
            <div className="flex items-end gap-2 flex-wrap">
              <GssInput
                className="w-[80px] font-mono"
                placeholder="150"
                value={chunkSize}
                onChange={e => setChunkSize(e.target.value)}
                disabled={sharedLock != null}
                title={
                  sharedLock != null
                    ? `Locked to ${sharedLock} — delete the file to recount at a different size`
                    : lockConflict
                    ? `Count → ${lockFromCnt}, Get → ${lockFromGet} — staged sizes resolved per row`
                    : undefined
                }
              />
              {sharedLock != null && (
                <span className="text-[10px] font-mono inline-flex items-center gap-1" style={{ color: colors.warning }}>
                  <Lock className="size-3" />locked to {sharedLock} · delete file to recount at a different size
                </span>
              )}
              {lockConflict && (
                <span className="text-[10px] font-mono inline-flex items-center gap-1" style={{ color: colors.danger }}>
                  <Lock className="size-3" />Count → {lockFromCnt}, Get → {lockFromGet} · staged per row
                </span>
              )}
              {sharedLock == null && !lockConflict && (
                <span className="text-[10px] font-mono" style={{ color: colors.dim }}>
                  applied to {fileCaps('image').cntCmd} & {fileCaps('image').getCmd}
                </span>
              )}
            </div>
          </div>

          <StageRow
            label="Count Chunks"
            sublabel={fileCaps('image').cntCmd}
            kind="image"
            filenameValue={cntFn}
            onFilenameChange={setCntFn}
            thumbPrefix={thumbPrefix}
            extras={
              <DestSelect
                effective={Number(resolveDest(cntDest, withJpg(cntFn.trim()), thumbPrefix))}
                override={cntDest}
                onChange={setCntDest}
              />
            }
            onStage={() => {
              const fn = withJpg(cntFn.trim());
              stage(fileCaps('image').cntCmd, {
                filename: fn,
                destination: resolveDest(cntDest, fn, thumbPrefix),
                chunk_size: lockFromCnt != null ? String(lockFromCnt) : chunkSize.trim(),
              });
            }}
          />

          <StageRow
            label="Get Chunks"
            sublabel={`${fileCaps('image').getCmd} · contiguous range`}
            kind="image"
            filenameValue={getFn}
            onFilenameChange={setGetFn}
            thumbPrefix={thumbPrefix}
            extras={
              <>
                <GssInput
                  className="w-[52px] font-mono"
                  placeholder="start"
                  value={getStart}
                  onChange={e => setGetStart(e.target.value)}
                />
                <GssInput
                  className="w-[52px] font-mono"
                  placeholder="count"
                  value={getCount}
                  onChange={e => setGetCount(e.target.value)}
                />
                <DestSelect
                  effective={Number(resolveDest(getDest, withJpg(getFn.trim()), thumbPrefix))}
                  override={getDest}
                  onChange={setGetDest}
                />
              </>
            }
            onStage={() => {
              const fn = withJpg(getFn.trim());
              stage(fileCaps('image').getCmd, {
                filename: fn,
                start_chunk: getStart.trim(),
                num_chunks: getCount.trim(),
                destination: resolveDest(getDest, fn, thumbPrefix),
                chunk_size: lockFromGet != null ? String(lockFromGet) : chunkSize.trim(),
              });
            }}
          />

          <StageRow
            label={<><Trash2 className="size-3 inline mr-1" />{fileCaps('image').deleteCmd}</>}
            kind="image"
            filenameValue={delFn}
            onFilenameChange={setDelFn}
            thumbPrefix={thumbPrefix}
            tone="destructive"
            onStage={() => {
              const fn = delFn.trim();
              if (!fn) {
                showToast('Filename required', 'error', 'tx');
                return;
              }
              stage(fileCaps('image').deleteCmd, { filename: withJpg(fn) });
            }}
          />
        </TabsContent>

        {/* Camera */}
        <TabsContent value="camera" className="flex-1 overflow-y-auto p-3 space-y-3 mt-0">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: colors.dim }}>
              cam_capture
            </div>

            {/* Row 1 — target file + capture timing */}
            <div className="flex items-end gap-2 mb-2">
              <LabeledField label="Filename" className="flex-1 min-w-[140px]">
                <FilenameInput kind="image" value={capFn} onChange={setCapFn} thumbPrefix={thumbPrefix} />
              </LabeledField>
              <LabeledField label="Qty" width={56}>
                <GssInput
                  className="w-[56px] font-mono"
                  value={capQty}
                  onChange={e => setCapQty(e.target.value)}
                />
              </LabeledField>
              <LabeledField label="Delay (s)" width={72}>
                <GssInput
                  className="w-[72px] font-mono"
                  value={capDelay}
                  onChange={e => setCapDelay(e.target.value)}
                />
              </LabeledField>
            </div>

            {/* Row 2 — image settings + stage */}
            <div className="flex items-end gap-2">
              <LabeledField label="Focus" width={64}>
                <GssInput
                  className="w-[64px] font-mono"
                  value={capFocus}
                  onChange={e => setCapFocus(e.target.value)}
                />
              </LabeledField>
              <LabeledField label="Exposure Time" width={80}>
                <GssInput
                  className="w-[80px] font-mono"
                  value={capExposure}
                  onChange={e => setCapExposure(e.target.value)}
                />
              </LabeledField>
              <LabeledField label="K" width={52}>
                <GssInput
                  className="w-[52px] font-mono"
                  value={capK}
                  onChange={e => setCapK(e.target.value)}
                />
              </LabeledField>
              <LabeledField label="Thumb K" width={64}>
                <GssInput
                  className="w-[64px] font-mono"
                  value={capThumbK}
                  onChange={e => setCapThumbK(e.target.value)}
                />
              </LabeledField>
              <LabeledField label="Quality" width={64}>
                <GssInput
                  className="w-[64px] font-mono"
                  value={capQuality}
                  onChange={e => setCapQuality(e.target.value)}
                />
              </LabeledField>
              <div className="flex-1" />
              <Button
                size="sm"
                onClick={() => {
                  const fn = capFn.trim();
                  const qty = capQty.trim();
                  const delay = capDelay.trim();
                  const focus = capFocus.trim();
                  const exposure = capExposure.trim();
                  const k = capK.trim();
                  const thumbK = capThumbK.trim();
                  const quality = capQuality.trim();
                  if (!fn) { showToast('Filename required', 'error', 'tx'); return; }
                  if (!qty) { showToast('Quantity required', 'error', 'tx'); return; }
                  if (!delay) { showToast('Delay required', 'error', 'tx'); return; }
                  if (!focus) { showToast('Focus required', 'error', 'tx'); return; }
                  if (!exposure) { showToast('Exposure Time required', 'error', 'tx'); return; }
                  if (!k) { showToast('K required', 'error', 'tx'); return; }
                  if (!thumbK) { showToast('Thumb K required', 'error', 'tx'); return; }
                  if (!quality) { showToast('Quality required', 'error', 'tx'); return; }
                  stage('cam_capture', {
                    filename: withJpg(fn),
                    quantity: qty,
                    dt: delay,
                    focus,
                    exposure_us: exposure,
                    k_cap: k,
                    k_thumb: thumbK,
                    quality,
                  });
                }}
                style={{ backgroundColor: colors.active, color: colors.bgApp }}
              >
                Stage
              </Button>
            </div>
          </div>

          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: colors.dim }}>
              Power
            </div>
            <div className="flex gap-1.5">
              <Button size="sm" variant="secondary" className="flex-1" onClick={() => stage('cam_on', {})}>
                <Power className="size-3" /> cam_on
              </Button>
              <Button size="sm" variant="secondary" className="flex-1" onClick={() => stage('cam_off', {})}>
                <PowerOff className="size-3" /> cam_off
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* LCD */}
        <TabsContent value="lcd" className="flex-1 overflow-y-auto p-3 space-y-3 mt-0">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: colors.dim }}>
              lcd_display
            </div>
            <div className="flex items-end gap-2">
              <FilenameInput
                kind="image"
                className="flex-1"
                value={lcdFn}
                onChange={setLcdFn}
                thumbPrefix={thumbPrefix}
              />
              <DestSelect
                effective={Number(resolveDest(lcdDest, withJpg(lcdFn.trim()), thumbPrefix))}
                override={lcdDest}
                onChange={setLcdDest}
              />
              <Button
                size="sm"
                onClick={() => {
                  const fn = lcdFn.trim();
                  if (!fn) {
                    showToast('Filename required', 'error', 'tx');
                    return;
                  }
                  const wrapped = withJpg(fn);
                  stage('lcd_display', {
                    filename: wrapped,
                    destination: resolveDest(lcdDest, wrapped, thumbPrefix),
                  });
                }}
                style={{ backgroundColor: colors.active, color: colors.bgApp }}
              >
                Stage
              </Button>
            </div>
          </div>

          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: colors.dim }}>
              Power / Clear
            </div>
            <div className="flex gap-1.5">
              <Button size="sm" variant="secondary" className="flex-1" onClick={() => stage('lcd_on', {})}>
                <Power className="size-3" /> lcd_on
              </Button>
              <Button size="sm" variant="secondary" className="flex-1" onClick={() => stage('lcd_off', {})}>
                <PowerOff className="size-3" /> lcd_off
              </Button>
              <Button size="sm" variant="secondary" className="flex-1" onClick={() => stage('lcd_clear', {})}>
                <Eraser className="size-3" /> lcd_clear
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function LabeledField({
  label,
  width,
  className = '',
  children,
}: {
  label: string;
  width?: number;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={className} style={width ? { width } : undefined}>
      <div
        className="text-[9px] uppercase tracking-wider mb-0.5 font-semibold"
        style={{ color: colors.dim }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}
