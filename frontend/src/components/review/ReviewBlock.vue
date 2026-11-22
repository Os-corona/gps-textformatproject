<script setup lang="ts">
import { computed } from 'vue'
import RunText from './RunText.vue'
import {
  blockPlainText,
  blockTypeLabel,
  keepKindLabel
} from './reviewUtils'

interface Run {
  text?: string
  bold?: boolean | null
  italic?: boolean | null
  underline?: boolean | null
}

interface TableCell {
  text?: string
  runs?: Run[]
  h_span?: number
}

interface ReviewBlockData {
  id?: string
  type: string
  level?: number
  generated?: boolean
  ordered?: boolean
  is_numbered?: boolean
  runs?: Run[]
  rows?: Array<Array<TableCell | string>>
  header_row?: boolean
  kind?: string
  src?: string[]
  keep_kind?: string
  caption?: string
  text?: string
  image_path?: string
}

const props = withDefaults(
  defineProps<{
    block: ReviewBlockData
    originalBlocks?: ReviewBlockData[]
    reverted?: boolean
    canRevert?: boolean
    tag?: string
  }>(),
  {
    originalBlocks: () => [],
    reverted: false,
    canRevert: false,
    tag: 'div'
  }
)

const emit = defineEmits<{
  (event: 'toggle-revert', block: ReviewBlockData): void
}>()

const headingTag = computed(() => {
  const level = Number(props.block?.level ?? 1)
  if (!Number.isFinite(level) || level <= 1) return 'h1'
  if (level === 2) return 'h2'
  return 'h3'
})

const calloutKind = computed(() => {
  const kind = props.block?.kind
  return kind === 'note' || kind === 'warning' ? kind : 'quote'
})

const keepKind = computed(
  () => props.block?.keep_kind || props.originalBlocks?.[0]?.keep_kind || null
)

const label = computed(() => {
  if (props.block?.type === 'keep') {
    return `Preservado · ${keepKindLabel(keepKind.value)}`
  }
  return blockTypeLabel(props.block)
})

const wrapperStyle = computed(() => {
  if (props.tag !== 'li') return undefined
  const level = Number(props.block?.level ?? 0)
  const safeLevel = Number.isFinite(level) ? Math.min(Math.max(level, 0), 5) : 0
  return { marginLeft: `${safeLevel * 1.25}rem` }
})

function normalizeRows(rows: unknown): TableCell[][] {
  if (!Array.isArray(rows)) return []
  return rows.map((row) => {
    if (!Array.isArray(row)) return []
    return row.map((cell) => {
      if (typeof cell === 'string') return { text: cell }
      return (cell && typeof cell === 'object' ? cell : {}) as TableCell
    })
  })
}

const tableRows = computed(() => normalizeRows(props.block?.rows))
const tableHeader = computed(() => {
  if (props.block?.header_row === false) return null
  return tableRows.value.length > 0 ? tableRows.value[0] : null
})
const tableBody = computed(() =>
  props.block?.header_row === false ? tableRows.value : tableRows.value.slice(1)
)

const originalTable = computed(() =>
  (props.originalBlocks || []).find(
    (block) => Array.isArray(block?.rows) && block.rows.length > 0
  )
)
const originalTableRows = computed(() => normalizeRows(originalTable.value?.rows))
const originalTableHeader = computed(() =>
  originalTableRows.value.length > 0 ? originalTableRows.value[0] : null
)
const originalTableBody = computed(() => originalTableRows.value.slice(1))

const originalText = computed(() => {
  const text = (props.originalBlocks || [])
    .map((block) => blockPlainText(block))
    .filter((value) => typeof value === 'string' && value.length > 0)
    .join('\n')

  return text.length > 0 ? text : 'Contenido original sin texto visible.'
})

const keepIcon = computed(() => {
  switch (keepKind.value) {
    case 'image':
    case 'drawing':
      return '🖼️'
    case 'table':
      return '📊'
    case 'section_break':
      return '➖'
    case 'field':
      return '🔤'
    case 'hyperlink':
      return '🔗'
    case 'footnote':
      return '📎'
    case 'empty':
      return '␣'
    default:
      return '📦'
  }
})

