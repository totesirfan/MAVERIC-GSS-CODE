import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FilenameInput } from '../FilenameInput';

describe('FilenameInput ghost suffix per kind', () => {
  it('shows .jpg when kind=image and value has no jpg/jpeg suffix', () => {
    render(<FilenameInput kind="image" value="photo" onChange={() => {}} />);
    expect(screen.getByText('.jpg')).toBeTruthy();
  });

  it('shows .json when kind=aii and value has no json suffix', () => {
    render(<FilenameInput kind="aii" value="report" onChange={() => {}} />);
    expect(screen.getByText('.json')).toBeTruthy();
  });

  it('shows .npz when kind=mag and value has no npz suffix', () => {
    render(<FilenameInput kind="mag" value="capture" onChange={() => {}} />);
    expect(screen.getByText('.npz')).toBeTruthy();
  });

  it('hides ghost suffix when value already has the extension', () => {
    render(<FilenameInput kind="aii" value="report.json" onChange={() => {}} />);
    expect(screen.queryByText('.json')).toBeNull();
  });

  it('hides ghost suffix when value is empty', () => {
    render(<FilenameInput kind="aii" value="" onChange={() => {}} />);
    expect(screen.queryByText('.json')).toBeNull();
  });

  it('thumbPrefix tag only appears when both prop is set and value is non-empty', () => {
    const { rerender } = render(
      <FilenameInput kind="image" value="photo" onChange={() => {}} thumbPrefix="tn_" />,
    );
    expect(screen.getByText('full')).toBeTruthy();
    rerender(
      <FilenameInput kind="image" value="tn_photo" onChange={() => {}} thumbPrefix="tn_" />,
    );
    expect(screen.getByText('thumb')).toBeTruthy();
  });
});
