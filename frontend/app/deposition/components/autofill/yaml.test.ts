import { sessionToYaml, yamlToSession } from './yaml';

describe('yamlToSession', () => {
  const YAML = [
    'tiltseries:',
    '  acceleration_voltage: 300',
    '  total_flux: 120', // readOnly -> ignored
    'reconstruction:', // shared fields emitted once
    '  voxel_spacing: 7.84',
    '  reconstruction_method: WBP', // readOnly shared -> ignored
    'tomograms:',
    '  - flavor: denoised',
    '    processing: denoised',
    '    processing_software: DenoisET',
    '    is_visualization_default: true',
    '  - flavor: filtered',
    '    processing: filtered',
    '    processing_software: null',
    '    is_visualization_default: false',
  ].join('\n');

  it('picks editable tiltseries fields and skips read-only ones', () => {
    const { tiltseries } = yamlToSession(YAML);
    expect(tiltseries.acceleration_voltage).toBe(300);
    expect('total_flux' in tiltseries).toBe(false); // read-only
  });

  it('reads shared tomogram fields from the reconstruction block, skipping read-only', () => {
    const { shared } = yamlToSession(YAML);
    expect(shared.voxel_spacing).toBe(7.84);
    expect('reconstruction_method' in shared).toBe(false); // read-only
    expect('processing' in shared).toBe(false); // per-flavor, not shared
  });

  it('ignores shared keys placed under a flavor block (reconstruction is the only source)', () => {
    const stray = [
      'reconstruction:',
      '  voxel_spacing: 7.84',
      'tomograms:',
      '  - flavor: filtered',
      '    voxel_spacing: 99', // shared key under a flavor -> not read anywhere
      '    processing: filtered',
    ].join('\n');
    const { shared, perFlavor } = yamlToSession(stray);
    expect(shared.voxel_spacing).toBe(7.84); 
    expect('voxel_spacing' in perFlavor.filtered).toBe(false); 
  });

  it('picks per-flavor fields per flavor with type coercion', () => {
    const { perFlavor } = yamlToSession(YAML);
    expect(perFlavor.denoised.processing).toBe('denoised');
    expect(perFlavor.denoised.processing_software).toBe('DenoisET');
    expect(perFlavor.denoised.is_visualization_default).toBe(true);
    expect(perFlavor.filtered.processing).toBe('filtered');
    expect(perFlavor.filtered.processing_software).toBeNull(); // "null" -> null
    expect(perFlavor.filtered.is_visualization_default).toBe(false);
  });

  it('is tolerant of blank lines, comments, and extra whitespace', () => {
    const messy = ['# heading', '', 'tiltseries:', '   acceleration_voltage:   300  ', ''].join('\n');
    expect(yamlToSession(messy).tiltseries.acceleration_voltage).toBe(300);
  });

  it('round-trips editable values through sessionToYaml -> yamlToSession', () => {
    const tiltseries = { acceleration_voltage: 300, pixel_spacing: 1.54 } as never;
    const tomograms = {
      denoised: { voxel_spacing: 7.84, processing: 'denoised', processing_software: 'DenoisET' },
      filtered: { voxel_spacing: 7.84, processing: 'filtered' },
    } as never;
    const parsed = yamlToSession(sessionToYaml(tiltseries, tomograms));
    expect(parsed.tiltseries.acceleration_voltage).toBe(300);
    expect(parsed.tiltseries.pixel_spacing).toBe(1.54);
    expect(parsed.shared.voxel_spacing).toBe(7.84);
    expect(parsed.perFlavor.denoised.processing_software).toBe('DenoisET');
  });
});
