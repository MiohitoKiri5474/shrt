import { describe, it, expect, vi, beforeEach } from 'vitest'
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
    deleteUser: vi.fn(),
  },
}))

// Stub AddUserForm so it doesn't attach document listeners during AdminView tests
const AddUserFormStub = defineComponent({
  name: 'AddUserForm',
  emits: ['close', 'user-added'],
  template: '<div class="add-user-form-stub" />',
})

const globalOptions = {
  stubs: {
    RouterLink: true,
    AddUserForm: AddUserFormStub,
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
})
