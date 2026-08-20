import type { TiltseriesMetadata, TomogramMetadata } from '../../types';
import { TILTSERIES_FIELDS, TOMOGRAM_FIELDS } from './fields';

function scalar(v: unknown): string {
  if (v === null || v === undefined) return 'null';
  return String(v);
}

export function toYaml(obj: unknown, indent = 0): string {
  const pad = '  '.repeat(indent);
  if (obj === null || obj === undefined) return `${pad}null`;
  if (typeof obj !== 'object') return `${pad}${scalar(obj)}`;

  if (Array.isArray(obj)) {
    if (obj.length === 0) return `${pad}[]`;
    return obj
      .map((v) => (v && typeof v === 'object' ? `${pad}-\n${toYaml(v, indent + 1)}` : `${pad}- ${scalar(v)}`))
      .join('\n');
  }

  const entries = Object.entries(obj as Record<string, unknown>);
  if (entries.length === 0) return `${pad}{}`;
  return entries
    .map(([k, v]) =>
      v && typeof v === 'object' ? `${pad}${k}:\n${toYaml(v, indent + 1)}` : `${pad}${k}: ${scalar(v)}`
    )
    .join('\n');
}

function fmt(v: unknown): string {
  if (v === null || v === undefined || v === '') return 'null';
  return String(v);
}

export function sessionToYaml(tiltseries: TiltseriesMetadata, tomogram: TomogramMetadata): string {
  const lines: string[] = ['tiltseries:'];
  for (const f of TILTSERIES_FIELDS) {
    lines.push(`  ${f.key}: ${fmt((tiltseries as Record<string, unknown>)[f.key])}`);
  }
  lines.push('tomograms:');
  for (const f of TOMOGRAM_FIELDS) {
    lines.push(`  ${f.key}: ${fmt((tomogram as Record<string, unknown>)[f.key])}`);
  }
  return lines.join('\n');
}

export interface ParsedSessionYaml {
  tiltseries: Record<string, string>;
  tomograms: Record<string, string>;
}

const KV = /^\s+(\w+):(.*)$/;

/** Parse the flat modeled-field YAML back into { tiltseries, tomograms } string maps. */
export function parseSessionYaml(text: string): ParsedSessionYaml {
  const out: ParsedSessionYaml = { tiltseries: {}, tomograms: {} };
  let cur: 'tiltseries' | 'tomograms' | null = null;
  for (const raw of text.split('\n')) {
    if (/^tiltseries:\s*$/.test(raw)) {
      cur = 'tiltseries';
      continue;
    }
    if (/^tomograms:\s*$/.test(raw)) {
      cur = 'tomograms';
      continue;
    }
    const m = KV.exec(raw);
    if (m && cur) out[cur][m[1]] = m[2];
  }
  return out;
}
