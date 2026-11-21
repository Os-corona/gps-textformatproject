import axios from 'axios'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/+$/, '')
const USE_MOCKS = String(import.meta.env.VITE_USE_MOCKS).toLowerCase() === 'true'

// Do not set a default 'Content-Type' here. Axios picks the right one per
// request: 'application/json' for plain objects and 'multipart/form-data'
// (with its boundary) for FormData. Forcing JSON globally made axios
// serialize the upload FormData as `{ "file": {} }`, so Django never
// received an UploadedFile.
export const apiClient = axios.create({
  baseURL: API_URL
})

/** Convert any backend message (string, array or validation object) to text. */
export function messageToString(value) {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map(messageToString).filter(Boolean).join(' ')
  }
  if (value && typeof value === 'object') {
    if (typeof value.message === 'string') return value.message
    if (typeof value.msg === 'string') return value.msg
    return Object.values(value).map(messageToString).filter(Boolean).join(' ')
  }
  return ''
}

/**
 * Normalize every error shape used by the backend into { code, message, details }:
 *  - Nested (API contract): { error: { code, message, details } }
 *  - Flat (current API): { error: "CODE", message: "...", details? }
 *  - Django REST Framework fallback: { detail: "..." }
 *
 * Keeping a single shape means views can always render `error.code` and
 * `error.message` without knowing which endpoint produced the failure.
 */
export function normalizeError(error) {
  const responseData = error?.response?.data
  const apiError = responseData?.error

  let code = 'ERR_UNKNOWN'
  let message = ''
  let details = {}

  if (apiError && typeof apiError === 'object') {
    // Nested: { error: { code, message, details } }
    code = apiError.code || code
    message = messageToString(apiError.message)
    details = apiError.details ?? {}
  } else if (typeof apiError === 'string') {
    // Flat: { error: "CODE", message: "..." }
    code = apiError
    message = messageToString(responseData?.message)
    details = responseData?.details ?? {}
  }

  // Fallbacks for partial bodies, plain DRF errors and network failures.
  if (!message) message = messageToString(responseData?.message ?? responseData?.detail)
  if (!message) message = error?.message || 'Ocurrió un error inesperado'
  if (code === 'ERR_UNKNOWN' && typeof responseData?.code === 'string') code = responseData.code
  if (code === 'ERR_UNKNOWN' && typeof error?.code === 'string') code = error.code

  return { code, message, details }
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeError(error))
)

// Mock error scenarios:
// Set VITE_MOCK_UPLOAD_ERROR=bad_extension | file_too_large | bad_signature | cannot_open
// in .env.local to simulate each failure case.
const MOCK_UPLOAD_ERROR = import.meta.env.VITE_MOCK_UPLOAD_ERROR

const MOCK_UPLOAD_ERRORS = {
  bad_extension: {
    code: 'INVALID_FILE',
    message: 'Solo se permiten archivos .docx.',
    details: { reason: 'bad_extension' }
  },
  file_too_large: {
    code: 'FILE_TOO_LARGE',
    message: 'El archivo supera el límite de 10 MB.',
    details: { reason: 'file_too_large' }
  },
  bad_signature: {
    code: 'INVALID_FILE',
    message: 'El archivo no es un documento de Word válido.',
    details: { reason: 'bad_signature' }
  },
  cannot_open: {
    code: 'INVALID_FILE',
    message: 'No se pudo abrir el documento. Puede estar dañado o protegido con contraseña.',
    details: { reason: 'cannot_open' }
  }
}

export async function uploadDocument(file) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 600))

    // Simulate a specific error when VITE_MOCK_UPLOAD_ERROR is set
    if (MOCK_UPLOAD_ERROR && MOCK_UPLOAD_ERRORS[MOCK_UPLOAD_ERROR]) {
      return Promise.reject(MOCK_UPLOAD_ERRORS[MOCK_UPLOAD_ERROR])
    }

    return {
      document_id: 1,
      job_id: 1,
      status: 'pending',
      original_name: file ? file.name : 'documento.docx',
      size_bytes: file ? file.size : 102400,
      uploaded_at: new Date().toISOString()
    }
  }

  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }
  // No manual Content-Type: axios sets multipart/form-data and the browser
  // adds the boundary. Setting it by hand (or as JSON) breaks the upload.
  const response = await apiClient.post('/documents/', formData)
  return response.data
}

