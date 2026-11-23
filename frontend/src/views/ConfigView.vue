<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getPresets, formatDocument } from '@/services/api'
import FlowStepper from '@/components/FlowStepper.vue'
import {
  DOCUMENT_THEMES,
  defaultThemeForPreset,
  getDocumentTheme,
  loadUserPrefs
} from '@/constants/documentThemes'

const ALLOWED_FONTS = [
  'Times New Roman',
  'Arial',
  'Calibri',
  'Cambria',
  'Georgia',
  'Verdana'
] as const

type AllowedFont = typeof ALLOWED_FONTS[number]

interface Margins {
  top: number | string
  bottom: number | string
  left: number | string
  right: number | string
}

interface FormState {
  preset_id: string | null
  margins_cm: Margins
  font_family: AllowedFont | string
  font_size_pt: number | string
  line_spacing: number | string
  color_theme: string
  show_dividers: boolean
  alignment: 'justify' | 'left'
  page_numbers: boolean
}

interface Preset {
  id: string
  name: string
  description: string
  config: {
    margins_cm: { top: number; bottom: number; left: number; right: number }
    font_family: string
    font_size_pt: number
    line_spacing: number
    heading_sizes_pt: { h1: number; h2: number; h3: number } | null
    paragraph?: { alignment?: string }
    page_numbers?: boolean
  }
}

const router = useRouter()
const flowStore = useFlowStore()
const userPrefs = loadUserPrefs()

const presets = ref<Preset[]>([])
const isLoadingPresets = ref(true)
const isSubmitting = ref(false)
const showAdvancedMetrics = ref(false)

const form = reactive<FormState>({
  preset_id: null,
  margins_cm: { top: 2.5, bottom: 2.5, left: 2.5, right: 2.5 },
  font_family: 'Calibri',
  font_size_pt: 11,
  line_spacing: 1.15,
  color_theme: userPrefs.defaultTheme || 'azul_ejecutivo',
  show_dividers: userPrefs.showDividers ?? true,
  alignment: 'justify',
  page_numbers: true
})

interface AiFormState {
  enabled: boolean
  document_type: string
  detect_titles: boolean
  detect_lists: boolean
  detect_tables: boolean
  creative_structure: boolean
  emphasis: 'ninguno' | 'ligero' | 'medio'
  accepted_disclaimer: boolean
}

const aiForm = reactive<AiFormState>({
  enabled: true,
  document_type: 'reporte',
  detect_titles: true,
  detect_lists: true,
  detect_tables: true,
  creative_structure: true,
  emphasis: (userPrefs.defaultEmphasis as AiFormState['emphasis']) || 'medio',
  accepted_disclaimer: false
})

const presetSnapshot = reactive({
  margins_cm: { top: 2.5, bottom: 2.5, left: 2.5, right: 2.5 },
  font_family: 'Calibri',
  font_size_pt: 11,
  line_spacing: 1.15,
  color_theme: 'azul_ejecutivo',
  show_dividers: true,
  alignment: 'justify' as 'justify' | 'left',
  page_numbers: true
})

const activeTheme = computed(() => getDocumentTheme(form.color_theme))

function isValidMargin(val: number | string): boolean {
  const n = Number(val)
  return !isNaN(n) && n >= 0.5 && n <= 5.0
}

function isValidFontSize(val: number | string): boolean {
  const n = Number(val)
  return !isNaN(n) && n >= 8 && n <= 24 && (n * 2) % 1 === 0
}

function isValidLineSpacing(val: number | string): boolean {
  const n = Number(val)
  return !isNaN(n) && n >= 1.0 && n <= 3.0
}

function isValidFont(val: string): boolean {
  return (ALLOWED_FONTS as readonly string[]).includes(val)
}

