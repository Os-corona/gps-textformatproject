<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'
import { getPresets, formatDocument } from '@/services/api'

// ─── Constants ───────────────────────────────────────────────────────────────
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
  }
}

// ─── Router & Store ───────────────────────────────────────────────────────────
const router = useRouter()
const flowStore = useFlowStore()

// ─── State ────────────────────────────────────────────────────────────────────
const presets = ref<Preset[]>([])
const isLoadingPresets = ref(true)
const isSubmitting = ref(false)

const form = reactive<FormState>({
  preset_id: null,
  margins_cm: { top: 2.54, bottom: 2.54, left: 2.54, right: 2.54 },
  font_family: 'Calibri',
  font_size_pt: 11,
  line_spacing: 1.15
})

// ─── AI Structuring State (Sprint 3) ──────────────────────────────────────────
interface AiFormState {
  enabled: boolean
  document_type: string
  detect_titles: boolean
  detect_lists: boolean
  detect_tables: boolean
  emphasis: 'ninguno' | 'ligero' | 'medio'
  accepted_disclaimer: boolean
}

const aiForm = reactive<AiFormState>({
  enabled: false,
  document_type: 'general',
  detect_titles: true,
  detect_lists: true,
  detect_tables: true,
  emphasis: 'ligero',
  accepted_disclaimer: false
})

// Snapshot of the current preset values (for Reset button)
const presetSnapshot = reactive<Omit<FormState, 'preset_id'>>({
  margins_cm: { top: 2.54, bottom: 2.54, left: 2.54, right: 2.54 },
  font_family: 'Calibri',
  font_size_pt: 11,
  line_spacing: 1.15
})

// ─── Validation helpers ───────────────────────────────────────────────────────
function isValidMargin(val: number | string): boolean {
  const n = Number(val)
  return !isNaN(n) && n >= 0.5 && n <= 5.0
}

function isValidFontSize(val: number | string): boolean {
  const n = Number(val)
  // Between 8 and 24, steps of 0.5
  return !isNaN(n) && n >= 8 && n <= 24 && (n * 2) % 1 === 0
}

function isValidLineSpacing(val: number | string): boolean {
  const n = Number(val)
  // Between 1.0 and 3.0, up to 2 decimals
  return !isNaN(n) && n >= 1.0 && n <= 3.0
}

function isValidFont(val: string): boolean {
  return (ALLOWED_FONTS as readonly string[]).includes(val)
}

const errors = computed(() => {
  const e: Record<string, string> = {}

  if (!isValidMargin(form.margins_cm.top))
    e['margins_top'] = 'Debe estar entre 0.5 y 5.0 cm.'
  if (!isValidMargin(form.margins_cm.bottom))
    e['margins_bottom'] = 'Debe estar entre 0.5 y 5.0 cm.'
  if (!isValidMargin(form.margins_cm.left))
    e['margins_left'] = 'Debe estar entre 0.5 y 5.0 cm.'
  if (!isValidMargin(form.margins_cm.right))
    e['margins_right'] = 'Debe estar entre 0.5 y 5.0 cm.'

  if (!isValidFont(form.font_family))
    e['font_family'] = 'Selecciona una fuente de la lista.'

  if (!isValidFontSize(form.font_size_pt))
    e['font_size_pt'] = 'Debe estar entre 8 y 24 pt, en pasos de 0.5.'

  if (!isValidLineSpacing(form.line_spacing))
    e['line_spacing'] = 'Debe estar entre 1.0 y 3.0.'

  if (aiForm.enabled && !aiForm.accepted_disclaimer)
    e['ai_disclaimer'] = 'Debes aceptar el aviso para poder usar la estructuración con IA.'

  return e
})

const hasErrors = computed(() => Object.keys(errors.value).length > 0)

