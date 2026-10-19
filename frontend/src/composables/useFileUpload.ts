import { ref } from 'vue'

const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB

/**
 * Validates a file against the API contract rules:
 *  - Must have .docx extension
 *  - Must not exceed 10 MB
 *
 * Returns null if valid, or a human-readable error string if invalid.
 */
export function validateFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!name.endsWith('.docx')) {
    return 'Solo se permiten archivos .docx.'
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `El archivo supera el límite de 10 MB (${(file.size / 1024 / 1024).toFixed(1)} MB).`
  }
  return null
}

export function useFileUpload() {
  const file = ref<File | null>(null)
  const fileError = ref<string | null>(null)
  const isDragging = ref(false)
  const fileInput = ref<HTMLInputElement | null>(null)

  function setFile(selected: File) {
    const err = validateFile(selected)
    if (err) {
      fileError.value = err
      file.value = null
      return
    }
    fileError.value = null
    file.value = selected
  }

  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement
    if (input.files?.length) setFile(input.files[0])
    // Reset input so the same file can be re-selected after clearing
    input.value = ''
  }

  function handleDrop(event: DragEvent) {
    isDragging.value = false
    const dropped = event.dataTransfer?.files[0]
    if (dropped) setFile(dropped)
  }

  function clearFile() {
    file.value = null
    fileError.value = null
    if (fileInput.value) fileInput.value.value = ''
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  return {
    file,
    fileError,
    isDragging,
    fileInput,
    handleFileSelect,
    handleDrop,
    clearFile,
    formatSize,
  }
}