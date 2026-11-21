import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import ResultView from '@/views/ResultView.vue'
import { useFlowStore } from '@/stores/flowStore'

const apiMocks = vi.hoisted(() => ({
  formatDocument: vi.fn(),
  downloadUrl: vi.fn((id) => `/api/documents/${id}/download/`),
  getDocument: vi.fn(),
  getPresets: vi.fn()
}))

vi.mock('@/services/api', () => apiMocks)

const baseConfig = {
  preset_id: 'reporte',
  use_ai: true,
  margins_cm: { top: 2.54, bottom: 2.54, left: 2.54, right: 2.54 },
  font_family: 'Calibri',
  font_size_pt: 11,
  line_spacing: 1.15
}

const aiSummary = {
  headings_detected: 4,
  lists_detected: 2,
  tables_detected: 1,
  bold_emphasis_applied: 8,
  chunks_total: 5,
  chunks_fallback: 0,
  fallback_only: false,
  reverted_blocks_count: 2
}

async function renderResultView({
  config = baseConfig,
  result = {},
  documentData = {}
} = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)

  const store = useFlowStore()
  store.setDocument({ document_id: 12, original_name: 'informe.docx' })
  store.setConfig(config)
  store.setResult({ document_id: 12, status: 'done', ...result })

  apiMocks.formatDocument.mockResolvedValue({ document_id: 12, status: 'done' })
  apiMocks.getDocument.mockResolvedValue({
    document_id: 12,
    status: 'done',
    use_ai: config.use_ai,
    config,
    ...documentData
  })
  apiMocks.getPresets.mockResolvedValue([
    { id: 'apa7', name: 'Formato académico (APA 7)' },
    { id: 'reporte', name: 'Reporte ejecutivo' }
  ])

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/config', component: { template: '<div />' } },
      { path: '/result', component: ResultView }
    ]
  })
  await router.push('/result')
  await router.isReady()

  const wrapper = mount(ResultView, {
    global: { plugins: [pinia, router] }
  })

  await flushPromises()
  await flushPromises()

  return { wrapper, store }
}

describe('ResultView — resumen de estructuración', () => {
  it('muestra reestructurados, revertidos y la plantilla usando ai_summary del backend', async () => {
    const { wrapper } = await renderResultView({
      documentData: { ai_summary: aiSummary }
    })

    expect(wrapper.find('[data-stat="restructured-blocks"]').text()).toBe('7')
    expect(wrapper.find('[data-stat="reverted-blocks"]').text()).toBe('2')
    expect(wrapper.find('[data-stat="template-name"]').text()).toBe('Reporte ejecutivo')
    expect(wrapper.text()).toContain('Títulos:')
    expect(wrapper.find('#btn-download').attributes('href')).toBe('/api/documents/12/download/')
  })

  it('oculta el bloque de IA cuando use_ai es false y mantiene la descarga', async () => {
    const noAiConfig = { ...baseConfig, use_ai: false }
    const { wrapper } = await renderResultView({
      config: noAiConfig,
      result: { config: noAiConfig },
      documentData: { ai_summary: null }
    })

    expect(wrapper.find('[data-stat="restructured-blocks"]').exists()).toBe(false)
    expect(wrapper.find('[data-stat="reverted-blocks"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('No utilizada')
    expect(wrapper.find('[data-stat="template-name"]').text()).toBe('Reporte ejecutivo')
    expect(wrapper.find('#btn-download').attributes('href')).toBe('/api/documents/12/download/')
  })

  it('toma los revertidos de summary cuando ai_summary no incluye el contador', async () => {
    const { reverted_blocks_count: _reverted, ...summaryWithoutReverted } = aiSummary
    const { wrapper } = await renderResultView({
      result: { summary: { reverted_blocks_count: 3 } },
      documentData: { ai_summary: summaryWithoutReverted }
    })

    expect(wrapper.find('[data-stat="reverted-blocks"]').text()).toBe('3')
    expect(wrapper.find('[data-stat="restructured-blocks"]').text()).toBe('7')
  })

  it('no rompe la vista si falla la consulta del resumen', async () => {
    apiMocks.getDocument.mockRejectedValue(new Error('network down'))
    apiMocks.getPresets.mockRejectedValue(new Error('network down'))

    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useFlowStore()
    store.setDocument({ document_id: 12, original_name: 'informe.docx' })
    store.setConfig(baseConfig)
    store.setResult({ document_id: 12, status: 'done' })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/result', component: ResultView }]
    })
    await router.push('/result')
    await router.isReady()

    const wrapper = mount(ResultView, {
      global: { plugins: [pinia, router] }
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('#btn-download').exists()).toBe(true)
    expect(wrapper.find('#btn-download').attributes('href')).toBe('/api/documents/12/download/')
    expect(wrapper.find('[data-stat="template-name"]').text()).toBe('Reporte')
  })
})
