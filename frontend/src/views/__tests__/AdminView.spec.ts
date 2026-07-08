import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AdminView from '../AdminView.vue'
import * as adminApiModule from '../../api/admin'

// jsdom doesn't implement matchMedia; stub it so useThemeStore doesn't throw
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock('../../api/admin', () => ({
  adminApi: {
    listUsers: vi.fn(),
    updateUser: vi.fn(),
    deleteUser: vi.fn(),
  },
}))

// Stub AddUserForm so it doesn't attach document listeners during AdminView tests
const AddUserFormStub = defineComponent({
  name: 'AddUserForm',
  emits: ['close', 'user-added'],
  template: '<div class="add-user-form-stub" />',
})

const AppNavbarStub = defineComponent({
  name: 'AppNavbar',
  template: '<div class="navbar-stub" />',
})

const globalOptions = {
  stubs: {
    RouterLink: true,
    AddUserForm: AddUserFormStub,
    AppNavbar: AppNavbarStub,
  },
}

describe('AdminView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([])
  })

  it('shows the Add User button and no modal initially', async () => {
    const wrapper = mount(AdminView, { global: globalOptions })
    await flushPromises()

    expect(wrapper.find('.btn-add-user').exists()).toBe(true)
    expect(wrapper.findComponent(AddUserFormStub).exists()).toBe(false)
  })

  it('opens the modal when Add User button is clicked', async () => {
    const wrapper = mount(AdminView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.btn-add-user').trigger('click')

    expect(wrapper.findComponent(AddUserFormStub).exists()).toBe(true)
  })

  it('closes modal when AddUserForm emits close', async () => {
    const wrapper = mount(AdminView, { global: globalOptions })
    await flushPromises()

    await wrapper.find('.btn-add-user').trigger('click')
    expect(wrapper.findComponent(AddUserFormStub).exists()).toBe(true)

    await wrapper.findComponent(AddUserFormStub).vm.$emit('close')
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent(AddUserFormStub).exists()).toBe(false)
  })

  it('renders AppNavbar', async () => {
    const wrapper = mount(AdminView, { global: globalOptions })
    await flushPromises()
    expect(wrapper.find('.navbar-stub').exists()).toBe(true)
  })

  describe('toast behaviour', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('shows toast with correct email after user-added emit', async () => {
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()

      await wrapper.find('.btn-add-user').trigger('click')
      await wrapper.findComponent(AddUserFormStub).vm.$emit('user-added', 'toast@example.com')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[role="status"]').text()).toContain('toast@example.com')
      wrapper.unmount()
    })

    it('toast clears after 3000ms', async () => {
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()

      await wrapper.find('.btn-add-user').trigger('click')
      await wrapper.findComponent(AddUserFormStub).vm.$emit('user-added', 'toast@example.com')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[role="status"]').exists()).toBe(true)

      vi.advanceTimersByTime(3000)
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[role="status"]').exists()).toBe(false)
      wrapper.unmount()
    })
  })

  it('handleUserAdded closes modal and calls fetchAll again', async () => {
    vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([])
    const wrapper = mount(AdminView, { global: globalOptions })
    await flushPromises()

    // onMounted triggers the first fetchAll
    expect(adminApiModule.adminApi.listUsers).toHaveBeenCalledTimes(1)

    await wrapper.find('.btn-add-user').trigger('click')
    expect(wrapper.findComponent(AddUserFormStub).exists()).toBe(true)

    await wrapper.findComponent(AddUserFormStub).vm.$emit('user-added', 'created@example.com')
    await wrapper.vm.$nextTick()
    await flushPromises()

    // modal is closed
    expect(wrapper.findComponent(AddUserFormStub).exists()).toBe(false)
    // fetchAll called a second time to refresh the user list
    expect(adminApiModule.adminApi.listUsers).toHaveBeenCalledTimes(2)
  })

  describe('role toggle', () => {
    const regularUser = {
      id: 2,
      email: 'user@example.com',
      username: 'user',
      is_admin: false,
      created_at: '2024-01-01T00:00:00Z',
      url_count: 0,
    }
    const adminUser = {
      id: 3,
      email: 'other@example.com',
      username: 'other',
      is_admin: true,
      created_at: '2024-01-01T00:00:00Z',
      url_count: 0,
    }

    it('shows Promote button for regular user', async () => {
      vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([regularUser])
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()
      expect(wrapper.find('.btn-toggle-role').text()).toBe('Promote')
    })

    it('shows Demote button for admin user', async () => {
      vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([adminUser])
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()
      expect(wrapper.find('.btn-toggle-role').text()).toBe('Demote')
    })

    it('calls updateUser and updates badge on Promote click', async () => {
      vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([regularUser])
      vi.mocked(adminApiModule.adminApi.updateUser).mockResolvedValue({ ...regularUser, is_admin: true })
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()
      await wrapper.find('.btn-toggle-role').trigger('click')
      await flushPromises()
      expect(adminApiModule.adminApi.updateUser).toHaveBeenCalledWith(2, true)
      expect(wrapper.find('.badge-admin').exists()).toBe(true)
    })

    it('calls updateUser and updates badge on Demote click', async () => {
      vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([adminUser])
      vi.mocked(adminApiModule.adminApi.updateUser).mockResolvedValue({ ...adminUser, is_admin: false })
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()
      await wrapper.find('.btn-toggle-role').trigger('click')
      await flushPromises()
      expect(adminApiModule.adminApi.updateUser).toHaveBeenCalledWith(3, false)
      expect(wrapper.find('.badge-user').exists()).toBe(true)
    })

    it('shows role error on updateUser failure', async () => {
      vi.mocked(adminApiModule.adminApi.listUsers).mockResolvedValue([regularUser])
      vi.mocked(adminApiModule.adminApi.updateUser).mockRejectedValue(new Error('fail'))
      const wrapper = mount(AdminView, { global: globalOptions })
      await flushPromises()
      await wrapper.find('.btn-toggle-role').trigger('click')
      await flushPromises()
      expect(wrapper.find('[role="alert"]').text()).toContain('Failed to update role')
    })
  })
})
