<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { downloadUrl } from '@/services/api'
import { getDocumentTheme, loadHistoryItems } from '@/constants/documentThemes'

interface StoredHistoryItem {
  document_id: number
  original_name: string
  size_bytes?: number
  preset_name?: string
  color_theme?: string
  use_ai?: boolean
  restructured_blocks?: number
  updated_at?: string
}

const router = useRouter()
const history = ref<StoredHistoryItem[]>([])

function load() {
  history.value = loadHistoryItems()
}

function clearHistory() {
  localStorage.removeItem('prettydocs_history_v1')
  history.value = []
}

function formatSize(bytes?: number) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDate(iso?: string) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return iso
  }
}

function themeOf(id?: string) {
  return getDocumentTheme(id)
}

onMounted(load)
</script>

<template>
  <div class="container-fluid history-container px-0">
    <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-4">
      <div>
        <h2 class="fw-bold text-dark mb-1">Historial de documentos</h2>
        <p class="text-secondary mb-0">
          Documentos formateados recientemente en esta sesión, listos para volver a descargar.
        </p>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-sm pd-btn-brand px-3" @click="router.push('/')">
          + Nuevo documento
        </button>
        <button
          v-if="history.length > 0"
          class="btn btn-sm btn-outline-secondary"
          @click="clearHistory"
        >
          Limpiar lista
        </button>
      </div>
    </div>

    <div v-if="history.length === 0" class="card pd-card text-center p-5 text-secondary">
      <div class="fs-2 mb-2">📄</div>
      <h5 class="fw-semibold text-dark mb-1">Aún no hay documentos en tu historial</h5>
      <p class="small mb-3">
        Cuando completes el formateo de un archivo Word, aparecerá aquí con su enlace directo de descarga.
      </p>
      <div>
        <button class="btn pd-btn-brand px-4" @click="router.push('/')">
          Subir primer documento
        </button>
      </div>
    </div>

    <div v-else class="d-flex flex-column gap-3">
      <div
        v-for="item in history"
        :key="item.document_id"
        class="card pd-card"
      >
        <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-3">
          <div class="d-flex align-items-center gap-3 min-w-0">
            <div
              class="doc-icon d-flex align-items-center justify-content-center rounded-3 flex-shrink-0"
              :style="{
                backgroundColor: themeOf(item.color_theme).headerFill,
                color: themeOf(item.color_theme).primary
              }"
            >
              DOCX
            </div>
            <div class="min-w-0">
              <div class="fw-bold text-dark text-truncate">{{ item.original_name }}</div>
              <div class="text-secondary small">
                #{{ item.document_id }} · {{ formatSize(item.size_bytes) }} · {{ formatDate(item.updated_at) }}
              </div>
            </div>
          </div>

          <div class="d-flex flex-wrap align-items-center gap-2">
            <span v-if="item.preset_name" class="badge rounded-pill text-bg-light border text-dark">
              {{ item.preset_name }}
            </span>
            <span
              class="badge rounded-pill border"
              :style="{
                backgroundColor: themeOf(item.color_theme).headerFill,
                color: themeOf(item.color_theme).primary
              }"
            >
              {{ themeOf(item.color_theme).name }}
            </span>
            <span v-if="item.use_ai" class="badge rounded-pill bg-primary-subtle text-primary border border-primary-subtle">
              IA · {{ item.restructured_blocks ?? 0 }} bloques
            </span>
            <a
              :href="downloadUrl(item.document_id)"
              class="btn btn-sm btn-success px-3"
              download
            >
              Descargar .docx
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-container {
  max-width: 960px;
  margin: 0 auto;
}

.doc-icon {
  width: 48px;
  height: 44px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}
</style>
