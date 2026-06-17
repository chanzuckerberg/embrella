/**
 * CLI Parser for AreTomo3 Commands
 *
 * Parses AreTomo3 CLI commands and maps them to form parameters using
 * the schema's x-cli-flag mappings.
 */

import type { JSONSchema, JSONSchemaProperty } from '@app/common/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface ParsedParameter {
  fieldName: string;
  cliFlag: string;
  title: string;
  rawValue: string;
  convertedValue: unknown;
}

export interface IgnoredToken {
  token: string;
  reason: 'executable' | 'redirect' | 'unknown_flag' | 'orphan_value' | 'shell_artifact';
}

export interface CliDefaultValue {
  fieldName: string;
  title: string;
  value: unknown;
}

export interface ParsedCLIResult {
  success: boolean;
  parsedParams: Record<string, unknown>;
  parsedDetails: ParsedParameter[];
  ignoredTokens: IgnoredToken[];
  warnings: string[];
  /** CLI default values (x-cli-default) for fields not explicitly in the command */
  cliDefaults: Record<string, unknown>;
  /** Details about CLI defaults for UI display */
  cliDefaultDetails: CliDefaultValue[];
}

interface FlagInfo {
  fieldName: string;
  type: string;
  title: string;
  isComposite: boolean;
  compositeFields?: string[];
}

type FlagMapping = Record<string, FlagInfo>;

// ============================================================================
// Flag Mapping Builder
// ============================================================================

/**
 * Build a reverse mapping from CLI flags to schema field names
 */
export function buildFlagMapping(schema: JSONSchema): FlagMapping {
  const mapping: FlagMapping = {};

  if (!schema.properties) {
    return mapping;
  }

  for (const [fieldName, prop] of Object.entries(schema.properties)) {
    const property = prop as JSONSchemaProperty;
    const cliFlag = property['x-cli-flag'];

    // Skip fields without CLI flags or with null flags
    if (!cliFlag || cliFlag === null) {
      continue;
    }

    const compositeValue = property['x-cli-composite'];
    const isComposite = Array.isArray(compositeValue);
    const compositeFields = isComposite ? compositeValue : undefined;

    mapping[cliFlag] = {
      fieldName,
      type: property.type || 'string',
      title: property.title || fieldName,
      isComposite,
      compositeFields,
    };
  }

  return mapping;
}

// ============================================================================
// Input Normalization
// ============================================================================

/**
 * Normalize CLI input by handling line continuations, tabs, and multiple spaces
 */
function normalizeInput(input: string): string {
  return (
    input
      // Remove backslash line continuations
      .replace(/\\\s*\n/g, ' ')
      // Replace tabs with spaces
      .replace(/\t/g, ' ')
      // Collapse multiple spaces into single space
      .replace(/\s+/g, ' ')
      // Trim
      .trim()
  );
}

// ============================================================================
// Token Detection Helpers
// ============================================================================

/**
 * Check if a token is a CLI flag (starts with -)
 */
function isFlag(token: string): boolean {
  return token.startsWith('-') && !/^-?\d+(\.\d+)?$/.test(token);
}

/**
 * Check if a token is an executable path
 */
function isExecutablePath(token: string): boolean {
  // Paths starting with / that contain AreTomo or common executable patterns
  if (token.startsWith('/')) {
    const lowerToken = token.toLowerCase();
    return (
      lowerToken.includes('aretomo') ||
      lowerToken.includes('/bin/') ||
      lowerToken.includes('/software/') ||
      lowerToken.includes('/executables/') ||
      // Ends with version-like pattern
      /\/[a-zA-Z0-9_-]+_\d+\.\d+/.test(token)
    );
  }
  return false;
}

/**
 * Check if a token is a shell redirect
 */
function isShellRedirect(token: string): boolean {
  // Matches: 2>/dev/null, 2>&1, >/path, >>, etc.
  return /^\d*[<>]|^&>/.test(token);
}

/**
 * Check if a token is a shell artifact to ignore
 */
function isShellArtifact(token: string): boolean {
  const artifacts = ['|', '||', '&&', ';', '&', '(', ')', '{', '}', '[[', ']]', '[', ']'];
  return artifacts.includes(token) || token.startsWith('#');
}

