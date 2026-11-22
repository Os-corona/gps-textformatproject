export const DOCUMENT_THEMES = [
  {
    id: 'azul_ejecutivo',
    name: 'Azul Ejecutivo',
    tagline: 'Corporativo clásico',
    primary: '#1F497D',
    secondary: '#2F5496',
    accent: '#B4C6E7',
    headerFill: '#D9E1F2',
    zebraFill: '#F7F9FC',
    calloutFill: '#F2F5F9',
    border: '#BFBFBF'
  },
  {
    id: 'esmeralda',
    name: 'Esmeralda Corporativo',
    tagline: 'Finanzas y estrategia',
    primary: '#0F5132',
    secondary: '#198754',
    accent: '#A3CFBB',
    headerFill: '#D1E7DD',
    zebraFill: '#F4FAF7',
    calloutFill: '#EDF7F2',
    border: '#B8D4C5'
  },
  {
    id: 'borgona',
    name: 'Borgoña Directivo',
    tagline: 'Institucional y jurídico',
    primary: '#6B1D2F',
    secondary: '#8C2D41',
    accent: '#DFB0BA',
    headerFill: '#F2D7DD',
    zebraFill: '#FCF6F7',
    calloutFill: '#FAF0F2',
    border: '#D8B8C0'
  },
  {
    id: 'indigo',
    name: 'Índigo Tecnológico',
    tagline: 'Producto e innovación',
    primary: '#312E81',
    secondary: '#4F46E5',
    accent: '#C7D2FE',
    headerFill: '#E0E7FF',
    zebraFill: '#F6F7FF',
    calloutFill: '#EEF2FF',
    border: '#C4C9E8'
  },
  {
    id: 'grafito',
    name: 'Grafito Minimalista',
    tagline: 'Académico y sobrio',
    primary: '#1F2937',
    secondary: '#4B5563',
    accent: '#CBD5E1',
    headerFill: '#E5E7EB',
    zebraFill: '#F9FAFB',
    calloutFill: '#F3F4F6',
    border: '#9CA3AF'
  }
]

export function getDocumentTheme(themeId) {
  return DOCUMENT_THEMES.find((t) => t.id === themeId) || DOCUMENT_THEMES[0]
}

export function defaultThemeForPreset(presetId) {
  if (presetId === 'apa7') return 'grafito'
  return 'azul_ejecutivo'
}

const PREFS_KEY = 'prettydocs_user_prefs_v1'
const HISTORY_KEY = 'prettydocs_history_v1'

export function loadUserPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) return { defaultTheme: 'azul_ejecutivo', defaultEmphasis: 'ligero', showDividers: true }
    return {
      defaultTheme: 'azul_ejecutivo',
      defaultEmphasis: 'ligero',
      showDividers: true,
      ...JSON.parse(raw)
    }
  } catch {
    return { defaultTheme: 'azul_ejecutivo', defaultEmphasis: 'ligero', showDividers: true }
  }
}

export function saveUserPrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    // ignore storage quota errors
  }
}

export function loadHistoryItems() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function recordHistoryItem(entry) {
  try {
    const current = loadHistoryItems().filter((item) => item.document_id !== entry.document_id)
    const next = [
      {
        ...entry,
        updated_at: entry.updated_at || new Date().toISOString()
      },
      ...current
    ].slice(0, 20)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
    return next
  } catch {
    return []
  }
}
