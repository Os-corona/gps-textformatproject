<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { uploadDocument } from '@/services/api'
import { useFileUpload } from '@/composables/useFileUpload'

const router = useRouter()
const flowStore = useFlowStore()
const isUploading = ref(false)

// Upload error message from the API (shown in the alert banner)
const uploadError = ref<{ code: string; message: string } | null>(null)

const {
  file,
  fileError,
  isDragging,
  fileInput,
  handleFileSelect,
  handleDrop,
  clearFile,
  formatSize,
} = useFileUpload()

// ─── Handlers ────────────────────────────────────────────────────────────────

function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  uploadError.value = null
  handleDrop(e)
}

function onFileSelect(e: Event) {
  uploadError.value = null
  handleFileSelect(e)
}

function onClear() {
  uploadError.value = null
  clearFile()
}

// ─── Upload ───────────────────────────────────────────────────────────────────

async function processUpload() {
  if (!file.value || isUploading.value) return

  isUploading.value = true
  uploadError.value = null
  flowStore.setError(null)

  try {
    const docData = await uploadDocument(file.value)
    flowStore.setFile(file.value)
    flowStore.setDocument(docData)
    router.push('/config')
  } catch (err: any) {
    // Show the message from the backend directly (already formatted by the interceptor)
    uploadError.value = {
      code: err.code ?? 'ERR_UNKNOWN',
      message: err.message ?? 'Ocurrió un error inesperado al subir el archivo.',
    }
  } finally {
    isUploading.value = false
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

    <!-- ── API error alert ──────────────────────────────────────────────────── -->
    <div
      v-if="uploadError"
      id="upload-error-alert"
      class="alert alert-danger d-flex align-items-start justify-content-between gap-3 mb-4"
      role="alert"
    >
      <div>
        <strong class="d-block mb-1">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-circle-fill me-1" viewBox="0 0 16 16">
            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293 5.354 4.646z"/>
          </svg>
          Error al subir el archivo
          <code class="ms-1 small">({{ uploadError.code }})</code>
        </strong>
        {{ uploadError.message }}
      </div>
      <button
        type="button"
        class="btn-close flex-shrink-0"
        aria-label="Cerrar"
        @click="uploadError = null"
      ></button>
    </div>

    <!-- ── Dropzone ────────────────────────────────────────────────────────── -->
    <div class="card border-0 shadow-sm rounded-4 p-4">

      <!-- Drop area -->
      <div
        id="dropzone"
        class="dropzone rounded-4 p-5 text-center w-100 border border-2 border-dashed"
        :class="{
          'border-primary bg-primary-subtle': isDragging,
          'border-danger': fileError,
          'border-success bg-success-subtle': file && !fileError,
          'border-secondary-subtle bg-light': !isDragging && !file && !fileError,
        }"
        role="button"
        tabindex="0"
        aria-label="Área de carga de archivos. Arrastra un .docx o haz clic para buscar."
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="fileInput?.click()"
        @keydown.enter.space.prevent="fileInput?.click()"
      >
        <!-- Icon -->
        <div
          class="icon-circle d-flex align-items-center justify-content-center rounded-circle mx-auto mb-4"
          :class="file && !fileError ? 'bg-success-subtle text-success' : 'bg-primary-subtle text-primary'"
        >
          <!-- Success checkmark -->
          <svg v-if="file && !fileError" xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-file-earmark-check-fill" viewBox="0 0 16 16">
            <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zm1.354 4.354-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708.708z"/>
          </svg>
          <!-- Upload arrow -->
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-cloud-arrow-up-fill" viewBox="0 0 16 16">
            <path d="M8 2a5.53 5.53 0 0 0-3.594 1.342c-.766.66-1.321 1.52-1.464 2.383C1.266 6.095 0 7.555 0 9.318 0 11.366 1.708 13 3.781 13h8.906C14.502 13 16 11.57 16 9.773c0-1.636-1.242-2.969-2.834-3.194C12.923 3.999 10.69 2 8 2zm2.354 5.146a.5.5 0 0 1-.708.708L8.5 6.707V10.5a.5.5 0 0 1-1 0V6.707L6.354 7.854a.5.5 0 1 1-.708-.708l2-2a.5.5 0 0 1 .708 0l2 2z"/>
          </svg>
        </div>

        <!-- Text -->
        <template v-if="!file">
          <h4 class="fw-semibold text-dark mb-2">Arrastra tu archivo aquí</h4>
          <p class="text-secondary mb-1">
            o haz clic para <span class="text-primary fw-semibold">buscar un archivo</span>
          </p>
          <p class="text-secondary small mb-0">Solo archivos <strong>.docx</strong> · Máximo <strong>10 MB</strong></p>
        </template>
        <template v-else>
          <h4 class="fw-semibold text-dark mb-1">Archivo listo</h4>
          <p class="text-secondary small mb-0">Haz clic en "Continuar" para subir el documento.</p>
        </template>

        <!-- Hidden file input -->
        <input
          id="file-input"
          ref="fileInput"
          type="file"
          accept=".docx"
          class="d-none"
          @change="onFileSelect"
        />
      </div>

      <!-- ── Client-side validation error ──────────────────────────────────── -->
      <div
        v-if="fileError"
        id="file-error-message"
        class="alert alert-warning d-flex align-items-center gap-2 mt-3 mb-0 py-2"
        role="alert"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-triangle-fill flex-shrink-0" viewBox="0 0 16 16">
          <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
        </svg>
        <span>{{ fileError }}</span>
      </div>

      <!-- ── Selected file info ─────────────────────────────────────────────── -->
      <div
        v-if="file && !fileError"
        id="selected-file-info"
        class="d-flex align-items-center justify-content-between gap-2 bg-white rounded-3 p-3 mt-3 shadow-sm border"
      >
        <div class="d-flex align-items-center gap-3 min-w-0">
          <!-- Word icon -->
          <div class="flex-shrink-0 d-flex align-items-center justify-content-center bg-primary-subtle text-primary rounded-2" style="width:40px;height:40px">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-file-earmark-word-fill" viewBox="0 0 16 16">
              <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zM5.485 6.879l1.036 4.144.997-3.655a.5.5 0 0 1 .964 0l.997 3.655 1.036-4.144a.5.5 0 0 1 .97.242l-1.5 6a.5.5 0 0 1-.967.01L8 9.402l-1.018 3.73a.5.5 0 0 1-.967-.01l-1.5-6a.5.5 0 1 1 .97-.242z"/>
            </svg>
          </div>
          <div class="d-flex flex-column min-w-0">
            <strong class="text-dark text-truncate" style="max-width: 320px">{{ file.name }}</strong>
            <span class="text-secondary small">{{ formatSize(file.size) }}</span>
          </div>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-outline-danger flex-shrink-0"
          aria-label="Quitar archivo"
          @click.stop="onClear"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-x-lg" viewBox="0 0 16 16">
            <path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854z"/>
          </svg>
        </button>
      </div>

      <!-- ── Upload progress indicator ─────────────────────────────────────── -->
      <div v-if="isUploading" class="mt-3">
        <div class="d-flex justify-content-between small text-secondary mb-1">
          <span>Subiendo documento…</span>
        </div>
        <div class="progress" style="height: 6px" role="progressbar" aria-label="Progreso de carga">
          <div class="progress-bar progress-bar-striped progress-bar-animated w-100"></div>
        </div>
      </div>

      <!-- ── Action button ──────────────────────────────────────────────────── -->
      <div class="mt-4 d-flex justify-content-center">
        <button
          id="btn-continue"
          class="btn btn-primary btn-lg px-5 py-2 rounded-3"
          :disabled="!file || !!fileError || isUploading"
          @click="processUpload"
        >
          <span v-if="isUploading" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          <span>{{ isUploading ? 'Subiendo…' : 'Continuar a Configuración' }}</span>
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
  transition: border-color 0.2s ease, background-color 0.2s ease;
}
.dropzone:hover:not(.border-success) {
  border-color: var(--bs-primary) !important;
  background-color: var(--bs-primary-bg-subtle) !important;
}
.icon-circle {
  width: 72px;
  height: 72px;
  transition: background-color 0.2s ease;
}
</style>
