import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import FileCard from '../FileCard.vue'
import * as filesApiModule from '../../api/files'

vi.mock('../../api/files', () => ({
  filesApi: {
    unlock: vi.fn(),
    fileUrl: vi.fn((code: string) => `https://api.example.com/f/${code}`),
    resolveDownloadUrl: vi.fn((url: string) => `https://api.example.com${url}`),
  },
}))

const mockFile = {
  id: 5,
  short_code: 'filecode1',
  kind: 'file' as const,
  original_filename: 'report.pdf',
  mime_type: 'application/pdf',
  size_bytes: 1024,
  created_at: '',
  expires_at: '2099-01-01T00:00:00Z',
  has_password: false,
}

const mockProtectedImage = {
  ...mockFile,
  id: 6,
  kind: 'image' as const,
  original_filename: 'photo.png',
  expires_at: null,
  has_password: true,
}

describe('FileCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders an Open link built from filesApi.fileUrl when not password protected', () => {
    const wrapper = mount(FileCard, { props: { file: mockFile } })
    expect(wrapper.find('.btn-open').attributes('href')).toBe('https://api.example.com/f/filecode1')
  })

  it('shows a Permanent chip when the file never expires', () => {
    const wrapper = mount(FileCard, { props: { file: mockProtectedImage } })
    expect(wrapper.text()).toContain('Permanent')
  })

  it('shows the formatted expiry date when the file has one', () => {
    const wrapper = mount(FileCard, { props: { file: mockFile } })
    expect(wrapper.text()).toContain(new Date(mockFile.expires_at).toLocaleDateString())
  })

  it('shows a password-input unlock control instead of Open when password protected', () => {
    const wrapper = mount(FileCard, { props: { file: mockProtectedImage } })
    expect(wrapper.find('.btn-open').exists()).toBe(false)
    expect(wrapper.find('[data-testid="file-unlock-input"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="file-unlock-button"]').exists()).toBe(true)
  })

  it('calls filesApi.unlock and opens the resolved download URL on success', async () => {
    vi.mocked(filesApiModule.filesApi.unlock).mockResolvedValue({ download_url: '/f/filecode1?token=t' })
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const wrapper = mount(FileCard, { props: { file: mockProtectedImage } })
    await wrapper.find('[data-testid="file-unlock-input"]').setValue('secretpw')
    await wrapper.find('[data-testid="file-unlock-button"]').trigger('click')
    await flushPromises()
    expect(filesApiModule.filesApi.unlock).toHaveBeenCalledWith('filecode1', 'secretpw')
    expect(openSpy).toHaveBeenCalledWith('https://api.example.com/f/filecode1?token=t', '_blank', 'noopener,noreferrer')
    openSpy.mockRestore()
  })

  it('shows an error on wrong password', async () => {
    vi.mocked(filesApiModule.filesApi.unlock).mockRejectedValue({ response: { status: 401 } })
    const wrapper = mount(FileCard, { props: { file: mockProtectedImage } })
    await wrapper.find('[data-testid="file-unlock-input"]').setValue('wrong')
    await wrapper.find('[data-testid="file-unlock-button"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Incorrect password')
  })

  it('shows an error when the file has expired', async () => {
    vi.mocked(filesApiModule.filesApi.unlock).mockRejectedValue({ response: { status: 410 } })
    const wrapper = mount(FileCard, { props: { file: mockProtectedImage } })
    await wrapper.find('[data-testid="file-unlock-input"]').setValue('secretpw')
    await wrapper.find('[data-testid="file-unlock-button"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('expired')
  })

  it('emits delete with the file id when the Delete button is clicked', async () => {
    const wrapper = mount(FileCard, { props: { file: mockFile } })
    await wrapper.find('.btn-delete').trigger('click')
    expect(wrapper.emitted('delete')).toEqual([[5]])
  })
})
