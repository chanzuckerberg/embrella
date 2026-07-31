import useMediaQuery from '@mui/material/useMediaQuery';

/**
 * Matches Tailwind's `lg` breakpoint (1024px), so `useIsNarrowViewport()` and the
 * `max-lg:` / `lg:hidden` utility classes always agree about what "narrow" means.
 */
export const NARROW_VIEWPORT_QUERY = '(max-width: 1023.95px)';

/** True on phones and portrait tablets. */
export const useIsNarrowViewport = () => useMediaQuery(NARROW_VIEWPORT_QUERY);
