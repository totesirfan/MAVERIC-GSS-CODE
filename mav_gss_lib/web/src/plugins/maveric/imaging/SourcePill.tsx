import { colors } from '@/lib/colors';

interface SourcePillProps {
  source: string | null | undefined;
}

export function SourcePill({ source }: SourcePillProps) {
  if (!source) return null;
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full border px-1.5 py-0 font-mono text-[9px] font-bold leading-4"
      style={{
        color: colors.label,
        borderColor: `${colors.label}66`,
        backgroundColor: `${colors.label}14`,
      }}
      title={`Source ${source}`}
    >
      {source}
    </span>
  );
}