// ─── Preset logic ─────────────────────────────────────────────────────────────
function applyPreset(preset: Preset) {
  const c = preset.config
  form.preset_id = preset.id
  form.margins_cm.top = c.margins_cm.top
  form.margins_cm.bottom = c.margins_cm.bottom
  form.margins_cm.left = c.margins_cm.left
  form.margins_cm.right = c.margins_cm.right
  form.font_family = c.font_family
  form.font_size_pt = c.font_size_pt
  form.line_spacing = c.line_spacing

  // Save snapshot for Reset
  presetSnapshot.margins_cm.top = c.margins_cm.top
  presetSnapshot.margins_cm.bottom = c.margins_cm.bottom
  presetSnapshot.margins_cm.left = c.margins_cm.left
  presetSnapshot.margins_cm.right = c.margins_cm.right
  presetSnapshot.font_family = c.font_family
  presetSnapshot.font_size_pt = c.font_size_pt
  presetSnapshot.line_spacing = c.line_spacing
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
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const data = await getPresets()
    presets.value = data
    // Auto-select first preset
    if (data.length > 0) applyPreset(data[0])
  } catch (err: any) {
    flowStore.setError(err)
  } finally {
    isLoadingPresets.value = false
  }
})

// ─── Submit ───────────────────────────────────────────────────────────────────
async function submitFormatting() {
  if (hasErrors.value || !flowStore.document?.document_id) return

  isSubmitting.value = true
  flowStore.setError(null)

  // Build payload v1.1 (when aiForm.enabled is true, include AI structuring fields; when false, identical to Sprint 2)
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
    use_ai: aiForm.enabled
  }

  if (aiForm.enabled) {
    payload.document_type = aiForm.document_type
    payload.detect_titles = aiForm.detect_titles
    payload.detect_lists = aiForm.detect_lists
    payload.detect_tables = aiForm.detect_tables
    payload.emphasis = aiForm.emphasis
    payload.ai_options = {
      document_type: aiForm.document_type,
      detect_titles: aiForm.detect_titles,
      detect_lists: aiForm.detect_lists,
      detect_tables: aiForm.detect_tables,
      emphasis: aiForm.emphasis,
      accepted_disclaimer: aiForm.accepted_disclaimer
    }
  }

  try {
    const resultData = await formatDocument(flowStore.document.document_id, payload)
    // Prefer the config resolved by the backend (preset + overrides).
    flowStore.setConfig(resultData.config ?? payload)
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

    <!-- Error Alert (API errors) -->
    <div
      v-if="flowStore.error"
      class="alert alert-danger d-flex align-items-center justify-content-between mb-4"
      role="alert"
    >
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
          <strong class="fs-5 text-dark">
            {{ flowStore.document?.original_name || flowStore.file?.name }}
          </strong>
        </div>
        <button class="btn btn-sm btn-outline-secondary" @click="cancel">Cambiar archivo</button>
      </div>
    </div>

    <!-- ── PRESET SELECTOR ──────────────────────────────────────────────────── -->
    <div class="card border-0 shadow-sm rounded-4 p-4 mb-4">
      <h4 class="fw-semibold text-dark mb-1">Plantilla de formato</h4>
      <p class="text-secondary small mb-3">
        Elige una plantilla para precargar los valores. Puedes ajustarlos manualmente después.
      </p>

      <div v-if="isLoadingPresets" class="text-center py-3">
        <div class="spinner-border text-primary spinner-border-sm me-2"></div>
        <span class="text-secondary">Cargando plantillas...</span>
      </div>

      <div v-else>
        <!-- Preset select dropdown -->
        <div class="mb-3">
          <label for="preset-select" class="form-label fw-semibold">Seleccionar preset</label>
          <select
            id="preset-select"
            v-model="form.preset_id"
            class="form-select"
          >
            <option :value="null" disabled>— Elige una plantilla —</option>
            <option v-for="p in presets" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
          <!-- Description of selected preset -->
          <div
            v-if="form.preset_id"
            class="form-text text-secondary mt-1"
          >
            {{ presets.find(p => p.id === form.preset_id)?.description }}
          </div>
        </div>

        <!-- Preset cards (visual selector) -->
        <div class="row g-3">
          <div v-for="p in presets" :key="p.id" class="col-md-4">
            <div
              class="preset-card card h-100 p-3 border-2"
              :class="form.preset_id === p.id
                ? 'border-primary bg-primary-subtle'
                : 'border-light-subtle'"
              @click="form.preset_id = p.id"
              role="button"
              :aria-pressed="form.preset_id === p.id"
            >
              <div class="d-flex align-items-center justify-content-between mb-2">
                <span class="fw-bold text-dark">{{ p.name }}</span>
                <input
                  type="radio"
                  name="preset"
                  :value="p.id"
                  v-model="form.preset_id"
                  class="form-check-input"
                />
              </div>
              <p class="text-secondary small mb-0">{{ p.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── FIELDS ────────────────────────────────────────────────────────────── -->
    <div class="card border-0 shadow-sm rounded-4 p-4 mb-4">
      <h4 class="fw-semibold text-dark mb-1">Parámetros de formato</h4>
      <p class="text-secondary small mb-4">
        Los valores se validan en tiempo real según el contrato de la API.
      </p>

      <!-- ── Margins ── -->
      <h6 class="text-uppercase text-secondary fw-semibold small letter-spacing-1 mb-3">
        Márgenes (cm)
      </h6>
      <div class="row g-3 mb-4">
        <!-- Top -->
        <div class="col-6 col-md-3">
          <label for="margin-top" class="form-label fw-semibold">Superior</label>
          <input
            id="margin-top"
            v-model.number="form.margins_cm.top"
            type="number"
            min="0.5"
            max="5.0"
            step="0.01"
            class="form-control"
            :class="{ 'is-invalid': errors.margins_top }"
          />
          <div v-if="errors.margins_top" class="invalid-feedback">
            {{ errors.margins_top }}
          </div>
        </div>

        <!-- Bottom -->
        <div class="col-6 col-md-3">
          <label for="margin-bottom" class="form-label fw-semibold">Inferior</label>
          <input
            id="margin-bottom"
            v-model.number="form.margins_cm.bottom"
            type="number"
            min="0.5"
            max="5.0"
            step="0.01"
            class="form-control"
            :class="{ 'is-invalid': errors.margins_bottom }"
          />
          <div v-if="errors.margins_bottom" class="invalid-feedback">
            {{ errors.margins_bottom }}
          </div>
        </div>

        <!-- Left -->
        <div class="col-6 col-md-3">
          <label for="margin-left" class="form-label fw-semibold">Izquierdo</label>
          <input
            id="margin-left"
            v-model.number="form.margins_cm.left"
            type="number"
            min="0.5"
            max="5.0"
            step="0.01"
            class="form-control"
            :class="{ 'is-invalid': errors.margins_left }"
          />
          <div v-if="errors.margins_left" class="invalid-feedback">
            {{ errors.margins_left }}
          </div>
        </div>

        <!-- Right -->
        <div class="col-6 col-md-3">
          <label for="margin-right" class="form-label fw-semibold">Derecho</label>
          <input
            id="margin-right"
            v-model.number="form.margins_cm.right"
            type="number"
            min="0.5"
            max="5.0"
            step="0.01"
            class="form-control"
            :class="{ 'is-invalid': errors.margins_right }"
          />
          <div v-if="errors.margins_right" class="invalid-feedback">
            {{ errors.margins_right }}
          </div>
        </div>
      </div>

      <!-- ── Typography ── -->
      <h6 class="text-uppercase text-secondary fw-semibold small letter-spacing-1 mb-3">
        Tipografía
      </h6>
      <div class="row g-3 mb-2">
        <!-- Font family -->
        <div class="col-md-5">
          <label for="font-family" class="form-label fw-semibold">Fuente</label>
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
          <div v-if="errors.font_family" class="invalid-feedback">
            {{ errors.font_family }}
          </div>
        </div>

        <!-- Font size -->
        <div class="col-md-3">
          <label for="font-size" class="form-label fw-semibold">Tamaño (pt)</label>
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
          <div v-if="errors.font_size_pt" class="invalid-feedback">
            {{ errors.font_size_pt }}
          </div>
        </div>

        <!-- Line spacing -->
        <div class="col-md-4">
          <label for="line-spacing" class="form-label fw-semibold">Interlineado</label>
          <input
            id="line-spacing"
            v-model.number="form.line_spacing"
            type="number"
            min="1.0"
            max="3.0"
            step="0.01"
            class="form-control"
            :class="{ 'is-invalid': errors.line_spacing }"
          />
          <div v-if="errors.line_spacing" class="invalid-feedback">
            {{ errors.line_spacing }}
          </div>
          <div class="form-text">Múltiplo de línea (1.0 – 3.0).</div>
        </div>
      </div>

      <!-- Validation summary banner -->
      <div
        v-if="hasErrors"
        class="alert alert-warning d-flex align-items-center gap-2 mt-3 mb-0 py-2"
        role="alert"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-triangle-fill flex-shrink-0" viewBox="0 0 16 16">
          <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
        </svg>
        <span class="small">
          Corrige los campos marcados en rojo antes de aplicar el formato.
        </span>
      </div>
    </div>

    <!-- ── ESTRUCTURAR CON IA (Sprint 3) ────────────────────────────────────── -->
    <div class="card border-0 shadow-sm rounded-4 p-4 mb-4" id="ai-structure-section">
      <div class="d-flex align-items-center justify-content-between">
        <div>
          <div class="d-flex align-items-center gap-2">
            <h4 class="fw-semibold text-dark mb-0">Estructurar con IA</h4>
            <span class="badge rounded-pill text-bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 small">
              Sprint 3
            </span>
          </div>
          <p class="text-secondary small mb-0 mt-1">
            Detecta y organiza jerárquicamente títulos, listas y tablas mediante inteligencia artificial sin modificar el contenido.
          </p>
        </div>

        <!-- Interruptor apagado por defecto -->
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

      <!-- Contenido desplegado al activar el interruptor -->
      <div v-if="aiForm.enabled" class="pt-4 mt-3 border-top">
        <div class="row g-4 mb-4">
          <!-- Tipo de documento -->
          <div class="col-md-6">
            <label for="ai-document-type" class="form-label fw-semibold">
              Tipo de documento
            </label>
            <select
              id="ai-document-type"
              v-model="aiForm.document_type"
              class="form-select"
            >
              <option value="general">General / Estándar</option>
              <option value="academico">Académico / Científico</option>
              <option value="informe">Informe / Reporte ejecutivo</option>
              <option value="ensayo">Ensayo</option>
              <option value="tesis">Tesis / Trabajo de grado</option>
              <option value="articulo">Artículo</option>
            </select>
            <div class="form-text">
              Contextualiza el análisis de la estructura según el tipo de documento.
            </div>
          </div>

          <!-- Selector de énfasis (ninguno, ligero, medio) -->
          <div class="col-md-6">
            <label class="form-label fw-semibold d-block">
              Selector de énfasis
            </label>
            <div class="btn-group w-100" role="group" aria-label="Selector de énfasis">
              <input
                type="radio"
                class="btn-check"
                name="ai-emphasis"
                id="emphasis-none"
                value="ninguno"
                v-model="aiForm.emphasis"
              />
              <label
                class="btn"
                :class="aiForm.emphasis === 'ninguno' ? 'btn-primary' : 'btn-outline-secondary'"
                for="emphasis-none"
              >
                Ninguno
              </label>

              <input
                type="radio"
                class="btn-check"
                name="ai-emphasis"
                id="emphasis-light"
                value="ligero"
                v-model="aiForm.emphasis"
              />
              <label
                class="btn"
                :class="aiForm.emphasis === 'ligero' ? 'btn-primary' : 'btn-outline-secondary'"
                for="emphasis-light"
              >
                Ligero
              </label>

              <input
                type="radio"
                class="btn-check"
                name="ai-emphasis"
                id="emphasis-medium"
                value="medio"
                v-model="aiForm.emphasis"
              />
              <label
                class="btn"
                :class="aiForm.emphasis === 'medio' ? 'btn-primary' : 'btn-outline-secondary'"
                for="emphasis-medium"
              >
                Medio
              </label>
            </div>
            <div class="form-text">
              Define el grado de ajuste en la jerarquía y formateo de elementos.
            </div>
          </div>
        </div>

        <!-- Casillas para detectar títulos, listas y tablas -->
        <div class="mb-4">
          <label class="form-label fw-semibold mb-2">
            Casillas de detección estructural
          </label>
          <div class="row g-3">
            <!-- Detectar títulos -->
            <div class="col-md-4">
              <div class="form-check p-3 border rounded-3 bg-light-subtle h-100">
                <input
                  id="detect-titles"
                  class="form-check-input ms-0 me-2"
                  type="checkbox"
                  v-model="aiForm.detect_titles"
                />
                <label class="form-check-label fw-medium text-dark" for="detect-titles">
                  Detectar títulos
                </label>
                <div class="small text-secondary mt-1">
                  Reconoce encabezados principales y secundarios (H1, H2, H3).
                </div>
              </div>
            </div>

            <!-- Detectar listas -->
            <div class="col-md-4">
              <div class="form-check p-3 border rounded-3 bg-light-subtle h-100">
                <input
                  id="detect-lists"
                  class="form-check-input ms-0 me-2"
                  type="checkbox"
                  v-model="aiForm.detect_lists"
                />
                <label class="form-check-label fw-medium text-dark" for="detect-lists">
                  Detectar listas
                </label>
                <div class="small text-secondary mt-1">
                  Estructura listas numeradas y viñetas con sangría uniforme.
                </div>
              </div>
            </div>

            <!-- Detectar tablas -->
            <div class="col-md-4">
              <div class="form-check p-3 border rounded-3 bg-light-subtle h-100">
                <input
                  id="detect-tables"
                  class="form-check-input ms-0 me-2"
                  type="checkbox"
                  v-model="aiForm.detect_tables"
                />
                <label class="form-check-label fw-medium text-dark" for="detect-tables">
                  Detectar tablas
                </label>
                <div class="small text-secondary mt-1">
                  Alinea y da formato coherente al contenido en tablas.
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Aviso y casilla obligatoria -->
        <div
          class="alert alert-warning border-warning-subtle d-flex flex-column gap-3 mb-0"
          role="alert"
        >
          <div class="d-flex align-items-start gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-shield-exclamation text-warning flex-shrink-0 mt-1" viewBox="0 0 16 16">
              <path d="M5.338 1.59a61.44 61.44 0 0 0-2.837.856.481.481 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.725 10.725 0 0 0 2.287 2.233c.346.244.652.42.893.533.12.057.218.095.293.118a.55.55 0 0 0 .101.025.615.615 0 0 0 .1-.025c.076-.023.174-.061.294-.118.24-.113.547-.29.893-.533a10.726 10.726 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.775 11.775 0 0 1-2.517 2.453 7.159 7.159 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7.158 7.158 0 0 1-1.048-.625 11.777 11.777 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 62.456 62.456 0 0 1 5.072.56z"/>
              <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
            </svg>
            <div class="text-dark fw-semibold">
              El texto de tu documento se enviará a un proveedor de IA. El contenido no se modifica, solo su estructura
            </div>
          </div>

          <!-- Casilla obligatoria -->
          <div class="form-check pt-2 border-top border-warning-subtle">
            <input
              id="ai-disclaimer"
              class="form-check-input"
              type="checkbox"
              v-model="aiForm.accepted_disclaimer"
              :class="{ 'is-invalid': errors.ai_disclaimer }"
              required
            />
            <label class="form-check-label fw-semibold text-dark cursor-pointer ms-1" for="ai-disclaimer">
              Acepto el procesamiento del documento con el proveedor de IA <span class="text-danger">*</span>
            </label>
            <div v-if="errors.ai_disclaimer" class="invalid-feedback d-block">
              {{ errors.ai_disclaimer }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Action Buttons ─────────────────────────────────────────────────────── -->
    <div class="d-flex justify-content-between align-items-center">
      <button class="btn btn-outline-secondary px-4" @click="cancel">
        Volver
      </button>

      <div class="d-flex gap-2">
        <!-- Reset button -->
        <button
          class="btn btn-outline-secondary px-4"
          :disabled="isSubmitting || !form.preset_id"
          @click="resetToPreset"
          title="Restablecer valores del preset seleccionado"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-arrow-counterclockwise me-1" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M8 3a5 5 0 1 1-4.546 2.914.5.5 0 0 0-.908-.417A6 6 0 1 0 8 2v1z"/>
            <path d="M8 4.466V.534a.25.25 0 0 0-.41-.192L5.23 2.308a.25.25 0 0 0 0 .384l2.36 1.966A.25.25 0 0 0 8 4.466z"/>
          </svg>
          Restablecer
        </button>

        <!-- Apply format button -->
        <button
          id="btn-apply-format"
          class="btn btn-primary btn-lg px-5"
          :disabled="isSubmitting || hasErrors"
          :title="hasErrors ? 'Corrige los errores antes de continuar' : 'Aplicar formato al documento'"
          @click="submitFormatting"
        >
          <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" role="status"></span>
          <span>{{ isSubmitting ? 'Aplicando formato...' : 'Aplicar formato' }}</span>
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.preset-card {
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}
.preset-card:hover {
  border-color: var(--bs-primary) !important;
  box-shadow: 0 0 0 3px rgba(var(--bs-primary-rgb), 0.12);
}
.letter-spacing-1 {
  letter-spacing: 0.05em;
}
.cursor-pointer {
  cursor: pointer;
}
</style>
