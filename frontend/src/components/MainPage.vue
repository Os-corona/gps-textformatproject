<script setup lang="ts">
import { ref } from "vue";

const file = ref<File | null>(null);
const isDragging = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;

  if (input.files?.length) {
    setFile(input.files[0]);
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;

  const droppedFile = event.dataTransfer?.files[0];

  if (droppedFile) {
    setFile(droppedFile);
  }
}

function setFile(selectedFile: File) {
  const maxSize = 10 * 1024 * 1024;

  if (selectedFile.size > maxSize) {
    alert("File is too large. Maximum size is 10MB.");
    return;
  }

  file.value = selectedFile;
}

function formatSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<template>
    <div class = "main">
        <!-- Header/Logotipo -->
        <div class = "mt-3 mb-3 mx-4">
            <p class = "fs-1 fw-semibold mb-1">PrettyDocs</p>
            <p style="font-size: 0.9em;">Formateo profesional de documentos a sólo un par de clicks...</p>
        </div>
        <!-- Contenido principal -->
        <div class = "mx-4 d-flex">
            <!-- Zona de Drag & Drop -->
            <div class = "me-3">
                <div>
                    <label
                        class="d-block text-center bg-white rounded-4 p-5"
                        :class="[
                        'border border-2 border-dashed',
                        isDragging
                            ? 'border-primary bg-primary-subtle'
                            : 'border-secondary-subtle'
                        ]"
                        @dragover.prevent="isDragging = true"
                        @dragleave.prevent="isDragging = false"
                        @drop.prevent="handleDrop"
                    >
                        <!-- Icono -->
                        <div
                            class="d-flex align-items-center justify-content-center
                                    bg-primary-subtle text-primary rounded-circle
                                    mx-auto mb-4"
                            style="width: 70px; height: 70px;"
                        >
                        <span class="fs-2">↑</span>
                        </div>

                        <!-- Texto -->
                        <h4 class="fw-semibold text-dark mb-2">
                        Arrastra tu archivo aquí
                        </h4>

                        <!-- Texto para buscar -->
                        <p class="text-secondary mb-2">
                        o da clic para
                        <span class="text-primary fw-semibold">
                            buscar un archivo
                        </span>
                        </p>

                        <!-- Supported formats -->
                        <p class="text-secondary small mb-0">
                        DOCX | Hasta 10MB
                        </p>

                        <!-- Hidden input -->
                        <input
                        ref="fileInput"
                        type="file"
                        class="d-none"
                        accept=".png,.jpg,.jpeg,.pdf"
                        @change="handleFileSelect"
                        />

                        <!-- Selected file -->
                        <div
                        v-if="file"
                        class="d-flex flex-column gap-1
                                bg-light rounded-3 p-3 mt-4 text-start"
                        >
                        <strong class="text-dark text-truncate">
                            {{ file.name }}
                        </strong>

                        <span class="text-secondary small">
                            {{ formatSize(file.size) }}
                        </span>
                        </div>
                    </label>
                </div>
            </div>
            <div class = "border border-primary-subtle"></div>
        </div>
    </div>
</template>

<style scoped>
.border-dashed {
  border-style: dashed !important;
}

label {
  max-width: 420px;
  margin: 0 auto;
  cursor: pointer;
  transition: all 0.2s ease;
}

label:hover {
  border-color: var(--bs-primary) !important;
  background-color: var(--bs-primary-bg-subtle) !important;
}
</style>