// ============================================================================
// Tokenizer
// ============================================================================

/**
 * Tokenize the normalized CLI string into an array of tokens
 */
function tokenize(normalizedInput: string): string[] {
  const tokens: string[] = [];
  let current = '';
  let inQuote = false;
  let quoteChar = '';

  for (let i = 0; i < normalizedInput.length; i++) {
    const char = normalizedInput[i];

    if (inQuote) {
      if (char === quoteChar) {
        inQuote = false;
        if (current) {
          tokens.push(current);
          current = '';
        }
      } else {
        current += char;
      }
    } else if (char === '"' || char === "'") {
      inQuote = true;
      quoteChar = char;
    } else if (char === ' ') {
      if (current) {
        tokens.push(current);
        current = '';
      }
    } else {
      current += char;
    }
  }

  if (current) {
    tokens.push(current);
  }

  return tokens;
}

// ============================================================================
// Type Conversion
// ============================================================================

/**
 * Convert a string value to the appropriate type based on schema
 */
function convertValue(values: string[], type: string): unknown {
  if (values.length === 0) {
    // Flag present without value - return empty string so it renders as just the flag
    return '';
  }

  switch (type) {
    case 'number': {
      const num = parseFloat(values[0]);
      return isNaN(num) ? values[0] : num;
    }

    case 'integer': {
      const int = parseInt(values[0], 10);
      return isNaN(int) ? values[0] : int;
    }

    case 'boolean':
      // Handle '0'/'1' boolean representations
      // Return false only for explicit '0' or 'false', otherwise true (presence implies true)
      return !(values[0] === '0' || values[0].toLowerCase() === 'false');

    case 'string':
    default:
      // For multi-value strings (like AtBin), join with space
      return values.join(' ');
  }
}

/**
 * Get title for a field from schema
 */
function getFieldTitle(schema: JSONSchema, fieldName: string): string {
  const prop = schema.properties?.[fieldName] as JSONSchemaProperty | undefined;
  return prop?.title || fieldName;
}

// ============================================================================
// Main Parser
// ============================================================================

/**
 * Parse an AreTomo3 CLI command and extract parameters
 *
 * @param cliText - The CLI command text to parse
 * @param schema - The processor JSON schema with x-cli-flag mappings
 * @returns ParsedCLIResult with parsed parameters and ignored tokens
 */
/**
 * Extract CLI default values from schema
 * These are the values the CLI tool uses when a flag is not provided
 */
function extractCliDefaults(
  schema: JSONSchema,
  excludeFields: Set<string>
): { defaults: Record<string, unknown>; details: CliDefaultValue[] } {
  const defaults: Record<string, unknown> = {};
  const details: CliDefaultValue[] = [];

  if (!schema.properties) {
    return { defaults, details };
  }

  for (const [fieldName, prop] of Object.entries(schema.properties)) {
    const property = prop as JSONSchemaProperty;
    const cliDefault = property['x-cli-default'];

    // Only include if field has x-cli-default and wasn't explicitly parsed
    if (cliDefault !== undefined && !excludeFields.has(fieldName)) {
      defaults[fieldName] = cliDefault;
      details.push({
        fieldName,
        title: property.title || fieldName,
        value: cliDefault,
      });
    }
  }

  return { defaults, details };
}

