<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { uploadDocument } from '@/services/api'
import { useFileUpload } from '@/composables/useFileUpload'
import FlowStepper from '@/components/FlowStepper.vue'

const router = useRouter()
const flowStore = useFlowStore()
const isUploading = ref(false)
const uploadError = ref<{ code: string; message: string } | null>(null)

const {
  file,
  fileError,
  isDragging,
  fileInput,
  handleFileSelect,
  handleDrop,
  clearFile,
  formatSize
} = useFileUpload()

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
    uploadError.value = {
      code: err.code ?? 'ERR_UNKNOWN',
      message: err.message ?? 'Ocurrió un error inesperado al subir el archivo.'
    }
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="container-fluid home-container px-0">
    <FlowStepper :current="1" />

    <!-- API error alert -->
    <div
      v-if="uploadError"
      id="upload-error-alert"
      class="alert alert-danger d-flex align-items-start justify-content-between gap-3 mb-4 rounded-4"
      role="alert"
    >
      <div>
        <strong class="d-block mb-1">
          Error al subir el archivo <code class="ms-1 small">({{ uploadError.code }})</code>
        </strong>
        {{ uploadError.message }}
      </div>
      <button type="button" class="btn-close flex-shrink-0" aria-label="Cerrar" @click="uploadError = null"></button>
    </div>

    <!-- Main Upload Card -->
    <div class="card pd-card p-4 p-md-5 mb-4">
      <div class="text-center mb-4">
        <span class="badge rounded-pill hero-chip mb-2">Paso 1 · Carga segura .docx</span>
        <h2 class="fw-bold text-dark mb-1">Sube tu documento Word</h2>
        <p class="text-secondary mb-0">
          Detectamos títulos, listas, tablas y bloques clave preservando intactas tus palabras, cifras e imágenes.
        </p>
      </div>

      <div
        id="dropzone"
        class="dropzone rounded-4 p-5 text-center w-100"
        :class="{
          'dropzone--drag': isDragging,
          'dropzone--error': fileError,
          'dropzone--ready': file && !fileError
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
        <div
          class="icon-circle d-flex align-items-center justify-content-center rounded-circle mx-auto mb-3"
          :class="file && !fileError ? 'bg-success-subtle text-success' : 'icon-circle--brand'"
        >
          <svg v-if="file && !fileError" xmlns="http://www.w3.org/2000/svg" width="30" height="30" fill="currentColor" viewBox="0 0 16 16">
            <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zm1.354 4.354-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708.708z"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="30" height="30" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 2a5.53 5.53 0 0 0-3.594 1.342c-.766.66-1.321 1.52-1.464 2.383C1.266 6.095 0 7.555 0 9.318 0 11.366 1.708 13 3.781 13h8.906C14.502 13 16 11.57 16 9.773c0-1.636-1.242-2.969-2.834-3.194C12.923 3.999 10.69 2 8 2zm2.354 5.146a.5.5 0 0 1-.708.708L8.5 6.707V10.5a.5.5 0 0 1-1 0V6.707L6.354 7.854a.5.5 0 1 1-.708-.708l2-2a.5.5 0 0 1 .708 0l2 2z"/>
          </svg>
        </div>

        <template v-if="!file">
          <h4 class="fw-semibold text-dark mb-1">Arrastra tu archivo aquí</h4>
          <p class="text-secondary mb-2">
            o haz clic para <span class="fw-semibold text-primary">explorar tus carpetas</span>
          </p>
          <span class="badge text-bg-light border text-secondary fw-normal px-3 py-2">
            Formato .docx · Hasta 10 MB
          </span>
        </template>
        <template v-else>
          <h4 class="fw-semibold text-success mb-1">Documento listo para configurar</h4>
          <p class="text-secondary small mb-0">Haz clic en "Continuar" para elegir paleta, plantilla y opciones de IA.</p>
        </template>

        <input
          id="file-input"
          ref="fileInput"
          type="file"
          accept=".docx"
          class="d-none"
          @change="onFileSelect"
        />
      </div>

      <div
        v-if="fileError"
        id="file-error-message"
        class="alert alert-warning d-flex align-items-center gap-2 mt-3 mb-0 py-2 rounded-3"
        role="alert"
      >
        <span>{{ fileError }}</span>
      </div>

      <div
        v-if="file && !fileError"
        id="selected-file-info"
        class="d-flex align-items-center justify-content-between gap-2 bg-light rounded-3 p-3 mt-3 border"
      >
        <div class="d-flex align-items-center gap-3 min-w-0">
          <div class="flex-shrink-0 d-flex align-items-center justify-content-center bg-primary-subtle text-primary rounded-2" style="width: 42px; height: 42px">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" viewBox="0 0 16 16">
              <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zM5.485 6.879l1.036 4.144.997-3.655a.5.5 0 0 1 .964 0l.997 3.655 1.036-4.144a.5.5 0 0 1 .97.242l-1.5 6a.5.5 0 0 1-.967.01L8 9.402l-1.018 3.73a.5.5 0 0 1-.967-.01l-1.5-6a.5.5 0 1 1 .97-.242z"/>
            </svg>
          </div>
          <div class="d-flex flex-column min-w-0">
            <strong class="text-dark text-truncate" style="max-width: 360px">{{ file.name }}</strong>
            <span class="text-secondary small">{{ formatSize(file.size) }}</span>
          </div>
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger flex-shrink-0" aria-label="Quitar archivo" @click.stop="onClear">
          Quitar
        </button>
      </div>

      <div v-if="isUploading" class="mt-3">
        <div class="small text-secondary mb-1">Subiendo y validando estructura del archivo…</div>
        <div class="progress" style="height: 6px" role="progressbar">
          <div class="progress-bar progress-bar-striped progress-bar-animated w-100"></div>
        </div>
      </div>

      <div class="mt-4 d-flex justify-content-center">
        <button
          id="btn-continue"
          class="btn pd-btn-brand btn-lg px-5 py-2 rounded-3"
          :disabled="!file || !!fileError || isUploading"
          @click="processUpload"
        >
          <span v-if="isUploading" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          <span>{{ isUploading ? 'Subiendo…' : 'Continuar a Personalización' }}</span>
        </button>
      </div>
    </div>

    <!-- Feature highlight cards -->
    <div class="row g-3">
      <div class="col-md-4">
        <div class="card pd-card p-3 h-100">
          <div class="feature-icon mb-2">✦</div>
          <h6 class="fw-bold text-dark mb-1">Estructura automática con IA</h6>
          <p class="small text-secondary mb-0">
            Convierte texto plano en títulos navegables, listas nativas, tablas con encabezado y tarjetas destacadas.
          </p>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card pd-card p-3 h-100">
          <div class="feature-icon mb-2">◈</div>
          <h6 class="fw-bold text-dark mb-1">Paletas ejecutivas reales</h6>
          <p class="small text-secondary mb-0">
            Personaliza el color de títulos, barras divisorias, tablas y notas destacadas directamente en tu Word.
          </p>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card pd-card p-3 h-100">
          <div class="feature-icon mb-2">✓</div>
          <h6 class="fw-bold text-dark mb-1">Integridad verificada 100%</h6>
          <p class="small text-secondary mb-0">
            Validador automático por código: tus cifras, porcentajes, monedas e imágenes se preservan intactos.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  max-width: 960px;
  margin: 0 auto;
}

.hero-chip {
  background: var(--pd-brand-soft);
  color: var(--pd-brand);
  font-weight: 600;
  padding: 0.4rem 0.85rem;
}

.dropzone {
  cursor: pointer;
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
  transition: all 0.2s ease;
}

.dropzone:hover {
  border-color: var(--pd-brand);
  background: var(--pd-brand-soft);
}

.dropzone--drag {
  border-color: var(--pd-brand);
  background: var(--pd-brand-soft);
  transform: scale(1.005);
}

.dropzone--ready {
  border-color: #16a34a;
  background: #f0fdf4;
}

.dropzone--error {
  border-color: #dc2626;
  background: #fef2f2;
}

.icon-circle {
  width: 68px;
  height: 68px;
}

.icon-circle--brand {
  background: var(--pd-brand-soft);
  color: var(--pd-brand);
}

.feature-icon {
  width: 34px;
  height: 34px;
  border-radius: 0.6rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--pd-brand-soft);
  color: var(--pd-brand);
  font-weight: 700;
}
</style>