const keepLabel = computed(() => {
  switch (keepKind.value) {
    case 'image':
      return 'Imagen preservada sin cambios'
    case 'table':
      return 'Tabla original preservada'
    case 'section_break':
      return 'Salto de sección preservado'
    case 'empty':
      return 'Espacio en blanco preservado'
    case 'field':
      return 'Campo de Word preservado'
    case 'hyperlink':
      return 'Enlace preservado'
    case 'footnote':
      return 'Nota al pie preservada'
    case 'drawing':
      return 'Dibujo preservado'
    default:
      return `Elemento preservado (${keepKindLabel(keepKind.value)})`
  }
})

const keepText = computed(() => {
  const text = (props.originalBlocks || [])
    .map((block) => {
      if (!block) return ''
      if (typeof block.text === 'string' && block.text.length > 0) return block.text
      if (Array.isArray(block.runs) && block.runs.length > 0) {
        return block.runs.map((run) => run?.text ?? '').join('')
      }
      return ''
    })
    .filter((value) => typeof value === 'string' && value.length > 0)
    .join('\n')
  return text
})
</script>

<template>
  <component
    :is="tag"
    class="doc-block"
    :class="{
      'doc-block--reverted': reverted,
      'doc-block--list-item': tag === 'li'
    }"
    :style="wrapperStyle"
    :data-block-id="block?.id"
    :data-block-type="block?.type"
  >
    <div class="block-meta">
      <span class="block-kind">{{ label }}</span>
      <span
        v-if="block?.generated"
        class="badge rounded-pill generated-badge"
      >
        ✦ Sugerido por IA
      </span>
      <span
        v-if="reverted"
        class="badge rounded-pill bg-warning-subtle text-warning-emphasis border border-warning-subtle"
      >
        Original
      </span>
      <button
        v-if="canRevert"
        type="button"
        class="btn btn-link btn-sm p-0 block-revert-btn"
        :aria-pressed="reverted"
        :data-revert-for="block?.id"
        @click="emit('toggle-revert', block)"
      >
        {{ reverted ? 'Reaplicar IA' : 'Revertir este bloque' }}
      </button>
    </div>

    <!-- Reverted blocks are shown exactly as plain original text. -->
    <p v-if="reverted" class="reverted-original">{{ originalText }}</p>

    <template v-else>
      <component
        :is="headingTag"
        v-if="block.type === 'heading'"
        class="preview-heading"
      >
        <RunText :runs="block.runs" :fallback="block.text" />
      </component>

      <p v-else-if="block.type === 'paragraph'" class="preview-paragraph">
        <RunText :runs="block.runs" :fallback="block.text" />
      </p>

      <template v-else-if="block.type === 'list_item'">
        <RunText :runs="block.runs" :fallback="block.text" />
      </template>

      <div v-else-if="block.type === 'table'" class="table-responsive">
        <table class="table table-sm table-bordered align-middle preview-table">
          <caption class="visually-hidden">Tabla propuesta</caption>
          <thead v-if="tableHeader">
            <tr>
              <th
                v-for="(cell, cellIndex) in tableHeader"
                :key="cellIndex"
                :colspan="cell.h_span && cell.h_span > 1 ? cell.h_span : null"
              >
                <RunText :runs="cell.runs" :fallback="cell.text" />
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in tableBody" :key="rowIndex">
              <td
                v-for="(cell, cellIndex) in row"
                :key="cellIndex"
                :colspan="cell.h_span && cell.h_span > 1 ? cell.h_span : null"
              >
                <RunText :runs="cell.runs" :fallback="cell.text" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <blockquote
        v-else-if="block.type === 'callout'"
        class="blockquote preview-callout"
        :class="`preview-callout--${calloutKind}`"
      >
        <RunText :runs="block.runs" :fallback="block.text" />
      </blockquote>

      <div v-else-if="block.type === 'image'" class="preserved-placeholder">
        <span class="preserved-icon">🖼️</span>
        <span>{{ block.caption || 'Imagen preservada sin cambios' }}</span>
      </div>

      <div v-else-if="block.type === 'keep'" class="preserved-placeholder">
        <template v-if="originalTable">
          <span class="preserved-icon">📊</span>
          <span>{{ keepLabel }}</span>
          <div class="table-responsive w-100">
            <table class="table table-sm table-bordered align-middle preview-table mb-0">
              <caption class="visually-hidden">Tabla original preservada</caption>
              <thead v-if="originalTableHeader">
                <tr>
                  <th
                    v-for="(cell, cellIndex) in originalTableHeader"
                    :key="cellIndex"
                    :colspan="cell.h_span && cell.h_span > 1 ? cell.h_span : null"
                  >
                    <RunText :runs="cell.runs" :fallback="cell.text" />
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in originalTableBody" :key="rowIndex">
                  <td
                    v-for="(cell, cellIndex) in row"
                    :key="cellIndex"
                    :colspan="cell.h_span && cell.h_span > 1 ? cell.h_span : null"
                  >
                    <RunText :runs="cell.runs" :fallback="cell.text" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-else>
          <span class="preserved-icon">{{ keepIcon }}</span>
          <span>{{ keepLabel }}</span>
          <p v-if="keepText" class="preserved-text">{{ keepText }}</p>
        </template>
      </div>

      <p v-else class="preview-paragraph">
        <RunText :runs="block.runs" :fallback="block.text" />
      </p>
    </template>
  </component>
