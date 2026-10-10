<script setup lang="ts">
import { ref } from "vue";
import type { HistoryItem } from "@/types";

const history = ref<HistoryItem[]>([
  {
    id: "1",
    fileName: "propuesta-acme.docx",
    topic: "Propuesta comercial Acme",
    preset: "corporate",
    date: "2025-01-14 10:32",
    size: 245_760,
  },
  {
    id: "2",
    fileName: "informe-q4.docx",
    topic: "Informe trimestral Q4",
    preset: "editorial",
    date: "2025-01-12 18:05",
    size: 512_000,
  },
]);

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<template>
  <div>
    <h2 class="fw-semibold mb-1">Historial</h2>
    <p class="text-secondary mb-4">Documentos procesados recientemente.</p>

    <div v-if="history.length === 0" class="text-center py-5 text-secondary">
      <div class="fs-1 mb-2">📭</div>
      <p>Aún no has formateado ningún documento.</p>
    </div>

    <div v-else class="d-flex flex-column gap-2">
      <div
        v-for="item in history"
        :key="item.id"
        class="card border-0 shadow-sm"
      >
        <div class="card-body d-flex flex-wrap align-items-center gap-3">
          <div class="fs-3">📄</div>
          <div class="flex-grow-1">
            <div class="fw-semibold">{{ item.topic }}</div>
            <div class="text-secondary small">
              {{ item.fileName }} · {{ formatSize(item.size) }} ·
              {{ item.date }}
            </div>
          </div>
          <span class="badge text-bg-light text-capitalize">
            {{ item.preset }}
          </span>
          <div class="d-flex gap-2">
            <button class="btn btn-sm btn-outline-primary">Descargar</button>
            <button class="btn btn-sm btn-outline-secondary">Reprocesar</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
