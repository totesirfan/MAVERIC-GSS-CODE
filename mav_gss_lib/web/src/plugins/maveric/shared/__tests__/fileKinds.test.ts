import { describe, it, expect } from 'vitest';
import { FILE_KIND_CAPS, fileCaps, allKinds } from '../fileKinds';

describe('FILE_KIND_CAPS registry', () => {
  it('exposes image, aii, mag', () => {
    expect(allKinds()).toEqual(['image', 'aii', 'mag']);
  });

  it('image has destination-arg semantics and pairing', () => {
    const c = fileCaps('image');
    expect(c.cntCmd).toBe('img_cnt_chunks');
    expect(c.getCmd).toBe('img_get_chunks');
    expect(c.deleteCmd).toBe('img_delete');
    expect(c.captureCmd).toBe('cam_capture');
    expect(c.hasDestinationArg).toBe(true);
    expect(c.hasPairing).toBe(true);
    expect(c.extension).toBe('.jpg');
    expect(c.extraCmds).toContain('lcd_display');
  });

  it('aii is flat with no destination arg', () => {
    const c = fileCaps('aii');
    expect(c.cntCmd).toBe('aii_cnt_chunks');
    expect(c.getCmd).toBe('aii_get_chunks');
    expect(c.deleteCmd).toBe('aii_delete');
    expect(c.captureCmd).toBeNull();
    expect(c.hasDestinationArg).toBe(false);
    expect(c.hasPairing).toBe(false);
    expect(c.extension).toBe('.json');
    expect(c.extraCmds).toEqual(expect.arrayContaining(['aii_dir', 'aii_img']));
  });

  it('mag is flat — backend has no capture_cmd, mag_capture lives in extraCmds', () => {
    const c = fileCaps('mag');
    expect(c.cntCmd).toBe('mag_cnt_chunks');
    expect(c.getCmd).toBe('mag_get_chunks');
    expect(c.deleteCmd).toBe('mag_delete');
    // Backend FILE_TRANSPORTS has capture_cmd=None for MAG; mirror it here.
    expect(c.captureCmd).toBeNull();
    expect(c.hasDestinationArg).toBe(false);
    expect(c.hasPairing).toBe(false);
    expect(c.extension).toBe('.npz');
    expect(c.extraCmds).toEqual(expect.arrayContaining(['mag_capture', 'mag_kill', 'mag_tlm']));
  });

  it('image opts in to error-ptype fallback for HLNV/ASTR; aii/mag opt out', () => {
    expect(fileCaps('image').errorNodes).toEqual(['HLNV', 'ASTR']);
    expect(fileCaps('aii').errorNodes).toEqual([]);
    expect(fileCaps('mag').errorNodes).toEqual([]);
  });

  it('AII overrides aii_img filename to image kind; image and mag have no overrides', () => {
    // aii_img.filename names the JPEG that the spacecraft will derive
    // an AII record from — NOT the .json output. Without this override
    // ExtraCmdRow would auto-append .json to a JPEG filename.
    expect(fileCaps('aii').extraCmdFilenameKind).toEqual({ aii_img: 'image' });
    expect(fileCaps('image').extraCmdFilenameKind).toEqual({});
    expect(fileCaps('mag').extraCmdFilenameKind).toEqual({});
  });

  it('AII has a singleton defaultFilename + subtitle; image and mag have neither', () => {
    // AII is always `transmit_dir.json` per source — pre-fill the
    // cnt/get/delete inputs so the operator doesn't retype it.
    expect(fileCaps('aii').defaultFilename).toBe('transmit_dir');
    expect(fileCaps('aii').subtitle).toBe('AI candidate list (transmit_dir)');
    expect(fileCaps('image').defaultFilename).toBeUndefined();
    expect(fileCaps('image').subtitle).toBeUndefined();
    expect(fileCaps('mag').defaultFilename).toBeUndefined();
    expect(fileCaps('mag').subtitle).toBeUndefined();
  });

  it('rxFilter matches cmd_ids in the kind family only', () => {
    expect(fileCaps('image').rxFilter.test('img_get_chunks')).toBe(true);
    expect(fileCaps('image').rxFilter.test('cam_capture')).toBe(true);
    expect(fileCaps('image').rxFilter.test('lcd_display')).toBe(true);
    expect(fileCaps('image').rxFilter.test('aii_get_chunks')).toBe(false);

    expect(fileCaps('aii').rxFilter.test('aii_dir')).toBe(true);
    expect(fileCaps('aii').rxFilter.test('mag_get_chunks')).toBe(false);

    expect(fileCaps('mag').rxFilter.test('mag_kill')).toBe(true);
    expect(fileCaps('mag').rxFilter.test('img_delete')).toBe(false);
  });

  it('all kinds default to HLNV/ASTR fallback nodes', () => {
    for (const k of allKinds()) {
      expect(fileCaps(k).fallbackNodes).toEqual(['HLNV', 'ASTR']);
    }
  });
});