</template>

<style scoped>
.doc-block {
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--bs-border-color-translucent);
  min-width: 0;
}

.doc-block:last-child {
  border-bottom: 0;
}

.doc-block--list-item {
  padding: 0.35rem 0;
  border-bottom: 0;
}

.doc-block--reverted {
  padding: 0.75rem;
  margin: 0.4rem 0;
  border: 1px dashed var(--bs-warning-border-subtle);
  border-left: 0.25rem solid var(--bs-warning);
  border-radius: 0.5rem;
  background: var(--bs-warning-bg-subtle);
}

.block-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.25rem;
}

.block-kind {
  display: inline-block;
  padding: 0.08rem 0.45rem;
  border: 1px solid var(--bs-primary-border-subtle);
  border-radius: 999px;
  background: var(--bs-primary-bg-subtle);
  color: var(--bs-primary-text-emphasis);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.block-revert-btn {
  font-size: 0.75rem;
  text-decoration: none;
}

.generated-badge {
  background: #ede9fe;
  color: #5b21b6;
  border: 1px solid #ddd6fe;
  font-size: 0.66rem;
  font-weight: 600;
}

.preview-heading {
  margin: 0.1rem 0 0.35rem;
  color: var(--doc-primary, var(--bs-body-color));
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

h1.preview-heading {
  font-size: 1.45rem;
  padding-bottom: 0.25rem;
  border-bottom: 2px solid var(--doc-divider, transparent);
}

h2.preview-heading {
  font-size: 1.2rem;
  color: var(--doc-secondary, var(--bs-body-color));
  padding-left: 0.5rem;
  border-left: 3px solid var(--doc-divider, transparent);
}

h3.preview-heading {
  font-size: 1.05rem;
}

.preview-paragraph {
  margin: 0;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.preview-table {
  margin-bottom: 0;
  font-size: 0.88rem;
}

.preview-table th {
  background: var(--doc-header-fill, var(--bs-light));
  color: var(--doc-primary, var(--bs-body-color));
}

.preview-table tbody tr:nth-child(even) td {
  background: var(--doc-zebra-fill, transparent);
}

.preview-callout {
  margin: 0.25rem 0 0;
  padding: 0.7rem 0.9rem;
  border-left: 0.28rem solid var(--doc-primary, var(--bs-primary));
  border-radius: 0.25rem;
  background: var(--doc-callout-fill, var(--bs-primary-bg-subtle));
  font-size: 0.95rem;
  font-style: italic;
  overflow-wrap: anywhere;
}

.preview-callout--note {
  border-left-color: var(--bs-info);
  background: var(--bs-info-bg-subtle);
}

.preview-callout--warning {
  border-left-color: var(--bs-warning);
  background: var(--bs-warning-bg-subtle);
}

.preserved-placeholder {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  padding: 0.7rem 0.9rem;
  border: 1px dashed var(--bs-border-color);
  border-radius: 0.5rem;
  background: var(--bs-light);
  color: var(--bs-secondary-color);
  font-size: 0.9rem;
}

.preserved-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.preserved-text {
  margin: 0;
  white-space: pre-line;
  overflow-wrap: anywhere;
}

.reverted-original {
  margin: 0;
  white-space: pre-line;
  overflow-wrap: anywhere;
  line-height: 1.55;
}
</style>
