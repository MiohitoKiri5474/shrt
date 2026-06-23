import { apiClient } from './client'

export interface HealthOut {
  status: string
}

// A short timeout keeps the connectivity poll responsive: a hung backend should
// surface as "offline" quickly rather than leaving the indicator stale for the
// full request-timeout default.
const HEALTH_TIMEOUT_MS = 5000

export const healthApi = {
  async check(): Promise<HealthOut> {
    const { data } = await apiClient.get<HealthOut>('/api/health', {
      timeout: HEALTH_TIMEOUT_MS,
    })
    return data
  },
}
