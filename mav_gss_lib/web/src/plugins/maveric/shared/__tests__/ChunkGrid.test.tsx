import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { ChunkGrid } from '../ChunkGrid';

describe('ChunkGrid', () => {
  it('renders one button per chunk', () => {
    const { container } = render(
      <ChunkGrid total={5} chunkSet={new Set([0, 2])} onRestageRange={() => {}} />,
    );
    expect(container.querySelectorAll('button').length).toBe(5);
  });

  it('disables received chunks and enables missing ones', () => {
    const { container } = render(
      <ChunkGrid total={3} chunkSet={new Set([1])} onRestageRange={() => {}} />,
    );
    const buttons = container.querySelectorAll<HTMLButtonElement>('button');
    expect(buttons[0].disabled).toBe(false); // missing
    expect(buttons[1].disabled).toBe(true);  // received
    expect(buttons[2].disabled).toBe(false); // missing
  });

  it('calls onRestageRange with single-chunk range when clicked', () => {
    const onRestageRange = vi.fn();
    const { container } = render(
      <ChunkGrid total={3} chunkSet={new Set()} onRestageRange={onRestageRange} />,
    );
    fireEvent.click(container.querySelectorAll('button')[2]);
    expect(onRestageRange).toHaveBeenCalledWith({ start: 2, end: 2, count: 1 });
  });

  it('renders nothing when total is 0', () => {
    const { container } = render(
      <ChunkGrid total={0} chunkSet={new Set()} onRestageRange={() => {}} />,
    );
    expect(container.querySelectorAll('button').length).toBe(0);
  });
});
