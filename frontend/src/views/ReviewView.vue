<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getDocument, formatDocument } from '@/services/api'

const route = useRoute()
const router = useRouter()
const flowStore = useFlowStore()

const documentId = computed(() => {
  const param = route.params.id
  return param ? Number(param) : (flowStore.document?.document_id ?? null)
})

const documentName = computed(() => {
  return flowStore.document?.original_name || `Documento #${documentId.value || ''}`
})

const isLoading = ref(true)
const isSubmitting = ref(false)
const docData = ref<any>(null)

const suggestions = computed(() => {
  if (docData.value?.ai_suggestions && Array.isArray(docData.value.ai_suggestions)) {
    return docData.value.ai_suggestions
  }
  // Fallback default suggestions for demonstration and testing
  return [
    {
      id: 1,
      type: 'Título principal (H1)',
      original: 'INTRODUCCIÓN GENERAL AL PROYECTO',
      suggested: 'Introducción General al Proyecto',
      reason: 'Normalización a título H1 con capitalización estándar APA.'
    },
    {
      id: 2,
      type: 'Subtítulo (H2)',
      original: '1.1 ANTECEDENTES Y JUSTIFICACION',
      suggested: '1.1 Antecedentes y justificación',
      reason: 'Asignación de estilo Heading 2 con jerarquía semántica.'
    },
    {
      id: 3,
      type: 'Lista numerada',
      original: 'Párrafos con guiones mixtos y asteriscos',
      suggested: 'Lista con viñetas uniformes y sangría de 1.27 cm',
      reason: 'Homogeneización de viñetas en el cuerpo del texto.'
    }
  ]
})

onMounted(async () => {
  if (documentId.value) {
    try {
      const data = await getDocument(documentId.value)
      docData.value = data
      flowStore.setDocument({
        document_id: data.document_id || documentId.value,
        original_name: data.original_name,
        size_bytes: data.size_bytes,
        uploaded_at: data.uploaded_at,
        status: data.status
      })
      if (data.config) {
        flowStore.setConfig(data.config)
      }
    } catch (e) {
      // Keep existing data in store
    } finally {
      isLoading.value = false
    }
  } else {
    isLoading.value = false
  }
})

function approveAndFinish() {
  flowStore.setResult({
    document_id: documentId.value,
    status: 'done',
    config: flowStore.config,
    finished_at: new Date().toISOString()
  })
  router.push('/result')
}

async function retryWithoutAi() {
  if (!documentId.value) return
  isSubmitting.value = true
  try {
    const baseConfig = flowStore.config || docData.value?.config || {}
    const payload = {
      ...baseConfig,
      use_ai: false
    }
    const result = await formatDocument(documentId.value, payload)
    flowStore.setConfig(result.config ?? payload)
    flowStore.setResult(result)
    router.push('/result')
  } catch (err: any) {
    flowStore.setError(err)
    router.push('/config')
  } finally {
    isSubmitting.value = false
  }
}

function goToConfig() {
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
        <span>Revisión con IA</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 text-secondary">
        <span class="badge rounded-circle bg-secondary text-white p-2">4</span>
        <span>Resultado</span>
      </div>
    </div>

    <!-- Active Document Banner -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-body d-flex align-items-center justify-content-between">
        <div>
          <span class="badge text-bg-primary me-2">Documento activo</span>
          <strong class="fs-5 text-dark">{{ documentName }}</strong>
        </div>
        <span class="badge text-bg-info-subtle text-info-emphasis border border-info-subtle px-3 py-2">
          Estado: En revisión (review)
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-5">
      <div class="spinner-border text-primary me-2" role="status"></div>
      <span class="text-secondary">Cargando revisión...</span>
    </div>

    <!-- Review Content -->
    <div v-else class="card border-0 shadow-sm rounded-4 p-4 mb-4">
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h4 class="fw-semibold text-dark mb-1">Revisión de cambios sugeridos por IA</h4>
          <p class="text-secondary small mb-0">
            La IA detectó las siguientes mejoras estructurales. El contenido textual no se alteró.
          </p>
        </div>
        <span class="badge text-bg-light border text-secondary px-3 py-2">
          {{ suggestions.length }} sugerencias
        </span>
      </div>

      <!-- Suggestions list -->
      <div class="d-flex flex-column gap-3 my-3">
        <div
          v-for="item in suggestions"
          :key="item.id"
          class="p-3 border rounded-3 bg-light-subtle"
        >
          <div class="d-flex align-items-center justify-content-between mb-2">
            <span class="badge text-bg-primary">{{ item.type }}</span>
            <small class="text-secondary">{{ item.reason }}</small>
          </div>
          <div class="row g-2 small">
            <div class="col-md-6">
              <div class="p-2 bg-danger-subtle text-danger-emphasis rounded border border-danger-subtle">
                <strong>Original:</strong> {{ item.original }}
              </div>
            </div>
            <div class="col-md-6">
              <div class="p-2 bg-success-subtle text-success-emphasis rounded border border-success-subtle">
                <strong>Estructurado:</strong> {{ item.suggested }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="d-flex justify-content-between align-items-center pt-3 border-top mt-2">
        <button class="btn btn-outline-secondary" @click="goToConfig">
          Volver a configuración
        </button>

        <div class="d-flex gap-2">
          <button
            class="btn btn-outline-secondary"
            :disabled="isSubmitting"
            @click="retryWithoutAi"
          >
            <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-1"></span>
            Reintentar sin IA
          </button>

          <button
            class="btn btn-success px-4"
            @click="approveAndFinish"
          >
            Aprobar cambios y descargar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

