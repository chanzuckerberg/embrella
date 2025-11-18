/**
 * Parses API error responses into user-friendly error messages
 * Handles multiple error formats from Django REST Framework
 * 
 * @param errorData - The error response from the API
 * @param defaultMessage - Fallback message if error parsing fails
 * @returns Formatted error message string
 */
export function parseApiError(errorData: any, defaultMessage: string): string {
    let errorMsg = defaultMessage;
  
    if (errorData.detail) {
      // Handle object with field-specific errors
      if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
        const fieldErrors = Object.entries(errorData.detail)
          .map(([field, messages]) => {
            const msgArray = Array.isArray(messages) ? messages : [messages];
            return `${field}: ${msgArray.join(', ')}`;
          })
          .join('; ');
        errorMsg = fieldErrors;
      }
      // Handle string error message
      else if (typeof errorData.detail === 'string') {
        errorMsg = errorData.detail;
      }
      // Handle array of error messages
      else if (Array.isArray(errorData.detail)) {
        errorMsg = errorData.detail.join(', ');
      }
    }
    // Fallback to generic error field
    else if (errorData.error) {
      errorMsg = errorData.error;
    }
    // Fallback to message field
    else if (errorData.message) {
      errorMsg = errorData.message;
    }
  
    // Clean up error message (remove "Error:" prefix if present)
    return errorMsg.replace(/^Error:\s*/i, '').trim();
  }