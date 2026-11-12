<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getDocument } from '@/services/api'

const route = useRoute()
const router = useRouter()
const flowStore = useFlowStore()

const documentId = computed(() => {
  const param = route.params.id
  return param ? Number(param) : (flowStore.document?.document_id ?? null)
})

const documentName = computed(() => {
  return flowStore.document?.original_name || flowStore.file?.name || `Documento #${documentId.value || ''}`
})

const config = computed(() => flowStore.config || {})
const aiOptions = computed(() => config.value.ai_options || {})

const statusText = ref('Enviando documento al proveedor de IA...')
const progressPercent = ref(30)
const errorMessage = ref<string | null>(null)
let pollTimer: any = null

async function checkStatus() {
  if (!documentId.value) return

  try {
    const doc = await getDocument(documentId.value)

    if (doc.status === 'processing') {
      progressPercent.value = Math.min(progressPercent.value + 15, 85)
      statusText.value = 'Analizando jerarquía de títulos, listas y tablas...'
    } else if (doc.status === 'done') {
      progressPercent.value = 100
      statusText.value = '¡Estructuración y formato completados!'
      flowStore.setResult(doc)
      if (pollTimer) clearInterval(pollTimer)
      setTimeout(() => {
        router.push('/result')
      }, 600)
    } else if (doc.status === 'error') {
      if (pollTimer) clearInterval(pollTimer)
      errorMessage.value = doc.error_message || 'Ocurrió un error durante la estructuración del documento.'
    }
  } catch (err: any) {
    // If backend returns an error during polling
    if (pollTimer) clearInterval(pollTimer)
    errorMessage.value = err?.message || 'Error al consultar el estado del procesamiento.'
  }
}

