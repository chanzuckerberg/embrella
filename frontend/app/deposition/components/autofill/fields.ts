import type { AutofillMetadata, TiltseriesMetadata, TomogramFlavor, TomogramMetadata } from '../../types';
import { TOMOGRAM_FLAVORS } from '../../types';

export type FieldType = 'number' | 'text' | 'boolean';

export interface FieldDef {
  key: string;
  label: string;
  section: string;
  type: FieldType;
  required?: boolean;
  unit?: string;
  autofillPath?: string;
  readOnly?: boolean;
  default?: string | number | boolean;
}

export const SECTION_SOURCE: Record<string, string> = {
  Acquisition: 'init',
  Instrument: 'facility record',
  Reconstruction: 'default',
  Paths: 'init',
};

export const TILTSERIES_FIELDS: FieldDef[] = [
  {
    key: 'acceleration_voltage',
    label: 'Accelerating voltage',
    section: 'Acquisition',
    unit: 'kV',
    type: 'number',
    required: true,
    autofillPath: 'acquisition.acceleration_voltage_kv',
  },
  { key: 'binning_from_frames', label: 'Binning (from frames)', section: 'Acquisition', type: 'number' },
  { key: 'data_acquisition_software', label: 'Acquisition software', section: 'Acquisition', type: 'text' },
  {
    key: 'pixel_spacing',
    label: 'Pixel size',
    section: 'Acquisition',
    unit: 'Å',
    type: 'number',
    required: true,
    autofillPath: 'acquisition.pixel_spacing',
  },
  {
    key: 'tilt_axis',
    label: 'Tilt-axis angle',
    section: 'Acquisition',
    unit: '°',
    type: 'number',
    required: true,
    default: -96,
  },
  { key: 'tilt_step', label: 'Tilt step', section: 'Acquisition', unit: '°', type: 'number' },
  { key: 'tilting_scheme', label: 'Tilting scheme', section: 'Acquisition', type: 'text', default: 'dose-symmetric' },
  {
    key: 'total_flux',
    label: 'Total dose',
    section: 'Acquisition',
    unit: 'e⁻/Å²',
    type: 'number',
    readOnly: true,
    autofillPath: 'total_dose',
  },
  { key: 'microscope_manufacturer', label: 'Microscope manufacturer', section: 'Instrument', type: 'text' },
  { key: 'microscope_model', label: 'Microscope model', section: 'Instrument', type: 'text' },
  { key: 'camera_manufacturer', label: 'Camera manufacturer', section: 'Instrument', type: 'text' },
  { key: 'camera_model', label: 'Camera model', section: 'Instrument', type: 'text' },
  { key: 'microscope_energy_filter', label: 'Energy filter', section: 'Instrument', type: 'text' },
  { key: 'microscope_image_corrector', label: 'Image corrector', section: 'Instrument', type: 'text' },
  { key: 'microscope_phase_plate', label: 'Phase plate', section: 'Instrument', type: 'text' },
  {
    key: 'spherical_aberration_constant',
    label: 'Spherical aberration',
    section: 'Instrument',
    unit: 'mm',
    type: 'number',
    required: true,
    autofillPath: 'acquisition.spherical_aberration_constant',
  },

  {
    key: '_path_gain',
    label: 'Gain reference',
    section: 'Paths',
    type: 'text',
    readOnly: true,
    autofillPath: 'paths.gain',
  },
  {
    key: '_path_frames',
    label: 'Frames',
    section: 'Paths',
    type: 'text',
    readOnly: true,
    autofillPath: 'paths.frames',
  },
  {
    key: '_path_mdoc',
    label: 'mdoc',
    section: 'Paths',
    type: 'text',
    readOnly: true,
    autofillPath: 'paths.mdoc',
  },
  {
    key: '_path_aretomo3',
    label: 'AreTomo3 output',
    section: 'Paths',
    type: 'text',
    readOnly: true,
    autofillPath: 'paths.aretomo3',
  },
  {
    key: '_path_dctf',
    label: 'dCTF volumes',
    section: 'Paths',
    type: 'text',
    readOnly: true,
    autofillPath: 'paths.dctf_vol',
  },
];

