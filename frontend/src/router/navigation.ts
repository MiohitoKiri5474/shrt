import type { Router } from 'vue-router'

/**
 * Navigates to the share page for a short link. Centralizes the 'share'
 * route name and its `code` param in one place so a future rename only
 * needs to happen here instead of at every call site.
 *
 * Returns the same promise `router.push` returns so callers can keep
 * awaiting/catching navigation failures exactly as before.
 */
export function goToShare(router: Router, shortCode: string): ReturnType<Router['push']> {
  return router.push({ name: 'share', params: { code: shortCode } })
}
