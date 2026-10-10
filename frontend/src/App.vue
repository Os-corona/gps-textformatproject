<script setup lang="ts">
import { ref } from "vue";
import Sidebar from "@/components/Sidebar.vue";
import FileDropzone from "@/components/FileDropzone.vue";
import HistoryView from "@/views/HistoryView.vue";
import SettingsView from "@/views/SettingsView.vue";
import type { ViewKey } from "@/types";

const activeView = ref<ViewKey>("format");
const sidebarExpanded = ref(true);
</script>

<template>
  <div class="d-flex vh-100 bg-light">
    <Sidebar
      :active="activeView"
      :expanded="sidebarExpanded"
      @update:active="activeView = $event"
      @toggle="sidebarExpanded = !sidebarExpanded"
    />

    <main class="flex-grow-1 overflow-auto">
      <!-- Header -->
      <div class="mt-3 mb-3 mx-4">
        <p class="fs-1 fw-semibold mb-1">PrettyDocs</p>
        <p style="font-size: 0.9em">
          Formateo profesional de documentos a sólo un par de clicks...
        </p>
      </div>

      <!-- Contenido -->
      <div class="mx-4 pb-5">
        <FileDropzone v-if="activeView === 'format'" />
        <HistoryView v-else-if="activeView === 'history'" />
        <SettingsView v-else-if="activeView === 'settings'" />
      </div>
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
}
</style>