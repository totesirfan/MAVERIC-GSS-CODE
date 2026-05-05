import { useEffect, useState } from 'react';
import { Send, Trash2, Lock, ChevronDown } from 'lucide-react';
import { GssInput } from '@/components/ui/gss-input';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { showToast } from '@/components/shared/overlays/StatusToast';
import { colors } from '@/lib/colors';
import { StageRow } from '../shared/StageRow';
import { FilenameInput } from '../shared/FilenameInput';
import { withExtension } from '../shared/extensions';
import { fileCaps, type FileKindId } from '../shared/fileKinds';
import type { TxArgSchema } from '@/lib/types';
import type { FileLeaf } from './types';

interface FilesTxControlsProps {
  kind: FileKindId;
  selected: FileLeaf | null;
  /** All known leaves of this kind from the chunk store. Used to derive
   *  the chunk_size lock (typed cnt/get filename → matched leaf →
   *  locked chunk_size). Match key is `(filename, source)`. */
  knownFiles: FileLeaf[];
  /** Operator-selected route fallback when no file is selected. */
  destNode: string;
  onDestNodeChange: (n: string) => void;
  schema: Record<string, Record<string, unknown>> | null;
  txConnected: boolean;
  queueCommand: (cmd: { cmd_id: string; args: Record<string, string>; packet: { dest: string } }) => void;
}

/**
 * Files-page TX controls for one kind. Auto-routes to the selected
 * file's source when one is selected; otherwise uses the operator-set
 * route. Renders the standard cnt/get/delete trio plus the kind's
 * extraCmds via a schema-driven generic form.
 */
