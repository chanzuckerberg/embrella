import type { TomogramFlavor, TiltseriesMetadata, TomogramMetadata } from '../../types';
import { TOMOGRAM_FLAVORS } from '../../types';
import { autofilledValue, type FieldDef, SHARED_TOMOGRAM_FIELDS, TILTSERIES_FIELDS, TOMOGRAM_FIELDS } from './fields';
import type { FieldValue } from './MetadataRow';

function fmt(v: unknown): string {
  if (v === null || v === undefined || v === '') return 'null';
  return String(v);
}

function shown(field: FieldDef, meta: TiltseriesMetadata | TomogramMetadata): unknown {
  const v = (meta as Record<string, unknown>)[field.key];
  if (v != null && v !== '') return v;
  return field.readOnly ? autofilledValue(field, meta as never) : v;
}

const SHARED_KEYS = new Set(SHARED_TOMOGRAM_FIELDS.map((f) => f.key));
const PER_FLAVOR_FIELDS = TOMOGRAM_FIELDS.filter((f) => !SHARED_KEYS.has(f.key));

export function sessionToYaml(
  tiltseries: TiltseriesMetadata,
  tomograms: Record<TomogramFlavor, TomogramMetadata>
): string {
  const lines: string[] = ['tiltseries:'];
  for (const f of TILTSERIES_FIELDS) {
    lines.push(`  ${f.key}: ${fmt(shown(f, tiltseries))}`);
  }
  lines.push('reconstruction:');
  for (const f of SHARED_TOMOGRAM_FIELDS) {
    lines.push(`  ${f.key}: ${fmt(shown(f, tomograms.denoised))}`);
  }
  lines.push('tomograms:');
  for (const flavor of TOMOGRAM_FLAVORS) {
    lines.push(`  - flavor: ${flavor}`);
    for (const f of PER_FLAVOR_FIELDS) {
      lines.push(`    ${f.key}: ${fmt(shown(f, tomograms[flavor]))}`);
    }
  }
  return lines.join('\n');
}

/** Editable overrides parsed back out of the YAML */
export interface YamlOverrides {
  tiltseries: Record<string, FieldValue>;
  /** Shared reconstruction fields - apply to BOTH flavors. */
  shared: Record<string, FieldValue>;
  perFlavor: Record<TomogramFlavor, Record<string, FieldValue>>;
}

type RawBlocks = {
  tiltseries: Record<string, string>;
  reconstruction: Record<string, string>;
  flavors: Record<string, Record<string, string>>;
};

const KEY_NAME_RE = /^\w+$/;

/**
 * Parse the flat key/value YAML that sessionToYaml emits.
 */
function parseBlocks(text: string): RawBlocks {
  const out: RawBlocks = { tiltseries: {}, reconstruction: {}, flavors: {} };
  let target: Record<string, string> | null = null;
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (trimmed === '' || trimmed.startsWith('#')) continue;
    if (trimmed === 'tiltseries:') {
      target = out.tiltseries;
      continue;
    }
    if (trimmed === 'reconstruction:') {
      target = out.reconstruction;
      continue;
    }
    if (trimmed === 'tomograms:') {
      target = null;
      continue;
    }
    const stripped = trimmed.startsWith('- ') ? trimmed.slice(2).trim() : trimmed;
    const colon = stripped.indexOf(':');
    if (colon === -1) continue;
    const key = stripped.slice(0, colon);
    const value = stripped.slice(colon + 1).trim();
    if (!KEY_NAME_RE.test(key)) continue;
    if (key === 'flavor') {
      const flavor = value.trim();
      out.flavors[flavor] = out.flavors[flavor] ?? {};
      target = out.flavors[flavor];
      continue;
    }
    if (target) target[key] = value;
  }
  return out;
}

function coerce(field: FieldDef, raw: string): FieldValue {
  const v = raw.trim();
  if (v === '' || v === 'null') return null;
  if (field.type === 'number') {
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  }
  if (field.type === 'boolean') return v === 'true';
  return v;
}

function pickEditable(fields: FieldDef[], raw: Record<string, string>): Record<string, FieldValue> {
  const out: Record<string, FieldValue> = {};
  for (const f of fields) {
    if (f.readOnly) continue;
    if (f.key in raw) out[f.key] = coerce(f, raw[f.key]);
  }
  return out;
}

/**
 * YAML → editable field overrides.
 */
export function yamlToSession(text: string): YamlOverrides {
  const { tiltseries: tsRaw, reconstruction: recRaw, flavors } = parseBlocks(text);

  const perFlavor = Object.fromEntries(
    TOMOGRAM_FLAVORS.map((flavor) => [flavor, pickEditable(PER_FLAVOR_FIELDS, flavors[flavor] ?? {})])
  ) as Record<TomogramFlavor, Record<string, FieldValue>>;

  return {
    tiltseries: pickEditable(TILTSERIES_FIELDS, tsRaw),
    shared: pickEditable(SHARED_TOMOGRAM_FIELDS, recRaw),
    perFlavor,
  };
}
