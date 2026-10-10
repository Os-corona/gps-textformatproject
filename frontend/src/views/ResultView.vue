<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { downloadUrl } from '@/services/api'

const router = useRouter()
const flowStore = useFlowStore()

function handleDownload() {
  const docId = flowStore.result?.id || flowStore.document?.id
  if (docId) {
    const url = downloadUrl(docId)
    window.open(url, '_blank')
  }
}

function resetAndNew() {
  flowStore.reset()
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
      <div class="d-flex align-items-center gap-2 text-success">
        <span class="badge rounded-circle bg-success text-white p-2">✓</span>
        <span>Configurar</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 fw-semibold text-primary">
        <span class="badge rounded-circle bg-primary text-white p-2">3</span>
        <span>Resultado</span>
      </div>
    </div>

    <!-- Success Message Card -->
    <div class="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
      <div
        class="d-flex align-items-center justify-content-center bg-success-subtle text-success rounded-circle mx-auto mb-4"
        style="width: 80px; height: 80px;"
      >
        <span class="fs-1">✓</span>
      </div>

      <h2 class="fw-bold text-dark mb-2">¡Documento listo!</h2>
      <p class="text-secondary mb-4">
        {{ flowStore.result?.message || 'Tu documento ha sido formateado exitosamente y listo para descargar.' }}
      </p>

      <!-- Document Summary -->
      <div class="bg-light rounded-3 p-4 mb-4 text-start mx-auto w-100" style="max-width: 500px;">
        <div class="d-flex justify-content-between border-bottom pb-2 mb-2">
          <span class="text-secondary">Documento:</span>
          <strong class="text-dark">{{ flowStore.document?.name || flowStore.file?.name || 'documento.docx' }}</strong>
        </div>
        <div class="d-flex justify-content-between border-bottom pb-2 mb-2">
          <span class="text-secondary">Preset aplicado:</span>
          <span class="badge text-bg-primary text-capitalize">{{ flowStore.config?.preset || 'corporate' }}</span>
        </div>
        <div class="d-flex justify-content-between border-bottom pb-2 mb-2">
          <span class="text-secondary">Fuente:</span>
          <span class="fw-medium text-dark">{{ flowStore.config?.fontFamily }}</span>
        </div>
        <div class="d-flex justify-content-between">
          <span class="text-secondary">Estado:</span>
          <span class="badge text-bg-success">Completado</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="d-flex justify-content-center gap-3">
        <button class="btn btn-success btn-lg px-5 py-3 rounded-3 shadow-sm" @click="handleDownload">
          ⬇ Descargar Documento
        </button>
        <button class="btn btn-outline-primary btn-lg px-4 py-3 rounded-3" @click="resetAndNew">
          Formatear otro documento
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
