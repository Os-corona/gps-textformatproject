import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const USE_MOCKS = String(import.meta.env.VITE_USE_MOCKS).toLowerCase() === 'true'

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError = error.response?.data?.error
    const formattedError = {
      code: apiError?.code || error.code || 'ERR_UNKNOWN',
      message: apiError?.message || error.message || 'Ocurrió un error inesperado',
      details: apiError?.details || {}
    }
    return Promise.reject(formattedError)
  }
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
  const response = await apiClient.post('/documents/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export async function formatDocument(id, config) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 400))
    return {
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
  return response.data
}

export async function getDocument(id) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return {
      document_id: id,
      job_id: id,
      original_name: 'documento_ejemplo.docx',
      size_bytes: 102400,
      uploaded_at: new Date().toISOString(),
      status: 'done',
      config: {},
      use_ai: false,
      error_message: null,
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      download_url: `/api/documents/${id}/download/`
    }
  }

  const response = await apiClient.get(`/documents/${id}/`)
  return response.data
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
