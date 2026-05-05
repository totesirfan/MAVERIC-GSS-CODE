import { useMemo } from 'react';
import { useNowMs } from '@/hooks/useNowMs';
import { RxLogPanel } from '../shared/RxLogPanel';
import { isFileKindRxPacket } from '../missionFacts';
import { fileCaps, type FileKindId, allKinds } from '../shared/fileKinds';
import type { ColumnDef, RxPacket } from '@/lib/types';

interface FilesRxLogPanelProps {
  /** When 'all', OR predicates across aii + mag (excludes image — that
   *  has its own page). */
  filter: 'all' | 'aii' | 'mag';
  packets: RxPacket[];
  columns?: ColumnDef[];
}

const FLAT_KINDS: FileKindId[] = allKinds().filter(k => k !== 'image');

export function FilesRxLogPanel({ filter, packets, columns }: FilesRxLogPanelProps) {
  const nowMs = useNowMs();
  const filtered = useMemo<RxPacket[]>(() => {
    if (filter === 'all') {
      const capsList = FLAT_KINDS.map(fileCaps);
      return packets.filter(p => capsList.some(c => isFileKindRxPacket(p, c)));
    }
    const caps = fileCaps(filter);
    return packets.filter(p => isFileKindRxPacket(p, caps));
  }, [packets, filter]);

  const lastMs = filtered[filtered.length - 1]?.received_at_ms ?? null;
  const receiving = lastMs !== null && nowMs - lastMs < 1500;
  const title = filter === 'all' ? 'Files RX Log' : `${fileCaps(filter).label} RX Log`;
  return <RxLogPanel title={title} packets={filtered} columns={columns} receiving={receiving} />;
}
