/*
 * Converts a camelCase string to a human readable string.
 * Example: "camelCase" -> "Camel Case"
 */
export const humanize = (s: string): string => {
  // Inserts a space before each capital letter
  const result = s.replace(/([A-Z])/g, " $1");

  // Capitalizes the first letter and returns string
  return result.charAt(0).toUpperCase() + result.slice(1);
};
