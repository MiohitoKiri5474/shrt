import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NotFoundView from '../NotFoundView.vue'

describe('NotFoundView', () => {
  it('renders a not-found heading', () => {
    const wrapper = mount(NotFoundView)
    expect(wrapper.find('h1').text()).toBe('Page not found')
  })

  it('has a link back to Manage', () => {
    const wrapper = mount(NotFoundView)
    const link = wrapper.find('.btn-home')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('/manage')
  })
})
