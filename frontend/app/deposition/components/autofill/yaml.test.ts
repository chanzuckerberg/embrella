import { sessionToYaml, yamlToSession } from './yaml';

describe('yamlToSession', () => {
  const YAML = [
    'tiltseries:',
    '  acceleration_voltage: 300',
    '  total_flux: 120', // readOnly -> ignored
    'tomograms:',
    '  - flavor: denoised',
    '    voxel_spacing: 7.84',
    '    reconstruction_method: WBP', // readOnly -> ignored
    '    processing: denoised',
    '    processing_software: DenoisET',
    '    is_visualization_default: true',
    '  - flavor: filtered',
    '    voxel_spacing: 15.68',
    '    processing: filtered',
    '    processing_software: null',
    '    is_visualization_default: false',
  ].join('\n');

  it('picks editable tiltseries fields and skips read-only ones', () => {
    const { tiltseries } = yamlToSession(YAML);
    expect(tiltseries.acceleration_voltage).toBe(300);
    expect('total_flux' in tiltseries).toBe(false); // read-only
  });

  it('reads voxel size + metadata per flavor, keeping them independent and skipping read-only', () => {
    const { perFlavor } = yamlToSession(YAML);
    expect(perFlavor.denoised.voxel_spacing).toBe(7.84);
    expect(perFlavor.filtered.voxel_spacing).toBe(15.68); // differs from denoised
    expect('reconstruction_method' in perFlavor.denoised).toBe(false); // read-only
  });

  it('picks per-flavor fields per flavor with type coercion', () => {
    const { perFlavor } = yamlToSession(YAML);
    expect(perFlavor.denoised.processing).toBe('denoised');
    expect(perFlavor.denoised.processing_software).toBe('DenoisET');
    expect(perFlavor.denoised.is_visualization_default).toBe(true);
    expect(perFlavor.filtered.processing).toBe('filtered');
    expect(perFlavor.filtered.processing_software).toBe('');
    expect(perFlavor.filtered.is_visualization_default).toBe(false);
  });

  it('is tolerant of blank lines, comments, and extra whitespace', () => {
    const messy = ['# heading', '', 'tiltseries:', '   acceleration_voltage:   300  ', ''].join('\n');
    expect(yamlToSession(messy).tiltseries.acceleration_voltage).toBe(300);
  });

  it('skips unparseable numbers but still clears on empty/null', () => {
    const yaml = ['tiltseries:', '  acceleration_voltage: not-a-number', '  pixel_spacing: null'].join('\n');
    const { tiltseries } = yamlToSession(yaml);
    expect('acceleration_voltage' in tiltseries).toBe(false);
    expect(tiltseries.pixel_spacing).toBeNull();
  });

  it('empty text -> "" (backend CharField rejects null), empty number -> null', () => {
    const yaml = ['tiltseries:', '  data_acquisition_software: null', '  tilting_scheme: ', '  tilt_step: null'].join(
      '\n'
    );
    const { tiltseries } = yamlToSession(yaml);
    expect(tiltseries.data_acquisition_software).toBe('');
    expect(tiltseries.tilting_scheme).toBe('');
    expect(tiltseries.tilt_step).toBeNull();
  });

  it('round-trips editable values through sessionToYaml -> yamlToSession', () => {
    const tiltseries = { acceleration_voltage: 300, pixel_spacing: 1.54, binning_from_frames: 2 } as never;
    const tomograms = {
      denoised: { voxel_spacing: 7.84, processing: 'denoised', processing_software: 'DenoisET' },
      filtered: { voxel_spacing: 15.68, processing: 'filtered' },
    } as never;
    const parsed = yamlToSession(sessionToYaml(tiltseries, tomograms));
    expect(parsed.tiltseries.acceleration_voltage).toBe(300);
    expect(parsed.tiltseries.pixel_spacing).toBe(1.54);
    expect(parsed.tiltseries.binning_from_frames).toBe(2);
    expect(parsed.perFlavor.denoised.voxel_spacing).toBe(7.84);
    expect(parsed.perFlavor.filtered.voxel_spacing).toBe(15.68); // per-flavor voxel round-trips
    expect(parsed.perFlavor.denoised.processing_software).toBe('DenoisET');
  });

  it('leaves frame binning empty despite volume binning and hides alignment fields', () => {
    const tiltseries = {
      autofill_metadata: { acquisition: { binned_voxel_ratio: 8 } },
      is_aligned: false,
      aligned_tiltseries_binning: 1,
    } as never;
    const yaml = sessionToYaml(tiltseries, { denoised: {}, filtered: {} } as never);
    expect(yaml).toContain('  binning_from_frames: null');
    expect(yaml).not.toContain('is_aligned:');
    expect(yaml).not.toContain('aligned_tiltseries_binning:');
    expect(yamlToSession(yaml).tiltseries.binning_from_frames).toBeNull();
  });
});
