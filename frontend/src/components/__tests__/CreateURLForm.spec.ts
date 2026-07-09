import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import CreateURLForm from '../CreateURLForm.vue'
import * as urlsStoreModule from '../../stores/urls'

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
    const wrapper = mount(CreateURLForm)
    expect(wrapper.find('#original-url').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').text()).toBe('Create short URL')
  })

  it('shows no error initially', () => {
    const wrapper = mount(CreateURLForm)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls store.create with valid URL', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
  })

  it('prepends https:// when protocol missing', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
  })

  it('passes custom code when provided', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('my-link')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', 'my-link', undefined, undefined)
  })

  it('passes password when provided', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#link-password').setValue('secret')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, 'secret', undefined)
  })

  it('passes expiry date when provided', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
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

  it('shows error for invalid custom code', async () => {
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('x!')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Custom code')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error for short password', async () => {
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#link-password').setValue('abc')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Password must be at least 6 characters')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error on 409 conflict', async () => {
    createSpy.mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('taken1')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('already taken')
  })

  it('shows generic error on other failures', async () => {
    createSpy.mockRejectedValue({ response: { status: 500 } })
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to create')
  })

  it('clears form fields after successful creation', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('mylink')
    await wrapper.find('#expires-at').setValue('2099-01-01T00:00')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect((wrapper.find('#original-url').element as HTMLInputElement).value).toBe('')
    expect((wrapper.find('#custom-code').element as HTMLInputElement).value).toBe('')
    expect((wrapper.find('#expires-at').element as HTMLInputElement).value).toBe('')
  })

  it('disables submit while loading', async () => {
    let resolve: () => void
    createSpy.mockImplementation(() => new Promise<void>((r) => { resolve = r }))
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    const btn = wrapper.find('button[type="submit"]')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    expect(btn.attributes('disabled')).toBeDefined()
    resolve!()
    await flushPromises()
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
