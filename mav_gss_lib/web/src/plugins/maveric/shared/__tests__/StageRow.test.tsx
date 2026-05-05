import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StageRow } from '../StageRow';

describe('StageRow', () => {
  it('renders label, sublabel, filename input, and Stage button', () => {
    render(
      <StageRow
        label="Count Chunks"
        sublabel="aii_cnt_chunks"
        kind="aii"
        filenameValue=""
        onFilenameChange={() => {}}
        onStage={() => {}}
      />,
    );
    expect(screen.getByText(/Count Chunks/)).toBeTruthy();
    expect(screen.getByText(/aii_cnt_chunks/)).toBeTruthy();
    expect(screen.getByPlaceholderText(/filename/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Stage/i })).toBeTruthy();
  });

  it('fires onFilenameChange', () => {
    const onChange = vi.fn();
    render(
      <StageRow
        label="x"
        kind="aii"
        filenameValue=""
        onFilenameChange={onChange}
        onStage={() => {}}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText(/filename/i), { target: { value: 'foo' } });
    expect(onChange).toHaveBeenCalledWith('foo');
  });

  it('fires onStage', () => {
    const onStage = vi.fn();
    render(
      <StageRow
        label="x"
        kind="aii"
        filenameValue="foo"
        onFilenameChange={() => {}}
        onStage={onStage}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Stage/i }));
    expect(onStage).toHaveBeenCalled();
  });

  it('renders extras between filename and Stage', () => {
    render(
      <StageRow
        label="x"
        kind="aii"
        filenameValue=""
        onFilenameChange={() => {}}
        onStage={() => {}}
        extras={<input data-testid="extra-input" placeholder="start" />}
      />,
    );
    expect(screen.getByTestId('extra-input')).toBeTruthy();
  });

  it('forwards kind to FilenameInput so the right ghost suffix renders', () => {
    render(
      <StageRow
        label="x"
        kind="mag"
        filenameValue="capture"
        onFilenameChange={() => {}}
        onStage={() => {}}
      />,
    );
    expect(screen.getByText('.npz')).toBeTruthy();
  });
});
