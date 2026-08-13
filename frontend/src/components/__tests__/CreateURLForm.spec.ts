import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import CreateURLForm from '../CreateURLForm.vue'
import * as urlsStoreModule from '../../stores/urls'
import * as filesStoreModule from '../../stores/files'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/links/:code/share', name: 'share', component: { template: '<div />' } },
    { path: '/manage', name: 'manage', component: { template: '<div />' } },
  ],
})

const globalOptions = { plugins: [router] }

const mockCreatedUrl = {
  id: 1,
  short_code: 'newcode1',
  original_url: 'https://example.com',
  created_at: '',
  click_count: 0,
  has_password: false,
  expires_at: null,
}

describe('CreateURLForm', () => {
  let createSpy: ReturnType<typeof vi.fn>
  let uploadSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    createSpy = vi.fn()
    uploadSpy = vi.fn()
    vi.spyOn(urlsStoreModule, 'useURLsStore').mockReturnValue({
      create: createSpy,
    } as unknown as ReturnType<typeof urlsStoreModule.useURLsStore>)
    vi.spyOn(filesStoreModule, 'useFilesStore').mockReturnValue({
      upload: uploadSpy,
    } as unknown as ReturnType<typeof filesStoreModule.useFilesStore>)
  })

  it('renders URL input and submit button', () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    expect(wrapper.find('#original-url').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').text()).toBe('Create short URL')
  })

  it('shows no error initially', () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls store.create with valid URL', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
  })

  it('prepends https:// when protocol missing', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
  })

  it('passes custom code when provided', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('my-link')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', 'my-link', undefined, undefined)
  })

  it('passes password when provided', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#link-password').setValue('secret')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, 'secret', undefined)
  })

  it('passes expiry date when provided', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#expires-at').setValue('2099-01-01T00:00')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith(
      'https://example.com',
      undefined,
      undefined,
      new Date('2099-01-01T00:00').toISOString(),
    )
  })

  it('navigates to the share page after successful creation', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('share')
    expect(router.currentRoute.value.params.code).toBe('newcode1')
  })

  it('keeps the submit button disabled until navigation to the share page completes', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    let resolveNav!: () => void
    const pushSpy = vi.spyOn(router, 'push').mockImplementation(
      () => new Promise<void>((resolve) => { resolveNav = resolve }),
    )
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()

    // create() has resolved but navigation is still pending: the button must stay disabled
    // so a second click can't fire a duplicate create() call.
    expect(createSpy).toHaveBeenCalledTimes(1)
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()

    resolveNav()
    await flushPromises()

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    pushSpy.mockRestore()
  })

  it('shows a distinct redirect-failure message (not the create-failure message) when navigation fails after a successful create', async () => {
    createSpy.mockResolvedValue(mockCreatedUrl)
    const pushSpy = vi.spyOn(router, 'push').mockRejectedValue(new Error('chunk load failed'))
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()

    expect(createSpy).toHaveBeenCalledTimes(1)
    const alert = wrapper.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).not.toContain('Failed to create URL.')
    expect(alert.text()).toContain('was created')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    pushSpy.mockRestore()
  })

  it('shows error for invalid custom code', async () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('x!')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Custom code')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error for short password', async () => {
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#link-password').setValue('abc')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Password must be at least 6 characters')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error on 409 conflict', async () => {
    createSpy.mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('taken1')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('already taken')
  })

  it('shows generic error on other failures', async () => {
    createSpy.mockRejectedValue({ response: { status: 500 } })
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to create')
  })

  it('disables submit while loading', async () => {
    let resolve: (value: typeof mockCreatedUrl) => void
    createSpy.mockImplementation(() => new Promise<typeof mockCreatedUrl>((r) => { resolve = r }))
    const wrapper = mount(CreateURLForm, { global: globalOptions })
    await wrapper.find('#original-url').setValue('https://example.com')
    const btn = wrapper.find('button[type="submit"]')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    expect(btn.attributes('disabled')).toBeDefined()
    resolve!(mockCreatedUrl)
    await flushPromises()
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  describe('File tab', () => {
    const mockUploadedFile = {
      id: 1, short_code: 'filecode1', kind: 'file' as const, original_filename: 'a.pdf',
      mime_type: 'application/pdf', size_bytes: 100, created_at: '', expires_at: '2099-01-01T00:00:00Z',
      has_password: false,
    }

    async function selectFileTab(wrapper: ReturnType<typeof mount>) {
      await wrapper.find('input[type="radio"][value="file"]').setValue()
    }

    function setFile(wrapper: ReturnType<typeof mount>, file: File) {
      const input = wrapper.find('#upload-file')
      Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
      return input.trigger('change')
    }

    it('shows the file input and hides link fields once File is selected', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      expect(wrapper.find('#upload-file').exists()).toBe(true)
      expect(wrapper.find('#original-url').exists()).toBe(false)
      expect(wrapper.find('button[type="submit"]').text()).toBe('Upload file')
    })

    it('calls filesStore.upload with the selected file and kind "file"', async () => {
      uploadSpy.mockResolvedValue(mockUploadedFile)
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      const file = new File(['content'], 'a.pdf', { type: 'application/pdf' })
      await setFile(wrapper, file)
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(uploadSpy).toHaveBeenCalledWith(file, 'file')
    })

    it('navigates to the manage page after a successful upload', async () => {
      uploadSpy.mockResolvedValue(mockUploadedFile)
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      await setFile(wrapper, new File(['content'], 'a.pdf', { type: 'application/pdf' }))
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(router.currentRoute.value.name).toBe('manage')
    })

    it('shows an error and does not call upload when no file is selected', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('choose a file')
      expect(uploadSpy).not.toHaveBeenCalled()
    })

    it('shows an error and does not call upload when the file exceeds 25MB', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      const bigFile = new File([new Uint8Array(1)], 'big.pdf', { type: 'application/pdf' })
      Object.defineProperty(bigFile, 'size', { value: 26 * 1024 * 1024 })
      await setFile(wrapper, bigFile)
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('25MB')
      expect(uploadSpy).not.toHaveBeenCalled()
    })

    it('shows a type-rejected error on a 422 response', async () => {
      uploadSpy.mockRejectedValue({ response: { status: 422 } })
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      await setFile(wrapper, new File(['content'], 'a.exe', { type: 'application/octet-stream' }))
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('not allowed')
    })

    it('shows a too-large error on a 413 response', async () => {
      uploadSpy.mockRejectedValue({ response: { status: 413 } })
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectFileTab(wrapper)
      await setFile(wrapper, new File(['content'], 'a.pdf', { type: 'application/pdf' }))
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('too large')
    })
  })

  describe('Image tab', () => {
    const mockUploadedImage = {
      id: 2, short_code: 'imgcode1', kind: 'image' as const, original_filename: 'pic.png',
      mime_type: 'image/png', size_bytes: 100, created_at: '', expires_at: null,
      has_password: false,
    }

    async function selectImageTab(wrapper: ReturnType<typeof mount>) {
      await wrapper.find('input[type="radio"][value="image"]').setValue()
    }

    function setImage(wrapper: ReturnType<typeof mount>, file: File) {
      const input = wrapper.find('#upload-image')
      Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
      return input.trigger('change')
    }

    it('shows the image input and hides link/file fields once Image is selected', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      expect(wrapper.find('#upload-image').exists()).toBe(true)
      expect(wrapper.find('#original-url').exists()).toBe(false)
      expect(wrapper.find('#upload-file').exists()).toBe(false)
      expect(wrapper.find('button[type="submit"]').text()).toBe('Upload image')
    })

    it('restricts the file picker to the image allowlist', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      expect(wrapper.find('#upload-image').attributes('accept')).toBe(
        'image/jpeg,image/png,image/gif,image/webp',
      )
    })

    it('calls filesStore.upload with the selected file and kind "image"', async () => {
      uploadSpy.mockResolvedValue(mockUploadedImage)
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      const file = new File(['content'], 'pic.png', { type: 'image/png' })
      await setImage(wrapper, file)
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(uploadSpy).toHaveBeenCalledWith(file, 'image')
    })

    it('navigates to the manage page after a successful upload', async () => {
      uploadSpy.mockResolvedValue(mockUploadedImage)
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      await setImage(wrapper, new File(['content'], 'pic.png', { type: 'image/png' }))
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(router.currentRoute.value.name).toBe('manage')
    })

    it('shows an error and does not call upload when no image is selected', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('choose an image')
      expect(uploadSpy).not.toHaveBeenCalled()
    })

    it('shows an error and does not call upload when the image exceeds 25MB', async () => {
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      const bigImage = new File([new Uint8Array(1)], 'big.png', { type: 'image/png' })
      Object.defineProperty(bigImage, 'size', { value: 26 * 1024 * 1024 })
      await setImage(wrapper, bigImage)
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('25MB')
      expect(uploadSpy).not.toHaveBeenCalled()
    })

    it('shows a quota error on a 413 response', async () => {
      uploadSpy.mockRejectedValue({ response: { status: 413 } })
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      await setImage(wrapper, new File(['content'], 'pic.png', { type: 'image/png' }))
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('500MB image quota')
    })

    it('shows a type-rejected error on a 422 response', async () => {
      uploadSpy.mockRejectedValue({ response: { status: 422 } })
      const wrapper = mount(CreateURLForm, { global: globalOptions })
      await selectImageTab(wrapper)
      await setImage(wrapper, new File(['content'], 'pic.bmp', { type: 'image/bmp' }))
      await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('This image type is not allowed')
    })
  })
})
