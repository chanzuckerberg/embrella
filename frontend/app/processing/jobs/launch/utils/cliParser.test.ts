/**
 * Unit tests for CLI Parser
 */

import { parseCLICommand, buildFlagMapping, getIgnoredReasonDescription } from './cliParser';
import type { JSONSchema } from '@app/common/types/workflow';

// Mock schema based on AreTomo3 schema.yaml
const mockSchema: JSONSchema = {
  type: 'object',
  properties: {
    pixel_size: {
      type: 'number',
      title: 'Pixel Size (Å)',
      'x-cli-flag': '-PixSize',
    },
    frame_dose: {
      type: 'number',
      title: 'Frame Dose (e⁻/Ų)',
      'x-cli-flag': '-FmDose',
    },
    high_tension_kv: {
      type: 'integer',
      title: 'High Tension (kV)',
      'x-cli-flag': '-kV',
    },
    vol_z: {
      type: 'integer',
      title: 'Volume Z Height',
      'x-cli-flag': '-VolZ',
    },
    at_bin: {
      type: 'string',
      title: 'Tomogram Binning Factors',
      'x-cli-flag': '-AtBin',
    },
    use_wbp: {
      type: 'boolean',
      title: 'Use Weighted Back Projection',
      'x-cli-flag': '-Wbp',
    },
    flip_vol: {
      type: 'boolean',
      title: 'Flip Volume to XYZ',
      'x-cli-flag': '-FlipVol',
    },
    tilt_axis: {
      type: 'number',
      title: 'Tilt Axis Angle (°)',
      'x-cli-flag': '-TiltAxis',
      'x-cli-composite': ['tilt_axis', 'tilt_axis_refine'],
    },
    tilt_axis_refine: {
      type: 'integer',
      title: 'Tilt Axis Refinement',
      'x-cli-flag': null,
      'x-cli-composite': true,
    },
    corr_ctf: {
      type: 'integer',
      title: 'Local CTF Correction',
      'x-cli-flag': '-CorrCTF',
    },
    serial: {
      type: 'integer',
      title: 'Live Processing Timeout',
      'x-cli-flag': '-Serial',
    },
    resume_processing: {
      type: 'boolean',
      title: 'Resume Processing',
      'x-cli-flag': '-Resume',
    },
    flip_gain: {
      type: 'integer',
      title: 'Flip Gain Reference',
      'x-cli-flag': '-FlipGain',
    },
    gain_file_name: {
      type: 'string',
      title: 'Gain File Name',
      'x-cli-flag': null, // No CLI flag
    },
    mc_patch: {
      type: 'string',
      title: 'Motion Correction Patches',
      'x-cli-flag': '-McPatch',
    },
  },
};

describe('buildFlagMapping', () => {
  it('builds correct mapping from schema', () => {
    const mapping = buildFlagMapping(mockSchema);

    expect(mapping['-PixSize']).toEqual({
      fieldName: 'pixel_size',
      type: 'number',
      title: 'Pixel Size (Å)',
      isComposite: false,
      compositeFields: undefined,
    });

    expect(mapping['-kV']).toEqual({
      fieldName: 'high_tension_kv',
      type: 'integer',
      title: 'High Tension (kV)',
      isComposite: false,
      compositeFields: undefined,
    });
  });

  it('handles composite flags correctly', () => {
    const mapping = buildFlagMapping(mockSchema);

    expect(mapping['-TiltAxis']).toEqual({
      fieldName: 'tilt_axis',
      type: 'number',
      title: 'Tilt Axis Angle (°)',
      isComposite: true,
      compositeFields: ['tilt_axis', 'tilt_axis_refine'],
    });
  });

  it('excludes fields with null x-cli-flag', () => {
    const mapping = buildFlagMapping(mockSchema);

    // gain_file_name has x-cli-flag: null
    expect(Object.values(mapping).find((v) => v.fieldName === 'gain_file_name')).toBeUndefined();
  });

  it('handles empty schema', () => {
    const mapping = buildFlagMapping({ type: 'object' });
    expect(mapping).toEqual({});
  });
});

