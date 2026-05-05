import { describe, it, expect } from 'vitest';
import { withExtension, withJpg } from '../extensions';

describe('withExtension', () => {
  it('appends .jpg for image kind when no jpg/jpeg suffix', () => {
    expect(withExtension('foo', 'image')).toBe('foo.jpg');
    expect(withExtension('foo.jpg', 'image')).toBe('foo.jpg');
    expect(withExtension('foo.JPEG', 'image')).toBe('foo.JPEG');
  });

  it('appends .json for aii kind', () => {
    expect(withExtension('foo', 'aii')).toBe('foo.json');
    expect(withExtension('foo.json', 'aii')).toBe('foo.json');
    expect(withExtension('foo.JSON', 'aii')).toBe('foo.JSON');
  });

  it('appends .npz for mag kind', () => {
    expect(withExtension('foo', 'mag')).toBe('foo.npz');
    expect(withExtension('foo.npz', 'mag')).toBe('foo.npz');
    expect(withExtension('foo.NPZ', 'mag')).toBe('foo.NPZ');
  });

  it('legacy withJpg still works', () => {
    expect(withJpg('foo')).toBe('foo.jpg');
    expect(withJpg('foo.jpeg')).toBe('foo.jpeg');
  });
});