onMounted(() => {
  const isMocks = String(import.meta.env.VITE_USE_MOCKS).toLowerCase() === 'true'

  // If in mock mode, simulate realistic AI processing stages
  if (isMocks) {
    setTimeout(() => {
      progressPercent.value = 60
      statusText.value = 'Detectando elementos estructurales (títulos, listas, tablas)...'
    }, 1200)

    setTimeout(() => {
      progressPercent.value = 90
      statusText.value = 'Aplicando formato y guardando versión final...'
    }, 2200)

    setTimeout(() => {
      progressPercent.value = 100
      flowStore.setResult({
        document_id: documentId.value || 1,
        job_id: documentId.value || 1,
        status: 'done',
        config: flowStore.config,
        finished_at: new Date().toISOString()
      })
      router.push('/result')
    }, 3200)
    return
  }

  // Real backend polling
  checkStatus()
  pollTimer = setInterval(checkStatus, 2500)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

function goBackToConfig() {
  if (pollTimer) clearInterval(pollTimer)
  router.push('/config')
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
        <span>Estructurando con IA</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 text-secondary">
        <span class="badge rounded-circle bg-secondary text-white p-2">4</span>
        <span>Resultado</span>
      </div>
    </div>

    <!-- Active document badge -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-body d-flex align-items-center justify-content-between">
        <div>
          <span class="badge text-bg-primary me-2">Documento activo</span>
          <strong class="fs-5 text-dark">{{ documentName }}</strong>
        </div>
        <span class="badge text-bg-warning-subtle text-warning-emphasis border border-warning-subtle px-3 py-2">
          Estado: Procesando con IA (202 Accepted)
        </span>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="errorMessage" class="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
      <div
        class="d-flex align-items-center justify-content-center bg-danger-subtle text-danger rounded-circle mx-auto mb-4"
        style="width: 80px; height: 80px;"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 16 16">
          <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
        </svg>
      </div>
      <h3 class="fw-bold text-dark mb-2">Error en el procesamiento</h3>
      <p class="text-secondary mb-4">{{ errorMessage }}</p>
      <div>
        <button class="btn btn-primary px-4" @click="goBackToConfig">
          Volver a configuración
        </button>
      </div>
    </div>

    <!-- Processing State -->
    <div v-else class="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
      <div
        class="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-4 bg-primary-subtle position-relative"
        style="width: 90px; height: 90px;"
      >
        <div class="spinner-border text-primary position-absolute" role="status" style="width: 4rem; height: 4rem;">
          <span class="visually-hidden">Cargando...</span>
        </div>
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-stars text-primary" viewBox="0 0 16 16">
          <path d="M7.657 6.247c.11-.33.576-.33.686 0l.645 1.937a2.89 2.89 0 0 0 1.829 1.828l1.936.645c.33.11.33.576 0 .686l-1.937.645a2.89 2.89 0 0 0-1.828 1.829l-.645 1.936a.361.361 0 0 1-.686 0l-.645-1.937a2.89 2.89 0 0 0-1.828-1.828l-1.937-.645a.361.361 0 0 1 0-.686l1.937-.645a2.89 2.89 0 0 0 1.828-1.828l.645-1.937zM3.794.115a.2.2 0 0 1 .38 0l.374 1.123a1.67 1.67 0 0 0 1.06 1.06l1.124.374a.2.2 0 0 1 0 .38l-1.124.374a1.67 1.67 0 0 0-1.06 1.06l-.374 1.124a.2.2 0 0 1-.38 0l-.374-1.124a1.67 1.67 0 0 0-1.06-1.06L1.24 3.052a.2.2 0 0 1 0-.38l1.124-.374a1.67 1.67 0 0 0 1.06-1.06L3.794.115z"/>
        </svg>
      </div>

      <h2 class="fw-bold text-dark mb-2">Estructurando documento con IA</h2>
      <p class="text-secondary mb-4 mx-auto" style="max-width: 600px;">
        {{ statusText }}
      </p>

      <!-- Progress bar -->
      <div class="progress mb-4 mx-auto" style="height: 12px; max-width: 500px;">
        <div
          class="progress-bar progress-bar-striped progress-bar-animated bg-primary"
          role="progressbar"
          :style="{ width: progressPercent + '%' }"
          :aria-valuenow="progressPercent"
          aria-valuemin="0"
          aria-valuemax="100"
        ></div>
      </div>

      <div class="d-flex justify-content-center gap-3 flex-wrap text-muted small mb-4">
        <span class="d-flex align-items-center gap-1">
          <span class="badge rounded-circle bg-primary p-1"></span>
          Proveedor IA conectado
        </span>
        <span class="d-flex align-items-center gap-1">
          <span class="badge rounded-circle bg-info p-1"></span>
          Preservación de contenido 100%
        </span>
        <span class="d-flex align-items-center gap-1">
          <span class="badge rounded-circle bg-success p-1"></span>
          Respetando reglas tipográficas
        </span>
      </div>

      <!-- AI Config summary -->
      <div class="card border border-light-subtle bg-light text-start p-3 mx-auto" style="max-width: 550px;">
        <h6 class="fw-semibold text-dark mb-2 small text-uppercase letter-spacing-1">
          Parámetros de IA aplicados
        </h6>
        <div class="row g-2 small">
          <div class="col-6">
            <span class="text-secondary">Tipo de documento:</span>
            <strong class="text-dark d-block text-capitalize">
              {{ config.document_type || aiOptions.document_type || 'General' }}
            </strong>
          </div>
          <div class="col-6">
            <span class="text-secondary">Nivel de énfasis:</span>
            <strong class="text-dark d-block text-capitalize">
              {{ config.emphasis || aiOptions.emphasis || 'Ligero' }}
            </strong>
          </div>
          <div class="col-12">
            <span class="text-secondary">Detección de elementos:</span>
            <div class="d-flex gap-2 mt-1">
              <span
                class="badge"
                :class="(config.detect_titles ?? aiOptions.detect_titles ?? true) ? 'text-bg-primary' : 'text-bg-secondary'"
              >
                Títulos
              </span>
              <span
                class="badge"
                :class="(config.detect_lists ?? aiOptions.detect_lists ?? true) ? 'text-bg-primary' : 'text-bg-secondary'"
              >
                Listas
              </span>
              <span
                class="badge"
                :class="(config.detect_tables ?? aiOptions.detect_tables ?? true) ? 'text-bg-primary' : 'text-bg-secondary'"
              >
                Tablas
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-4">
        <button class="btn btn-outline-secondary btn-sm px-4" @click="goBackToConfig">
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