export async function formatDocument(id, config) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 400))
    if (config?.use_ai) {
      return {
        httpStatus: 202,
        status: 202,
        job_status: 'processing',
        document_id: id,
        job_id: id,
        config: {
          ...config
        },
        message: 'Job encolado para procesamiento con IA.'
      }
    }
    return {
      httpStatus: 200,
      document_id: id,
      job_id: id,
      status: 'done',
      config: {
        ...config,
        use_ai: false
      },
      finished_at: new Date().toISOString()
    }
  }

  const response = await apiClient.post(`/documents/${id}/format/`, config)

  // The current backend only returns { status }, while the contract may also
  // include document_id/config. Fill in the missing values so the result view
  // always has everything it needs.
  return {
    ...response.data,
    httpStatus: response.status,
    status: response.status === 202 ? 202 : (response.data?.status ?? response.status),
    document_id: response.data?.document_id ?? id,
    config: response.data?.config ?? config
  }
}

const mockPollCounts = {}

export async function getDocument(id) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 200))
    const mockStatusEnv = import.meta.env.VITE_MOCK_JOB_STATUS
    mockPollCounts[id] = (mockPollCounts[id] || 0) + 1
    const count = mockPollCounts[id]

    let status = 'processing'
    let current_chunk = Math.min(count, 4)
    let total_chunks = 4
    let stage = 'Estructurando jerarquía de títulos y párrafos'

    if (count >= 3) {
      if (mockStatusEnv === 'review') {
        status = 'review'
      } else if (mockStatusEnv === 'error') {
        status = 'error'
      } else {
        status = 'done'
      }
    }

    const hasAiSummary = status === 'review' || status === 'done'

    return {
      document_id: id,
      job_id: id,
      original_name: 'documento_ejemplo.docx',
      size_bytes: 102400,
      uploaded_at: new Date().toISOString(),
      status,
      current_chunk,
      total_chunks,
      stage,
      progress: {
        stage: status === 'done' ? 'building' : 'structuring',
        done: status === 'processing' ? Math.min(count, total_chunks) : total_chunks,
        total: total_chunks
      },
      ai_summary: hasAiSummary
        ? {
            headings_detected: 3,
            lists_detected: 2,
            tables_detected: 1,
            bold_emphasis_applied: 8,
            chunks_total: total_chunks,
            chunks_fallback: 1,
            fallback_only: false
          }
        : null,
      error_code: status === 'error' ? (import.meta.env.VITE_MOCK_ERROR_CODE || 'AI_PROVIDER_ERROR') : null,
      error_message: status === 'error' ? 'El proveedor de IA no pudo procesar el documento.' : null,
      config: {},
      use_ai: true,
      started_at: new Date().toISOString(),
      finished_at: status === 'done' ? new Date().toISOString() : null,
      download_url: status === 'done' ? `/api/documents/${id}/download/` : null
    }
  }

  const response = await apiClient.get(`/documents/${id}/`)
  return response.data
}

// ─── Review screen mocks (Sprint 3) ──────────────────────────────────────────

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function buildMockStructureError(id) {
  const scenario = String(import.meta.env.VITE_MOCK_STRUCTURE_ERROR || '').toLowerCase()

  if (!scenario) return null

  if (scenario === 'invalid_state') {
    return {
      code: 'INVALID_STATE',
      message: 'El documento no se encuentra en estado de revisión.',
      details: { current_status: 'processing', required_status: 'review' }
    }
  }

  if (scenario === 'not_found') {
    return {
      code: 'NOT_FOUND',
      message: 'El documento solicitado no existe.',
      details: { document_id: id }
    }
  }

  return {
    code: 'PROCESSING_ERROR',
    message: 'No se pudo cargar la estructura propuesta por la IA.',
    details: {}
  }
}

