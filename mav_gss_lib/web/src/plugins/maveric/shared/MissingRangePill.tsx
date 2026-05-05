import { Download, RefreshCcw } from 'lucide-react';
import { colors } from '@/lib/colors';
import type { MissingRange } from './missingRanges';

interface MissingRangePillProps {
  received: number;
  total: number | null;
  ranges: MissingRange[];
  onClick: () => void;
}

export function MissingRangePill({ received, total, ranges, onClick }: MissingRangePillProps) {
  if (total === null) return null;
  if (total > 0 && received === total) {
    return (
      <span className="text-[11px]" style={{ color: colors.success }}>
        Complete
      </span>
    );
  }
  const missing = total - received;
  const initial = received === 0;
  const tone = initial ? colors.active : colors.warning;
  const Icon = initial ? Download : RefreshCcw;
  const label = initial ? `get ${total}` : `${missing} missing`;
  const title = initial
    ? `Download all ${total} chunks`
    : `Re-request ${missing} missing chunk${missing === 1 ? '' : 's'} (${ranges.length} range${ranges.length === 1 ? '' : 's'})`;
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-1.5 rounded-sm border font-mono text-[11px] color-transition btn-feedback"
      style={{
        height: 20,
        color: tone,
        borderColor: `${tone}66`,
        backgroundColor: `${tone}0A`,
      }}
      title={title}
    >
      <Icon className="size-2.5" />
      {label}
    </button>
  );
}
