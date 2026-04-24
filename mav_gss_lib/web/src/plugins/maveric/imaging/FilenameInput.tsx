import { GssInput } from '@/components/ui/gss-input';
import { colors } from '@/lib/colors';

interface FilenameInputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  /** Mission's `imaging.thumb_prefix`. When set, the input shows a
   *  small "thumb" / "full" tag so the operator sees which
   *  Destination the filename will resolve to before staging — no
   *  silent thumb/full mismatch. */
  thumbPrefix?: string;
}

/**
 * Filename text input with a ghost `.jpg` suffix shown when the typed
 * value doesn't already end in `.jpg` / `.jpeg`. The suffix indicates
 * the filename will be auto-appended on send (see `withJpg` in
 * helpers.ts).
 *
 * When `thumbPrefix` is provided and the value is non-empty, also
 * renders a destination tag ("thumb" if value starts with the prefix,
 * "full" otherwise). The tag is derived from the filename so the
 * operator can't accidentally stage a thumb command against a full
 * filename (or vice versa).
 */
export function FilenameInput({
  value,
  onChange,
  placeholder = 'filename',
  className = '',
  thumbPrefix,
}: FilenameInputProps) {
  const trimmed = value.trim();
  const needsSuffix = trimmed !== '' && !/\.jpe?g$/i.test(trimmed);
  const showTag = !!thumbPrefix && trimmed !== '';
  const isThumb = showTag && trimmed.startsWith(thumbPrefix!);
  const tagColor = isThumb ? colors.warning : colors.active;
  const tagLabel = isThumb ? 'thumb' : 'full';

  // Reserve left-side space whenever a thumb_prefix convention is in
  // effect — keeps the input's text anchor stable whether the tag is
  // visible or not (no jump when the operator types the first char).
  const leftPad = thumbPrefix ? 'pl-[52px]' : '';
  const rightPad = needsSuffix ? 'pr-9' : '';

  return (
    <div className={`relative ${className}`}>
      <GssInput
        className={`w-full font-mono ${leftPad} ${rightPad}`}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
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
          .jpg
        </span>
      )}
    </div>
  );
}