const errors = computed(() => {
  const e: Record<string, string> = {}

  if (!isValidMargin(form.margins_cm.top)) e['margins_top'] = 'Entre 0.5 y 5.0 cm.'
  if (!isValidMargin(form.margins_cm.bottom)) e['margins_bottom'] = 'Entre 0.5 y 5.0 cm.'
  if (!isValidMargin(form.margins_cm.left)) e['margins_left'] = 'Entre 0.5 y 5.0 cm.'
  if (!isValidMargin(form.margins_cm.right)) e['margins_right'] = 'Entre 0.5 y 5.0 cm.'
  if (!isValidFont(form.font_family)) e['font_family'] = 'Selecciona una fuente de la lista.'
  if (!isValidFontSize(form.font_size_pt)) e['font_size_pt'] = 'Entre 8 y 24 pt (pasos de 0.5).'
  if (!isValidLineSpacing(form.line_spacing)) e['line_spacing'] = 'Entre 1.0 y 3.0.'
  if (aiForm.enabled && !aiForm.accepted_disclaimer) {
    e['ai_disclaimer'] = 'Debes aceptar el aviso para poder usar la estructuración con IA.'
  }

  return e
})

const hasErrors = computed(() => Object.keys(errors.value).length > 0)

function applyPreset(preset: Preset) {
  const c = preset.config
  const defaultTheme = defaultThemeForPreset(preset.id)
  const defaultAlign = c.paragraph?.alignment === 'left' || preset.id === 'apa7' ? 'left' : 'justify'
  const defaultDividers = preset.id !== 'apa7'
  const defaultPageNums = c.page_numbers ?? preset.id !== 'personalizado'

  form.preset_id = preset.id
  form.margins_cm.top = c.margins_cm.top
  form.margins_cm.bottom = c.margins_cm.bottom
  form.margins_cm.left = c.margins_cm.left
  form.margins_cm.right = c.margins_cm.right
  form.font_family = c.font_family
  form.font_size_pt = c.font_size_pt
  form.line_spacing = c.line_spacing
  form.color_theme = preset.id === 'reporte' ? (userPrefs.defaultTheme || defaultTheme) : defaultTheme
  form.show_dividers = defaultDividers
  form.alignment = defaultAlign
  form.page_numbers = defaultPageNums

  presetSnapshot.margins_cm.top = c.margins_cm.top
  presetSnapshot.margins_cm.bottom = c.margins_cm.bottom
  presetSnapshot.margins_cm.left = c.margins_cm.left
  presetSnapshot.margins_cm.right = c.margins_cm.right
  presetSnapshot.font_family = c.font_family
  presetSnapshot.font_size_pt = c.font_size_pt
  presetSnapshot.line_spacing = c.line_spacing
  presetSnapshot.color_theme = form.color_theme
  presetSnapshot.show_dividers = defaultDividers
  presetSnapshot.alignment = defaultAlign
  presetSnapshot.page_numbers = defaultPageNums
}

watch(
  () => form.preset_id,
  (newId) => {
    if (!newId) return
    const found = presets.value.find((p) => p.id === newId)
    if (found) applyPreset(found)
  }
)

function resetToPreset() {
  form.margins_cm.top = presetSnapshot.margins_cm.top
  form.margins_cm.bottom = presetSnapshot.margins_cm.bottom
  form.margins_cm.left = presetSnapshot.margins_cm.left
  form.margins_cm.right = presetSnapshot.margins_cm.right
  form.font_family = presetSnapshot.font_family
  form.font_size_pt = presetSnapshot.font_size_pt
  form.line_spacing = presetSnapshot.line_spacing
  form.color_theme = presetSnapshot.color_theme
  form.show_dividers = presetSnapshot.show_dividers
  form.alignment = presetSnapshot.alignment
  form.page_numbers = presetSnapshot.page_numbers
}

onMounted(async () => {
  try {
    const data = await getPresets()
    presets.value = data
    const preferred = data.find((p: Preset) => p.id === 'reporte') || data[0]
    if (preferred) applyPreset(preferred)
  } catch (err: any) {
    flowStore.setError(err)
  } finally {
    isLoadingPresets.value = false
  }
})

