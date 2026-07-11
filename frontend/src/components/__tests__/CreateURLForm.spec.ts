import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import CreateURLForm from '../CreateURLForm.vue'
import * as urlsStoreModule from '../../stores/urls'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/links/:code/share', name: 'share', component: { template: '<div />' } },
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

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    createSpy = vi.fn()
    vi.spyOn(urlsStoreModule, 'useURLsStore').mockReturnValue({
      create: createSpy,
    } as unknown as ReturnType<typeof urlsStoreModule.useURLsStore>)
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
})
