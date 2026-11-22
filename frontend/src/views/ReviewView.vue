<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getDocument, getStructure, submitReview } from '@/services/api'
import ReviewBlock from '@/components/review/ReviewBlock.vue'
import FlowStepper from '@/components/FlowStepper.vue'
import { getDocumentTheme, defaultThemeForPreset } from '@/constants/documentThemes'
import {
  blockPlainText,
  blockSources,
  countBlocksByType,
  countBoldRuns,
  isOrderedList,
  originalTypeLabel
} from '@/components/review/reviewUtils'

// ─── Router & store ──────────────────────────────────────────────────────────
const route = useRoute()
const router = useRouter()
const flowStore = useFlowStore()

const documentId = computed<number | null>(() => {
  const raw = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
})

// ─── Local state ─────────────────────────────────────────────────────────────
interface ReviewError {
  code: string
  message: string
  details?: Record<string, unknown>
}

type SubmittingAction = '' | 'accept' | 'reject'

interface ListUnit {
  kind: 'list'
  key: string
  ordered: boolean
  items: any[]
}

interface BlockUnit {
  kind: 'block'
  key: string
  block: any
}

type RenderUnit = ListUnit | BlockUnit

const structure = ref<any>(null)
const documentData = ref<any>(null)
const isLoading = ref(true)
const loadError = ref<ReviewError | null>(null)
const actionError = ref<ReviewError | null>(null)
const submittingAction = ref<SubmittingAction>('')
const revertIds = ref<string[]>([])

// ─── Derived document data ───────────────────────────────────────────────────
const documentName = computed(
  () =>
    documentData.value?.original_name ||
    flowStore.document?.original_name ||
    `Documento #${documentId.value ?? ''}`
)

const documentStatus = computed(
  () => structure.value?.status || documentData.value?.status || 'review'
)

const originalBlocks = computed<any[]>(() =>
  Array.isArray(structure.value?.original?.blocks) ? structure.value.original.blocks : []
)

const proposedBlocks = computed<any[]>(() =>
  Array.isArray(structure.value?.proposed?.blocks) ? structure.value.proposed.blocks : []
)

function isBlankOrSectionKeep(block: any, origLookup?: Map<string, any>): boolean {
  if (!block || block.type !== 'keep') return false
  const kind =
    block.keep_kind ||
    (origLookup && Array.isArray(block.src) && block.src[0] ? origLookup.get(block.src[0])?.keep_kind : null)
  return kind === 'empty' || kind === 'section_break'
}

const originalById = computed(() => {
  const map = new Map<string, any>()
  for (const block of originalBlocks.value) {
    if (block && typeof block.id === 'string') map.set(block.id, block)
  }
  return map
})

const visibleOriginalBlocks = computed<any[]>(() =>
  originalBlocks.value.filter((block) => !isBlankOrSectionKeep(block))
)

const normalizedBlankCount = computed<number>(() =>
  originalBlocks.value.filter((block) => block?.type === 'keep' && block?.keep_kind === 'empty').length
)

const activeDocTheme = computed(() => {
  const cfg = flowStore.config || documentData.value?.config || {}
  const themeId = cfg.color_theme || defaultThemeForPreset(cfg.preset_id)
  return getDocumentTheme(themeId)
})

const proposedThemeStyle = computed(() => {
  const cfg = flowStore.config || documentData.value?.config || {}
  const t = activeDocTheme.value
  const useDividers = cfg.show_dividers !== false && cfg.preset_id !== 'apa7'
  return {
    '--doc-primary': t.primary,
    '--doc-secondary': t.secondary,
    '--doc-divider': useDividers ? t.secondary : 'transparent',
    '--doc-header-fill': t.headerFill,
    '--doc-zebra-fill': t.zebraFill,
    '--doc-callout-fill': t.calloutFill,
    fontFamily: cfg.font_family ? `'${cfg.font_family}', sans-serif` : undefined
  }
})

const revertibleIds = computed(() => {
  const fromSummary = structure.value?.summary?.revertible_blocks
  if (Array.isArray(fromSummary) && fromSummary.length > 0) {
    return new Set<string>(
      fromSummary.filter((id: unknown): id is string => typeof id === 'string')
    )
  }

  // Fallback for older payloads that do not expose summary.revertible_blocks.
  const all = new Set<string>()
  for (const block of proposedBlocks.value) {
    for (const id of blockSources(block)) all.add(id)
  }
  return all
})

const revertIdSet = computed(() => new Set(revertIds.value))

