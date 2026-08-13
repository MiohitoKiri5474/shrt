import { apiClient, BASE_URL } from './client'

export type FileKind = 'image' | 'file'

export interface FileOut {
  id: number
  short_code: string
  kind: FileKind
  original_filename: string
  mime_type: string
  size_bytes: number
  created_at: string
  expires_at: string | null
  has_password: boolean
}

function apiOrigin(): string {
  return BASE_URL || window.location.origin
}

export const filesApi = {
  // axios's default transformRequest detects a FormData body and strips the
  // instance's default JSON Content-Type, letting the browser set the
  // multipart boundary itself — no manual header handling needed here.
  async upload(file: File, kind: FileKind, password?: string): Promise<FileOut> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('kind', kind)
    // Only append when non-empty — the backend's Form(None, min_length=6, ...)
    // constraint would 422 an empty string, rejecting a plain no-password upload.
    if (password) formData.append('password', password)
    const { data } = await apiClient.post<FileOut>('/api/files', formData)
    return data
  },
  async list(): Promise<FileOut[]> {
    const { data } = await apiClient.get<FileOut[]>('/api/files')
    return data
  },
  async unlock(shortCode: string, password: string): Promise<{ download_url: string }> {
    const { data } = await apiClient.post<{ download_url: string }>(
      `/api/files/${shortCode}/unlock`,
      { password },
    )
    return data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/api/files/${id}`)
  },
  /**
   * The user-facing share link that serves the uploaded blob. Same
   * BASE_URL-first rule as urlsApi.shortUrl — must be absolute since it's
   * copied to the clipboard, not just used as a same-page fetch target.
   */
  fileUrl(shortCode: string): string {
    return `${apiOrigin()}/f/${encodeURIComponent(shortCode)}`
  },
  /**
   * Resolves the relative `download_url` returned by `unlock` (e.g.
   * `/f/abc123?token=...`) against the API origin. Same BASE_URL-first rule
   * as `fileUrl` — the path is relative to the backend host, not necessarily
   * the frontend host, in a split-domain deployment.
   */
  resolveDownloadUrl(downloadUrl: string): string {
    return `${apiOrigin()}${downloadUrl}`
  },
}
