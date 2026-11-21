import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import ReviewView from '@/views/ReviewView.vue'
import ReviewViewSource from '@/views/ReviewView.vue?raw'
import { getDocument, getStructure, submitReview } from '@/services/api'

vi.mock('@/services/api', () => ({
  getDocument: vi.fn(),
  getStructure: vi.fn(),
  submitReview: vi.fn()
}))

const baseDocument = {
  document_id: 1,
  original_name: 'documento_ejemplo.docx',
  status: 'review',
  config: { use_ai: true }
}

function makeStructure(overrides = {}) {
  return {
    document_id: 1,
    job_id: 1,
    status: 'review',
    original: {
      schema_version: 'di.v1',
      blocks: [
        { id: 'b1', type: 'paragraph', text: 'RESUMEN', runs: [{ text: 'RESUMEN' }] },
        { id: 'b2', type: 'paragraph', text: 'Primer punto', runs: [{ text: 'Primer punto' }] },
        { id: 'b3', type: 'paragraph', text: 'Segundo punto', runs: [{ text: 'Segundo punto' }] },
        { id: 'b4', type: 'paragraph', text: 'Paso 1', runs: [{ text: 'Paso 1' }] },
        { id: 'b5', type: 'paragraph', text: 'Paso 2', runs: [{ text: 'Paso 2' }] },
        {
          id: 'b6',
          type: 'table',
          rows: [
            [{ text: 'A' }, { text: 'B' }],
            [{ text: '1' }, { text: '2' }]
          ]
        },
        { id: 'b7', type: 'paragraph', text: 'Nota original', runs: [{ text: 'Nota original' }] },
        { id: 'b8', type: 'keep', keep_kind: 'image' }
      ]
    },
    proposed: {
      schema_version: 'di.v1',
      blocks: [
        { id: 'p1', type: 'heading', level: 1, src: ['b1'], runs: [{ text: 'RESUMEN' }] },
        { id: 'p2', type: 'heading', level: 2, src: ['b1'], runs: [{ text: 'Detalle' }] },
        { id: 'p3', type: 'heading', level: 4, src: ['b1'], runs: [{ text: 'Subdetalle' }] },
        { id: 'p4', type: 'list_item', ordered: false, src: ['b2'], runs: [{ text: 'Primer punto' }] },
        { id: 'p5', type: 'list_item', ordered: false, src: ['b3'], runs: [{ text: 'Segundo punto' }] },
        { id: 'p6', type: 'list_item', ordered: true, src: ['b4'], runs: [{ text: 'Paso 1' }] },
        { id: 'p7', type: 'list_item', ordered: true, src: ['b5'], runs: [{ text: 'Paso 2' }] },
        {
          id: 'p8',
          type: 'table',
          header_row: true,
          src: ['b6'],
          rows: [
            [{ text: 'A' }, { text: 'B' }],
            [{ text: '1' }, { text: '2' }]
          ]
        },
        {
          id: 'p9',
          type: 'callout',
          kind: 'note',
          src: ['b7'],
          runs: [
            { text: 'Nota:', bold: true },
            { text: ' original' }
          ]
        },
        { id: 'p10', type: 'keep', src: ['b8'] }
      ]
    },
    summary: {
      headings_detected: 3,
      lists_detected: 4,
      tables_detected: 1,
      bold_emphasis_applied: 1,
      revertible_blocks: ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7'],
      chunks_total: 4,
      chunks_fallback: 1,
      fallback_only: false
    },
    ...overrides
  }
}

function makeLargeStructure(count = 100) {
  const original = []
  const proposed = []
  const revertible = []

  for (let index = 1; index <= count; index += 1) {
    const src = `b${index}`
    const text = `Texto del bloque ${index}`
    original.push({ id: src, type: 'paragraph', text, runs: [{ text }] })
    proposed.push({ id: `p${index}`, type: 'paragraph', src: [src], runs: [{ text }] })
    revertible.push(src)
  }

  return makeStructure({
    original: { schema_version: 'di.v1', blocks: original },
    proposed: { schema_version: 'di.v1', blocks: proposed },
    summary: {
      headings_detected: 0,
      lists_detected: 0,
      tables_detected: 0,
      bold_emphasis_applied: 0,
      revertible_blocks: revertible,
      chunks_total: 10,
      chunks_fallback: 2,
      fallback_only: false
    }
  })
}

const Dummy = { render: () => null }

async function mountReview(structure) {
  getStructure.mockResolvedValue(structure)
  getDocument.mockResolvedValue(baseDocument)

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Dummy },
      { path: '/config', name: 'config', component: Dummy },
      { path: '/processing/:id', name: 'processing', component: Dummy },
      { path: '/review/:id', name: 'review', component: ReviewView },
      { path: '/result', name: 'result', component: Dummy }
    ]
  })

  router.push('/review/1')
  await router.isReady()

  const wrapper = mount(ReviewView, {
    global: { plugins: [createPinia(), router] }
  })
  await flushPromises()

  return { wrapper, router }
}