const revertedBlockCount = computed(
  () => proposedBlocks.value.filter((block) => isReverted(block)).length
)

const isBusy = computed(() => submittingAction.value !== '')
const isReady = computed(
  () => !isLoading.value && loadError.value === null && !isBusy.value
)
// Accepting an empty proposal makes no sense, but rejecting it must always be
// possible: that is exactly the "solo plantilla" escape hatch.
const canAccept = computed(() => isReady.value && proposedBlocks.value.length > 0)
const canReject = isReady

// ─── Summary ─────────────────────────────────────────────────────────────────
function numericOr(value: unknown, fallback: number): number {
  if (value === null || value === undefined || value === '') return fallback
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const summaryStats = computed(() => {
  const summary = structure.value?.summary || {}
  const aiSummary = documentData.value?.ai_summary || {}

  return {
    headings: numericOr(
      summary.headings_detected,
      countBlocksByType(proposedBlocks.value, 'heading')
    ),
    lists: numericOr(
      summary.lists_detected,
      countBlocksByType(proposedBlocks.value, 'list_item')
    ),
    tables: numericOr(
      summary.tables_detected,
      countBlocksByType(proposedBlocks.value, 'table')
    ),
    bold: numericOr(
      summary.bold_emphasis_applied,
      countBoldRuns(proposedBlocks.value)
    ),
    fallbackChunks: numericOr(
      summary.chunks_fallback,
      numericOr(aiSummary.chunks_fallback, 0)
    ),
    totalChunks: numericOr(
      summary.chunks_total,
      numericOr(aiSummary.chunks_total, 0)
    ),
    fallbackOnly: Boolean(summary.fallback_only ?? aiSummary.fallback_only ?? false)
  }
})

const fallbackText = computed(() => {
  const { fallbackChunks, totalChunks, fallbackOnly } = summaryStats.value
  if (fallbackOnly) return 'Todo el documento usó respaldo heurístico'
  if (fallbackChunks <= 0) return 'Ningún fragmento usó respaldo heurístico'
  if (totalChunks > 0) {
    return `${fallbackChunks} de ${totalChunks} fragmentos usaron respaldo heurístico`
  }
  return `${fallbackChunks} fragmento(s) usaron respaldo heurístico`
})

// ─── Revert helpers ──────────────────────────────────────────────────────────
function isReverted(block: any): boolean {
  const src = blockSources(block)
  return src.length > 0 && src.every((id) => revertIdSet.value.has(id))
}

function canRevert(block: any): boolean {
  if (!block || block.type === 'keep' || block.type === 'image') return false
  const src = blockSources(block)
  return src.length > 0 && src.every((id) => revertibleIds.value.has(id))
}

function toggleRevert(block: any): void {
  const src = blockSources(block)
  if (src.length === 0) return

  const allReverted = src.every((id) => revertIdSet.value.has(id))

  if (allReverted) {
    revertIds.value = revertIds.value.filter((id) => !src.includes(id))
    return
  }

  const next = new Set(revertIds.value)
  src.forEach((id) => next.add(id))
  revertIds.value = Array.from(next)
}

function clearReverts(): void {
  revertIds.value = []
}

function originalFor(block: any): any[] {
  return blockSources(block)
    .map((id) => originalById.value.get(id))
    .filter(Boolean)
}

// ─── Proposed blocks grouped into semantic lists ─────────────────────────────
const renderUnits = computed<RenderUnit[]>(() => {
  const units: RenderUnit[] = []
  let currentList: ListUnit | null = null

  const flush = () => {
    if (currentList) {
      units.push(currentList)
      currentList = null
    }
  }

  proposedBlocks.value.forEach((block, index) => {
    if (!block || typeof block !== 'object') return
    if (isBlankOrSectionKeep(block, originalById.value)) return

    if (block.type === 'list_item' && !isReverted(block)) {
      const ordered = isOrderedList(block)

      if (!currentList || currentList.ordered !== ordered) {
        flush()
        currentList = {
          kind: 'list',
          key: `list-${block.id ?? index}`,
          ordered,
          items: []
        }
      }

      currentList.items.push(block)
      return
    }

    flush()
    units.push({
      kind: 'block',
      key: `block-${block.id ?? index}`,
      block
    })
  })

  flush()
  return units
})

// ─── Loading ─────────────────────────────────────────────────────────────────
function applyDocument(data: any): void {
  if (!data) return

  documentData.value = data
  flowStore.setDocument({
    document_id: data.document_id || documentId.value,
    original_name: data.original_name,
    size_bytes: data.size_bytes,
    uploaded_at: data.uploaded_at,
    status: data.status
  })

  if (data.config && typeof data.config === 'object' && Object.keys(data.config).length > 0) {
    flowStore.setConfig(data.config)
  }
}

function ensureFlowContext(): void {
  if (!flowStore.document) {
    flowStore.setDocument({
      document_id: documentId.value,
      original_name: `Documento #${documentId.value ?? ''}`,
      status: 'review'
    })
  }

  if (!flowStore.config) {
    flowStore.setConfig({ use_ai: true })
  }
}

async function loadReview(): Promise<void> {
  isLoading.value = true
  loadError.value = null
  actionError.value = null
  revertIds.value = []
  structure.value = null
  documentData.value = null

  if (!documentId.value) {
    loadError.value = {
      code: 'NOT_FOUND',
      message: 'El identificador del documento no es válido.'
    }
    isLoading.value = false
    return
  }

  const [structureResult, documentResult] = await Promise.allSettled([
    getStructure(documentId.value),
    getDocument(documentId.value)
  ])

  if (documentResult.status === 'fulfilled') {
    applyDocument(documentResult.value)
  }

  if (structureResult.status === 'rejected') {
    const error: any = structureResult.reason || {}
    loadError.value = {
      code: error.code || 'ERR_UNKNOWN',
      message: error.message || 'No se pudo cargar la estructura propuesta por la IA.',
      details: error.details
    }
    ensureFlowContext()
    isLoading.value = false
    return
  }

  structure.value = structureResult.value
  ensureFlowContext()
  isLoading.value = false
}

onMounted(loadReview)

// ─── Review actions ──────────────────────────────────────────────────────────
async function submit(action: 'accept' | 'reject'): Promise<void> {
  if (!documentId.value || isBusy.value) return
  if (action === 'accept' && proposedBlocks.value.length === 0) return

  actionError.value = null
  submittingAction.value = action

  const payload =
    action === 'accept'
      ? { action: 'accept' as const, revert: [...revertIds.value] }
      : { action: 'reject' as const }

  try {
    const result = await submitReview(documentId.value, payload)

    flowStore.setResult({
      ...result,
      document_id: result?.document_id ?? documentId.value
    })

    if (flowStore.document) {
      flowStore.setDocument({
        ...flowStore.document,
        status: result?.status || 'done'
      })
    } else {
      flowStore.setDocument({
        document_id: documentId.value,
        original_name: documentName.value,
        status: result?.status || 'done'
      })
    }

    if (!flowStore.config) {
      flowStore.setConfig({ use_ai: true })
    }

    if (result?.status === 'processing') {
      router.push(`/processing/${documentId.value}`)
    } else {
      router.push('/result')
    }
  } catch (error: any) {
    actionError.value = {
      code: error?.code || 'ERR_UNKNOWN',
      message: error?.message || 'No se pudo confirmar la revisión.'
    }
  } finally {
    submittingAction.value = ''
  }
}

function acceptProposal(): void {
  void submit('accept')
}

function rejectProposal(): void {
  void submit('reject')
}

function clearActionError(): void {
  actionError.value = null
}

// ─── Navigation ──────────────────────────────────────────────────────────────
function goToProcessing(): void {
  if (documentId.value) router.push(`/processing/${documentId.value}`)
}

function goToConfig(): void {
  router.push('/config')
}

function goHome(): void {
  router.push('/')
}
</script>

<template>
  <div class="container-fluid px-0 review-view">
    <FlowStepper :current="3" />

    <!-- Active document banner -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-body d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-2">
        <div class="min-w-0">
          <span class="badge text-bg-primary me-2">Documento activo</span>
          <strong class="fs-5 text-dark text-break">{{ documentName }}</strong>
          <span v-if="documentId" class="text-secondary small ms-2">#{{ documentId }}</span>
        </div>
        <span class="badge bg-info-subtle text-info-emphasis border border-info-subtle px-3 py-2 align-self-start">
          Estado: {{ documentStatus }}
        </span>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="card border-0 shadow-sm rounded-4 p-5 text-center" role="status">
      <div class="spinner-border text-primary mx-auto mb-3" aria-hidden="true"></div>
      <p class="text-secondary mb-0">Cargando la estructura propuesta por la IA…</p>
    </div>

    <!-- Structure loading error -->
    <div v-else-if="loadError" class="card border-0 shadow-sm rounded-4 p-5 text-center">
      <div
        class="d-flex align-items-center justify-content-center bg-danger-subtle text-danger rounded-circle mx-auto mb-4"
        style="width: 80px; height: 80px"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z" />
        </svg>
      </div>

      <h2 class="fw-bold text-dark mb-2">No se pudo cargar la revisión</h2>

      <div class="alert alert-danger text-start mx-auto mb-4" role="alert" style="max-width: 640px">
        <div class="d-flex align-items-center gap-2 mb-1">
          <span class="badge text-bg-danger">{{ loadError.code }}</span>
          <strong class="text-danger-emphasis">Error al consultar la estructura</strong>
        </div>
        <p class="mb-0">{{ loadError.message }}</p>
        <p v-if="loadError.code === 'INVALID_STATE'" class="small mb-0 mt-2">
          El documento debe encontrarse en estado <strong>review</strong>. Si el procesamiento sigue en curso, espera a que termine.
        </p>
      </div>

      <div class="d-flex justify-content-center gap-2 flex-wrap">
        <button id="btn-retry-structure" type="button" class="btn btn-primary px-4" @click="loadReview">
          Reintentar
        </button>
        <button
          v-if="loadError.code === 'INVALID_STATE'"
          type="button"
          class="btn btn-outline-primary px-4"
          @click="goToProcessing"
        >
          Ir a procesamiento
        </button>
        <button type="button" class="btn btn-outline-secondary px-4" @click="goToConfig">
          Volver a configuración
        </button>
        <button type="button" class="btn btn-outline-secondary px-4" @click="goHome">
          Inicio
        </button>
      </div>
    </div>

    <!-- Review content -->
    <template v-else>
      <!-- Summary bar -->
      <div id="review-summary" class="card border-0 shadow-sm rounded-4 p-4 mb-4">
        <div class="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-3">
          <div>
            <h1 class="h4 fw-semibold text-dark mb-1">Revisa la propuesta de estructura</h1>
            <p class="text-secondary small mb-0">
              Compara el texto original con la propuesta. La IA no reescribe el contenido: solo organiza títulos, listas, tablas y énfasis.
            </p>
          </div>
          <span class="badge bg-primary-subtle text-primary-emphasis border border-primary-subtle px-3 py-2 align-self-start">
            {{ proposedBlocks.length }} bloques propuestos
          </span>
        </div>

        <div class="row row-cols-2 row-cols-md-5 g-2">
          <div class="col">
            <div class="summary-stat h-100">
              <span class="summary-value" data-stat="headings">{{ summaryStats.headings }}</span>
              <span class="summary-label">Títulos</span>
            </div>
          </div>
          <div class="col">
            <div class="summary-stat h-100">
              <span class="summary-value" data-stat="lists">{{ summaryStats.lists }}</span>
              <span class="summary-label">Listas</span>
            </div>
          </div>
          <div class="col">
            <div class="summary-stat h-100">
              <span class="summary-value" data-stat="tables">{{ summaryStats.tables }}</span>
              <span class="summary-label">Tablas</span>
            </div>
          </div>
          <div class="col">
            <div class="summary-stat h-100">
              <span class="summary-value" data-stat="bold">{{ summaryStats.bold }}</span>
              <span class="summary-label">Negritas</span>
            </div>
          </div>
          <div class="col">
            <div
              class="summary-stat h-100"
              :class="{ 'summary-stat--warning': summaryStats.fallbackChunks > 0 }"
            >
              <span class="summary-value" data-stat="fallback">{{ summaryStats.fallbackChunks }}</span>
              <span class="summary-label">Respaldo heurístico</span>
            </div>
          </div>
        </div>

        <div class="d-flex flex-wrap align-items-center gap-2 mt-3 pt-3 border-top">
          <span
            class="badge rounded-pill px-3 py-2"
            :class="
              summaryStats.fallbackChunks > 0
                ? 'bg-warning-subtle text-warning-emphasis border border-warning-subtle'
                : 'bg-success-subtle text-success-emphasis border border-success-subtle'
            "
          >
            {{ fallbackText }}
          </span>
          <span v-if="summaryStats.fallbackOnly" class="badge rounded-pill bg-danger-subtle text-danger-emphasis border border-danger-subtle">
            Sin IA efectiva
          </span>
          <span class="small text-secondary">
            {{ visibleOriginalBlocks.length }} bloques de contenido · Paleta: <strong>{{ activeDocTheme.name }}</strong>
          </span>
          <span
            v-if="normalizedBlankCount > 0"
            class="badge rounded-pill text-bg-light border text-secondary"
          >
            {{ normalizedBlankCount }} saltos de línea vacíos normalizados automáticamente
          </span>
        </div>
      </div>

      <!-- Action error -->
      <div v-if="actionError" class="alert alert-danger d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2" role="alert">
        <div>
          <strong>{{ actionError.code }}:</strong> {{ actionError.message }}
        </div>
        <div class="d-flex gap-2">
          <button
            v-if="actionError.code === 'INVALID_STATE'"
            type="button"
            class="btn btn-sm btn-outline-danger"
            @click="goToProcessing"
          >
            Ir a procesamiento
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearActionError">
            Cerrar
          </button>
        </div>
      </div>

      <!-- Two-column comparison -->
      <div class="row g-4 align-items-stretch review-compare">
        <!-- Original text -->
        <div class="col-12 col-lg-6 d-flex">
          <div class="card border-0 shadow-sm rounded-4 w-100 compare-card">
            <div class="card-header bg-white d-flex justify-content-between align-items-start gap-2">
              <div>
                <h2 class="h6 fw-semibold text-dark mb-0">Texto original</h2>
                <span class="text-secondary small">Extraído del documento, sin formato</span>
              </div>
              <span class="badge text-bg-light border text-secondary">{{ visibleOriginalBlocks.length }} bloques</span>
            </div>
            <div class="card-body compare-body original-column" data-column="original" tabindex="0">
              <div
                v-for="(block, index) in visibleOriginalBlocks"
                :key="block?.id || index"
                class="original-block"
                :data-original-id="block?.id"
              >
                <span class="original-kind">{{ originalTypeLabel(block) }}</span>
                <p v-if="blockPlainText(block)" class="original-text">{{ blockPlainText(block) }}</p>
                <p v-else class="original-empty">Sin texto visible</p>
              </div>
              <p v-if="visibleOriginalBlocks.length === 0" class="text-secondary small mb-0">
                El documento no contiene bloques originales para mostrar.
              </p>
            </div>
          </div>
        </div>

        <!-- Structured proposal -->
        <div class="col-12 col-lg-6 d-flex">
          <div class="card border-0 shadow-sm rounded-4 w-100 compare-card">
            <div class="card-header bg-white d-flex justify-content-between align-items-start gap-2">
              <div>
                <h2 class="h6 fw-semibold text-dark mb-0">Propuesta estructurada</h2>
                <span class="text-secondary small">Previsualización con la paleta {{ activeDocTheme.name }}</span>
              </div>
              <span
                class="badge rounded-pill border"
                :style="{ backgroundColor: activeDocTheme.headerFill, color: activeDocTheme.primary }"
              >
                {{ activeDocTheme.name }}
              </span>
            </div>
            <div
              class="card-body compare-body preview-column"
              data-column="proposed"
              tabindex="0"
              :style="proposedThemeStyle"
            >
              <div v-if="proposedBlocks.length === 0" class="alert alert-info mb-0" role="status">
                La IA no propuso bloques para este documento. Puedes descartar la IA y aplicar solo la plantilla.
              </div>

              <template v-for="unit in renderUnits" :key="unit.key">
                <ul v-if="unit.kind === 'list' && !unit.ordered" class="preview-list">
                  <ReviewBlock
                    v-for="block in unit.items"
                    :key="block.id"
                    :block="block"
                    :original-blocks="originalFor(block)"
                    :reverted="isReverted(block)"
                    :can-revert="canRevert(block)"
                    tag="li"
                    @toggle-revert="toggleRevert"
                  />
                </ul>

                <ol v-else-if="unit.kind === 'list' && unit.ordered" class="preview-list">
                  <ReviewBlock
                    v-for="block in unit.items"
                    :key="block.id"
                    :block="block"
                    :original-blocks="originalFor(block)"
                    :reverted="isReverted(block)"
                    :can-revert="canRevert(block)"
                    tag="li"
                    @toggle-revert="toggleRevert"
                  />
                </ol>

                <ReviewBlock
                  v-else
                  :block="unit.block"
                  :original-blocks="originalFor(unit.block)"
                  :reverted="isReverted(unit.block)"
                  :can-revert="canRevert(unit.block)"
                  @toggle-revert="toggleRevert"
                />
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Decision bar -->
      <div class="card border-0 shadow-sm rounded-4 p-4 mt-4 review-actions">
        <div class="d-flex flex-column flex-xl-row justify-content-between align-items-xl-center gap-3">
          <div class="min-w-0">
            <div class="fw-semibold text-dark">
              <span v-if="revertedBlockCount > 0">
                {{ revertedBlockCount }} bloque(s) revertido(s) a su formato original
              </span>
              <span v-else>Se aplicará la estructura propuesta completa</span>
            </div>
            <div class="small text-secondary">
              <template v-if="revertIds.length > 0">
                {{ revertIds.length }} ID(s) de origen se enviarán en <code>revert[]</code>.
                <button type="button" class="btn btn-link btn-sm p-0 ms-1" @click="clearReverts">
                  Restablecer todo
                </button>
              </template>
              <template v-else>
                Puedes revertir bloques individuales antes de continuar.
              </template>
            </div>
          </div>

          <div class="d-flex flex-column flex-sm-row gap-2 flex-shrink-0">
            <button
              type="button"
              class="btn btn-outline-secondary px-4"
              :disabled="isBusy"
              @click="goToConfig"
            >
              Volver a configuración
            </button>

            <button
              id="btn-reject-review"
              type="button"
              class="btn btn-outline-danger px-4"
              :disabled="!canReject"
              @click="rejectProposal"
            >
              <span
                v-if="submittingAction === 'reject'"
                class="spinner-border spinner-border-sm me-2"
                role="status"
                aria-hidden="true"
              ></span>
              Descartar IA, solo plantilla
            </button>

            <button
              id="btn-accept-review"
              type="button"
              class="btn btn-success px-4"
              :disabled="!canAccept"
              @click="acceptProposal"
            >
              <span
                v-if="submittingAction === 'accept'"
                class="spinner-border spinner-border-sm me-2"
                role="status"
                aria-hidden="true"
              ></span>
              Aplicar y generar documento
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.review-view {
  max-width: 1500px;
  margin: 0 auto;
}

.review-stepper {
  row-gap: 0.5rem;
}

.min-w-0 {
  min-width: 0;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--bs-border-color);
  border-radius: 0.75rem;
  background: var(--bs-light);
}

