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
    const formattedError = {
      code: error.response?.data?.code || error.code || 'ERR_UNKNOWN',
      message: error.response?.data?.message || error.message || 'Ocurrió un error inesperado'
    }
    return Promise.reject(formattedError)
  }
)

export async function uploadDocument(file) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 300))
    return {
      id: `doc-${Date.now()}`,
      name: file ? file.name : 'documento.docx',
      size: file ? file.size : 102400,
      status: 'uploaded',
      createdAt: new Date().toISOString()
    }
  }

  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }
  const response = await apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export async function formatDocument(id, config) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 400))
    return {
      id,
      status: 'completed',
      downloadUrl: downloadUrl(id),
      config,
      message: 'Documento formateado con éxito',
      formattedAt: new Date().toISOString()
    }
  }

  const response = await apiClient.post(`/documents/${id}/format`, config)
  return response.data
}

export async function getDocument(id) {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return {
      id,
      name: 'documento_ejemplo.docx',
      status: 'ready',
      size: 102400,
      createdAt: new Date().toISOString()
    }
  }

  const response = await apiClient.get(`/documents/${id}`)
  return response.data
}

export function downloadUrl(id) {
  return `${API_URL}/documents/${id}/download`
}

export async function getPresets() {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return [
      { id: 'classic', name: 'Clásico', description: 'Estilo tradicional para documentos académicos o formales' },
      { id: 'modern', name: 'Moderno', description: 'Diseño limpio y contemporáneo con colores sobrios' },
      { id: 'corporate', name: 'Corporativo', description: 'Formato profesional para informes de empresa' },
      { id: 'minimal', name: 'Minimalista', description: 'Enfoque simple y despejado sin distracciones' },
      { id: 'editorial', name: 'Editorial', description: 'Estilo elegante tipo publicación o revista' }
    ]
  }

  const response = await apiClient.get('/presets')
  return response.data
}

export default apiClient
