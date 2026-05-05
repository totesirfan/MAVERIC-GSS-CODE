import type { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { colors } from '@/lib/colors';
import { FilenameInput } from './FilenameInput';
import type { FileKindId } from './fileKinds';

export type StageRowTone = 'default' | 'destructive';

interface StageRowProps {
  label: ReactNode;
  /** Inline mono caption shown next to the label, typically the cmd_id. */
  sublabel?: string;
  /** Forwarded to FilenameInput so the ghost suffix matches the kind. */
  kind: FileKindId;
  filenameValue: string;
  onFilenameChange: (s: string) => void;
  /** Image-only: when set, FilenameInput shows the thumb/full destination tag. */
  thumbPrefix?: string;
  /** Forwarded to FilenameInput. Locks the filename input for kinds with
   *  a singleton canonical name (e.g. AII = `transmit_dir`). */
  filenameDisabled?: boolean;
  /** Render between the filename input and the Stage button (e.g. start/count GssInputs). */
  extras?: ReactNode;
  onStage: () => void;
  /** Override the Stage button tone. Default = active blue, destructive = red. */
  tone?: StageRowTone;
  /** Override the Stage button label. */
  buttonLabel?: string;
}

export function StageRow({
  label,
  sublabel,
  kind,
  filenameValue,
  onFilenameChange,
  thumbPrefix,
  filenameDisabled,
  extras,
  onStage,
  tone = 'default',
  buttonLabel = 'Stage',
}: StageRowProps) {
  const labelTone = tone === 'destructive' ? colors.danger : colors.dim;
  const buttonBg = tone === 'destructive' ? colors.danger : colors.active;
  return (
    <div>
      <div
        className="text-[10px] font-semibold uppercase tracking-wider mb-1"
        style={{ color: labelTone }}
      >
        {label}
        {sublabel && (
          <span className="font-mono normal-case ml-1" style={{ color: colors.sep }}>
            {sublabel}
          </span>
        )}
      </div>
      <div className="flex items-end gap-2">
        <FilenameInput
          className="flex-1"
          kind={kind}
          value={filenameValue}
          onChange={onFilenameChange}
          thumbPrefix={thumbPrefix}
          disabled={filenameDisabled}
        />
        {extras}
        <Button
          size="sm"
          onClick={onStage}
          style={{ backgroundColor: buttonBg, color: colors.bgApp }}
        >
          {buttonLabel}
        </Button>
      </div>
    </div>
  );
}
