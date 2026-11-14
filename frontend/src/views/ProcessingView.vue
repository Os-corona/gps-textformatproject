<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getDocument, formatDocument } from '@/services/api'

// ─── Router & Store ───────────────────────────────────────────────────────────
const route = useRoute()
const router = useRouter()
const flowStore = useFlowStore()

// ─── Document identification & reload survival ────────────────────────────────
const documentId = computed(() => {
  const param = route.params.id
  return param ? Number(param) : (flowStore.document?.document_id ?? null)
})

const docData = ref<any>(null)
const isLoadingDoc = ref(true)

const documentName = computed(() => {
  return docData.value?.original_name || flowStore.document?.original_name || flowStore.file?.name || `Documento #${documentId.value || ''}`
})

// ─── Stages and Chunks Progress ───────────────────────────────────────────────
const STAGES = [
  'Extracción y análisis de contenido',
  'Identificación de jerarquías y títulos',
  'Detección de listas y tablas',
  'Aplicación de estilos y formato'
] as const

const currentChunkInternal = ref(1)
const totalChunksInternal = ref(4)

const currentChunk = computed(() => {
  if (docData.value?.current_chunk != null) return Number(docData.value.current_chunk)
  if (docData.value?.chunk != null) return Number(docData.value.chunk)
  return currentChunkInternal.value
})

const totalChunks = computed(() => {
  if (docData.value?.total_chunks != null) return Number(docData.value.total_chunks)
  if (docData.value?.chunks != null) return Number(docData.value.chunks)
  return totalChunksInternal.value
})

const currentStage = computed(() => {
  if (docData.value?.stage) return docData.value.stage
  const idx = Math.min(Math.max(currentChunk.value - 1, 0), STAGES.length - 1)
  return STAGES[idx]
})

const progressPercent = computed(() => {
  if (docData.value?.status === 'done') return 100
  const ratio = Math.min(currentChunk.value / Math.max(totalChunks.value, 1), 0.95)
  return Math.round(ratio * 100)
})

// ─── Error Handling ───────────────────────────────────────────────────────────
const isError = ref(false)
const errorCode = ref<string>('PROCESSING_ERROR')
const errorMessage = ref<string>('')
const isRetrying = ref(false)

const ERROR_MESSAGES: Record<string, string> = {
  AI_PROVIDER_ERROR: 'El proveedor de inteligencia artificial no respondió o no se encuentra disponible.',
  AI_TIMEOUT: 'Se agotó el tiempo de espera con el servicio de IA. Intenta de nuevo más tarde.',
  AI_TOKEN_LIMIT: 'El documento supera la longitud máxima de procesamiento permitida por la IA.',
  AI_RATE_LIMIT: 'Se excedió el límite de consultas permitidas al proveedor de IA.',
  INVALID_STRUCTURE: 'No se pudo identificar una estructura coherente en el documento.',
  CORRUPTED_DOCUMENT: 'El archivo está dañado o contiene elementos no compatibles.',
  INVALID_FILE: 'El archivo suministrado no es un documento de Word válido.',
  INVALID_CONFIG: 'La configuración enviada no es compatible con el formato requerido.',
  PROCESSING_ERROR: 'Ocurrió un error inesperado durante el procesamiento del documento.',
  NOT_FOUND: 'No se encontró el documento solicitado.',
  ERR_NETWORK: 'No se pudo conectar con el servidor. Revisa tu conexión a internet.'
}

function resolveErrorMessage(code: string, rawMessage?: string): string {
  if (code && ERROR_MESSAGES[code]) {
    return rawMessage ? `${ERROR_MESSAGES[code]} (${rawMessage})` : ERROR_MESSAGES[code]
  }
  return rawMessage || ERROR_MESSAGES.PROCESSING_ERROR
}

