import type { TiltseriesMetadata, TomogramMetadata } from '../../types';
import { autofilledValue, type FieldDef, TILTSERIES_FIELDS, TOMOGRAM_FIELDS } from './fields';

function fmt(v: unknown): string {
  if (v === null || v === undefined || v === '') return 'null';
  return String(v);
}

function shown(field: FieldDef, meta: TiltseriesMetadata | TomogramMetadata): unknown {
  const v = (meta as Record<string, unknown>)[field.key];
  if (v != null && v !== '') return v;
  return field.readOnly ? autofilledValue(field, meta as never) : v;
}

export function sessionToYaml(tiltseries: TiltseriesMetadata, tomogram: TomogramMetadata): string {
  const lines: string[] = ['tiltseries:'];
  for (const f of TILTSERIES_FIELDS) {
    lines.push(`  ${f.key}: ${fmt(shown(f, tiltseries))}`);
  }
  lines.push('tomograms:');
  for (const f of TOMOGRAM_FIELDS) {
    lines.push(`  ${f.key}: ${fmt(shown(f, tomogram))}`);
  }
  return lines.join('\n');
}
