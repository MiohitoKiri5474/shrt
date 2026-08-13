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

export const filesApi = {
  // axios's default transformRequest detects a FormData body and strips the
  // instance's default JSON Content-Type, letting the browser set the
  // multipart boundary itself — no manual header handling needed here.
  async upload(file: File, kind: FileKind): Promise<FileOut> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('kind', kind)
    const { data } = await apiClient.post<FileOut>('/api/files', formData)
    return data
  },
  async list(): Promise<FileOut[]> {
    const { data } = await apiClient.get<FileOut[]>('/api/files')
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
    const base = BASE_URL || window.location.origin
    return `${base}/f/${encodeURIComponent(shortCode)}`
  },
}