describe('parseCLICommand', () => {
  describe('basic parsing', () => {
    it('parses single-value numeric flags', () => {
      const result = parseCLICommand('-PixSize 1.540', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.pixel_size).toBe(1.54);
      expect(result.parsedDetails).toHaveLength(1);
      expect(result.parsedDetails[0]).toMatchObject({
        fieldName: 'pixel_size',
        cliFlag: '-PixSize',
        rawValue: '1.540',
        convertedValue: 1.54,
      });
    });

    it('parses single-value integer flags', () => {
      const result = parseCLICommand('-VolZ 1600', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.vol_z).toBe(1600);
    });

    it('parses multi-value flags as space-separated string', () => {
      const result = parseCLICommand('-AtBin 3.25 6.49 6.49', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.at_bin).toBe('3.25 6.49 6.49');
    });

    it('parses multiple flags in one command', () => {
      const result = parseCLICommand('-PixSize 1.5 -kV 300 -VolZ 1600', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.pixel_size).toBe(1.5);
      expect(result.parsedParams.high_tension_kv).toBe(300);
      expect(result.parsedParams.vol_z).toBe(1600);
      expect(result.parsedDetails).toHaveLength(3);
    });
  });

  describe('boolean handling', () => {
    it('parses 1 as true for boolean fields', () => {
      const result = parseCLICommand('-Wbp 1', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.use_wbp).toBe(true);
    });

    it('parses 0 as false for boolean fields', () => {
      const result = parseCLICommand('-Resume 0', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.resume_processing).toBe(false);
    });

    it('parses integer enums correctly', () => {
      const result = parseCLICommand('-FlipGain 1', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.flip_gain).toBe(1);
    });
  });

  describe('composite flags', () => {
    it('parses composite flag into multiple fields', () => {
      const result = parseCLICommand('-TiltAxis 85.0 1', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.tilt_axis).toBe(85.0);
      expect(result.parsedParams.tilt_axis_refine).toBe(1);
      expect(result.parsedDetails).toHaveLength(2);
    });
  });

  describe('line continuation handling', () => {
    it('handles backslash line continuations', () => {
      const cli = `-PixSize 1.540 \\
      -VolZ 1600`;
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.pixel_size).toBe(1.54);
      expect(result.parsedParams.vol_z).toBe(1600);
    });

    it('handles tabs as whitespace', () => {
      const cli = '-PixSize\t1.540\t-VolZ\t1600';
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.pixel_size).toBe(1.54);
      expect(result.parsedParams.vol_z).toBe(1600);
    });
  });

  describe('ignored tokens', () => {
    it('ignores executable paths', () => {
      const cli = '/hpc/projects/group.czii/software/AreTomo3_2.2.3 -PixSize 1.5';
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.pixel_size).toBe(1.5);
      expect(result.ignoredTokens).toContainEqual({
        token: expect.stringContaining('AreTomo3'),
        reason: 'executable',
      });
    });

    it('ignores shell redirects', () => {
      const cli = '-PixSize 1.5 2>/dev/null';
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.ignoredTokens).toContainEqual({
        token: '2>/dev/null',
        reason: 'redirect',
      });
    });

    it('ignores unknown flags', () => {
      const cli = '-PixSize 1.5 -UnknownFlag value -VolZ 1600';
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.pixel_size).toBe(1.5);
      expect(result.parsedParams.vol_z).toBe(1600);
      expect(result.ignoredTokens).toContainEqual({
        token: '-UnknownFlag',
        reason: 'unknown_flag',
      });
    });

    it('ignores shell artifacts', () => {
      const cli = '-PixSize 1.5 && -VolZ 1600';
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.ignoredTokens).toContainEqual({
        token: '&&',
        reason: 'shell_artifact',
      });
    });
  });

  describe('complete command parsing', () => {
    it('parses complete AreTomo3 command from example', () => {
      const cli = `/hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.2.3_07-16-2025
        -InPrefix /hpc/projects/krios1.processing/aretomo3/24nov27a/run005/Position_
        -InSkips _CTF,_ODD,_EVN,_Vol
        -InSuffix .mrc
        -OutDir /hpc/projects/group.czii/krios1.processing/aretomo3/24nov27a/run008
        -kV 300 -SplitSum 0 -PixSize 1.540
        -AtBin 3.25 6.49 6.49
        -Wbp 1 -FlipVol 1 -VolZ 1600
        -OutImod 1 -TotalDose 120 -FmDose
        -Resume 0 -FlipGain 1 -Serial 43000
        -Cmd 2 -CorrCTF 3
        -Gpu 0,1,2,3,4,5,6,7
        2>/dev/null`;

      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.high_tension_kv).toBe(300);
      expect(result.parsedParams.pixel_size).toBe(1.54);
      expect(result.parsedParams.at_bin).toBe('3.25 6.49 6.49');
      expect(result.parsedParams.use_wbp).toBe(true);
      expect(result.parsedParams.flip_vol).toBe(true);
      expect(result.parsedParams.vol_z).toBe(1600);
      expect(result.parsedParams.resume_processing).toBe(false);
      expect(result.parsedParams.flip_gain).toBe(1);
      expect(result.parsedParams.serial).toBe(43000);
      expect(result.parsedParams.corr_ctf).toBe(3);

      // Check ignored tokens
      expect(result.ignoredTokens.some((t) => t.reason === 'executable')).toBe(true);
      expect(result.ignoredTokens.some((t) => t.reason === 'redirect')).toBe(true);
      expect(result.ignoredTokens.some((t) => t.reason === 'unknown_flag')).toBe(true);
    });

    it('handles quoted values', () => {
      const cli = '-McPatch "5 5" -PixSize 1.5';
      const result = parseCLICommand(cli, mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.mc_patch).toBe('5 5');
      expect(result.parsedParams.pixel_size).toBe(1.5);
    });
  });

  describe('error handling', () => {
    it('handles empty input', () => {
      const result = parseCLICommand('', mockSchema);

      expect(result.success).toBe(false);
      expect(result.warnings).toContain('No CLI command provided');
    });

    it('handles whitespace-only input', () => {
      const result = parseCLICommand('   \n\t  ', mockSchema);

      expect(result.success).toBe(false);
      expect(result.warnings).toContain('No CLI command provided');
    });

    it('handles input with no recognized flags', () => {
      const result = parseCLICommand('-Unknown 1 -AnotherUnknown 2', mockSchema);

      expect(result.success).toBe(false);
      expect(result.warnings.some((w) => w.includes('No recognized parameters'))).toBe(true);
    });
  });

  describe('negative numbers', () => {
    it('handles negative numeric values correctly', () => {
      // Using tilt_axis which accepts -180 to 180
      const result = parseCLICommand('-TiltAxis -85.5 1', mockSchema);

      expect(result.success).toBe(true);
      expect(result.parsedParams.tilt_axis).toBe(-85.5);
    });
  });
});

describe('getIgnoredReasonDescription', () => {
  it('returns correct descriptions', () => {
    expect(getIgnoredReasonDescription('executable')).toBe('Executable path');
    expect(getIgnoredReasonDescription('redirect')).toBe('Shell redirect');
    expect(getIgnoredReasonDescription('unknown_flag')).toBe('Unrecognized flag');
    expect(getIgnoredReasonDescription('orphan_value')).toBe('Value without flag');
    expect(getIgnoredReasonDescription('shell_artifact')).toBe('Shell syntax');
  });
});
