import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import KpiCard from '../KpiCard.vue'

describe('KpiCard', () => {
  it('renders label and value', () => {
    const wrapper = mount(KpiCard, {
      props: { label: '今日仿真', value: 42, unit: '次', delta: 5.6, trend: 'up' },
    })
    expect(wrapper.text()).toContain('今日仿真')
    expect(wrapper.text()).toContain('42')
    expect(wrapper.text()).toContain('次')
  })

  it('shows delta tag when delta is provided', () => {
    const wrapper = mount(KpiCard, {
      props: { label: 'GMV', value: 100, delta: -3.4, trend: 'down' },
    })
    expect(wrapper.text()).toMatch(/3\.4%/)
  })

  it('omits delta tag when undefined', () => {
    const wrapper = mount(KpiCard, { props: { label: 'X', value: 1 } })
    expect(wrapper.text()).not.toMatch(/%/)
  })
})
