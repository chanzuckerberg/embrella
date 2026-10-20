import { format, isToday, isYesterday } from 'date-fns';
import { FORMAT_PATTERN } from '@app/common/utils/format';

/**
 * Day header for a timeline entry, in local time: "Today", "Yesterday", else e.g. "Oct 16 2026".
 */
export const dayLabel = (at: string): string => {
  const date = new Date(at);

  if (isToday(date)) return 'Today';
  if (isYesterday(date)) return 'Yesterday';

  return format(date, FORMAT_PATTERN.MMM_D_YYYY);
};
