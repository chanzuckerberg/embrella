import { format } from 'date-fns';

/**
 * Turning values into text for people to read.
 *
 * One module rather than one per primitive: these are all the same job, they are
 * all one-liners, and table columns routinely need two or three of them at once.
 */

export const FORMAT_PATTERN = {
  YYYY_MM_DD: 'yyyy-MM-dd',
};

/**
 * Returns date, formatted as a string.
 * @param dateStr - Date string.
 * @param formatStr - Format string.
 * @returns date, formatted as a string.
 */
export function formatDate(dateStr: string, formatStr = FORMAT_PATTERN.YYYY_MM_DD): string {
  const date = new Date(dateStr);
  return format(date, formatStr);
}

/*
 * Converts a camelCase string to a human readable string.
 * Example: "camelCase" -> "Camel Case"
 */
export const humanize = (s: string): string => {
  // Inserts a space before each capital letter
  const result = s.replace(/([A-Z])/g, ' $1');

  // Capitalizes the first letter and returns string
  return result.charAt(0).toUpperCase() + result.slice(1);
};

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];

/**
 * Human-readable byte count.
 */
export function formatBytes(size: number | null | undefined): string {
  let value = Number(size ?? 0);

  for (const unit of BYTE_UNITS.slice(0, -1)) {
    if (value < 1024) return `${value.toFixed(2)} ${unit}`;
    value /= 1024;
  }

  return `${value.toFixed(2)} ${BYTE_UNITS[BYTE_UNITS.length - 1]}`;
}