export function FilesTxControls({
  kind, selected, knownFiles, destNode, onDestNodeChange,
  schema, txConnected, queueCommand,
}: FilesTxControlsProps) {
  const caps = fileCaps(kind);
  const nodes = (() => {
    const cmd = schema?.[caps.getCmd];
    const allowed = ((cmd as { nodes?: string[] } | undefined)?.nodes) ?? [];
    return allowed.length > 0 ? allowed : [...caps.fallbackNodes];
  })();
  // Resolution chain matches imaging/TxControlsPanel: file source wins
  // when a file is selected; otherwise operator-set route; otherwise
  // first available node so commands like `aii_dir` (no file context)
  // still have a valid dest.
  const effectiveDest =
    (selected?.source && nodes.includes(selected.source) ? selected.source : '')
    || destNode
    || nodes[0]
    || '';

  // Pre-fill cnt/get/delete inputs from caps.defaultFilename when set.
  // AII has `defaultFilename = 'transmit_dir'` because all AII downlinks
  // are the singleton top-N AI-ranked candidate list. Image / MAG have
  // no canonical default — operator names every file.
  const [cntFn, setCntFn] = useState<string>(caps.defaultFilename ?? '');
  const [getFn, setGetFn] = useState<string>(caps.defaultFilename ?? '');
  const [getStart, setGetStart] = useState('');
  const [getCount, setGetCount] = useState('');
  const [delFn, setDelFn] = useState<string>(caps.defaultFilename ?? '');
  const [extrasOpen, setExtrasOpen] = useState(false);
  // Shared chunk-size for cnt/get. Default to selected file's chunk_size
  // when one is selected (so restage matches what was downloaded), else
  // '150' to mirror imaging's default.
  const [chunkSize, setChunkSize] = useState<string>(() =>
    selected?.chunk_size != null ? String(selected.chunk_size) : '150',
  );

  // ── chunk_size lock ─────────────────────────────────────────────
  // If the typed cnt or get filename matches a known file, lock the
  // chunk_size for THAT row to that file's recorded chunk_size. Mixing
  // sizes against the same filename would corrupt the spacecraft-side
  // slicing AND the local assembly. Deleting the file removes the
  // store entry → no match → input unlocks. Typing a different name
  // also unlocks. Match key: (filename, source).
  //
  // Per-row resolution: Count and Get can name different known files
  // with different sizes. The shared input shows a unanimous lock when
  // both rows agree (or one is unlocked); when they conflict, the
  // shared input is left to the operator and each stage uses its own
  // row's lock.
  function lockedSizeForTyped(typedFn: string): number | null {
    const trimmed = typedFn.trim();
    if (!trimmed) return null;
    const fn = withExtension(trimmed, kind);
    const matchSourceFirst =
      knownFiles.find(f => f.filename === fn && f.source === effectiveDest);
    const match =
      matchSourceFirst ?? knownFiles.find(f => f.filename === fn);
    return match?.chunk_size ?? null;
  }
  const lockFromCnt = lockedSizeForTyped(cntFn);
  const lockFromGet = lockedSizeForTyped(getFn);
  const lockConflict =
    lockFromCnt != null && lockFromGet != null && lockFromCnt !== lockFromGet;
  const sharedLock = lockConflict ? null : (lockFromCnt ?? lockFromGet);

  // Force the input value when a unanimous lock engages. When the lock
  // releases (filename cleared or file deleted), the input keeps its
  // last value but becomes editable again.
  useEffect(() => {
    if (sharedLock != null) setChunkSize(String(sharedLock));
  }, [sharedLock]);

  const stage = (cmdId: string, args: Record<string, string>) => {
    if (!txConnected) { showToast('TX not connected', 'error', 'tx'); return; }
    if (!effectiveDest) { showToast('No destination node selected', 'error', 'tx'); return; }
    queueCommand({ cmd_id: cmdId, args, packet: { dest: effectiveDest } });
  };

  return (
    <div
      className="rounded-md border overflow-hidden flex flex-col flex-1 min-h-0"
      style={{ borderColor: colors.borderSubtle, backgroundColor: colors.bgPanel, boxShadow: '0 1px 3px rgba(0,0,0,0.4)' }}
    >
      <div
        className="flex items-center gap-2 px-3 border-b flex-wrap"
        style={{ borderColor: colors.borderSubtle, minHeight: 34, paddingTop: 6, paddingBottom: 6 }}
      >
        <Send className="size-3.5" style={{ color: colors.dim }} />
        <span className="font-bold uppercase" style={{ color: colors.value, fontSize: 14, letterSpacing: '0.02em' }}>
          {caps.label} TX
        </span>
        {caps.defaultFilename ? (
          <span
            className="inline-flex items-center gap-1 text-[10px] font-mono"
            style={{ color: colors.warning }}
            title={`Spacecraft accepts only ${withExtension(caps.defaultFilename, kind)} for this kind. Use the main TX panel for ad-hoc filenames.`}
          >
            <Lock className="size-3" />{withExtension(caps.defaultFilename, kind)}
          </span>
        ) : caps.subtitle && (
          <span className="text-[11px] font-mono normal-case" style={{ color: colors.dim }}>
            {caps.subtitle}
          </span>
        )}
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {nodes.map(n => {
            const active = effectiveDest === n;
            return (
              <button
                key={n}
                onClick={() => onDestNodeChange(n)}
                disabled={!!selected}
                className="px-2 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
                style={{
                  height: 20,
                  color: active ? colors.label : colors.dim,
                  borderColor: active ? colors.label : colors.borderSubtle,
                  backgroundColor: active ? `${colors.label}18` : 'transparent',
                  opacity: selected ? 0.6 : 1,
                  cursor: selected ? 'not-allowed' : 'pointer',
                }}
                title={selected ? `Auto-routed to ${selected.source}` : `Route · ${n}`}
              >
                {n}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: colors.dim }}>
            Chunk
          </span>
          <GssInput
            className="w-[72px] font-mono"
            placeholder="150"
            value={chunkSize}
            onChange={e => setChunkSize(e.target.value)}
            disabled={sharedLock != null}
            title={
              sharedLock != null
                ? `Locked to ${sharedLock} — delete the file to recount at a different size`
                : lockConflict
                ? `Count → ${lockFromCnt}, Get → ${lockFromGet} — staged sizes resolved per row`
                : 'bytes per chunk · applied to count + get'
            }
          />
          {sharedLock != null && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono" style={{ color: colors.warning }} title={`Locked to ${sharedLock} — delete file to recount`}>
              <Lock className="size-3" />{sharedLock}
            </span>
          )}
          {lockConflict && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono" style={{ color: colors.danger }} title={`Count → ${lockFromCnt}, Get → ${lockFromGet}; each row stages with its own lock`}>
              <Lock className="size-3" />conflict {lockFromCnt}/{lockFromGet}
            </span>
          )}
        </div>

        <StageRow
          label="Count Chunks"
          sublabel={caps.cntCmd}
          kind={kind}
          filenameValue={cntFn}
          onFilenameChange={setCntFn}
          filenameDisabled={!!caps.defaultFilename}
          onStage={() => stage(caps.cntCmd, {
            filename: withExtension(cntFn.trim(), kind),
            // Per-row resolution: Count's own lock wins over the shared input.
            chunk_size: lockFromCnt != null ? String(lockFromCnt) : chunkSize.trim(),
          })}
        />

        <StageRow
          label="Get Chunks"
          sublabel={`${caps.getCmd} · contiguous range`}
          kind={kind}
          filenameValue={getFn}
          onFilenameChange={setGetFn}
          filenameDisabled={!!caps.defaultFilename}
          extras={
            <>
              <GssInput className="w-[52px] font-mono" placeholder="start" value={getStart} onChange={e => setGetStart(e.target.value)} />
              <GssInput className="w-[52px] font-mono" placeholder="count" value={getCount} onChange={e => setGetCount(e.target.value)} />
            </>
          }
          onStage={() => stage(caps.getCmd, {
            filename: withExtension(getFn.trim(), kind),
            start_chunk: getStart.trim(),
            num_chunks: getCount.trim(),
            // Per-row resolution: Get's own lock wins over the shared input.
            chunk_size: lockFromGet != null ? String(lockFromGet) : chunkSize.trim(),
          })}
        />

        <StageRow
          label={<><Trash2 className="size-3 inline mr-1" />{caps.deleteCmd}</>}
          kind={kind}
          filenameValue={delFn}
          onFilenameChange={setDelFn}
          filenameDisabled={!!caps.defaultFilename}
          tone="destructive"
          onStage={() => {
            const fn = delFn.trim();
            if (!fn) { showToast('Filename required', 'error', 'tx'); return; }
            stage(caps.deleteCmd, { filename: withExtension(fn, kind) });
          }}
        />

        {caps.extraCmds.length > 0 && (
          <Collapsible
            open={extrasOpen}
            onOpenChange={setExtrasOpen}
            className="border-t pt-2 -mx-3 px-3"
            style={{ borderColor: colors.borderSubtle }}
          >
            <CollapsibleTrigger
              className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider w-full text-left hover:opacity-80 transition-opacity outline-none"
              style={{ color: colors.dim }}
            >
              <ChevronDown
                className="size-3 transition-transform duration-200"
                style={{ transform: extrasOpen ? 'rotate(0deg)' : 'rotate(-90deg)' }}
              />
              Extra commands
              <span className="font-mono normal-case ml-1" style={{ color: colors.sep }}>
                {caps.extraCmds.length}
              </span>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2 space-y-2">
              {caps.extraCmds.map(cmdId => (
                <ExtraCmdRow
                  key={cmdId}
                  cmdId={cmdId}
                  /* Per-cmd override: aii_img.filename is image, not aii. */
                  filenameKind={caps.extraCmdFilenameKind[cmdId] ?? kind}
                  schema={schema?.[cmdId] ?? null}
                  onStage={(args) => stage(cmdId, args)}
                />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  );
}

/** True when an arg should be treated as a filename (renders FilenameInput
 *  + has the kind's extension auto-appended on stage). Matches the mission
 *  schema's two filename conventions: arg name === 'filename' OR
 *  arg type === 'Filename'. Covers `aii_img.filename`, `mag_capture.filename`,
 *  the cnt/get/delete trio, etc. */
function isFilenameArg(arg: TxArgSchema): boolean {
  return arg.name === 'filename' || arg.type === 'Filename';
}

interface ExtraCmdRowProps {
  cmdId: string;
  /** Which file kind's extension to apply to the filename arg. May
   *  differ from the surrounding row's kind — see
   *  FileKindCaps.extraCmdFilenameKind. */
  filenameKind: FileKindId;
  /** /api/schema entry for this cmd_id (mirrors backend `CommandSchemaItem`).
   *  Field is `tx_args`, not `args` — matches mav_gss_lib/web/src/lib/types.ts. */
  schema: Record<string, unknown> | null;
  onStage: (args: Record<string, string>) => void;
}

/** Schema-driven generic form: one input per declared arg, in order.
 *  Filename-shaped args (name='filename' or type='Filename') render
 *  through `FilenameInput` for `filenameKind` so the right ghost
 *  suffix shows, and get `withExtension(_, filenameKind)` applied on
 *  submit. Non-filename args stay as plain `GssInput` and are
 *  submitted verbatim. */
function ExtraCmdRow({ cmdId, filenameKind, schema, onStage }: ExtraCmdRowProps) {
  const txArgs = (schema?.tx_args as TxArgSchema[] | undefined) ?? [];
  const argNames = txArgs.map(a => a.name);
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <div>
      <div className="text-[10px] font-mono mb-1" style={{ color: colors.sep }}>{cmdId}</div>
      <div className="flex items-end gap-2 flex-wrap">
        {argNames.length === 0 && (
          <span className="text-[10px] italic" style={{ color: colors.dim }}>(no args)</span>
        )}
        {txArgs.map(arg => (
          <div key={arg.name} style={isFilenameArg(arg) ? { flex: '1 1 200px', minWidth: 160 } : undefined}>
            <div className="text-[9px] uppercase tracking-wider mb-0.5 font-semibold" style={{ color: colors.dim }}>
              {arg.name}
              {arg.optional && <span className="ml-1" style={{ color: colors.sep }}>?</span>}
            </div>
            {isFilenameArg(arg) ? (
              <FilenameInput
                kind={filenameKind}
                value={values[arg.name] ?? ''}
                onChange={(v) => setValues((prev) => ({ ...prev, [arg.name]: v }))}
              />
            ) : (
              <GssInput
                className="w-[120px] font-mono"
                value={values[arg.name] ?? ''}
                onChange={e => setValues(v => ({ ...v, [arg.name]: e.target.value }))}
                title={arg.description}
              />
            )}
          </div>
        ))}
        <div className="flex-1" />
        <Button
          size="sm"
          onClick={() => {
            const submitArgs: Record<string, string> = {};
            for (const arg of txArgs) {
              const raw = (values[arg.name] ?? '').trim();
              submitArgs[arg.name] = isFilenameArg(arg) && raw !== '' ? withExtension(raw, filenameKind) : raw;
            }
            onStage(submitArgs);
          }}
          style={{ backgroundColor: colors.active, color: colors.bgApp }}
        >
          Stage
        </Button>
      </div>
    </div>
  );
}