async function submitFormatting() {
  if (hasErrors.value || !flowStore.document?.document_id) return

  isSubmitting.value = true
  flowStore.setError(null)

  const payload: Record<string, any> = {
    preset_id: form.preset_id ?? null,
    margins_cm: {
      top: Number(form.margins_cm.top),
      bottom: Number(form.margins_cm.bottom),
      left: Number(form.margins_cm.left),
      right: Number(form.margins_cm.right)
    },
    font_family: form.font_family,
    font_size_pt: Number(form.font_size_pt),
    line_spacing: Number(form.line_spacing),
    color_theme: form.color_theme,
    show_dividers: form.show_dividers,
    page_numbers: form.page_numbers,
    paragraph: {
      alignment: form.alignment,
      first_line_indent_cm: form.preset_id === 'apa7' ? 1.27 : 0.0,
      space_after_pt: form.preset_id === 'apa7' ? 0.0 : 6.0
    },
    use_ai: aiForm.enabled
  }

  if (aiForm.enabled) {
    payload.document_type = aiForm.document_type
    payload.detect_titles = aiForm.detect_titles
    payload.detect_lists = aiForm.detect_lists
    payload.detect_tables = aiForm.detect_tables
    payload.creative_structure = aiForm.creative_structure
    payload.emphasis = aiForm.emphasis
    payload.ai_options = {
      document_type: aiForm.document_type,
      detect_titles: aiForm.detect_titles,
      detect_lists: aiForm.detect_lists,
      detect_tables: aiForm.detect_tables,
      creative_structure: aiForm.creative_structure,
      emphasis: aiForm.emphasis,
      accepted_disclaimer: aiForm.accepted_disclaimer
    }
  }

  try {
    const resultData = await formatDocument(flowStore.document.document_id, payload)
    flowStore.setConfig({
      ...payload,
      ...(resultData.config || {}),
      color_theme: form.color_theme,
      show_dividers: form.show_dividers
    })
    flowStore.setResult(resultData)

    const is202 = resultData.httpStatus === 202 || resultData.status === 202
    if (is202) {
      router.push(`/processing/${flowStore.document.document_id}`)
    } else {
      router.push('/result')
    }
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
  <div class="container-fluid config-container px-0">
    <FlowStepper :current="2" />

    <!-- API Error Alert -->
    <div
      v-if="flowStore.error"
      class="alert alert-danger d-flex align-items-center justify-content-between mb-4 rounded-4"
      role="alert"
    >
      <div>
        <strong>Error ({{ flowStore.error.code }}):</strong> {{ flowStore.error.message }}
      </div>
      <button type="button" class="btn-close" @click="flowStore.setError(null)"></button>
    </div>

    <!-- Active Document Banner -->
    <div class="card pd-card mb-4">
      <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-2 py-3 px-4">
        <div class="d-flex align-items-center gap-2 min-w-0">
          <span class="badge rounded-pill doc-pill">Documento activo</span>
          <strong class="fs-5 text-dark text-truncate">
            {{ flowStore.document?.original_name || flowStore.file?.name }}
          </strong>
        </div>
        <button class="btn btn-sm btn-outline-secondary" @click="cancel">Cambiar archivo</button>
      </div>
    </div>

    <div class="row g-4 align-items-start">
      <!-- LEFT COLUMN: Customization Controls -->
      <div class="col-12 col-xl-7">
        <!-- 1. PLANTILLA BASE -->
        <div class="card pd-card p-4 mb-4">
          <h5 class="fw-bold text-dark mb-1">1. Plantilla base</h5>
          <p class="text-secondary small mb-3">
            Elige el estilo estructural del documento. Luego podrás personalizar su paleta de colores y acabados.
          </p>

          <div v-if="isLoadingPresets" class="text-center py-3">
            <div class="spinner-border text-primary spinner-border-sm me-2"></div>
            <span class="text-secondary">Cargando plantillas…</span>
          </div>

          <div v-else class="row g-3">
            <div v-for="p in presets" :key="p.id" class="col-md-4">
              <div
                class="preset-card card h-100 p-3"
                :class="form.preset_id === p.id ? 'preset-card--active' : ''"
                @click="form.preset_id = p.id"
                role="button"
                :aria-pressed="form.preset_id === p.id"
              >
                <div class="d-flex align-items-center justify-content-between mb-1">
                  <span class="fw-bold text-dark small">{{ p.name }}</span>
                  <input
                    type="radio"
                    name="preset"
                    :value="p.id"
                    v-model="form.preset_id"
                    class="form-check-input mt-0"
                  />
                </div>
                <p class="text-secondary mb-0" style="font-size: 0.78rem">{{ p.description }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. PALETA DE COLORES PARA EL DOCUMENTO WORD -->
        <div class="card pd-card p-4 mb-4" id="color-theme-section">
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-1">
            <h5 class="fw-bold text-dark mb-0">2. Paleta de colores del documento Word</h5>
            <span class="badge rounded-pill text-bg-light border text-secondary small">
              Se aplica al .docx final
            </span>
          </div>
          <p class="text-secondary small mb-3">
            Define los colores reales de títulos, barras divisorias, encabezados de tabla, filas alternadas y tarjetas destacadas en Word.
          </p>

          <div class="row g-2 mb-3">
            <div v-for="theme in DOCUMENT_THEMES" :key="theme.id" class="col-6 col-md-4">
              <button
                type="button"
                class="theme-card w-100 text-start p-3 rounded-3"
                :class="{ 'theme-card--active': form.color_theme === theme.id }"
                :data-theme-id="theme.id"
                @click="form.color_theme = theme.id"
              >
                <div class="d-flex align-items-center gap-1 mb-2">
                  <span class="swatch swatch--lg" :style="{ backgroundColor: theme.primary }"></span>
                  <span class="swatch" :style="{ backgroundColor: theme.secondary }"></span>
                  <span class="swatch" :style="{ backgroundColor: theme.headerFill }"></span>
                  <span class="swatch" :style="{ backgroundColor: theme.accent }"></span>
                </div>
                <div class="fw-bold text-dark" style="font-size: 0.85rem">{{ theme.name }}</div>
                <div class="text-secondary" style="font-size: 0.72rem">{{ theme.tagline }}</div>
              </button>
            </div>
          </div>

          <!-- Acabado editorial rápido -->
          <div class="row g-3 pt-3 border-top">
            <div class="col-md-4">
              <label class="form-label fw-semibold small mb-1 d-block">Alineación del texto</label>
              <div class="btn-group btn-group-sm w-100" role="group">
                <button
                  type="button"
                  class="btn"
                  :class="form.alignment === 'justify' ? 'btn-dark' : 'btn-outline-secondary'"
                  @click="form.alignment = 'justify'"
                >
                  Justificado
                </button>
                <button
                  type="button"
                  class="btn"
                  :class="form.alignment === 'left' ? 'btn-dark' : 'btn-outline-secondary'"
                  @click="form.alignment = 'left'"
                >
                  Izquierda
                </button>
              </div>
            </div>

            <div class="col-md-4 d-flex align-items-end">
              <div class="form-check form-switch mb-1">
                <input
                  id="toggle-dividers"
                  v-model="form.show_dividers"
                  class="form-check-input cursor-pointer"
                  type="checkbox"
                />
                <label class="form-check-label small fw-semibold text-dark cursor-pointer" for="toggle-dividers">
                  Barras divisorias y acentos
                </label>
              </div>
            </div>

            <div class="col-md-4 d-flex align-items-end">
              <div class="form-check form-switch mb-1">
                <input
                  id="toggle-page-numbers"
                  v-model="form.page_numbers"
                  class="form-check-input cursor-pointer"
                  type="checkbox"
                />
                <label class="form-check-label small fw-semibold text-dark cursor-pointer" for="toggle-page-numbers">
                  Numeración de páginas
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. TIPOGRAFÍA Y MÁRGENES -->
        <div class="card pd-card p-4 mb-4">
          <div class="d-flex align-items-center justify-content-between mb-3">
            <div>
              <h5 class="fw-bold text-dark mb-0">3. Tipografía y márgenes</h5>
              <span class="text-secondary small">Ajusta fuente, tamaño, interlineado o márgenes exactos.</span>
            </div>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="showAdvancedMetrics = !showAdvancedMetrics"
            >
              {{ showAdvancedMetrics ? 'Ocultar márgenes' : 'Editar márgenes (cm)' }}
            </button>
          </div>

          <div class="row g-3">
            <div class="col-md-5">
              <label for="font-family" class="form-label fw-semibold small">Fuente</label>
              <select
                id="font-family"
                v-model="form.font_family"
                class="form-select"
                :class="{ 'is-invalid': errors.font_family }"
              >
                <option v-for="font in ALLOWED_FONTS" :key="font" :value="font">
                  {{ font }}
                </option>
              </select>
              <div v-if="errors.font_family" class="invalid-feedback">{{ errors.font_family }}</div>
            </div>

            <div class="col-md-3">
              <label for="font-size" class="form-label fw-semibold small">Tamaño (pt)</label>
              <input
                id="font-size"
                v-model.number="form.font_size_pt"
                type="number"
                min="8"
                max="24"
                step="0.5"
                class="form-control"
                :class="{ 'is-invalid': errors.font_size_pt }"
              />
              <div v-if="errors.font_size_pt" class="invalid-feedback">{{ errors.font_size_pt }}</div>
            </div>

            <div class="col-md-4">
              <label for="line-spacing" class="form-label fw-semibold small">Interlineado</label>
              <input
                id="line-spacing"
                v-model.number="form.line_spacing"
                type="number"
                min="1.0"
                max="3.0"
                step="0.05"
                class="form-control"
                :class="{ 'is-invalid': errors.line_spacing }"
              />
              <div v-if="errors.line_spacing" class="invalid-feedback">{{ errors.line_spacing }}</div>
            </div>
          </div>

          <div v-if="showAdvancedMetrics" class="row g-3 mt-2 pt-3 border-top">
            <div class="col-6 col-md-3">
              <label for="margin-top" class="form-label fw-semibold small">Superior (cm)</label>
              <input id="margin-top" v-model.number="form.margins_cm.top" type="number" min="0.5" max="5.0" step="0.01" class="form-control form-control-sm" :class="{ 'is-invalid': errors.margins_top }" />
            </div>
            <div class="col-6 col-md-3">
              <label for="margin-bottom" class="form-label fw-semibold small">Inferior (cm)</label>
              <input id="margin-bottom" v-model.number="form.margins_cm.bottom" type="number" min="0.5" max="5.0" step="0.01" class="form-control form-control-sm" :class="{ 'is-invalid': errors.margins_bottom }" />
            </div>
            <div class="col-6 col-md-3">
              <label for="margin-left" class="form-label fw-semibold small">Izquierdo (cm)</label>
              <input id="margin-left" v-model.number="form.margins_cm.left" type="number" min="0.5" max="5.0" step="0.01" class="form-control form-control-sm" :class="{ 'is-invalid': errors.margins_left }" />
            </div>
            <div class="col-6 col-md-3">
              <label for="margin-right" class="form-label fw-semibold small">Derecho (cm)</label>
              <input id="margin-right" v-model.number="form.margins_cm.right" type="number" min="0.5" max="5.0" step="0.01" class="form-control form-control-sm" :class="{ 'is-invalid': errors.margins_right }" />
            </div>
          </div>
        </div>

        <!-- 4. ESTRUCTURAR CON IA -->
        <div class="card pd-card p-4 mb-4" id="ai-structure-section">
          <div class="d-flex align-items-center justify-content-between">
            <div>
              <div class="d-flex align-items-center gap-2">
                <h5 class="fw-bold text-dark mb-0">4. Estructurar con IA</h5>
                <span class="badge rounded-pill ai-chip">Recomendado</span>
              </div>
              <p class="text-secondary small mb-0 mt-1">
                Detecta títulos, listas, tablas y tarjetas destacadas preservando el 100% de tus palabras y cifras.
              </p>
            </div>
            <div class="form-check form-switch fs-4 mb-0 ms-3">
              <input
                id="ai-switch"
                class="form-check-input cursor-pointer"
                type="checkbox"
                role="switch"
                v-model="aiForm.enabled"
                aria-label="Interruptor Estructurar con IA"
              />
            </div>
          </div>

          <div v-if="aiForm.enabled" class="pt-3 mt-3 border-top">
            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label for="ai-document-type" class="form-label fw-semibold small">Tipo de documento</label>
                <select id="ai-document-type" v-model="aiForm.document_type" class="form-select">
                  <option value="reporte">Reporte ejecutivo</option>
                  <option value="propuesta">Propuesta / Proyecto</option>
                  <option value="academico">Académico / Tesis</option>
                  <option value="acta">Acta de reunión</option>
                  <option value="general">General / Otro</option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label fw-semibold small d-block">Nivel de énfasis (negritas)</label>
                <div class="btn-group w-100" role="group">
                  <input type="radio" class="btn-check" name="ai-emphasis" id="emphasis-none" value="ninguno" v-model="aiForm.emphasis" />
                  <label class="btn" :class="aiForm.emphasis === 'ninguno' ? 'btn-dark' : 'btn-outline-secondary'" for="emphasis-none">Ninguno</label>

                  <input type="radio" class="btn-check" name="ai-emphasis" id="emphasis-light" value="ligero" v-model="aiForm.emphasis" />
                  <label class="btn" :class="aiForm.emphasis === 'ligero' ? 'btn-dark' : 'btn-outline-secondary'" for="emphasis-light">Ligero</label>

                  <input type="radio" class="btn-check" name="ai-emphasis" id="emphasis-medium" value="medio" v-model="aiForm.emphasis" />
                  <label class="btn" :class="aiForm.emphasis === 'medio' ? 'btn-dark' : 'btn-outline-secondary'" for="emphasis-medium">Medio</label>
                </div>
              </div>
            </div>

            <div class="d-flex flex-wrap gap-3 mb-3">
              <div class="form-check">
                <input id="detect-titles" class="form-check-input" type="checkbox" v-model="aiForm.detect_titles" />
                <label class="form-check-label small fw-medium" for="detect-titles">Detectar títulos y subtítulos</label>
              </div>
              <div class="form-check">
                <input id="detect-lists" class="form-check-input" type="checkbox" v-model="aiForm.detect_lists" />
                <label class="form-check-label small fw-medium" for="detect-lists">Detectar listas</label>
              </div>
              <div class="form-check">
                <input id="detect-tables" class="form-check-input" type="checkbox" v-model="aiForm.detect_tables" />
                <label class="form-check-label small fw-medium" for="detect-tables">Crear tablas desde texto</label>
              </div>
            </div>

            <div class="p-3 mb-3 rounded-3 border bg-light-subtle">
              <div class="form-check form-switch mb-0">
                <input
                  id="ai-creative-structure"
                  class="form-check-input cursor-pointer"
                  type="checkbox"
                  role="switch"
                  v-model="aiForm.creative_structure"
                />
                <label class="form-check-label fw-semibold small text-dark cursor-pointer d-flex flex-wrap align-items-center gap-2" for="ai-creative-structure">
                  <span>Enriquecimiento estructural proactivo</span>
                  <span class="badge rounded-pill ai-chip">✦ Crea estructura faltante</span>
                </label>
              </div>
              <p class="text-secondary mb-0 mt-1 ms-5" style="font-size: 0.78rem">
                Impulsa a la IA a sugerir subtítulos temáticos, viñetas, tablas comparativas y tarjetas destacadas en textos planos sin modificar tus palabras ni cifras originales.
              </p>
            </div>

            <div class="alert alert-warning border-warning-subtle d-flex flex-column gap-2 mb-0 rounded-3" role="alert">
              <div class="small fw-semibold text-dark">
                El texto de tu documento se enviará al proveedor de IA solo para estructurarlo. El contenido no se modifica.
              </div>
              <div class="form-check mb-0">
                <input
                  id="ai-disclaimer"
                  class="form-check-input"
                  type="checkbox"
                  v-model="aiForm.accepted_disclaimer"
                  :class="{ 'is-invalid': errors.ai_disclaimer }"
                  required
                />
                <label class="form-check-label small fw-semibold text-dark cursor-pointer" for="ai-disclaimer">
                  Acepto el procesamiento del documento con el proveedor de IA <span class="text-danger">*</span>
                </label>
                <div v-if="errors.ai_disclaimer" class="invalid-feedback d-block">{{ errors.ai_disclaimer }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ACTION BUTTONS -->
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
          <button class="btn btn-outline-secondary px-4" @click="cancel">Volver</button>
          <div class="d-flex gap-2">
            <button class="btn btn-outline-secondary px-3" :disabled="isSubmitting || !form.preset_id" @click="resetToPreset">
              Restablecer
            </button>
            <button
              id="btn-apply-format"
              class="btn pd-btn-brand btn-lg px-5"
              :disabled="isSubmitting || hasErrors"
              @click="submitFormatting"
            >
              <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" role="status"></span>
              <span>{{ isSubmitting ? 'Procesando…' : (aiForm.enabled ? 'Estructurar con IA' : 'Aplicar plantilla') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- RIGHT COLUMN: LIVE MINI WORD SHEET PREVIEW -->
      <div class="col-12 col-xl-5">
        <div class="live-preview-sticky">
          <div class="card pd-card p-3">
            <div class="d-flex align-items-center justify-content-between mb-2 px-1">
              <div>
                <span class="small fw-bold text-dark">Vista previa en vivo del Word</span>
                <span class="d-block text-secondary" style="font-size: 0.72rem">
                  {{ activeTheme.name }} · {{ form.font_family }} {{ form.font_size_pt }} pt
                </span>
              </div>
              <span
                class="badge rounded-pill px-2 py-1"
                :style="{ backgroundColor: activeTheme.headerFill, color: activeTheme.primary }"
              >
                {{ form.show_dividers ? 'Con barras' : 'Limpio' }}
              </span>
            </div>

            <!-- Simulated Word Page -->
            <div
              class="mini-word-sheet"
              :style="{
                fontFamily: `'${form.font_family}', sans-serif`,
                lineHeight: Number(form.line_spacing) || 1.15
              }"
            >
              <div v-if="form.page_numbers" class="mini-page-num">1</div>

              <div
                class="mini-title"
                :style="{
                  color: activeTheme.primary,
                  borderBottom: form.show_dividers ? `2.5px solid ${activeTheme.primary}` : 'none',
                  textAlign: form.preset_id === 'apa7' ? 'center' : 'left'
                }"
              >
                Informe Ejecutivo de Operaciones
              </div>

              <div
                class="mini-h1"
                :style="{
                  color: activeTheme.primary,
                  borderBottom: form.show_dividers ? `1.5px solid ${activeTheme.secondary}` : 'none',
                  textAlign: form.preset_id === 'apa7' ? 'center' : 'left'
                }"
              >
                1. Resumen Ejecutivo
              </div>

              <p
                class="mini-p"
                :style="{
                  textAlign: form.alignment,
                  textIndent: form.preset_id === 'apa7' ? '1.1rem' : '0'
                }"
              >
                Este documento muestra en tiempo real cómo se verán tus títulos, párrafos, tablas y bloques destacados en el archivo Word final.
              </p>

              <div
                class="mini-h2"
                :style="{
                  color: activeTheme.secondary,
                  borderLeft: form.show_dividers ? `3px solid ${activeTheme.secondary}` : 'none',
                  paddingLeft: form.show_dividers ? '0.45rem' : '0'
                }"
              >
                1.1 Hallazgos Clave
              </div>

              <p
                class="mini-p mini-kv"
                :style="{
                  textAlign: form.alignment,
                  borderLeft: form.show_dividers ? `2.5px solid ${activeTheme.accent}` : 'none',
                  paddingLeft: form.show_dividers ? '0.45rem' : '0'
                }"
              >
                <strong>Eficiencia operativa:</strong> reducción del 65% en tiempos de maquetación y estandarización documental.
              </p>

              <table
                class="mini-table"
                :style="{ borderColor: activeTheme.border }"
              >
                <thead>
                  <tr :style="{ backgroundColor: activeTheme.headerFill, color: activeTheme.primary }">
                    <th :style="{ borderColor: activeTheme.border }">Indicador</th>
                    <th :style="{ borderColor: activeTheme.border }">Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td :style="{ borderColor: activeTheme.border }">Crecimiento anual</td>
                    <td :style="{ borderColor: activeTheme.border }">+22.5%</td>
                  </tr>
                  <tr :style="{ backgroundColor: activeTheme.zebraFill }">
                    <td :style="{ borderColor: activeTheme.border }">Integridad verificada</td>
                    <td :style="{ borderColor: activeTheme.border }">100%</td>
                  </tr>
                </tbody>
              </table>

              <div
                class="mini-callout"
                :style="{
                  backgroundColor: activeTheme.calloutFill,
                  borderLeft: `3.5px solid ${activeTheme.primary}`
                }"
              >
                <strong>Nota:</strong> Todas las cifras e imágenes del documento original se conservan intactas.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-container {
  max-width: 1320px;
  margin: 0 auto;
}

