<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { uploadDocument } from '@/services/api'
import { useFileUpload } from '@/composables/useFileUpload'

const router = useRouter()
const flowStore = useFlowStore()
const isLoading = ref(false)

const {
  file,
  isDragging,
  fileInput,
  handleFileSelect,
  handleDrop,
  clearFile,
  formatSize
} = useFileUpload(10)

async function processUpload() {
  if (!file.value) return

  isLoading.value = true
  flowStore.setError(null)

  try {
    const docData = await uploadDocument(file.value)
    flowStore.setFile(file.value)
    flowStore.setDocument(docData)
    router.push('/config')
  } catch (err: any) {
    flowStore.setError(err)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="container-fluid max-w-900 px-0">
    <!-- Stepper indicator -->
    <div class="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
      <div class="d-flex align-items-center gap-2 fw-semibold text-primary">
        <span class="badge rounded-circle bg-primary text-white p-2">1</span>
        <span>Subir Documento</span>
      </div>
      <div class="text-muted">→</div>
      <div class="d-flex align-items-center gap-2 text-secondary">
        <span class="badge rounded-circle bg-secondary text-white p-2">2</span>
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

    <!-- Dropzone Area -->
    <div class="card border-0 shadow-sm rounded-4 p-4 text-center">
      <label
        class="d-block text-center bg-light rounded-4 p-5 w-100 dropzone"
        :class="[
          'border border-2 border-dashed',
          isDragging ? 'border-primary bg-primary-subtle' : 'border-secondary-subtle'
        ]"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div
          class="d-flex align-items-center justify-content-center bg-primary-subtle text-primary rounded-circle mx-auto mb-4"
          style="width: 70px; height: 70px;"
        >
          <span class="fs-2">↑</span>
        </div>

        <h4 class="fw-semibold text-dark mb-2">Arrastra tu archivo aquí</h4>
        <p class="text-secondary mb-2">
          o da clic para <span class="text-primary fw-semibold">buscar un archivo</span>
        </p>
        <p class="text-secondary small mb-0">Formats: .DOCX | Hasta 10MB</p>

        <input
          ref="fileInput"
          type="file"
          class="d-none"
          accept=".docx,.doc"
          @change="handleFileSelect"
        />

        <div
          v-if="file"
          class="d-flex align-items-center justify-content-between gap-2 bg-white rounded-3 p-3 mt-4 text-start shadow-sm border"
        >
          <div class="d-flex flex-column text-truncate">
            <strong class="text-dark text-truncate">{{ file.name }}</strong>
            <span class="text-secondary small">{{ formatSize(file.size) }}</span>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-outline-danger"
            @click.prevent.stop="clearFile"
          >
            ✕
          </button>
        </div>
      </label>

      <div class="mt-4 d-flex justify-content-center">
        <button
          class="btn btn-primary btn-lg px-5 py-2 rounded-3"
          :disabled="!file || isLoading"
          @click="processUpload"
        >
          <span v-if="isLoading" class="spinner-border spinner-border-sm me-2" role="status"></span>
          <span>{{ isLoading ? 'Cargando archivo...' : 'Continuar a Configuración' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.border-dashed {
  border-style: dashed !important;
}
.dropzone {
  cursor: pointer;
  transition: all 0.2s ease;
}
.dropzone:hover {
  border-color: var(--bs-primary) !important;
  background-color: var(--bs-primary-bg-subtle) !important;
}
</style>