// ─── Polling management (2s interval, stops on exit or non-processing) ────────
let pollTimer: ReturnType<typeof setInterval> | null = null

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollStatus() {
  if (!documentId.value) {
    stopPolling()
    isError.value = true
    errorCode.value = 'NOT_FOUND'
    errorMessage.value = 'Identificador de documento no válido.'
    isLoadingDoc.value = false
    return
  }

  try {
    const data = await getDocument(documentId.value)
    docData.value = data
    isLoadingDoc.value = false

    // Update and restore store to survive page reloads
    flowStore.setDocument({
      document_id: data.document_id || documentId.value,
      original_name: data.original_name,
      size_bytes: data.size_bytes,
      uploaded_at: data.uploaded_at,
      status: data.status
    })

    if (data.config && Object.keys(data.config).length > 0) {
      flowStore.setConfig(data.config)
    }

    // Check status
    if (data.status === 'processing') {
      // Advance simulated fragment counter if not supplied by backend
      if (currentChunkInternal.value < totalChunksInternal.value) {
        currentChunkInternal.value++
      }
    } else {
      // Stop polling as soon as status is NOT 'processing'
      stopPolling()

      if (data.status === 'review') {
        router.push(`/review/${documentId.value}`)
      } else if (data.status === 'done') {
        flowStore.setResult(data)
        router.push('/result')
      } else if (data.status === 'error') {
        isError.value = true
        const code = data.error_code || data.error?.code || (typeof data.error === 'string' ? data.error : 'PROCESSING_ERROR')
        errorCode.value = code
        errorMessage.value = resolveErrorMessage(code, data.error_message || data.error?.message)
      }
    }
  } catch (err: any) {
    stopPolling()
    isLoadingDoc.value = false
    isError.value = true
    const code = err.code || 'PROCESSING_ERROR'
    errorCode.value = code
    errorMessage.value = resolveErrorMessage(code, err.message)
  }
}

onMounted(() => {
  // Compute estimated fragments from store if document size is available
  if (flowStore.document?.size_bytes) {
    totalChunksInternal.value = Math.max(3, Math.min(8, Math.ceil(flowStore.document.size_bytes / 25000)))
  }

  // Initial fetch immediately
  pollStatus()

  // Polling every 2s
  pollTimer = setInterval(pollStatus, 2000)
})

onUnmounted(() => {
  stopPolling()
})

onBeforeRouteLeave(() => {
  stopPolling()
})

// ─── Actions for Error State ──────────────────────────────────────────────────
function goToConfig() {
  stopPolling()
  router.push('/config')
}

async function retryWithoutAi() {
  if (!documentId.value) return
  isRetrying.value = true
  stopPolling()

  try {
    const baseConfig = flowStore.config || docData.value?.config || {}
    const payloadNoAi: Record<string, any> = {
      preset_id: baseConfig.preset_id ?? null,
      margins_cm: baseConfig.margins_cm ?? { top: 2.54, bottom: 2.54, left: 2.54, right: 2.54 },
      font_family: baseConfig.font_family ?? 'Calibri',
      font_size_pt: baseConfig.font_size_pt ?? 11,
      line_spacing: baseConfig.line_spacing ?? 1.15,
      use_ai: false
    }

    const resultData = await formatDocument(documentId.value, payloadNoAi)
    flowStore.setConfig(resultData.config ?? payloadNoAi)
    flowStore.setResult(resultData)
    router.push('/result')
  } catch (err: any) {
    isError.value = true
    const code = err.code || 'PROCESSING_ERROR'
    errorCode.value = code
    errorMessage.value = resolveErrorMessage(code, err.message)
  } finally {
    isRetrying.value = false
  }
}
</script>

