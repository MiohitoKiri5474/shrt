import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AddUserForm from '../AddUserForm.vue'
import * as authApiModule from '../../api/auth'

vi.mock('../../api/auth', () => ({
  authApi: {
    addUser: vi.fn(),
  },
}))

const mockUser = {
  email: 'new@example.com',
  created_at: '2024-01-01T00:00:00Z',
  is_admin: false,
  username: null,
}

describe('AddUserForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('emits user-added with email on successful creation', async () => {
    vi.mocked(authApiModule.authApi.addUser).mockResolvedValue(mockUser)
    const wrapper = mount(AddUserForm)

    await wrapper.find('input[type="email"]').setValue('new@example.com')
    await wrapper.find('input[type="password"]').setValue('strongpassword123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.emitted('user-added')).toEqual([['new@example.com']])
    wrapper.unmount()
  })

  it('emits close when Escape key is pressed', async () => {
    const wrapper = mount(AddUserForm)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('close')).toHaveLength(1)
    wrapper.unmount()
  })

  it('emits close when the × close button is clicked', async () => {
    const wrapper = mount(AddUserForm)

    await wrapper.find('.close-btn').trigger('click')

    expect(wrapper.emitted('close')).toHaveLength(1)
    wrapper.unmount()
  })

  it('does not call addUser and shows error when password is too short', async () => {
    const wrapper = mount(AddUserForm)

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('input[type="password"]').setValue('short')
    await wrapper.find('form').trigger('submit.prevent')

    expect(authApiModule.authApi.addUser).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').text()).toContain('12 characters')
    wrapper.unmount()
  })

  it('shows "already taken" error when API returns 409', async () => {
    vi.mocked(authApiModule.authApi.addUser).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(AddUserForm)

    await wrapper.find('input[type="email"]').setValue('taken@example.com')
    await wrapper.find('input[type="password"]').setValue('strongpassword123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('already taken')
    wrapper.unmount()
  })

  it('shows generic error when API returns non-409 failure', async () => {
    vi.mocked(authApiModule.authApi.addUser).mockRejectedValue({ response: { status: 500 } })
    const wrapper = mount(AddUserForm)

    await wrapper.find('input[type="email"]').setValue('user@example.com')
    await wrapper.find('input[type="password"]').setValue('strongpassword123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('Failed to create user')
    wrapper.unmount()
  })
})