describe('ReviewView', () => {
  beforeEach(() => {
    getDocument.mockReset()
    getStructure.mockReset()
    submitReview.mockReset()
    submitReview.mockResolvedValue({
      document_id: 1,
      job_id: 1,
      status: 'done',
      action: 'accept',
      download_url: '/api/documents/1/download/'
    })
  })

  it('consumes GET /documents/1/structure/ on mount and renders semantic blocks safely', async () => {
    const { wrapper } = await mountReview(makeStructure())

    expect(getStructure).toHaveBeenCalledWith(1)
    expect(wrapper.find('#review-summary').exists()).toBe(true)
    expect(wrapper.find('[data-stat="headings"]').text()).toBe('3')
    expect(wrapper.find('[data-stat="lists"]').text()).toBe('4')
    expect(wrapper.find('[data-stat="tables"]').text()).toBe('1')
    expect(wrapper.find('[data-stat="bold"]').text()).toBe('1')
    expect(wrapper.find('[data-stat="fallback"]').text()).toBe('1')

    const proposed = wrapper.find('[data-column="proposed"]')
    expect(proposed.find('h1').exists()).toBe(true)
    expect(proposed.find('h2').exists()).toBe(true)
    expect(proposed.find('h3').exists()).toBe(true)
    expect(proposed.find('ul.preview-list').exists()).toBe(true)
    expect(proposed.find('ol.preview-list').exists()).toBe(true)
    expect(proposed.find('table').exists()).toBe(true)
    expect(proposed.find('blockquote').exists()).toBe(true)
    expect(proposed.find('strong').exists()).toBe(true)

    // Two independent columns on desktop, stacked on small screens.
    expect(wrapper.findAll('.review-compare > .col-12.col-lg-6')).toHaveLength(2)
    expect(wrapper.find('[data-column="original"] .original-kind').exists()).toBe(true)
    expect(ReviewViewSource).toMatch(/@media \(max-width: 991\.98px\)/)
  })

  it('renders run text as interpolation only (no v-html / HTML injection)', async () => {
    const payload = makeStructure()
    const malicious = '<img src=x onerror="window.__xss=1">'
    payload.proposed.blocks[0].runs[0].text = malicious

    const { wrapper } = await mountReview(payload)

    expect(wrapper.find('[data-column="proposed"] img').exists()).toBe(false)
    expect(wrapper.text()).toContain(malicious)
    expect(wrapper.element.innerHTML).not.toContain('<img src=x')
    expect(ReviewViewSource).not.toMatch(/v-html/)
  })

  it('renders a 100-block document from the mock structure', async () => {
    const { wrapper } = await mountReview(makeLargeStructure(100))

    expect(wrapper.findAll('.original-block')).toHaveLength(100)
    expect(wrapper.findAll('[data-column="proposed"] [data-block-id]')).toHaveLength(100)
    expect(wrapper.find('[data-column="proposed"]').exists()).toBe(true)
  })

  it('reverts a block visually and sends its source id in the accept payload', async () => {
    const { wrapper } = await mountReview(makeStructure())

    await wrapper.find('[data-revert-for="p1"]').trigger('click')

    const reverted = wrapper.find('[data-block-id="p1"]')
    expect(reverted.classes()).toContain('doc-block--reverted')
    expect(reverted.text()).toContain('RESUMEN')

    await wrapper.find('#btn-accept-review').trigger('click')
    await flushPromises()

    expect(submitReview).toHaveBeenCalledWith(1, { action: 'accept', revert: ['b1'] })
  })

  it('can re-apply the AI to a reverted block before accepting', async () => {
    const { wrapper } = await mountReview(makeStructure())

    await wrapper.find('[data-revert-for="p1"]').trigger('click')
    expect(wrapper.find('[data-block-id="p1"]').classes()).toContain('doc-block--reverted')

    await wrapper.find('[data-revert-for="p1"]').trigger('click')
    expect(wrapper.find('[data-block-id="p1"]').classes()).not.toContain('doc-block--reverted')

    await wrapper.find('#btn-accept-review').trigger('click')
    await flushPromises()

    expect(submitReview).toHaveBeenCalledWith(1, { action: 'accept', revert: [] })
  })

  it('sends the exact reject payload and allows rejecting an empty proposal', async () => {
    const { wrapper } = await mountReview(makeStructure())

    await wrapper.find('#btn-reject-review').trigger('click')
    await flushPromises()

    expect(submitReview).toHaveBeenCalledWith(1, { action: 'reject' })

    const empty = await mountReview(
      makeStructure({
        proposed: { schema_version: 'di.v1', blocks: [] },
        summary: {
          headings_detected: 0,
          lists_detected: 0,
          tables_detected: 0,
          bold_emphasis_applied: 0,
          revertible_blocks: [],
          chunks_total: 0,
          chunks_fallback: 0,
          fallback_only: false
        }
      })
    )

    expect(empty.wrapper.find('#btn-accept-review').attributes('disabled')).toBeDefined()
    expect(empty.wrapper.find('#btn-reject-review').attributes('disabled')).toBeUndefined()

    await empty.wrapper.find('#btn-reject-review').trigger('click')
    await flushPromises()
    expect(submitReview).toHaveBeenLastCalledWith(1, { action: 'reject' })
  })
})