.doc-pill {
  background: var(--pd-brand-soft);
  color: var(--pd-brand);
  font-weight: 600;
  padding: 0.4rem 0.75rem;
}

.ai-chip {
  background: #ede9fe;
  color: #5b21b6;
  font-size: 0.72rem;
  font-weight: 600;
}

.preset-card {
  cursor: pointer;
  border: 2px solid #e2e8f0;
  border-radius: 0.75rem;
  transition: all 0.15s ease;
}

.preset-card:hover {
  border-color: var(--pd-brand-2);
}

.preset-card--active {
  border-color: var(--pd-brand);
  background: var(--pd-brand-soft);
}

.theme-card {
  border: 2px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.theme-card:hover {
  border-color: #94a3b8;
  transform: translateY(-1px);
}

.theme-card--active {
  border-color: #0f172a;
  background: #f8fafc;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.swatch {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  display: inline-block;
}

.swatch--lg {
  width: 22px;
  height: 22px;
}

.live-preview-sticky {
  position: sticky;
  top: 5.5rem;
}

.mini-word-sheet {
  position: relative;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 1.5rem 1.45rem;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  font-size: 0.76rem;
  color: #1e293b;
}

.mini-page-num {
  position: absolute;
  top: 0.65rem;
  right: 1rem;
  font-size: 0.65rem;
  color: #94a3b8;
}

.mini-title {
  font-size: 1.15rem;
  font-weight: 800;
  padding-bottom: 0.35rem;
  margin-bottom: 0.8rem;
}

.mini-h1 {
  font-size: 0.92rem;
  font-weight: 700;
  padding-bottom: 0.2rem;
  margin-bottom: 0.45rem;
}

.mini-h2 {
  font-size: 0.82rem;
  font-weight: 700;
  margin: 0.65rem 0 0.35rem;
}

.mini-p {
  margin: 0 0 0.5rem;
  color: #334155;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.65rem 0;
  font-size: 0.72rem;
}

.mini-table th,
.mini-table td {
  border: 1px solid;
  padding: 0.28rem 0.45rem;
}

.mini-callout {
  padding: 0.45rem 0.65rem;
  font-style: italic;
  border-radius: 0.2rem;
  font-size: 0.72rem;
  margin-top: 0.55rem;
}

.cursor-pointer {
  cursor: pointer;
}
</style>
