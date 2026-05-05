/**
 * Table component for the Files page — shared across AII and Mag rows.
 * Pure presentational; row selection is owned by the parent.
 */

import { colors } from '@/lib/colors';
import { useNowMs } from '@/hooks/useNowMs';
import { SourcePill } from '../shared/SourcePill';
import type { FileKind, FileLeaf } from './types';

interface Props {
  files: FileLeaf[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (file: FileLeaf) => void;
  selectedIds?: Set<string>;
  onToggleSelected?: (id: string) => void;
  onToggleSelectAll?: () => void;
}

export function FilesTable({
  files, selectedId, onSelect, onDelete,
  selectedIds, onToggleSelected, onToggleSelectAll,
}: Props) {
  const nowMs = useNowMs();
  const showCheckbox = !!selectedIds && !!onToggleSelected;
  const allSelected = showCheckbox && files.length > 0
    && files.every(f => selectedIds!.has(f.id));
  return (
    <table className="w-full text-[11px] font-mono">
      <thead className="sticky top-0" style={{ background: colors.bgPanelRaised, color: colors.textMuted }}>
        <tr>
          {showCheckbox && (
            <th className="px-2 py-1 w-6">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={onToggleSelectAll}
                aria-label="Select all"
              />
            </th>
          )}
          <th className="text-left px-2 py-1">SOURCE</th>
          <th className="text-left px-2 py-1">FILENAME</th>
          <th className="text-left px-2 py-1">KIND</th>
          <th className="text-left px-2 py-1">PROGRESS</th>
          <th className="text-left px-2 py-1">STATUS</th>
          <th className="text-left px-2 py-1">AGE</th>
          <th className="text-right px-2 py-1"></th>
        </tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <FilesRow
            key={f.id}
            file={f}
            selected={f.id === selectedId}
            onSelect={() => onSelect(f.id)}
            onDelete={() => onDelete(f)}
            nowMs={nowMs}
            checkboxChecked={selectedIds?.has(f.id) ?? false}
            onCheckboxToggle={onToggleSelected ? () => onToggleSelected(f.id) : undefined}
          />
        ))}
        {files.length === 0 && (
          <tr>
            <td colSpan={showCheckbox ? 8 : 7} className="px-2 py-4 italic" style={{ color: colors.textMuted }}>
              no files yet
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

function FilesRow({
  file, selected, onSelect, onDelete, nowMs, checkboxChecked, onCheckboxToggle,
}: {
  file: FileLeaf;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  nowMs: number;
  checkboxChecked: boolean;
  onCheckboxToggle?: () => void;
}) {
  const progress = file.total ? `${file.received}/${file.total}` : `${file.received}/—`;
  const status = file.complete
    ? (file.valid === false ? 'invalid' : 'complete')
    : 'in-progress';
  return (
    <tr
      className="cursor-pointer border-t"
      style={{ borderColor: colors.borderSubtle, background: selected ? colors.bgPanelRaised : undefined }}
      onClick={onSelect}
    >
      {onCheckboxToggle && (
        <td className="px-2 py-1" onClick={e => e.stopPropagation()}>
          <input type="checkbox" checked={checkboxChecked} onChange={onCheckboxToggle} aria-label={`Select ${file.filename}`} />
        </td>
      )}
      <td className="px-2 py-1"><SourcePill source={file.source} /></td>
      <td className="px-2 py-1" style={{ color: colors.textPrimary }}>{file.filename}</td>
      <td className="px-2 py-1"><KindBadge kind={file.kind} /></td>
      <td className="px-2 py-1">{progress}</td>
      <td className="px-2 py-1"><StatusBadge status={status} /></td>
      <td className="px-2 py-1" style={{ color: colors.textMuted }}>{formatAge(file.last_activity_ms, nowMs)}</td>
      <td className="px-2 py-1 text-right">
        <button
          className="text-[10px] hover:underline"
          style={{ color: colors.danger }}
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
        >
          DELETE
        </button>
      </td>
    </tr>
  );
}

function KindBadge({ kind }: { kind: FileKind }) {
  const tone = kind === 'aii' ? colors.active : colors.neutral;
  return (
    <span className="text-[10px] px-1 py-[1px] border" style={{ borderColor: tone, color: tone }}>
      {kind.toUpperCase()}
    </span>
  );
}

function StatusBadge({ status }: { status: 'complete' | 'invalid' | 'in-progress' }) {
  const tone = status === 'complete'
    ? colors.success
    : status === 'invalid'
    ? colors.danger
    : colors.neutral;
  return <span className="text-[10px]" style={{ color: tone }}>{status}</span>;
}

function formatAge(ms: number | null | undefined, nowMs: number): string {
  if (ms == null) return '—';
  const diff = Math.max(0, nowMs - ms);
  if (diff < 5_000) return 'now';
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h`;
  return `${Math.floor(diff / 86_400_000)}d`;
}
