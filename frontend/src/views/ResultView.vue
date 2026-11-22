<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { formatDocument, downloadUrl, getDocument, getPresets } from '@/services/api'
import FlowStepper from '@/components/FlowStepper.vue'
import { getDocumentTheme, defaultThemeForPreset, recordHistoryItem } from '@/constants/documentThemes'

// ─── Router & Store ───────────────────────────────────────────────────────────
const router = useRouter()
const flowStore = useFlowStore()

// ─── Local UI state ───────────────────────────────────────────────────────────
// 'processing' | 'done' | 'error'
const status = ref<'processing' | 'done' | 'error'>('processing')
const localError = ref<{ code: string; message: string } | null>(null)

// Datos frescos del backend y catálogo de plantillas para el resumen final.
const documentData = ref<any>(null)
const presetNames = ref<Record<string, string>>({})

// ─── Helpers ──────────────────────────────────────────────────────────────────
function numericOr(value: unknown, fallback: number): number {
  if (value === null || value === undefined || value === '') return fallback
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function configValue(key: string): unknown {
  return (
    flowStore.config?.[key] ??
    documentData.value?.config?.[key] ??
    flowStore.result?.config?.[key] ??
    flowStore.result?.[key]
  )
}

function humanizePresetId(id: string): string {
  const known: Record<string, string> = { apa7: 'APA 7' }
  return (
    known[id.toLowerCase()] ||
    id.replace(/[-_]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  )
}

function docId(): number | null {
  return flowStore.result?.document_id ?? flowStore.document?.document_id ?? null
}

function getDownloadUrl(): string {
  const id = docId()
  return id !== null ? downloadUrl(id) : '#'
}

function marginLabel(): string {
  const m = flowStore.config?.margins_cm
  if (!m) return '—'
  if (m.top === m.bottom && m.top === m.left && m.top === m.right) {
    return `${m.top} cm (todos)`
  }
  return `↑${m.top} ↓${m.bottom} ←${m.left} →${m.right} cm`
}

// ─── Resumen de estructuración (ai_summary) ──────────────────────────────────
const usedAi = computed<boolean>(() => {
  const raw = configValue('use_ai') ?? documentData.value?.use_ai ?? flowStore.result?.use_ai
  return raw === true || raw === 'true' || raw === 1
})

/** ai_summary del backend; se acepta también desde el store como respaldo. */
const aiSummary = computed<Record<string, any> | null>(() => {
  const candidate =
    documentData.value?.ai_summary ??
    flowStore.result?.ai_summary ??
    flowStore.document?.ai_summary ??
    null
  return candidate && typeof candidate === 'object' ? candidate : null
})

/**
 * El contrato no expone un total único: se calcula a partir de los bloques
 * estructurales detectados, salvo que el backend envíe un contador explícito.
 */
const restructuredBlocks = computed<number>(() => {
  const summary = aiSummary.value
  const reviewSummary = flowStore.result?.summary
  if ((!summary && !reviewSummary) || !usedAi.value) return 0

  const explicit = numericOr(
    summary?.restructured_blocks_count ??
      summary?.blocks_restructured ??
      summary?.structured_blocks_count,
    NaN
  )
  if (!Number.isNaN(explicit)) return explicit

  const headings = numericOr(
    summary?.headings_applied ?? reviewSummary?.headings_applied ?? summary?.headings_detected,
    0
  )
  const lists = numericOr(
    summary?.lists_applied ?? reviewSummary?.lists_applied ?? summary?.lists_detected,
    0
  )
  const tables = numericOr(
    summary?.tables_applied ?? reviewSummary?.tables_applied ?? summary?.tables_detected,
    0
  )
  return headings + lists + tables
})

const revertedBlocks = computed<number>(() => {
  const explicit = aiSummary.value
    ? numericOr(aiSummary.value.reverted_blocks_count, NaN)
    : NaN
  if (!Number.isNaN(explicit)) return explicit
  // La respuesta de /review/ entrega este dato fuera de ai_summary.
  return numericOr(flowStore.result?.summary?.reverted_blocks_count, 0)
})

const templateName = computed<string>(() => {
  const explicitName =
    configValue('preset_name') ?? configValue('template_name') ?? documentData.value?.template_name
  if (explicitName) return String(explicitName)

  const id = String(
    configValue('preset_id') ?? configValue('template_id') ?? documentData.value?.preset_id ?? ''
  )
  if (!id) return '—'
  return presetNames.value[id] || humanizePresetId(id)
})

const aiBreakdown = computed(() => {
  const summary = aiSummary.value || {}
  const reviewSummary = flowStore.result?.summary || {}
  return {
    headings: numericOr(
      summary.headings_applied ?? reviewSummary.headings_applied ?? summary.headings_detected,
      0
    ),
    lists: numericOr(
      summary.lists_applied ?? reviewSummary.lists_applied ?? summary.lists_detected,
      0
    ),
    tables: numericOr(
      summary.tables_applied ?? reviewSummary.tables_applied ?? summary.tables_detected,
      0
    ),
    bold: numericOr(summary.bold_emphasis_applied, 0),
    fallbackOnly: Boolean(summary.fallback_only ?? false)
  }
})

const activeDocTheme = computed(() => {
  const themeId =
    configValue('color_theme') ??
    defaultThemeForPreset(String(configValue('preset_id') ?? ''))
  return getDocumentTheme(String(themeId))
})

async function loadSummaryData(id: number): Promise<void> {
  const [documentResult, presetsResult] = await Promise.allSettled([
    getDocument(id),
    getPresets()
  ])

  if (documentResult.status === 'fulfilled' && documentResult.value) {
    documentData.value = documentResult.value
  }
  if (presetsResult.status === 'fulfilled' && Array.isArray(presetsResult.value)) {
    presetNames.value = presetsResult.value.reduce<Record<string, string>>((names, preset) => {
      if (preset?.id && preset?.name) names[String(preset.id)] = String(preset.name)
      return names
    }, {})
  }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  // Guard: store vacío (recarga de página) → redirigir a /
  if (!flowStore.document || !flowStore.config) {
    router.replace('/')
    return
  }

  // Si ConfigView / ProcessingView / ReviewView ya guardaron el resultado, no repetir
  if (!flowStore.result) {
    // Ruta de seguridad: llamar formatDocument desde aquí si faltan datos
    status.value = 'processing'
    try {
      const resultData = await formatDocument(
        flowStore.document.document_id,
        flowStore.config
      )
      flowStore.setResult(resultData)
    } catch (err: any) {
      localError.value = {
        code: err.code || 'ERR_UNKNOWN',
        message: err.message || 'Ocurrió un error inesperado al formatear el documento.'
      }
      flowStore.setError(localError.value)
      status.value = 'error'
      return
    }
  }

  status.value = 'done'

  // Leer ai_summary y la plantilla directamente del backend. Este bloque es
  // informativo: si falla, la vista y la descarga siguen funcionando igual.
  const id = docId()
  if (id !== null) {
    try {
      await loadSummaryData(id)
    } catch {
      // Intencionalmente silencioso.
    }
    recordHistoryItem({
      document_id: id,
      original_name:
        documentData.value?.original_name ||
        flowStore.document?.original_name ||
        flowStore.file?.name ||
        `Documento #${id}`,
      size_bytes: documentData.value?.size_bytes ?? flowStore.document?.size_bytes ?? flowStore.file?.size ?? 0,
      preset_name: templateName.value,
      color_theme: activeDocTheme.value.id,
      use_ai: usedAi.value,
      restructured_blocks: restructuredBlocks.value
    })
  }
})

// ─── Actions ──────────────────────────────────────────────────────────────────
/** "Ajustar y reintentar" – vuelve a /config conservando document y config */
function retryWithConfig() {
  flowStore.setResult(null)
  flowStore.setError(null)
  router.push('/config')
}

/** "Formatear otro documento" – limpia el store y vuelve a / */
function formatAnother() {
  flowStore.reset()
  router.push('/')
}
</script>

<template>
  <div class="container-fluid max-w-900 px-0">

    <FlowStepper :current="4" />

    <!-- ═══════════════════════════════════════
         ESTADO: PROCESANDO
    ════════════════════════════════════════ -->
    <div v-if="status === 'processing'" class="card border-0 shadow-sm rounded-4 p-5 text-center">
      <div
        class="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-4 bg-primary-subtle"
        style="width: 80px; height: 80px;"
      >
        <div class="spinner-border text-primary" role="status" style="width: 2.5rem; height: 2.5rem;">
          <span class="visually-hidden">Procesando...</span>
        </div>
      </div>
      <h2 class="fw-bold text-dark mb-2">Aplicando formato…</h2>
      <p class="text-secondary mb-0">
        Estamos procesando tu documento. Esto puede tardar unos segundos.
      </p>
    </div>

    <!-- ═══════════════════════════════════════
         ESTADO: LISTO
    ════════════════════════════════════════ -->
    <template v-else-if="status === 'done'">
      <!-- Success card -->
      <div class="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
        <div
          class="d-flex align-items-center justify-content-center bg-success-subtle text-success rounded-circle mx-auto mb-4"
          style="width: 80px; height: 80px;"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 16 16">
            <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
          </svg>
        </div>

        <h2 class="fw-bold text-dark mb-2">¡Documento listo!</h2>
        <p class="text-secondary mb-4">
          Tu documento ha sido formateado exitosamente y está listo para descargar.
        </p>

        <!-- Botón Descargar: enlace nativo a downloadUrl(id) -->
        <div class="d-flex justify-content-center mb-4">
          <a
            id="btn-download"
            :href="getDownloadUrl()"
            class="btn btn-success btn-lg px-5 py-3 rounded-3 shadow-sm"
            download
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="me-2 mb-1" viewBox="0 0 16 16">
              <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
              <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
            </svg>
            Descargar
          </a>
        </div>

        <!-- Botones de acción -->
        <div class="d-flex justify-content-center gap-3 flex-wrap">
          <button
            id="btn-retry-config"
            class="btn btn-outline-secondary px-4"
            @click="retryWithConfig"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-sliders me-1" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M11.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM9.05 3a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0V3h9.05zM4.5 7a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM2.05 8a2.5 2.5 0 0 1 4.9 0H16v1H6.95a2.5 2.5 0 0 1-4.9 0H0V8h2.05zm9.45 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-2.45 1a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0v-1h9.05z"/>
            </svg>
            Ajustar y reintentar
          </button>

          <button
            id="btn-format-another"
            class="btn btn-outline-primary px-4"
            @click="formatAnother"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-file-earmark-plus me-1" viewBox="0 0 16 16">
              <path d="M8 6.5a.5.5 0 0 1 .5.5v1.5H10a.5.5 0 0 1 0 1H8.5V11a.5.5 0 0 1-1 0V9.5H6a.5.5 0 0 1 0-1h1.5V7a.5.5 0 0 1 .5-.5z"/>
              <path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z"/>
            </svg>
            Formatear otro documento
          </button>
        </div>
      </div>

      <!-- Tarjeta: resumen de cambios estructurales (ai_summary) -->
      <div class="card border-0 shadow-sm rounded-4 p-4 mb-4" data-test="ai-summary-card">
        <h5 class="fw-semibold text-dark mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-clipboard-check me-2 text-primary" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0z"/>
            <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
            <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
          </svg>
          Resumen de cambios
        </h5>

        <div class="row g-3">
          <div class="col-12">
            <div class="config-item p-3 rounded-3 bg-light h-100 d-flex flex-wrap align-items-center justify-content-between gap-2">
              <div>
                <div class="text-uppercase text-secondary small fw-semibold mb-1 letter-spacing">Plantilla aplicada</div>
                <div class="fw-medium text-dark" data-stat="template-name">{{ templateName }}</div>
              </div>
              <span
                class="badge rounded-pill px-3 py-2 border"
                :style="{ backgroundColor: activeDocTheme.headerFill, color: activeDocTheme.primary }"
              >
                Paleta: {{ activeDocTheme.name }}
              </span>
            </div>
          </div>

          <template v-if="usedAi">
            <div class="col-sm-6">
              <div class="config-item p-3 rounded-3 bg-primary-subtle border border-primary-subtle h-100">
                <div class="text-uppercase text-primary small fw-semibold mb-1 letter-spacing">Bloques reestructurados</div>
                <div class="summary-number fw-bold text-dark" data-stat="restructured-blocks">
                  {{ restructuredBlocks }}
                </div>
                <div class="small text-secondary">Títulos, listas y tablas detectados por la IA</div>
              </div>
            </div>

            <div class="col-sm-6">
              <div class="config-item p-3 rounded-3 bg-primary-subtle border border-primary-subtle h-100">
                <div class="text-uppercase text-primary small fw-semibold mb-1 letter-spacing">Bloques revertidos</div>
                <div class="summary-number fw-bold text-dark" data-stat="reverted-blocks">
                  {{ revertedBlocks }}
                </div>
                <div class="small text-secondary">Bloques que conservaron su formato original</div>
              </div>
            </div>

            <div v-if="aiSummary" class="col-12">
              <div class="config-item p-3 rounded-3 bg-light h-100">
                <div class="text-uppercase text-secondary small fw-semibold mb-2 letter-spacing">Detalle de la estructuración</div>
                <div class="d-flex flex-wrap gap-3 small">
                  <span>Títulos: <strong>{{ aiBreakdown.headings }}</strong></span>
                  <span>Listas: <strong>{{ aiBreakdown.lists }}</strong></span>
                  <span>Tablas: <strong>{{ aiBreakdown.tables }}</strong></span>
                  <span>Negritas: <strong>{{ aiBreakdown.bold }}</strong></span>
                </div>
                <div v-if="aiBreakdown.fallbackOnly" class="small text-warning-emphasis mt-2">
                  Todo el documento usó respaldo heurístico.
                </div>
              </div>
            </div>
            <div v-else class="col-12">
              <div class="config-item p-3 rounded-3 bg-light h-100 small text-secondary">
                El backend no devolvió métricas de IA para este documento.
              </div>
            </div>
          </template>

          <div v-else class="col-12">
            <div class="config-item p-3 rounded-3 bg-light h-100">
              <div class="text-uppercase text-secondary small fw-semibold mb-1 letter-spacing">Estructuración con IA</div>
              <div class="fw-medium text-dark">No utilizada · se aplicó únicamente la plantilla</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tarjeta: resumen de configuración aplicada -->
      <div class="card border-0 shadow-sm rounded-4 p-4">
        <h5 class="fw-semibold text-dark mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-list-check me-2 text-primary" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M5 11.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zM3.854 2.146a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0l-.5-.5a.5.5 0 1 1 .708-.708L2 3.293l1.146-1.147a.5.5 0 0 1 .708 0zm0 4a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0l-.5-.5a.5.5 0 1 1 .708-.708L2 7.293l1.146-1.147a.5.5 0 0 1 .708 0zm0 4a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0l-.5-.5a.5.5 0 1 1 .708-.708L2 11.293l1.146-1.147a.5.5 0 0 1 .708 0z"/>
          </svg>
          Configuración aplicada
        </h5>
        <div class="row g-3">
          <div class="col-sm-6">
            <div class="config-item p-3 rounded-3 bg-light h-100">
              <div class="text-uppercase text-secondary small fw-semibold mb-1 letter-spacing">Margenes</div>
              <div class="fw-medium text-dark">{{ marginLabel() }}</div>
            </div>
          </div>
          <div class="col-sm-6">
            <div class="config-item p-3 rounded-3 bg-light h-100">
              <div class="text-uppercase text-secondary small fw-semibold mb-1 letter-spacing">Fuente</div>
              <div class="fw-medium text-dark">{{ flowStore.config?.font_family || '—' }}</div>
            </div>
          </div>
          <div class="col-sm-6">
            <div class="config-item p-3 rounded-3 bg-light h-100">
              <div class="text-uppercase text-secondary small fw-semibold mb-1 letter-spacing">Tamaño</div>
              <div class="fw-medium text-dark">
                {{ flowStore.config?.font_size_pt != null ? `${flowStore.config.font_size_pt} pt` : '—' }}
              </div>
            </div>
          </div>
          <div class="col-sm-6">
            <div class="config-item p-3 rounded-3 bg-light h-100">
              <div class="text-uppercase text-secondary small fw-semibold mb-1 letter-spacing">Interlineado</div>
              <div class="fw-medium text-dark">
                {{ flowStore.config?.line_spacing != null ? `× ${flowStore.config.line_spacing}` : '—' }}
              </div>
            </div>
          </div>
          <div v-if="usedAi" class="col-12">
            <div class="config-item p-3 rounded-3 bg-primary-subtle border border-primary-subtle h-100">
              <div class="text-uppercase text-primary small fw-semibold mb-1 letter-spacing">Estructuración con IA</div>
              <div class="fw-medium text-dark">
                Activada · Tipo: <span class="text-capitalize">{{ flowStore.config.document_type || flowStore.config.ai_options?.document_type || 'General' }}</span>
                · Énfasis: <span class="text-capitalize">{{ flowStore.config.emphasis || flowStore.config.ai_options?.emphasis || 'Ligero' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ═══════════════════════════════════════
         ESTADO: ERROR
    ════════════════════════════════════════ -->
    <div v-else-if="status === 'error'" class="card border-0 shadow-sm rounded-4 p-5 text-center">
      <div
        class="d-flex align-items-center justify-content-center bg-danger-subtle text-danger rounded-circle mx-auto mb-4"
        style="width: 80px; height: 80px;"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 16 16">
          <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
        </svg>
      </div>

      <h2 class="fw-bold text-dark mb-2">Error al formatear</h2>

      <div
        id="result-error-alert"
        class="alert alert-danger text-start mx-auto mb-4"
        role="alert"
        style="max-width: 520px;"
      >
        <div class="fw-semibold mb-1">
          {{ localError?.code || flowStore.error?.code || 'ERR_UNKNOWN' }}
        </div>
        <div>
          {{ localError?.message || flowStore.error?.message || 'Ocurrió un error inesperado.' }}
        </div>
      </div>

      <div class="d-flex justify-content-center gap-3 flex-wrap">
        <button
          id="btn-retry-config-error"
          class="btn btn-primary btn-lg px-5"
          @click="retryWithConfig"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-sliders me-2" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M11.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM9.05 3a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0V3h9.05zM4.5 7a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM2.05 8a2.5 2.5 0 0 1 4.9 0H16v1H6.95a2.5 2.5 0 0 1-4.9 0H0V8h2.05zm9.45 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-2.45 1a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0v-1h9.05z"/>
          </svg>
          Ajustar y reintentar
        </button>

        <button
          id="btn-format-another-error"
          class="btn btn-outline-secondary px-4"
          @click="formatAnother"
        >
          Formatear otro documento
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.letter-spacing {
  letter-spacing: 0.05em;
}
.summary-number {
  font-size: 2rem;
  line-height: 1.1;
}
.config-item {
  border: 1px solid var(--bs-border-color);
  transition: box-shadow 0.15s ease;
}
.config-item:hover {
  box-shadow: 0 0 0 2px rgba(var(--bs-primary-rgb), 0.15);
}
</style>
