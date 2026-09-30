import { ref } from "vue";

export function useFileUpload(maxSizeMB = 10) {
  const file = ref<File | null>(null);
  const isDragging = ref(false);
  const fileInput = ref<HTMLInputElement | null>(null);

  const maxSize = maxSizeMB * 1024 * 1024;

  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) setFile(input.files[0]);
  }

  function handleDrop(event: DragEvent) {
    isDragging.value = false;
    const droppedFile = event.dataTransfer?.files[0];
    if (droppedFile) setFile(droppedFile);
  }

  function setFile(selectedFile: File) {
    if (selectedFile.size > maxSize) {
      alert(`File is too large. Maximum size is ${maxSizeMB}MB.`);
      return;
    }
    file.value = selectedFile;
  }

  function clearFile() {
    file.value = null;
    if (fileInput.value) fileInput.value.value = "";
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return {
    file,
    isDragging,
    fileInput,
    handleFileSelect,
    handleDrop,
    clearFile,
    formatSize,
  };
}