/**
 * JSON preview pane for AII files. Fetches the assembled file
 * via /api/plugins/files/preview?kind=aii and renders pretty-printed.
 */

import { useEffect, useState } from 'react';
import { colors } from '@/lib/colors';
import { filesEndpoint } from './helpers';
import type { FileLeaf } from './types';

interface Props { file: FileLeaf | null }

export function JsonPreview({ file }: Props) {
  const [text, setText] = useState<string>('');
  const [valid, setValid] = useState<boolean | null>(null);

  useEffect(() => {
    if (!file) return;
    // Reset stale render state synchronously when the file changes —
    // otherwise an "(invalid JSON)" banner from the previous file
    // persists if the new fetch errors out before its parse step.
    setValid(null);
    setText('');
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(filesEndpoint('preview', file.kind, file.filename, file.source));
        if (!r.ok) { if (!cancelled) setText(`(no data — HTTP ${r.status})`); return; }
        const raw = await r.text();
        if (cancelled) return;
        try {
          const parsed = JSON.parse(raw);
          setText(JSON.stringify(parsed, null, 2));
          setValid(true);
        } catch {
          setText(raw);
          setValid(false);
        }
      } catch {
        if (!cancelled) setText('(fetch failed)');
      }
    })();
    return () => { cancelled = true; };
    // Dep on stable identity, not the `file` object reference — the
    // parent rebuilds the FileLeaf on every progress tick, so depending
    // on `file` triggers a re-fetch on every chunk arrival even though
    // the file is unchanged. The endpoint is keyed by (kind, source,
    // filename); those are the right deps.
  }, [file?.kind, file?.source, file?.filename]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!file) {
    return (
      <div className="p-4 italic text-[11px]" style={{ color: colors.textMuted }}>
        select a file to preview
      </div>
    );
  }
  // Filename, source, and chunk count all already render in the
  // surrounding FocusHeader. Only show a header here when there's
  // unique info worth surfacing — currently the JSON-validity flag
  // when parsing failed.
  return (
    <div className="flex flex-col h-full">
      {valid === false && (
        <div
          className="text-[11px] px-2 py-1 border-b"
          style={{ color: colors.danger, borderColor: colors.borderSubtle }}
        >
          invalid JSON
        </div>
      )}
      <pre
        className="flex-1 overflow-auto text-[11px] font-mono p-2"
        style={{ background: colors.bgApp, color: colors.textPrimary }}
      >{text}</pre>
    </div>
  );
}