function buildDefaultMockStructure(id) {
  return {
    document_id: id,
    job_id: id,
    status: 'review',
    original: {
      schema_version: 'di.v1',
      doc_context: { document_type: 'reporte', body_font_size: 11.0 },
      blocks: [
        {
          id: 'b1',
          type: 'paragraph',
          text: '1. RESUMEN EJECUTIVO',
          runs: [{ text: '1. RESUMEN EJECUTIVO', bold: true }],
          hints: {
            all_bold: true,
            is_all_caps: true,
            size_ratio: 1.45,
            words: 3,
            ends_with_period: false,
            alignment: 'left'
          }
        },
        {
          id: 'b2',
          type: 'paragraph',
          text: 'El plan estratégico contempla las siguientes metas prioritarias para el trimestre:',
          runs: [
            {
              text: 'El plan estratégico contempla las siguientes metas prioritarias para el trimestre:'
            }
          ],
          hints: { ends_with_period: false }
        },
        {
          id: 'b3',
          type: 'paragraph',
          text: '• Optimización de costos: reducción del 12% en compras directas.',
          runs: [{ text: '• Optimización de costos: reducción del 12% en compras directas.' }],
          hints: { starts_with_glyph: true, indent_level: 0, has_key_value_pattern: true }
        },
        {
          id: 'b4',
          type: 'paragraph',
          text: '• Tiempo de entrega: promedio inferior a 48 horas.',
          runs: [{ text: '• Tiempo de entrega: promedio inferior a 48 horas.' }],
          hints: { starts_with_glyph: true, indent_level: 0, has_key_value_pattern: true }
        },
        {
          id: 'b5',
          type: 'paragraph',
          text: '1. Ampliar la cobertura regional.',
          runs: [{ text: '1. Ampliar la cobertura regional.' }],
          hints: { manual_numbering: true, indent_level: 0 }
        },
        {
          id: 'b6',
          type: 'paragraph',
          text: '2. Reducir el consumo energético en un 8%.',
          runs: [{ text: '2. Reducir el consumo energético en un 8%.' }],
          hints: { manual_numbering: true, indent_level: 0 }
        },
        {
          id: 'b7',
          type: 'paragraph',
          text: 'Sección de métricas operativas:',
          runs: [{ text: 'Sección de métricas operativas:' }],
          hints: { ends_with_period: false }
        },
        {
          id: 'b8',
          type: 'table',
          rows: [
            [{ text: 'Indicador' }, { text: 'Meta' }],
            [{ text: 'Ventas' }, { text: '+15%' }],
            [{ text: 'Margen' }, { text: '+3 pp' }]
          ],
          hints: { has_key_value_pattern: true }
        },
        {
          id: 'b9',
          type: 'paragraph',
          text: 'Nota: las cifras son preliminares y pueden variar.',
          runs: [{ text: 'Nota: las cifras son preliminares y pueden variar.' }],
          hints: { ends_with_period: true }
        },
        {
          id: 'b10',
          type: 'keep',
          keep_kind: 'image'
        },
        {
          id: 'b11',
          type: 'keep',
          keep_kind: 'table',
          rows: [
            [{ text: 'Concepto' }, { text: 'Monto' }],
            [{ text: 'Ingresos' }, { text: '1.2 M' }]
          ]
        },
        {
          id: 'b12',
          type: 'paragraph',
          text: 'Conclusión: el proyecto es viable con los ajustes propuestos.',
          runs: [{ text: 'Conclusión: el proyecto es viable con los ajustes propuestos.' }],
          hints: { ends_with_period: true }
        }
      ]
    },
    proposed: {
      schema_version: 'di.v1',
      blocks: [
        {
          id: 'p1',
          type: 'heading',
          level: 1,
          src: ['b1'],
          runs: [{ text: '1. RESUMEN EJECUTIVO' }]
        },
        {
          id: 'p2',
          type: 'paragraph',
          src: ['b2'],
          runs: [
            {
              text: 'El plan estratégico contempla las siguientes metas prioritarias para el trimestre:'
            }
          ]
        },
        {
          id: 'p3',
          type: 'list_item',
          ordered: false,
          level: 0,
          src: ['b3'],
          runs: [
            { text: 'Optimización de costos:', bold: true },
            { text: ' reducción del 12% en compras directas.' }
          ]
        },
        {
          id: 'p4',
          type: 'list_item',
          ordered: false,
          level: 0,
          src: ['b4'],
          runs: [
            { text: 'Tiempo de entrega:', bold: true },
            { text: ' promedio inferior a 48 horas.' }
          ]
        },
        {
          id: 'p5',
          type: 'list_item',
          ordered: true,
          level: 0,
          src: ['b5'],
          runs: [{ text: 'Ampliar la cobertura regional.' }]
        },
        {
          id: 'p6',
          type: 'list_item',
          ordered: true,
          level: 0,
          src: ['b6'],
          runs: [{ text: 'Reducir el consumo energético en un 8%.' }]
        },
        {
          id: 'p7',
          type: 'paragraph',
          src: ['b7'],
          runs: [{ text: 'Sección de métricas operativas:' }]
        },
        {
          id: 'p8',
          type: 'table',
          header_row: true,
          src: ['b8'],
          rows: [
            [{ text: 'Indicador' }, { text: 'Meta' }],
            [{ text: 'Ventas' }, { text: '+15%' }],
            [{ text: 'Margen' }, { text: '+3 pp' }]
          ]
        },
        {
          id: 'p9',
          type: 'callout',
          kind: 'note',
          src: ['b9'],
          runs: [
            { text: 'Nota:', bold: true },
            { text: ' las cifras son preliminares y pueden variar.' }
          ]
        },
        {
          id: 'p10',
          type: 'keep',
          src: ['b10']
        },
        {
          id: 'p11',
          type: 'keep',
          src: ['b11']
        },
        {
          id: 'p12',
          type: 'paragraph',
          src: ['b12'],
          runs: [
            { text: 'Conclusión:', bold: true },
            { text: ' el proyecto es viable con los ajustes propuestos.' }
          ]
        }
      ]
    },
    summary: {
      headings_detected: 1,
      lists_detected: 4,
      tables_detected: 1,
      bold_emphasis_applied: 4,
      revertible_blocks: ['b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'b12'],
      chunks_total: 4,
      chunks_fallback: 1,
      fallback_only: false
    }
  }
}

function buildLargeMockStructure(id, count) {
  const originalBlocks = []
  const proposedBlocks = []
  const revertible = []
  let headings = 0
  let lists = 0
  let tables = 0
  let bold = 0

  for (let index = 0; index < count; index += 1) {
    const number = index + 1
    const src = `b${number}`
    const proposedId = `p${number}`
    const baseText = `Bloque ${number} del documento de prueba con contenido suficiente para validar el ajuste de líneas.`
    const variant = index % 10

    if (variant === 0) {
      headings += 1
      originalBlocks.push({
        id: src,
        type: 'paragraph',
        text: `SECCIÓN ${number}`,
        runs: [{ text: `SECCIÓN ${number}`, bold: true }],
        hints: { all_bold: true, is_all_caps: true, words: 2 }
      })
      proposedBlocks.push({
        id: proposedId,
        type: 'heading',
        level: (index % 3) + 1,
        src: [src],
        runs: [{ text: `SECCIÓN ${number}` }]
      })
      revertible.push(src)
      continue
    }

    if (variant === 2 || variant === 3) {
      lists += 1
      bold += 1
      originalBlocks.push({
        id: src,
        type: 'paragraph',
        text: `• ${baseText}`,
        runs: [{ text: `• ${baseText}` }],
        hints: { starts_with_glyph: true, indent_level: 0 }
      })
      proposedBlocks.push({
        id: proposedId,
        type: 'list_item',
        ordered: false,
        level: 0,
        src: [src],
        runs: [
          { text: 'Punto clave:', bold: true },
          { text: ` ${baseText}` }
        ]
      })
      revertible.push(src)
      continue
    }

    if (variant === 4) {
      lists += 1
      originalBlocks.push({
        id: src,
        type: 'paragraph',
        text: `1. ${baseText}`,
        runs: [{ text: `1. ${baseText}` }],
        hints: { manual_numbering: true, indent_level: 0 }
      })
      proposedBlocks.push({
        id: proposedId,
        type: 'list_item',
        ordered: true,
        level: 0,
        src: [src],
        runs: [{ text: baseText }]
      })
      revertible.push(src)
      continue
    }

    if (variant === 5) {
      tables += 1
      const rows = [
        [{ text: 'Indicador' }, { text: 'Valor' }],
        [{ text: `Métrica ${number}` }, { text: `${number}%` }]
      ]
      originalBlocks.push({ id: src, type: 'table', rows })
      proposedBlocks.push({
        id: proposedId,
        type: 'table',
        header_row: true,
        src: [src],
        rows
      })
      revertible.push(src)
      continue
    }

    if (variant === 6) {
      bold += 1
      originalBlocks.push({
        id: src,
        type: 'paragraph',
        text: `Nota ${number}: ${baseText}`,
        runs: [{ text: `Nota ${number}: ${baseText}` }]
      })
      proposedBlocks.push({
        id: proposedId,
        type: 'callout',
        kind: index % 2 === 0 ? 'note' : 'quote',
        src: [src],
        runs: [
          { text: `Nota ${number}:`, bold: true },
          { text: ` ${baseText}` }
        ]
      })
      revertible.push(src)
      continue
    }

    if (variant === 7) {
      bold += 1
      originalBlocks.push({
        id: src,
        type: 'paragraph',
        text: `Conclusión ${number}: ${baseText}`,
        runs: [{ text: `Conclusión ${number}: ${baseText}` }]
      })
      proposedBlocks.push({
        id: proposedId,
        type: 'paragraph',
        src: [src],
        runs: [
          { text: `Conclusión ${number}:`, bold: true },
          { text: ` ${baseText}` }
        ]
      })
      revertible.push(src)
      continue
    }

    if (variant === 8) {
      originalBlocks.push({ id: src, type: 'keep', keep_kind: 'image' })
      proposedBlocks.push({ id: proposedId, type: 'keep', src: [src] })
      continue
    }

    originalBlocks.push({
      id: src,
      type: 'paragraph',
      text: baseText,
      runs: [{ text: baseText }]
    })
    proposedBlocks.push({
      id: proposedId,
      type: 'paragraph',
      src: [src],
      runs: [{ text: baseText }]
    })
    revertible.push(src)
  }

  const chunksTotal = Math.max(1, Math.ceil(count / 10))

  return {
    document_id: id,
    job_id: id,
    status: 'review',
    original: {
      schema_version: 'di.v1',
      doc_context: { document_type: 'reporte', body_font_size: 11.0 },
      blocks: originalBlocks
    },
    proposed: {
      schema_version: 'di.v1',
      blocks: proposedBlocks
    },
    summary: {
      headings_detected: headings,
      lists_detected: lists,
      tables_detected: tables,
      bold_emphasis_applied: bold,
      revertible_blocks: revertible,
      chunks_total: chunksTotal,
      chunks_fallback: Math.min(5, Math.max(1, Math.floor(count / 20))),
      fallback_only: false
    }
  }
}

function buildMockStructure(id) {
  const requested = Number(import.meta.env.VITE_MOCK_REVIEW_BLOCKS)
  const large = String(import.meta.env.VITE_MOCK_REVIEW_LARGE).toLowerCase() === 'true'

  if (Number.isFinite(requested) && requested > 0) {
    return buildLargeMockStructure(id, Math.min(Math.floor(requested), 500))
  }

  if (large) {
    return buildLargeMockStructure(id, 100)
  }

  return buildDefaultMockStructure(id)
}

/**
 * GET /api/documents/{id}/structure/
 * Returns the original and proposed DI for the review screen.
 */
export async function getStructure(id) {
  if (USE_MOCKS) {
    await delay(250)
    const mockError = buildMockStructureError(id)
    if (mockError) throw mockError
    return buildMockStructure(id)
  }

  const response = await apiClient.get(`/documents/${id}/structure/`)
  return response.data
}

function buildMockReviewError(id) {
  const scenario = String(import.meta.env.VITE_MOCK_REVIEW_ERROR || '').toLowerCase()

  if (!scenario) return null

  if (scenario === 'invalid_state') {
    return {
      code: 'INVALID_STATE',
      message: 'El documento no se encuentra en estado de revisión.',
      details: { current_status: 'processing', required_status: 'review' }
    }
  }

  if (scenario === 'invalid_config') {
    return {
      code: 'INVALID_CONFIG',
      message: 'La solicitud de revisión no es válida.',
      details: { document_id: id }
    }
  }

  return {
    code: 'PROCESSING_ERROR',
    message: 'No se pudo generar el documento final. Intenta de nuevo.',
    details: {}
  }
}

/**
 * POST /api/documents/{id}/review/
 * Payload contract:
 *   { action: 'accept', revert: ['b2'] } | { action: 'reject' }
 */
export async function submitReview(id, payload) {
  if (USE_MOCKS) {
    await delay(450)
    const mockError = buildMockReviewError(id)
    if (mockError) throw mockError

    const action = payload?.action
    if (action !== 'accept' && action !== 'reject') {
      throw {
        code: 'INVALID_CONFIG',
        message: 'La acción debe ser "accept" o "reject".',
        details: { action }
      }
    }

    const revertedCount =
      action === 'accept' && Array.isArray(payload?.revert) ? payload.revert.length : 0

    return {
      document_id: id,
      job_id: id,
      status: 'done',
      action,
      summary: {
        headings_applied: action === 'accept' ? 1 : 0,
        lists_applied: action === 'accept' ? 4 : 0,
        tables_applied: action === 'accept' ? 1 : 0,
        reverted_blocks_count: revertedCount
      },
      download_url: `/api/documents/${id}/download/`,
      finished_at: new Date().toISOString()
    }
  }

  const response = await apiClient.post(`/documents/${id}/review/`, payload)

  return {
    ...response.data,
    httpStatus: response.status,
    document_id: response.data?.document_id ?? id
  }
}

export function downloadUrl(id) {
  return `${API_URL}/documents/${id}/download/`
}

export async function getPresets() {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return [
      {
        id: 'apa7',
        name: 'Formato académico (APA 7)',
        description: 'Times New Roman 12, interlineado doble, márgenes de 2.54 cm.',
        config: {
          margins_cm: { top: 2.54, bottom: 2.54, left: 2.54, right: 2.54 },
          font_family: 'Times New Roman',
          font_size_pt: 12,
          line_spacing: 2.0,
          heading_sizes_pt: { h1: 12, h2: 12, h3: 12 }
        }
      },
      {
        id: 'reporte',
        name: 'Reporte ejecutivo',
        description: 'Calibri 11, interlineado 1.15, márgenes de 2.5 cm.',
        config: {
          margins_cm: { top: 2.5, bottom: 2.5, left: 2.5, right: 2.5 },
          font_family: 'Calibri',
          font_size_pt: 11,
          line_spacing: 1.15,
          heading_sizes_pt: { h1: 16, h2: 14, h3: 12 }
        }
      },
      {
        id: 'personalizado',
        name: 'Personalizado',
        description: 'Valores base editables.',
        config: {
          margins_cm: { top: 2.54, bottom: 2.54, left: 2.54, right: 2.54 },
          font_family: 'Calibri',
          font_size_pt: 11,
          line_spacing: 1.15,
          heading_sizes_pt: null
        }
      }
    ]
  }

  const response = await apiClient.get('/templates/')
  return response.data.presets
}

export default apiClient
