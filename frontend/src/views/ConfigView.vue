<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getPresets, formatDocument } from '@/services/api'

const router = useRouter()
const flowStore = useFlowStore()

const presets = ref<any[]>([])
const isLoadingPresets = ref(true)
const isSubmitting = ref(false)

const configForm = ref({
  preset: 'corporate',
  fontFamily: 'Arial',
  margins: 'normal',
  includeToc: true,
  pageNumbers: true
})

onMounted(async () => {
  try {
    const data = await getPresets()
    presets.value = data
  } catch (err: any) {
    flowStore.setError(err)
  } finally {
    isLoadingPresets.value = false
  }
})

async function submitFormatting() {
  if (!flowStore.document?.id) return

  isSubmitting.value = true
  flowStore.setError(null)

  try {
    const resultData = await formatDocument(flowStore.document.id, configForm.value)
    flowStore.setConfig(configForm.value)
    flowStore.setResult(resultData)
    router.push('/result')
  } catch (err: any) {
    flowStore.setError(err)
  } finally {
    isSubmitting.value = false
  }
}

function cancel() {
  router.push('/')
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
      <div class="d-flex align-items-center gap-2 fw-semibold text-primary">
        <span class="badge rounded-circle bg-primary text-white p-2">2</span>
        <span>Configurar</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 text-secondary">
        <span class="badge rounded-circle bg-secondary text-white p-2">3</span>
        <span>Resultado</span>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="flowStore.error" class="alert alert-danger d-flex align-items-center justify-content-between mb-4" role="alert">
      <div>
        <strong>Error ({{ flowStore.error.code }}):</strong> {{ flowStore.error.message }}
      </div>
      <button type="button" class="btn-close" @click="flowStore.setError(null)"></button>
    </div>

    <!-- Document Info Header -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-body d-flex align-items-center justify-content-between">
        <div>
          <span class="badge text-bg-primary me-2">Documento activo</span>
          <strong class="fs-5 text-dark">{{ flowStore.document?.name || flowStore.file?.name }}</strong>
        </div>
        <button class="btn btn-sm btn-outline-secondary" @click="cancel">Cambiar archivo</button>
      </div>
    </div>

    <!-- Configuration Options -->
    <div class="card border-0 shadow-sm rounded-4 p-4 mb-4">
      <h4 class="fw-semibold text-dark mb-3">Estilo y Formato</h4>

      <!-- Presets selection -->
      <div class="mb-4">
        <label class="form-label fw-semibold">Seleccionar Preset</label>
        <div v-if="isLoadingPresets" class="text-center py-3">
          <div class="spinner-border text-primary spinner-border-sm me-2"></div>
          <span class="text-secondary">Cargando presets...</span>
        </div>
        <div v-else class="row g-3">
          <div v-for="p in presets" :key="p.id" class="col-md-4">
            <div
              class="card h-100 p-3 preset-card cursor-pointer border-2"
              :class="configForm.preset === p.id ? 'border-primary bg-primary-subtle' : 'border-light-subtle'"
              @click="configForm.preset = p.id"
            >
              <div class="d-flex align-items-center justify-content-between mb-2">
                <span class="fw-bold text-dark text-capitalize">{{ p.name }}</span>
                <input
                  type="radio"
                  name="preset"
                  :value="p.id"
                  v-model="configForm.preset"
                  class="form-check-input"
                />
              </div>
              <p class="text-secondary small mb-0">{{ p.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced Options -->
      <div class="row g-3 border-top pt-3">
        <div class="col-md-6">
          <label class="form-label fw-semibold">Fuente Principal</label>
          <select v-model="configForm.fontFamily" class="form-select">
            <option value="Arial">Arial (Sans-serif)</option>
            <option value="Times New Roman">Times New Roman (Serif)</option>
            <option value="Calibri">Calibri</option>
            <option value="Georgia">Georgia</option>
            <option value="Inter">Inter</option>
          </select>
        </div>

        <div class="col-md-6">
          <label class="form-label fw-semibold">Márgenes</label>
          <select v-model="configForm.margins" class="form-select">
            <option value="normal">Normal (2.5 cm)</option>
            <option value="narrow">Estrecho (1.27 cm)</option>
            <option value="wide">Ancho (3.18 cm)</option>
          </select>
        </div>

        <div class="col-md-6">
          <div class="form-check form-switch mt-2">
            <input
              id="includeToc"
              v-model="configForm.includeToc"
              type="checkbox"
              class="form-check-input"
            />
            <label for="includeToc" class="form-check-label fw-medium">Generar Tabla de Contenido</label>
          </div>
        </div>

        <div class="col-md-6">
          <div class="form-check form-switch mt-2">
            <input
              id="pageNumbers"
              v-model="configForm.pageNumbers"
              type="checkbox"
              class="form-check-input"
            />
            <label for="pageNumbers" class="form-check-label fw-medium">Número de página en pie</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="d-flex justify-content-between">
      <button class="btn btn-outline-secondary px-4" @click="cancel">Volver</button>
      <button
        class="btn btn-primary btn-lg px-5"
        :disabled="isSubmitting"
        @click="submitFormatting"
      >
        <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" role="status"></span>
        <span>{{ isSubmitting ? 'Procesando formato...' : 'Formatear Documento' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.preset-card {
  cursor: pointer;
  transition: all 0.2s ease;
}
.preset-card:hover {
  border-color: var(--bs-primary) !important;
}
</style>
