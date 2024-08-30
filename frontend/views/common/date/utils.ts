import { format } from "date-fns";
import { FORMAT_PATTERN } from "@/views/common/date/constants";

/**
 * Returns date, formatted as a string.
 * @param dateStr - Date string.
 * @param formatStr - Format string.
 * @returns date, formatted as a string.
 */
export function formatDate(
  dateStr: string,
  formatStr = FORMAT_PATTERN.YYYY_MM_DD,
): string {
  const date = new Date(dateStr);
  return format(date, formatStr);
}
