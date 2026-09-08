/**
 * Pure helpers for applying server-resolved defaults to the launch form state.
 *
 * The form keeps two buckets: `parameters` for tool options and `slurmOptions` for
 * compute resources. Defaults arrive as one flat map and must be routed to the right
 * bucket without overwriting anything the user already typed.
 */

import type { JSONSchema, JSONSchemaProperty } from '@app/common/types/workflow';

export const isSlurmField = (prop: JSONSchemaProperty | undefined): boolean =>
  Boolean(prop && (prop['x-slurm-directive'] || prop['x-compute-resource']));

export const isFilled = (value: unknown): boolean => value !== undefined && value !== null && value !== '';

/** Route a flat defaults map into the two form buckets. Unknown keys go with parameters. */
export function splitDefaults(
  schema: JSONSchema,
  defaults: Record<string, unknown>
): { params: Record<string, unknown>; slurm: Record<string, unknown> } {
  const params: Record<string, unknown> = {};
  const slurm: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(defaults)) {
    (isSlurmField(schema.properties[key]) ? slurm : params)[key] = value;
  }
  return { params, slurm };
}

/**
 * New bucket state: incoming defaults win over previous defaults, user edits win over
 * everything, and cleared keys are removed unless the user typed them.
 */
export function applyUntouched(
  prev: Record<string, unknown>,
  incoming: Record<string, unknown>,
  touched: Set<string>,
  cleared: string[] = []
): Record<string, unknown> {
  const next = { ...prev };
  for (const [key, value] of Object.entries(incoming)) {
    if (!touched.has(key)) next[key] = value;
  }
  for (const key of cleared) {
    if (!touched.has(key)) delete next[key];
  }
  return next;
}

/** Required keys (schema plus cleared overrides) that are blank across the given buckets. */
export function missingRequired(required: string[], ...buckets: Record<string, unknown>[]): string[] {
  const unique = Array.from(new Set(required));
  return unique.filter((key) => !buckets.some((bucket) => isFilled(bucket[key])));
}