export function parseCLICommand(cliText: string, schema: JSONSchema): ParsedCLIResult {
  const result: ParsedCLIResult = {
    success: false,
    parsedParams: {},
    parsedDetails: [],
    ignoredTokens: [],
    warnings: [],
    cliDefaults: {},
    cliDefaultDetails: [],
  };

  // Handle empty input
  if (!cliText || !cliText.trim()) {
    result.warnings.push('No CLI command provided');
    return result;
  }

  // Build flag mapping from schema
  const flagMapping = buildFlagMapping(schema);

  // Normalize and tokenize
  const normalized = normalizeInput(cliText);
  const tokens = tokenize(normalized);

  // Process tokens
  let i = 0;
  while (i < tokens.length) {
    const token = tokens[i];

    // Check for tokens to ignore
    if (isExecutablePath(token)) {
      result.ignoredTokens.push({ token, reason: 'executable' });
      i++;
      continue;
    }

    if (isShellRedirect(token)) {
      result.ignoredTokens.push({ token, reason: 'redirect' });
      i++;
      continue;
    }

    if (isShellArtifact(token)) {
      result.ignoredTokens.push({ token, reason: 'shell_artifact' });
      i++;
      continue;
    }

    // Check if this is a flag
    if (isFlag(token)) {
      const flagInfo = flagMapping[token];

      if (flagInfo) {
        // Collect values until the next flag
        const values: string[] = [];
        while (i + 1 < tokens.length && !isFlag(tokens[i + 1])) {
          i++;
          const nextToken = tokens[i];

          // Skip shell artifacts in value position
          if (isShellRedirect(nextToken) || isShellArtifact(nextToken)) {
            result.ignoredTokens.push({
              token: nextToken,
              reason: isShellRedirect(nextToken) ? 'redirect' : 'shell_artifact',
            });
            continue;
          }

          values.push(nextToken);
        }

        // Handle composite flags (like -TiltAxis which maps to multiple fields)
        if (flagInfo.isComposite && flagInfo.compositeFields) {
          flagInfo.compositeFields.forEach((fieldName, index) => {
            if (values[index] !== undefined) {
              const fieldType = (schema.properties?.[fieldName] as JSONSchemaProperty | undefined)?.type || 'string';
              const convertedValue = convertValue([values[index]], fieldType);
              result.parsedParams[fieldName] = convertedValue;
              result.parsedDetails.push({
                fieldName,
                cliFlag: token,
                title: getFieldTitle(schema, fieldName),
                rawValue: values[index],
                convertedValue,
              });
            }
          });
        } else {
          // Regular flag
          const convertedValue = convertValue(values, flagInfo.type);
          result.parsedParams[flagInfo.fieldName] = convertedValue;
          result.parsedDetails.push({
            fieldName: flagInfo.fieldName,
            cliFlag: token,
            title: flagInfo.title,
            rawValue: values.join(' '),
            convertedValue,
          });
        }
      } else {
        // Unknown flag
        result.ignoredTokens.push({ token, reason: 'unknown_flag' });

        // Skip its values too, but still record them as ignored
        while (i + 1 < tokens.length && !isFlag(tokens[i + 1])) {
          i++;
          const skippedValue = tokens[i];
          if (isShellRedirect(skippedValue)) {
            result.ignoredTokens.push({ token: skippedValue, reason: 'redirect' });
          } else if (isShellArtifact(skippedValue)) {
            result.ignoredTokens.push({ token: skippedValue, reason: 'shell_artifact' });
          } else {
            result.ignoredTokens.push({ token: skippedValue, reason: 'orphan_value' });
          }
        }
      }
    } else {
      // Orphan value (not preceded by a recognized flag)
      result.ignoredTokens.push({ token, reason: 'orphan_value' });
    }

    i++;
  }

  // Mark as successful if we parsed at least one parameter
  result.success = result.parsedDetails.length > 0;

  if (!result.success && result.ignoredTokens.length > 0) {
    result.warnings.push('No recognized parameters found. Check that the CLI flags match AreTomo3 syntax.');
  }

  // Extract CLI defaults for fields that weren't explicitly parsed
  // These represent what the CLI tool would use when the flag is absent
  const parsedFieldNames = new Set(result.parsedDetails.map((p) => p.fieldName));
  const { defaults, details } = extractCliDefaults(schema, parsedFieldNames);
  result.cliDefaults = defaults;
  result.cliDefaultDetails = details;

  return result;
}

/**
 * Get a human-readable description for an ignored token reason
 */
export function getIgnoredReasonDescription(reason: IgnoredToken['reason']): string {
  switch (reason) {
    case 'executable':
      return 'Executable path';
    case 'redirect':
      return 'Shell redirect';
    case 'unknown_flag':
      return 'Unrecognized flag';
    case 'orphan_value':
      return 'Value without flag';
    case 'shell_artifact':
      return 'Shell syntax';
    default:
      return 'Unknown';
  }
}
