/**
 * Maps HTTP error responses to safe, user-facing messages.
 *
 * @param error - The caught error (expected to have an axios-style response shape).
 * @param overrides - Status-code-keyed map of messages that take precedence over the defaults.
 *   Use this to pass through known-safe business-rule messages (e.g. 409 conflict text).
 * @returns A safe string suitable for display in the UI.
 */
export function mapErrorToMessage(
  error: unknown,
  overrides: Record<number, string> = {},
): string {
  const resp =
    typeof error === 'object' && error !== null && 'response' in error
      ? (error as { response?: unknown }).response
      : undefined
  const status: number | undefined =
    typeof resp === 'object' && resp !== null && 'status' in resp &&
    typeof (resp as { status?: unknown }).status === 'number'
      ? (resp as { status: number }).status
      : undefined

  if (status !== undefined && Object.prototype.hasOwnProperty.call(overrides, status)) {
    return overrides[status]!
  }

  switch (status) {
    case 409:
      return 'A conflict occurred. Please try again.'
    case 422:
      return 'Invalid input. Please check the form.'
    case 401:
    case 403:
      return 'Authentication required.'
    case 503:
      return 'Service temporarily unavailable.'
    default:
      return 'An error occurred. Please try again.'
  }
}