<template>
  <div class="container-fluid max-w-900 px-0">
    <!-- Stepper indicator -->
    <div class="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
      <div class="d-flex align-items-center gap-2 text-success">
        <span class="badge rounded-circle bg-success text-white p-2">✓</span>
        <span>Subir Documento</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 text-success">
        <span class="badge rounded-circle bg-success text-white p-2">✓</span>
        <span>Configurar</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 fw-semibold text-primary">
        <span class="badge rounded-circle bg-primary text-white p-2">3</span>
        <span>Procesando</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 text-secondary">
        <span class="badge rounded-circle bg-secondary text-white p-2">4</span>
        <span>Resultado</span>
      </div>
    </div>

    <!-- Active document header (survives reload) -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-body d-flex align-items-center justify-content-between">
        <div>
          <span class="badge text-bg-primary me-2">Documento activo</span>
          <strong class="fs-5 text-dark">{{ documentName }}</strong>
        </div>
        <span
          class="badge px-3 py-2"
          :class="isError ? 'text-bg-danger-subtle text-danger border border-danger-subtle' : 'text-bg-warning-subtle text-warning-emphasis border border-warning-subtle'"
        >
          Estado: {{ isError ? 'Error en formateo' : 'Procesando (polling cada 2s)' }}
        </span>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════
         ESTADO DE ERROR
    ═══════════════════════════════════════════════════════════════ -->
    <div v-if="isError" class="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
      <div
        class="d-flex align-items-center justify-content-center bg-danger-subtle text-danger rounded-circle mx-auto mb-4"
        style="width: 80px; height: 80px;"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 16 16">
          <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
        </svg>
      </div>

      <h3 class="fw-bold text-dark mb-2">Error al procesar el documento</h3>

      <!-- Mensaje según error_code -->
      <div
        id="processing-error-alert"
        class="alert alert-danger text-start mx-auto mb-4"
        role="alert"
        style="max-width: 560px;"
      >
        <div class="d-flex align-items-center gap-2 mb-1">
          <span class="badge text-bg-danger">{{ errorCode }}</span>
          <strong class="text-danger-emphasis">Falla en la estructuración</strong>
        </div>
        <p class="mb-0 text-dark">
          {{ errorMessage }}
        </p>
      </div>

      <!-- Botones de acción requeridos -->
      <div class="d-flex justify-content-center gap-3 flex-wrap">
        <button
          id="btn-go-to-config"
          class="btn btn-outline-secondary px-4 py-2"
          @click="goToConfig"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-sliders me-2" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M11.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM9.05 3a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0V3h9.05zM4.5 7a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM2.05 8a2.5 2.5 0 0 1 4.9 0H16v1H6.95a2.5 2.5 0 0 1-4.9 0H0V8h2.05zm9.45 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-2.45 1a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0v-1h9.05z"/>
          </svg>
          Volver a configuración
        </button>

        <button
          id="btn-retry-without-ai"
          class="btn btn-primary px-4 py-2"
          :disabled="isRetrying"
          @click="retryWithoutAi"
        >
          <span v-if="isRetrying" class="spinner-border spinner-border-sm me-2" role="status"></span>
          <span>{{ isRetrying ? 'Reintentando sin IA...' : 'Reintentar sin IA' }}</span>
        </button>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════
         ESTADO DE PROCESAMIENTO ACTIVO (POLLING CADA 2 S)
    ═══════════════════════════════════════════════════════════════ -->
    <div v-else class="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
      <div
        class="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-4 bg-primary-subtle position-relative"
        style="width: 90px; height: 90px;"
      >
        <div class="spinner-border text-primary position-absolute" role="status" style="width: 4rem; height: 4rem;">
          <span class="visually-hidden">Procesando...</span>
        </div>
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-cpu text-primary" viewBox="0 0 16 16">
          <path d="M5 0a.5.5 0 0 1 .5.5V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2A2.5 2.5 0 0 1 14 4.5h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14A2.5 2.5 0 0 1 11.5 14v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14A2.5 2.5 0 0 1 2 11.5H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2A2.5 2.5 0 0 1 4.5 2V.5A.5.5 0 0 1 5 0zm-.5 3A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13h7a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 11.5 3h-7zM5 6.5A1.5 1.5 0 0 1 6.5 5h3A1.5 1.5 0 0 1 11 6.5v3A1.5 1.5 0 0 1 9.5 11h-3A1.5 1.5 0 0 1 5 9.5v-3zM6.5 6a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3z"/>
        </svg>
      </div>

      <h2 class="fw-bold text-dark mb-1">Estructurando documento con IA</h2>
      <p class="text-secondary small mb-4">
        Sondeando estado cada 2 segundos. Por favor, espera mientras se procesa tu archivo.
      </p>

      <!-- ── BARRA CON LA ETAPA Y "Estructurando fragmento X de Y" ── -->
      <div class="mx-auto text-start mb-4" style="max-width: 580px;">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="badge text-bg-primary-subtle text-primary border border-primary-subtle px-3 py-2 fw-semibold">
            Etapa: {{ currentStage }}
          </span>
          <span class="fw-bold text-primary small">
            Estructurando fragmento {{ currentChunk }} de {{ totalChunks }}
          </span>
        </div>

        <div class="progress" style="height: 18px;">
          <div
            class="progress-bar progress-bar-striped progress-bar-animated bg-primary fw-medium"
            role="progressbar"
            :style="{ width: progressPercent + '%' }"
            :aria-valuenow="progressPercent"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            {{ progressPercent }}%
          </div>
        </div>

        <div class="d-flex justify-content-between text-muted small mt-2">
          <span>Inicio</span>
          <span>Fragmento {{ currentChunk }} de {{ totalChunks }}</span>
          <span>Finalización</span>
        </div>
      </div>

      <!-- Indicadores de estado -->
      <div class="d-flex justify-content-center gap-3 flex-wrap text-muted small mt-2">
        <span class="d-flex align-items-center gap-1">
          <span class="badge rounded-circle bg-success p-1"></span>
          Conexión activa con el backend
        </span>
        <span class="d-flex align-items-center gap-1">
          <span class="badge rounded-circle bg-primary p-1"></span>
          Respetando contenido original
        </span>
      </div>

      <div class="mt-4 pt-3 border-top">
        <button class="btn btn-outline-secondary btn-sm px-4" @click="goToConfig">
          Cancelar y volver a configuración
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.letter-spacing-1 {
  letter-spacing: 0.05em;
}
</style>
