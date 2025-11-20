/**
 * Parses API error responses into user-friendly error messages
 * Handles multiple error formats from Django REST Framework
 *
 * @param errorData - The error response from the API
 * @param defaultMessage - Fallback message if error parsing fails
 * @returns Formatted error message string
 */
export function parseApiError(errorData: unknown, defaultMessage: string): string {
  let errorMsg = defaultMessage;

  // Type guard: check if errorData is an object
  if (typeof errorData === 'object' && errorData !== null) {
    const error = errorData as Record<string, unknown>;

    if ('detail' in error) {
      // Handle object with field-specific errors
      if (typeof error.detail === 'object' && error.detail !== null && !Array.isArray(error.detail)) {
        const fieldErrors = Object.entries(error.detail)
          .map(([field, messages]) => {
            const msgArray = Array.isArray(messages) ? messages : [messages];
            return `${field}: ${msgArray.join(', ')}`;
          })
          .join('; ');
        errorMsg = fieldErrors;
      }
      // Handle string error message
      else if (typeof error.detail === 'string') {
        errorMsg = error.detail;
      }
      // Handle array of error messages
      else if (Array.isArray(error.detail)) {
        errorMsg = error.detail.join(', ');
      }
    }
    // Fallback to generic error field
    else if ('error' in error && typeof error.error === 'string') {
      errorMsg = error.error;
    }
    // Fallback to message field
    else if ('message' in error && typeof error.message === 'string') {
      errorMsg = error.message;
    }
  }

  // Clean up error message (remove "Error:" prefix if present)
  return errorMsg.replace(/^Error:\s*/i, '').trim();
}
