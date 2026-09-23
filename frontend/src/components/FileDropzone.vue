<script setup lang="ts">
import { useFileUpload } from "@/composables/useFileUpload";

const {
  file,
  isDragging,
  fileInput,
  handleFileSelect,
  handleDrop,
  clearFile,
  formatSize,
} = useFileUpload(10);

defineExpose({ file, clearFile });
</script>

<template>
  <label
    class="d-block text-center bg-white rounded-4 p-5 w-100 dropzone"
    :class="[
      'border border-2 border-dashed',
      isDragging
        ? 'border-primary bg-primary-subtle'
        : 'border-secondary-subtle',
    ]"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
  >
    <div
      class="d-flex align-items-center justify-content-center bg-primary-subtle text-primary rounded-circle mx-auto mb-4"
      style="width: 70px; height: 70px"
    >
      <span class="fs-2">↑</span>
    </div>

    <h4 class="fw-semibold text-dark mb-2">Arrastra tu archivo aquí</h4>

    <p class="text-secondary mb-2">
      o da clic para
      <span class="text-primary fw-semibold">buscar un archivo</span>
    </p>

    <p class="text-secondary small mb-0">DOCX | Hasta 10MB</p>

    <input
      ref="fileInput"
      type="file"
      class="d-none"
      accept=".docx,.doc"
      @change="handleFileSelect"
    />

    <div
      v-if="file"
      class="d-flex align-items-center justify-content-between gap-2 bg-light rounded-3 p-3 mt-4 text-start"
    >
      <div class="d-flex flex-column text-truncate">
        <strong class="text-dark text-truncate">{{ file.name }}</strong>
        <span class="text-secondary small">{{ formatSize(file.size) }}</span>
      </div>
      <button
        type="button"
        class="btn btn-sm btn-outline-danger"
        @click.prevent.stop="clearFile"
      >
        ✕
      </button>
    </div>
  </label>
</template>

<style scoped>
.border-dashed {
  border-style: dashed !important;
}
.dropzone {
  max-width: 420px;
  margin: 0 auto;
  cursor: pointer;
  transition: all 0.2s ease;
}
.dropzone:hover {
  border-color: var(--bs-primary) !important;
  background-color: var(--bs-primary-bg-subtle) !important;
}
</style>