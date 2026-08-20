import type { AutofillMetadata, TiltseriesMetadata, TomogramMetadata } from '../../types';

export type FieldType = 'number' | 'text' | 'boolean';

export interface FieldDef {
  key: string;
  label: string;
  section: string;
  type: FieldType;
  required?: boolean;
  unit?: string;
  autofillPath?: string;
}

export const SECTION_SOURCE: Record<string, string> = {
  Acquisition: 'mdoc',
  Instrument: 'facility record',
  Reconstruction: 'derived',
};

export const TILTSERIES_FIELDS: FieldDef[] = [
  {
    key: 'acceleration_voltage',
    label: 'acceleration_voltage',
    section: 'Acquisition',
    unit: 'kV',
    type: 'number',
    required: true,
    autofillPath: 'acquisition.acceleration_voltage_kv',
  },
  {
    key: 'binning_from_frames',
    label: 'binning_from_frames',
    section: 'Acquisition',
    type: 'number',
    autofillPath: 'acquisition.binned_voxel_ratio',
  },
  { key: 'data_acquisition_software', label: 'data_acquisition_software', section: 'Acquisition', type: 'text' },
  {
    key: 'pixel_spacing',
    label: 'pixel_spacing',
    section: 'Acquisition',
    unit: 'Å',
    type: 'number',
    required: true,
    autofillPath: 'acquisition.pixel_spacing',
  },
  { key: 'tilt_axis', label: 'tilt_axis', section: 'Acquisition', unit: '°', type: 'number', required: true },
  { key: 'tilt_min', label: 'tilt_min', section: 'Acquisition', unit: '°', type: 'number', required: true },
  { key: 'tilt_max', label: 'tilt_max', section: 'Acquisition', unit: '°', type: 'number', required: true },
  { key: 'tilt_step', label: 'tilt_step', section: 'Acquisition', unit: '°', type: 'number' },
  { key: 'tilting_scheme', label: 'tilting_scheme', section: 'Acquisition', type: 'text' },
  {
    key: 'total_flux',
    label: 'total_flux',
    section: 'Acquisition',
    unit: 'e⁻/Å²',
    type: 'number',
    required: true,
    autofillPath: 'total_dose',
  },
  { key: 'is_aligned', label: 'is_aligned', section: 'Acquisition', type: 'boolean' },

  { key: 'microscope_manufacturer', label: 'microscope_manufacturer', section: 'Instrument', type: 'text' },
  { key: 'microscope_model', label: 'microscope_model', section: 'Instrument', type: 'text' },
  { key: 'camera_manufacturer', label: 'camera_manufacturer', section: 'Instrument', type: 'text' },
  { key: 'camera_model', label: 'camera_model', section: 'Instrument', type: 'text' },
  { key: 'microscope_energy_filter', label: 'energy_filter', section: 'Instrument', type: 'text' },
  {
    key: 'spherical_aberration_constant',
    label: 'spherical_aberration',
    section: 'Instrument',
    unit: 'mm',
    type: 'number',
    required: true,
    autofillPath: 'acquisition.spherical_aberration_constant',
  },
];

export const TOMOGRAM_FIELDS: FieldDef[] = [
  {
    key: 'voxel_spacing',
    label: 'voxel_spacing',
    section: 'Reconstruction',
    unit: 'Å',
    type: 'number',
    required: true,
  },
  {
    key: 'reconstruction_method',
    label: 'reconstruction_method',
    section: 'Reconstruction',
    type: 'text',
    required: true,
  },
  {
    key: 'reconstruction_software',
    label: 'reconstruction_software',
    section: 'Reconstruction',
    type: 'text',
    autofillPath: 'acquisition.aretomo_version',
  },
  { key: 'processing', label: 'processing', section: 'Reconstruction', type: 'text' },
  { key: 'ctf_corrected', label: 'ctf_corrected', section: 'Reconstruction', type: 'boolean' },
  { key: 'is_visualization_default', label: 'is_visualization_default', section: 'Reconstruction', type: 'boolean' },
];

export type Provenance = 'mdoc' | 'overridden' | 'required' | 'none';

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

/**
 * Where a field's current value came from, for the Source column:
 * - `mdoc`       init populated it and the user hasn't changed it
 * - `overridden` init populated it but the current value differs
 * - `required`   required and still empty
 * - `none`       optional + empty, or user-entered with no init source
 */
export function provenance(field: FieldDef, meta: Meta | null | undefined): Provenance {
  const current = meta?.[field.key] as MetaValue;
  const autofilled = field.autofillPath ? getPath(meta?.autofill_metadata, field.autofillPath) : undefined;

  if (autofilled != null) {
    return sameValue(current, autofilled) ? 'mdoc' : 'overridden';
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

export function coerceValue(field: FieldDef, raw: string): MetaValue {
  const v = raw.trim();
  if (v === '' || v === 'null') return field.type === 'text' ? '' : null;
  if (field.type === 'number') {
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  }
  if (field.type === 'boolean') return v === 'true';
  return v;
}