.summary-stat--warning {
  border-color: var(--bs-warning-border-subtle);
  background: var(--bs-warning-bg-subtle);
}

.summary-value {
  display: block;
  color: var(--bs-body-color);
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1.1;
}

.summary-label {
  color: var(--bs-secondary-color);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.compare-card {
  overflow: hidden;
}

.compare-body {
  min-height: 280px;
  padding: 1rem 1.1rem;
}

@media (min-width: 992px) {
  .compare-body {
    max-height: calc(100vh - 360px);
    min-height: 420px;
    overflow-y: auto;
  }
}

/* On phones/tablets both panels stay independently scrollable so a
   100-block document does not turn into an endless page. */
@media (max-width: 991.98px) {
  .compare-body {
    max-height: 60vh;
    overflow-y: auto;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }
}

.original-column {
  background: #fbfcfd;
}

.original-block {
  padding: 0.55rem 0;
  border-bottom: 1px dashed var(--bs-border-color-translucent);
}

.original-block:last-child {
  border-bottom: 0;
}

.original-kind {
  display: block;
  margin-bottom: 0.15rem;
  color: var(--bs-secondary-color);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.original-text {
  margin: 0;
  white-space: pre-line;
  overflow-wrap: anywhere;
  line-height: 1.55;
}

.original-empty {
  margin: 0;
  color: var(--bs-secondary-color);
  font-size: 0.9rem;
  font-style: italic;
}

.preview-column {
  background: #fff;
}

.preview-list {
  margin: 0 0 0.9rem;
  padding-left: 1.5rem;
}

.preview-list:last-child {
  margin-bottom: 0;
}

.preview-list > li {
  margin-bottom: 0.45rem;
}

.preview-list > li::marker {
  color: var(--bs-primary);
  font-weight: 700;
}

.review-actions {
  position: sticky;
  bottom: 1rem;
  z-index: 10;
}

@media (max-width: 1199.98px) {
  .review-actions {
    position: static;
  }
}

@media (max-width: 575.98px) {
  .compare-body {
    padding: 0.85rem;
  }

  .summary-value {
    font-size: 1.3rem;
  }

  .review-stepper {
    justify-content: flex-start !important;
  }

  .review-stepper > .text-muted {
    display: none;
  }

  .review-actions .btn {
    width: 100%;
  }
}
</style>