export const TOMOGRAM_FIELDS: FieldDef[] = [
  {
    key: 'voxel_spacing',
    label: 'Voxel size',
    section: 'Reconstruction',
    unit: 'Å',
    type: 'number',
    required: true,
  },
  {
    key: 'reconstruction_software',
    label: 'Reconstruction software',
    section: 'Reconstruction',
    type: 'text',
    required: true,
    autofillPath: 'acquisition.aretomo_version',
  },
  {
    key: 'reconstruction_method',
    label: 'Reconstruction method',
    section: 'Reconstruction',
    type: 'text',
    readOnly: true,
    default: 'WBP',
  },
  {
    key: 'ctf_corrected',
    label: 'CTF corrected',
    section: 'Reconstruction',
    type: 'boolean',
    readOnly: true,
    default: true,
  },
  { key: 'is_visualization_default', label: 'Default view', section: 'Reconstruction', type: 'boolean' },
  { key: 'processing', label: 'Processing', section: 'Reconstruction', type: 'text' },
  { key: 'processing_software', label: 'Processing software', section: 'Reconstruction', type: 'text', required: true },
];
// Voxel size + reconstruction metadata are set per tomogram type (flavor); only the
// visualization-default toggle renders outside the grid, as a header checkbox.
const PER_FLAVOR_FIELDS = TOMOGRAM_FIELDS.filter((f) => f.key !== 'is_visualization_default');

export function perFlavorTomogramFields(_flavor: TomogramFlavor): FieldDef[] {
  return PER_FLAVOR_FIELDS;
}

export type Provenance = 'init' | 'overridden' | 'required' | 'none';

type MetaValue = string | number | boolean | null | undefined;
type Meta = (TiltseriesMetadata | TomogramMetadata) & Record<string, unknown>;

function getPath(obj: AutofillMetadata | undefined, path: string): unknown {
  if (!obj) return undefined;
  return path.split('.').reduce<unknown>((acc, key) => {
    if (acc && typeof acc === 'object') return (acc as Record<string, unknown>)[key];
    return undefined;
  }, obj);
}

function isEmpty(v: MetaValue): boolean {
  return v == null || v === '';
}

function sameValue(a: unknown, b: unknown): boolean {
  if (a == null || b == null) return a === b;
  if (typeof a === 'number' || typeof b === 'number') return Number(a) === Number(b);
  return String(a) === String(b);
}

export function provenance(field: FieldDef, meta: Meta | null | undefined): Provenance {
  const autofilled = field.autofillPath ? getPath(meta?.autofill_metadata, field.autofillPath) : undefined;

  if (field.readOnly) return autofilled != null ? 'init' : 'none';

  const current = meta?.[field.key] as MetaValue;
  if (autofilled != null) {
    return sameValue(current, autofilled) ? 'init' : 'overridden';
  }
  if (field.required && isEmpty(current)) return 'required';
  return 'none';
}

export function autofilledValue(field: FieldDef, meta: Meta | null | undefined): unknown {
  return field.autofillPath ? getPath(meta?.autofill_metadata, field.autofillPath) : undefined;
}

export function isIssue(field: FieldDef, meta: Meta | null | undefined): boolean {
  return provenance(field, meta) === 'required';
}

export function countIssues(fields: FieldDef[], meta: Meta | null | undefined): number {
  return fields.filter((f) => isIssue(f, meta)).length;
}

export function countTomogramIssues(tomograms: Record<TomogramFlavor, TomogramMetadata>): number {
  let n = 0;
  for (const flavor of TOMOGRAM_FLAVORS) {
    n += countIssues(perFlavorTomogramFields(flavor), tomograms[flavor] as never);
  }
  return n;
}

export interface FieldSection {
  section: string;
  fields: FieldDef[];
}

export function groupBySection(fields: FieldDef[]): FieldSection[] {
  const out: FieldSection[] = [];
  for (const field of fields) {
    let group = out.find((g) => g.section === field.section);
    if (!group) {
      group = { section: field.section, fields: [] };
      out.push(group);
    }
    group.fields.push(field);
  }
  return out;
}

export function applyDefaults<T extends object>(fields: FieldDef[], meta: T): T {
  const out = { ...meta } as Record<string, unknown>;
  for (const f of fields) {
    if (f.default !== undefined && (out[f.key] == null || out[f.key] === '')) {
      out[f.key] = f.default;
    }
  }
  return out as T;
}
