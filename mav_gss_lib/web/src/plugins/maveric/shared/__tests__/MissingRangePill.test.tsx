import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MissingRangePill } from '../MissingRangePill';

describe('MissingRangePill', () => {
  it('renders Complete when received === total', () => {
    render(<MissingRangePill received={5} total={5} ranges={[]} onClick={() => {}} />);
    expect(screen.getByText(/Complete/i)).toBeTruthy();
  });

  it('renders "get N" when nothing received', () => {
    render(
      <MissingRangePill received={0} total={4} ranges={[{ start: 0, end: 3, count: 4 }]} onClick={() => {}} />,
    );
    expect(screen.getByText(/get 4/i)).toBeTruthy();
  });

  it('renders "N missing" when partially received', () => {
    render(
      <MissingRangePill
        received={3}
        total={5}
        ranges={[{ start: 3, end: 4, count: 2 }]}
        onClick={() => {}}
      />,
    );
    expect(screen.getByText(/2 missing/i)).toBeTruthy();
  });

  it('invokes onClick on press', () => {
    const onClick = vi.fn();
    render(
      <MissingRangePill received={0} total={2} ranges={[{ start: 0, end: 1, count: 2 }]} onClick={onClick} />,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders nothing when total is null', () => {
    const { container } = render(
      <MissingRangePill received={0} total={null} ranges={[]} onClick={() => {}} />,
    );
    expect(container.textContent).toBe('');
  });
});
