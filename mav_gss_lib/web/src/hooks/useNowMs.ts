import { useEffect, useState } from 'react';

/**
 * Module-level 1 Hz "now" tick. A single setInterval is shared across
 * all consumers; subscribers are notified together so timestamps stay
 * in lock-step. Interval starts on first subscriber and stops on last.
 *
 * Lazy initialization: `currentNow` is null at module import time —
 * the first read (via `readNow()` or `ensureInterval()`) snapshots
 * `Date.now()`. This avoids capturing the import-time wall clock,
 * which would (a) be stale by the time the first hook mounts, and
 * (b) bypass `vi.useFakeTimers()` in tests that activate fake timers
 * AFTER the module is imported.
 *
 * Late-subscriber correctness: a hook mounted between ticks reads the
 * shared `currentNow` for its initial state — it does NOT mutate it
 * with a fresh `Date.now()`, which would skew earlier peers. Then the
 * effect immediately re-syncs via `setNow(currentNow)` after subscribing,
 * so a late subscriber matches peers without waiting for the next tick.
 *
 * Idle reset: when the last subscriber unmounts, `currentNow` is
 * reset to null so the next session starts fresh (important for tests
 * that expect a clean slate after `renderHook` cleanup).
 *
 * Usage:
 *   const nowMs = useNowMs();
 *   const ageMs = nowMs - someTimestampMs;
 */
let intervalId: number | null = null;
let currentNow: number | null = null;
const subscribers = new Set<(t: number) => void>();

function readNow(): number {
  if (currentNow === null) currentNow = Date.now();
  return currentNow;
}

function ensureInterval(): void {
  if (intervalId !== null) return;
  if (currentNow === null) currentNow = Date.now();
  intervalId = window.setInterval(() => {
    currentNow = Date.now();
    for (const fn of subscribers) fn(currentNow);
  }, 1000);
}

function stopIntervalIfIdle(): void {
  if (subscribers.size === 0 && intervalId !== null) {
    window.clearInterval(intervalId);
    intervalId = null;
    currentNow = null;
  }
}

export function useNowMs(): number {
  const [now, setNow] = useState<number>(readNow);
  useEffect(() => {
    subscribers.add(setNow);
    ensureInterval();
    // currentNow is non-null after ensureInterval — assert for tsc.
    setNow(currentNow!);
    return () => {
      subscribers.delete(setNow);
      stopIntervalIfIdle();
    };
  }, []);
  return now;
}
