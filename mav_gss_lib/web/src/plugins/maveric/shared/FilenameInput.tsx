import { GssInput } from '@/components/ui/gss-input';
import { colors } from '@/lib/colors';
import { fileCaps, type FileKindId } from './fileKinds';

interface FilenameInputProps {
  /** File kind drives the ghost suffix and the suffix-detection regex. */
  kind: FileKindId;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  /** Image-only: when set, renders a small "thumb"/"full" tag derived
   *  from whether `value` starts with the prefix. AII/MAG callers omit. */
  thumbPrefix?: string;
  /** When true, the underlying input is disabled. Used by FilesTxControls
   *  to lock the filename for kinds with a singleton canonical name
   *  (`caps.defaultFilename` set — currently AII/`transmit_dir`). */
  disabled?: boolean;
}

/**
 * Filename text input with a ghost suffix shown when the typed value
 * doesn't already end in the kind's extension. The suffix is appended
 * on send by `withExtension(filename, kind)` from `./extensions`.
 *
 * For image kind, an optional `thumbPrefix` prop renders a destination
 * tag — `thumb` when `value` starts with the prefix, otherwise `full`.
 * Derived from the filename so the operator can't stage a thumb command
 * against a full filename or vice versa.
 */
export function FilenameInput({
  kind,
  value,
  onChange,
  placeholder = 'filename',
  className = '',
  thumbPrefix,
  disabled,
}: FilenameInputProps) {
  const ext = fileCaps(kind).extension;
  const trimmed = value.trim();
  // Suffix-detection: image accepts both .jpg and .jpeg; other kinds
  // accept only their declared extension. Case-insensitive.
  const suffixRegex =
    kind === 'image' ? /\.jpe?g$/i : new RegExp(`\\${ext}$`, 'i');
  const needsSuffix = trimmed !== '' && !suffixRegex.test(trimmed);
  const showTag = !!thumbPrefix && trimmed !== '';
  const isThumb = showTag && trimmed.startsWith(thumbPrefix!);
  const tagColor = isThumb ? colors.warning : colors.active;
  const tagLabel = isThumb ? 'thumb' : 'full';

  const leftPad = thumbPrefix ? 'pl-[52px]' : '';
  // Right padding scales with extension length so longer suffixes (`.json`)
  // don't overlap the input text.
  const rightPad = needsSuffix ? (ext.length >= 5 ? 'pr-12' : 'pr-9') : '';

  return (
    <div className={`relative ${className}`}>
      <GssInput
        className={`w-full font-mono ${leftPad} ${rightPad}`}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
      {showTag && (
        <span
          className="absolute left-1.5 top-1/2 -translate-y-1/2 inline-flex items-center px-1.5 rounded-sm border font-mono text-[9px] uppercase tracking-wider pointer-events-none"
          style={{
            height: 15,
            color: tagColor,
            borderColor: `${tagColor}66`,
            backgroundColor: `${tagColor}14`,
          }}
          title={isThumb ? `Destination 2 · thumb (matches ${thumbPrefix}* prefix)` : 'Destination 1 · full'}
        >
          {tagLabel}
        </span>
      )}
      {needsSuffix && (
        <span
          className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] font-mono pointer-events-none"
          style={{ color: colors.dim }}
          title="auto-appended on send"
        >
          {ext}
        </span>
      )}
    </div>
  );
}
