/**
 * Helpers shared by the review screen and the structured-block preview.
 *
 * All helpers return plain strings/booleans so the templates can render the
 * backend payload exclusively with Vue interpolation (never with v-html).
 */

const KEEP_KIND_LABELS = {
  image: 'imagen',
  table: 'tabla',
  section_break: 'salto de sección',
  empty: 'espacio en blanco',
  drawing: 'dibujo',
  field: 'campo',
  footnote: 'nota al pie',
  hyperlink: 'enlace',
  track_changes: 'cambios registrados',
  other: 'elemento'
}

export function keepKindLabel(kind) {
  if (!kind) return 'elemento preservado'
  return KEEP_KIND_LABELS[kind] || 'elemento'
}

export function cellPlainText(cell) {
  if (cell == null) return ''
  if (typeof cell === 'string') return cell
  if (typeof cell.text === 'string' && cell.text.length > 0) return cell.text
  if (Array.isArray(cell.runs)) {
    return cell.runs.map((run) => run?.text ?? '').join('')
  }
  return ''
}

export function blockPlainText(block) {
  if (!block || typeof block !== 'object') return ''

  if (typeof block.text === 'string' && block.text.length > 0) return block.text

  if (Array.isArray(block.runs) && block.runs.length > 0) {
    const text = block.runs.map((run) => run?.text ?? '').join('')
    if (text.length > 0) return text
  }

  if (Array.isArray(block.rows) && block.rows.length > 0) {
    return block.rows
      .map((row) => (Array.isArray(row) ? row.map(cellPlainText).join(' | ') : ''))
      .join('\n')
  }

  if (block.type === 'image') return block.caption || 'Imagen preservada sin cambios'
  if (block.type === 'keep') return `Elemento preservado (${keepKindLabel(block.keep_kind)})`

  return ''
}

export function isOrderedList(block) {
  if (!block) return false
  if (typeof block.ordered === 'boolean') return block.ordered
  return block.is_numbered === true
}

export function blockTypeLabel(block) {
  if (!block) return 'Bloque'

  switch (block.type) {
    case 'heading': {
      const level = Number(block.level ?? 1)
      if (!Number.isFinite(level) || level <= 0) return 'Título'
      // The preview intentionally maps H4+ to h3 to keep the h1-h3 hierarchy.
      return `Título H${Math.min(Math.max(level, 1), 3)}`
    }
    case 'paragraph':
      return 'Párrafo'
    case 'list_item':
      return isOrderedList(block) ? 'Lista numerada' : 'Lista'
    case 'table':
      return 'Tabla'
    case 'callout':
      if (block.kind === 'warning') return 'Aviso'
      if (block.kind === 'note') return 'Nota'
      return 'Cita'
    case 'keep':
      return `Preservado · ${keepKindLabel(block.keep_kind)}`
    case 'image':
      return 'Imagen'
    default:
      return typeof block.type === 'string' ? block.type : 'Bloque'
  }
}

export function originalTypeLabel(block) {
  if (!block) return 'Bloque original'

  switch (block.type) {
    case 'heading':
      return 'Título original'
    case 'paragraph':
      return block.hints?.starts_with_glyph ? 'Párrafo con viñeta' : 'Párrafo'
    case 'list_item':
      return 'Elemento de lista'
    case 'table':
      return 'Tabla original'
    case 'keep':
      return `Original · ${keepKindLabel(block.keep_kind)}`
    case 'image':
      return 'Imagen original'
    default:
      return 'Bloque original'
  }
}

export function blockSources(block) {
  if (!block || !Array.isArray(block.src)) return []
  return block.src.filter((id) => typeof id === 'string' && id.length > 0)
}

export function countBoldRuns(blocks) {
  if (!Array.isArray(blocks)) return 0

  const countRuns = (runs) =>
    Array.isArray(runs) ? runs.filter((run) => run && run.bold === true).length : 0

  return blocks.reduce((total, block) => {
    if (!block || typeof block !== 'object') return total

    let count = countRuns(block.runs)

    if (Array.isArray(block.rows)) {
      block.rows.forEach((row) => {
        if (!Array.isArray(row)) return
        row.forEach((cell) => {
          if (cell && typeof cell === 'object') count += countRuns(cell.runs)
        })
      })
    }

    return total + count
  }, 0)
}

export function countBlocksByType(blocks, type) {
  if (!Array.isArray(blocks)) return 0
  return blocks.filter((block) => block && block.type === type).length
}
