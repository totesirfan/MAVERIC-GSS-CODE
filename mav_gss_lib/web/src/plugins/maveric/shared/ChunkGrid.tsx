import { colors } from '@/lib/colors';
import type { MissingRange } from './missingRanges';

interface ChunkGridProps {
  total: number;
  chunkSet: Set<number>;
  onRestageRange: (range: MissingRange) => void;
}

/** Wrap-flow grid of one dot per chunk. Green = received (disabled),
 *  red-outlined = missing (clickable to restage that single chunk). */
export function ChunkGrid({ total, chunkSet, onRestageRange }: ChunkGridProps) {
  if (total <= 0) return null;
  return (
    <div className="flex flex-wrap gap-[3px]">
      {Array.from({ length: total }, (_, i) => {
        const received = chunkSet.has(i);
        return (
          <button
            key={i}
            disabled={received}
            onClick={() => onRestageRange({ start: i, end: i, count: 1 })}
            title={received ? `Chunk ${i}` : `Chunk ${i} (click to re-request)`}
            className="rounded-full"
            style={{
              width: 8,
              height: 8,
              backgroundColor: received ? colors.success : 'transparent',
              border: received ? 'none' : `1px solid ${colors.danger}`,
              cursor: received ? 'default' : 'pointer',
              boxSizing: 'border-box',
              padding: 0,
            }}
          />
        );
      })}
    </div>
  );
}
