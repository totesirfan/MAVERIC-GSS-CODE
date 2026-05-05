import { RxLogPanel as SharedRxLogPanel } from '../shared/RxLogPanel';
import type { ColumnDef, RxPacket } from '@/lib/types';

interface ImagingRxLogPanelProps {
  packets: RxPacket[];
  columns?: ColumnDef[];
  receiving: boolean;
}

export function RxLogPanel(props: ImagingRxLogPanelProps) {
  return <SharedRxLogPanel title="Imaging RX Log" {...props} />;
}
